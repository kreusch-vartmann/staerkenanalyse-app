"""
Hauptanwendung für das Stärkenanalyse-Tool.
"""
import os
import io
import json
from datetime import datetime, UTC

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify, session)
from flask import Response
from werkzeug.utils import secure_filename

import database as db
import pandas as pd
from ki_services import generate_report_with_ai
from utils import get_file_content, clean_json_response

app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_prompt_list():
    try:
        prompts_dir = os.path.join(app.root_path, 'prompts')
        if os.path.isdir(prompts_dir):
            return [f for f in os.listdir(prompts_dir) if f.endswith('.txt')]
        return []
    except FileNotFoundError:
        return []

@app.teardown_appcontext
def close_connection(_exception):
    db.close_db()

@app.context_processor
def inject_now():
    return {'current_year': datetime.now(UTC).year}

@app.template_filter('datetimeformat')
def datetimeformat(value, fmt='%d.%m.%Y'):
    if not value: return ""
    if isinstance(value, datetime): return value.strftime(fmt)
    if isinstance(value, str):
        try:
            dt = datetime.strptime(value, '%Y-%m-%d')
            return dt.strftime(fmt)
        except ValueError:
            try:
                dt = datetime.strptime(value, '%d.%m.%Y')
                return dt.strftime(fmt)
            except ValueError:
                return value
    return value

@app.route('/')
def dashboard():
    breadcrumbs = [{"text": "Dashboard"}]
    return render_template('dashboard.html', breadcrumbs=breadcrumbs)

@app.route('/groups')
def manage_groups():
    page = request.args.get('page', 1, type=int)
    pagination, groups = db.get_paginated_groups(page)
    breadcrumbs = [{"link": url_for('dashboard'), "text": "Dashboard"}, {"text": "Gruppen"}]
    return render_template('manage_groups.html', groups=groups, pagination=pagination, breadcrumbs=breadcrumbs)

@app.route('/participants')
def manage_participants():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')
    sort_order = request.args.get('sort', 'name_asc')
    pagination, participants = db.get_paginated_participants(page, search_query, sort_order)
    breadcrumbs = [{"link": url_for('dashboard'), "text": "Dashboard"}, {"text": "Teilnehmer"}]
    return render_template('manage_participants.html', participants=participants, pagination=pagination, breadcrumbs=breadcrumbs)

@app.route('/group/<int:group_id>/participants')
def show_group_participants(group_id):
    group = db.get_group_by_id(group_id)
    participants = db.get_participants_by_group(group_id)
    breadcrumbs = [{"link": url_for('dashboard'), "text": "Dashboard"}, {"link": url_for('manage_groups'), "text": "Gruppen"}, {"text": group['name']}]
    return render_template('participants.html', group=group, participants=participants, breadcrumbs=breadcrumbs)

@app.route('/group/add', methods=['POST'])
def add_group():
    details = {k: request.form.get(k) for k in ['name', 'date', 'location', 'leitung', 'beobachter1', 'beobachter2']}
    db.add_group(**details)
    flash(f'Gruppe "{details["name"]}" wurde erfolgreich hinzugefügt.', 'success')
    return redirect(url_for('manage_groups'))

@app.route('/group/edit/<int:group_id>', methods=['POST'])
def edit_group(group_id):
    details = {
        'name': request.form.get('group_name'), 'date': request.form.get('group_date'),
        'location': request.form.get('group_location'), 'leitung': request.form.get('group_leitung'),
        'beobachter1': request.form.get('beobachter1'), 'beobachter2': request.form.get('beobachter2')
    }
    db.update_group_details(group_id, details)
    flash('Gruppe erfolgreich aktualisiert.', 'success')
    return redirect(url_for('manage_groups'))

@app.route('/group/delete/<int:group_id>', methods=['POST'])
def delete_group(group_id):
    db.delete_group_by_id(group_id)
    flash('Gruppe und alle zugehörigen Teilnehmer wurden gelöscht.', 'success')
    return redirect(url_for('manage_groups'))

@app.route('/group/<int:group_id>/participant/add', methods=['POST'])
def add_participant(group_id):
    names_input = request.form.get('participant_names', '')
    valid_names = [name.strip() for name in names_input.splitlines() if name.strip()]
    if valid_names:
        count = db.add_multiple_participants_to_group(group_id, valid_names)
        flash(f'{count} Teilnehmer wurden hinzugefügt.', 'success')
    else:
        flash('Keine gültigen Namen eingegeben.', 'warning')
    return redirect(url_for('show_group_participants', group_id=group_id))

@app.route('/participant/edit/<int:participant_id>', methods=['POST'])
def edit_participant(participant_id):
    new_name, group_id = request.form['new_name'], request.form['group_id']
    if new_name:
        db.update_participant_name(participant_id, new_name)
        flash('Teilnehmername wurde aktualisiert.', 'success')
    return redirect(url_for('show_group_participants', group_id=group_id))

@app.route('/participant/delete/<int:participant_id>', methods=['POST'])
def delete_participant(participant_id):
    group_id = request.form['group_id']
    db.delete_participant_by_id(participant_id)
    flash('Teilnehmer wurde gelöscht.', 'success')
    return redirect(url_for('show_group_participants', group_id=group_id))

@app.route('/participant/<int:participant_id>/data_entry')
def show_data_entry(participant_id):
    participant = db.get_participant_by_id(participant_id)
    if participant:
        group = db.get_group_by_id(participant['group_id'])
        breadcrumbs = [{"link": url_for('dashboard'), "text": "Dashboard"}, {"link": url_for('manage_groups'), "text": "Gruppen"}, {"link": url_for('show_group_participants', group_id=group['id']), "text": group['name']}, {"text": f"Dateneingabe: {participant['name']}"}]
        return render_template('data_entry.html', participant=participant, group=group, breadcrumbs=breadcrumbs, prompts=get_prompt_list())
    flash("Teilnehmer nicht gefunden.", "error")
    return redirect(url_for('manage_participants'))

@app.route('/participant/<int:participant_id>/report')
def show_report(participant_id):
    participant = db.get_participant_by_id(participant_id)
    if not participant:
        flash("Teilnehmer nicht gefunden.", "error")
        return redirect(url_for('manage_participants'))

    group = db.get_group_by_id(participant['group_id'])

    # Den Vornamen direkt zum participant-Objekt hinzufügen
    full_name = participant.get('name', '')
    participant['first_name'] = full_name.split(' ')[0] if full_name else ''
    
    # Aktuelle Daten für den Footer automatisch ermitteln
    current_location_for_footer = "Lingen (Ems)"
    current_date_for_footer = datetime.now().strftime('%d.%m.%Y')

    breadcrumbs = [{"link": url_for('dashboard'), "text": "Dashboard"}, 
                   {"link": url_for('manage_groups'), "text": "Gruppen"}, 
                   {"link": url_for('show_group_participants', group_id=group['id']), "text": group['name']}, 
                   {"text": f"Bericht: {participant['name']}"}]
    
    return render_template('staerkenanalyse_bericht_vorlage3.html', 
                           participant=participant, 
                           group=group, 
                           breadcrumbs=breadcrumbs,
                           current_date=current_date_for_footer,
                           current_location=current_location_for_footer)

@app.route('/entry')
def data_entry_rework():
    groups = db.get_all_groups()
    breadcrumbs = [{"link": url_for('dashboard'), "text": "Dashboard"}, {"text": "Dateneingabe"}]
    return render_template('data_entry_rework.html', groups=groups, breadcrumbs=breadcrumbs)

@app.route('/ai_analysis/select_group')
def ai_analysis_select_group():
    groups = db.get_all_groups()
    breadcrumbs = [{"link": url_for('dashboard'), "text": "Dashboard"}, {"text": "KI-Analyse"}]
    return render_template('ai_analysis_select_group.html', groups=groups, breadcrumbs=breadcrumbs)

@app.route('/ai_analysis/group/<int:group_id>')
def ai_analysis_select_participants(group_id):
    group = db.get_group_by_id(group_id)
    participants = db.get_participants_by_group(group_id)
    breadcrumbs = [{"link": url_for('dashboard'), "text": "Dashboard"}, {"link": url_for('ai_analysis_select_group'), "text": "KI-Analyse"}, {"text": f"Auswahl für: {group['name']}"}]
    return render_template('ai_analysis_select_participants.html', group=group, participants=participants, breadcrumbs=breadcrumbs)

@app.route('/ai_analysis/configure', methods=['POST'])
def configure_batch_ai_analysis():
    participant_ids = request.form.getlist('participant_ids')
    if not participant_ids:
        flash("Keine Teilnehmer ausgewählt.", "warning")
        return redirect(url_for('ai_analysis_select_group'))
    
    participants = [db.get_participant_by_id(pid) for pid in participant_ids]
    group = db.get_group_by_id(participants[0]['group_id']) if participants else None
    breadcrumbs = [{"link": url_for('dashboard'), "text": "Dashboard"}, {"link": url_for('ai_analysis_select_group'), "text": "KI-Analyse"}, {"link": url_for('ai_analysis_select_participants', group_id=group['id']), "text": f"Auswahl für: {group['name']}"}, {"text": "Analyse konfigurieren"}]
    
    return render_template('run_batch_ai.html', participants=participants, group=group, prompts=get_prompt_list(), breadcrumbs=breadcrumbs)

@app.route('/ai_analysis/execute', methods=['POST'])
def execute_batch_ai_analysis():
    participant_ids = request.form.getlist('participant_ids')
    
    # KORREKTUR: Die fehleranfällige Session-Logik wird entfernt.
    # Die Daten werden stattdessen direkt an die Status-Seite übergeben.
    analysis_data = {
        'prompt_template': request.form.get('ki_prompt', ''),
        'ki_model': request.form.get('ki_model', 'mistral'),
        'additional_content': "\n\n---\n\n".join(
            [get_file_content(file) for file in request.files.getlist('additional_files') if file and file.filename != '']
        )
    }
    
    participants = [db.get_participant_by_id(pid) for pid in participant_ids]
    group = db.get_group_by_id(participants[0]['group_id']) if participants else None

    breadcrumbs = [{"link": url_for('dashboard'), "text": "Dashboard"}, {"link": url_for('ai_analysis_select_group'), "text": "KI-Analyse"}, {"text": "Analyse-Status"}]
    
    # Die Status-Seite wird direkt gerendert, um den TypeError zu vermeiden.
    return render_template(
        'ai_analysis_status.html',
        participants=participants,
        group=group,
        analysis_data=analysis_data,
        breadcrumbs=breadcrumbs
    )
@app.route('/export/selection')
def export_selection():
    """Zeigt die Seite zur Auswahl der zu exportierenden Daten an."""
    groups = db.get_all_groups()
    groups_with_participants = []
    for group in groups:
        participants = db.get_participants_by_group(group['id'])
        groups_with_participants.append({
            'id': group['id'],
            'name': group['name'],
            'participants': participants
        })
    
    breadcrumbs = [{"link": url_for('dashboard'), "text": "Dashboard"}, {"text": "Datenexport"}]
    return render_template('export_selection.html', 
                           groups_with_participants=groups_with_participants, 
                           breadcrumbs=breadcrumbs)

@app.route('/export/data', methods=['POST'])
def export_data():
    """Verarbeitet die Auswahl und generiert die Export-Datei (XLSX oder CSV)."""
    participant_ids = request.form.getlist('participant_ids')
    export_format = request.form.get('format', 'xlsx') # Standard ist xlsx

    if not participant_ids:
        flash("Keine Teilnehmer für den Export ausgewählt.", "warning")
        return redirect(url_for('export_selection'))

    selected_participants = [db.get_participant_by_id(pid) for pid in participant_ids]
    
    # --- KORREKTUR HIER ---
    # Wir wandeln jedes 'group' (ein sqlite3.Row-Objekt) in ein echtes dict() um.
    all_groups = {group['id']: dict(group) for group in db.get_all_groups()}
    
    records = []
    for p in selected_participants:
        if not p: continue
        group_info = all_groups.get(p.get('group_id'), {})
        record = {
            'Teilnehmer ID': p.get('id'),
            'Name': p.get('name'),
            'Gruppe': group_info.get('name'), # Diese Zeile funktioniert jetzt, da group_info ein dict ist
            'Beobachtung (Sozial)': p.get('observations', {}).get('social', ''),
            'Beobachtung (Verbal)': p.get('observations', {}).get('verbal', ''),
            'SK - Flexibilität': p.get('sk_ratings', {}).get('flexibility'),
            'SK - Teamorientierung': p.get('sk_ratings', {}).get('team_orientation'),
            'SK - Prozessorientierung': p.get('sk_ratings', {}).get('process_orientation'),
            'SK - Ergebnisorientierung': p.get('sk_ratings', {}).get('results_orientation'),
            'VK - Flexibilität': p.get('vk_ratings', {}).get('flexibility'),
            'VK - Beratung': p.get('vk_ratings', {}).get('consulting'),
            'VK - Sachlichkeit': p.get('vk_ratings', {}).get('objectivity'),
            'VK - Zielorientierung': p.get('vk_ratings', {}).get('goal_orientation'),
            'KI-Text (Sozial)': p.get('ki_texts', {}).get('social_text', ''),
            'KI-Text (Verbal)': p.get('ki_texts', {}).get('verbal_text', ''),
            'KI-Text (Zusammenfassung)': p.get('ki_texts', {}).get('summary_text', ''),
        }
        records.append(record)
    
    if not records:
        flash("Konnte Daten für die ausgewählten Teilnehmer nicht laden.", "error")
        return redirect(url_for('export_selection'))

    df = pd.DataFrame(records)
    output = io.BytesIO()
    filename = f"staerkenanalyse_export_{datetime.now().strftime('%Y-%m-%d')}"

    if export_format == 'xlsx':
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Export')
            worksheet = writer.sheets['Export']
            for idx, col in enumerate(df):
                max_len = max((df[col].astype(str).map(len).max(), len(str(df[col].name)))) + 2
                worksheet.set_column(idx, idx, max_len if max_len < 100 else 100)
        
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename += ".xlsx"
    
    elif export_format == 'csv':
        df.to_csv(output, index=False, encoding='utf-8-sig')
        mimetype = "text/csv"
        filename += ".csv"
        
    else:
        flash("Ungültiges Exportformat ausgewählt.", "error")
        return redirect(url_for('export_selection'))

    output.seek(0)

    return Response(
        output,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
    
@app.route('/api/group/<int:group_id>/participants')
def get_participants_for_group(group_id):
    return jsonify([dict(p) for p in db.get_participants_by_group(group_id)])

@app.route('/api/participant/<int:participant_id>/observations')
def get_participant_observations(participant_id):
    p = db.get_participant_by_id(participant_id)
    return jsonify(p.get('observations', {'social': '', 'verbal': ''}))

@app.route('/save_observations/<int:participant_id>', methods=['POST'])
def save_observations(participant_id):
    data = request.get_json()
    if data and 'social' in data:
        db.save_participant_data(participant_id, {'observations': data})
        return jsonify({"status": "success", "message": "Beobachtungen gespeichert!"})
    return jsonify({"status": "error", "message": "Ungültige Daten."}), 400

@app.route('/save_report/<int:participant_id>', methods=['POST'])
def save_report(participant_id):
    data = request.get_json()
    db.save_participant_data(participant_id, {
        'sk_ratings': data.get('sk_ratings'),
        'vk_ratings': data.get('vk_ratings'),
        'ki_texts': data.get('ki_texts')
    })
    # Speichert die editierbaren Header- und Footer-Daten
    db.save_report_details(participant_id, data.get('group_details'), data.get('footer_data'))
    return jsonify({"status": "success", "message": "Bericht erfolgreich gespeichert!"})

@app.route('/run_ki_analysis/<int:participant_id>', methods=['POST'])
def run_ki_analysis(participant_id):
    participant = db.get_participant_by_id(participant_id)
    final_prompt = request.form.get('ki_prompt', '')
    ki_model = request.form.get('ki_model', 'mistral')

    full_name = participant.get('name', '')
    first_name = full_name.split(' ')[0] if full_name else ''
    final_prompt = final_prompt.replace('{{name}}', first_name).replace('{{vorname}}', first_name).replace('{{first_name}}', first_name).replace('{{ganzer_name}}', full_name)

    # Lädt Beobachtungen direkt und frisch aus der Datenbank, um Verwechslungen zu vermeiden
    observations = participant.get('observations', {})
    social_obs = observations.get('social', '')
    verbal_obs = observations.get('verbal', '')
    final_prompt = final_prompt.replace('{{social_observations}}', social_obs).replace('{{verbal_observations}}', verbal_obs)

    additional_content = ""
    if 'additional_files' in request.files:
        file = request.files.get('additional_files')
        if file and file.filename != '':
            additional_content = get_file_content(file)
    final_prompt = final_prompt.replace('{{additional_content}}', additional_content)

    ki_response_str = generate_report_with_ai(final_prompt, ki_model)
    db.save_ki_raw_response(participant_id, ki_response_str)

    try:
        ki_data = json.loads(clean_json_response(ki_response_str))
        if "error" in ki_data:
            return jsonify({"status": "error", "message": f"KI-Fehler: {ki_data['error']}"})
        
        db.save_participant_data(participant_id, {
            'sk_ratings': ki_data.get('sk_ratings', {}),
            'vk_ratings': ki_data.get('vk_ratings', {}),
            'ki_texts': ki_data.get('ki_texts', {})
        })
        return jsonify({
            "status": "success",
            "message": "KI-Analyse erfolgreich. Bericht wird geladen...",
            "redirect_url": url_for('show_report', participant_id=participant_id)
        })
    except json.JSONDecodeError as e:
        return jsonify({"status": "error", "message": f"Fehler beim Verarbeiten der KI-Antwort: {e}", "raw_response": ki_response_str})

@app.route('/api/run_single_analysis/<int:participant_id>', methods=['POST'])
def run_single_analysis_api(participant_id):
    data = request.get_json()
    participant = db.get_participant_by_id(participant_id)
    if not participant:
        return jsonify({"status": "error", "message": "Teilnehmer nicht gefunden."}), 404

    full_name = participant.get('name', '')
    first_name = full_name.split(' ')[0] if full_name else ''
    obs = participant.get('observations', {})
    
    # --- FINALE KORREKTUR: Unmissverständlichen Kontext-Block erstellen ---
    # Dieser "Steckbrief" macht es der KI unmöglich, die Person zu verwechseln.
    context_block = (
        f"ANALYSE-SUBJEKT:\n"
        f"- Vorname: {first_name}\n"
        f"- Ganzer Name: {full_name}\n\n"
        f"BEOBACHTUNGEN ZUM VERHALTEN DES ANALYSE-SUBJEKTS:\n"
        f"- Soziale Kompetenzen: {obs.get('social', '')}\n"
        f"- Verbale Kompetenzen: {obs.get('verbal', '')}\n\n"
        f"ZUSÄTZLICHER KONTEXT:\n"
        f"{data.get('additional_content', '')}"
    )
    
    prompt = data.get('prompt_template', '')
    # Der gesamte Kontext wird jetzt in den neuen Platzhalter {{context}} eingesetzt.
    prompt = prompt.replace('{{context}}', context_block)
    # Alte Platzhalter werden sicherheitshalber auch ersetzt, falls sie noch im Prompt sind.
    prompt = prompt.replace('{{name}}', first_name).replace('{{vorname}}', first_name).replace('{{first_name}}', first_name).replace('{{ganzer_name}}', full_name)
    prompt = prompt.replace('{{social_observations}}', obs.get('social', '')).replace('{{verbal_observations}}', obs.get('verbal', ''))
    prompt = prompt.replace('{{additional_content}}', data.get('additional_content', ''))


    response_str = generate_report_with_ai(prompt, data.get('ki_model'))
    db.save_ki_raw_response(participant_id, response_str)

    try:
        ki_data = json.loads(clean_json_response(response_str))
        if "error" in ki_data:
            return jsonify({"status": "error", "message": f"KI-Fehler: {ki_data['error']}"})
        
        db.save_participant_data(participant_id, {
            'sk_ratings': ki_data.get('sk_ratings', {}),
            'vk_ratings': ki_data.get('vk_ratings', {}),
            'ki_texts': ki_data.get('ki_texts', {})
        })
        return jsonify({"status": "success", "message": "Analyse erfolgreich."})
    except json.JSONDecodeError as e:
        return jsonify({"status": "error", "message": f"Formatfehler: {e}", "raw_response": response_str})
    
@app.route('/prompts/<path:filename>')
def get_prompt_content(filename):
    prompts_dir = os.path.join(app.root_path, 'prompts')
    safe_path = os.path.normpath(os.path.join(prompts_dir, secure_filename(filename)))
    if not safe_path.startswith(os.path.normpath(prompts_dir)):
        return jsonify({"error": "Ungültiger Pfad"}), 400
    try:
        with open(safe_path, 'r', encoding='utf-8') as f:
            return jsonify({'content': f.read()})
    except FileNotFoundError:
        return jsonify({'error': 'Datei nicht gefunden.'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/info')
def info():
    breadcrumbs = [{"link": url_for('dashboard'), "text": "Dashboard"}, {"text": "Info"}]
    return render_template('info.html', breadcrumbs=breadcrumbs)

if __name__ == '__main__':
    app.run(port=5001, debug=True)