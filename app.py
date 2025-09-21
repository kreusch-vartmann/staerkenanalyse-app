"""
Hauptanwendung für das Stärkenanalyse-Tool.

Diese Datei enthält alle Routen und die Kernlogik der Flask-Webanwendung,
einschließlich der Verwaltung von Gruppen, Teilnehmern und der Ausführung
von KI-Analysen.
"""
import os
import json
from datetime import datetime, UTC

from flask import (Flask, render_template, request, redirect, url_for,
                   flash, jsonify)
from werkzeug.utils import secure_filename

# Lokale Module importieren
import database as db
from ki_services import generate_report_with_ai
from utils import get_file_content, clean_json_response

app = Flask(__name__)
app.secret_key = os.urandom(24)


def get_prompt_list():
    """Gibt eine Liste der verfügbaren Prompt-Dateinamen zurück."""
    try:
        prompts_dir = os.path.join(app.root_path, 'prompts')
        if os.path.isdir(prompts_dir):
            return [f for f in os.listdir(prompts_dir) if f.endswith('.txt')]
        return []
    except FileNotFoundError:
        return []

# --- App-Kontext und Filter ---


@app.teardown_appcontext
def close_connection(_exception):
    """Schließt die Datenbankverbindung am Ende jedes Requests."""
    db.close_db()


@app.context_processor
def inject_now():
    """Stellt das aktuelle Jahr für den Footer bereit."""
    return {'current_year': datetime.now(UTC).year}


@app.template_filter('datetimeformat')
def datetimeformat(value, fmt='%d.%m.%Y'):
    """Ein robuster Filter, um Datumsangaben im Template zu formatieren."""
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, str):
        try:
            # Versucht zuerst das ISO-Format zu parsen
            dt_object = datetime.strptime(value, '%Y-%m-%d')
            return dt_object.strftime(fmt)
        except ValueError:
            try:
                # Fallback auf das deutsche Datumsformat
                dt_object = datetime.strptime(value, '%d.%m.%Y')
                return dt_object.strftime(fmt)
            except ValueError:
                # Wenn beides fehlschlägt, den Originalstring zurückgeben
                return value
    return value

# --- Dashboard & Hauptseiten ---


@app.route('/')
def dashboard():
    """Zeigt das Haupt-Dashboard an."""
    breadcrumbs = [{"text": "Dashboard"}]
    return render_template('dashboard.html', breadcrumbs=breadcrumbs)


@app.route('/groups')
def manage_groups():
    """Zeigt die Seite zur Verwaltung von Gruppen an."""
    page = request.args.get('page', 1, type=int)
    pagination, groups = db.get_paginated_groups(page)
    breadcrumbs = [
        {"link": url_for('dashboard'), "text": "Dashboard"},
        {"text": "Gruppen"}
    ]
    return render_template(
        'manage_groups.html',
        groups=groups,
        pagination=pagination,
        breadcrumbs=breadcrumbs
    )


@app.route('/participants')
def manage_participants():
    """Zeigt eine durchsuch- und sortierbare Liste aller Teilnehmer."""
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')
    sort_order = request.args.get('sort', 'name_asc')

    pagination, participants = db.get_paginated_participants(
        page, search_query, sort_order
    )

    breadcrumbs = [
        {"link": url_for('dashboard'), "text": "Dashboard"},
        {"text": "Teilnehmer"}
    ]
    return render_template(
        'manage_participants.html',
        participants=participants,
        pagination=pagination,
        breadcrumbs=breadcrumbs
    )


@app.route('/group/<int:group_id>/participants')
def show_group_participants(group_id):
    """Zeigt die Teilnehmer einer bestimmten Gruppe an."""
    group = db.get_group_by_id(group_id)
    participants = db.get_participants_by_group(group_id)
    breadcrumbs = [
        {"link": url_for('dashboard'), "text": "Dashboard"},
        {"link": url_for('manage_groups'), "text": "Gruppen"},
        {"text": group['name']}
    ]
    return render_template(
        'participants.html',
        group=group,
        participants=participants,
        breadcrumbs=breadcrumbs
    )

# --- CRUD-Operationen für Gruppen ---


@app.route('/group/add', methods=['POST'])
def add_group():
    """Fügt eine neue Gruppe hinzu."""
    name = request.form['name']
    date = request.form.get('date')
    location = request.form.get('location')
    leitung = request.form.get('leitung')
    beobachter1 = request.form.get('beobachter1')
    beobachter2 = request.form.get('beobachter2')
    db.add_group(name, date, location, leitung, beobachter1, beobachter2)
    flash(f'Gruppe "{name}" wurde erfolgreich hinzugefügt.', 'success')
    return redirect(url_for('manage_groups'))


@app.route('/group/edit/<int:group_id>', methods=['POST'])
def edit_group(group_id):
    """Bearbeitet eine bestehende Gruppe."""
    details = {
        'name': request.form.get('group_name'),
        'date': request.form.get('group_date'),
        'location': request.form.get('group_location'),
        'leitung': request.form.get('group_leitung'),
        'beobachter1': request.form.get('beobachter1'),
        'beobachter2': request.form.get('beobachter2')
    }
    db.update_group_details(group_id, details)
    flash('Gruppe erfolgreich aktualisiert.', 'success')
    return redirect(url_for('manage_groups'))


@app.route('/group/delete/<int:group_id>', methods=['POST'])
def delete_group(group_id):
    """Löscht eine Gruppe und alle zugehörigen Teilnehmer."""
    db.delete_group_by_id(group_id)
    flash('Gruppe und alle zugehörigen Teilnehmer wurden gelöscht.', 'success')
    return redirect(url_for('manage_groups'))

# --- CRUD-Operationen für Teilnehmer ---


@app.route('/group/<int:group_id>/participant/add', methods=['POST'])
def add_participant(group_id):
    """Fügt einen neuen Teilnehmer zu einer Gruppe hinzu."""
    name = request.form['participant_name']
    if name:
        db.add_participant_to_group(group_id, name)
        flash(f'Teilnehmer "{name}" wurde hinzugefügt.', 'success')
    return redirect(url_for('show_group_participants', group_id=group_id))


@app.route('/participant/edit/<int:participant_id>', methods=['POST'])
def edit_participant(participant_id):
    """Bearbeitet den Namen eines Teilnehmers."""
    new_name = request.form['new_name']
    group_id = request.form['group_id']
    if new_name:
        db.update_participant_name(participant_id, new_name)
        flash('Teilnehmername wurde aktualisiert.', 'success')
    return redirect(url_for('show_group_participants', group_id=group_id))


@app.route('/participant/delete/<int:participant_id>', methods=['POST'])
def delete_participant(participant_id):
    """Löscht einen Teilnehmer."""
    group_id = request.form['group_id']
    db.delete_participant_by_id(participant_id)
    flash('Teilnehmer wurde gelöscht.', 'success')
    return redirect(url_for('show_group_participants', group_id=group_id))

# --- Dateneingabe und Berichtsseiten ---


@app.route('/participant/<int:participant_id>/data_entry')
def show_data_entry(participant_id):
    """Zeigt die Seite zur Dateneingabe für einen Teilnehmer an."""
    participant = db.get_participant_by_id(participant_id)
    if participant:
        group = db.get_group_by_id(participant['group_id'])
        prompt_files = get_prompt_list()
        breadcrumbs = [
            {"link": url_for('dashboard'), "text": "Dashboard"},
            {"link": url_for('manage_groups'), "text": "Gruppen"},
            {
                "link": url_for('show_group_participants', group_id=group['id']),
                "text": group['name']
            },
            {"text": f"Dateneingabe: {participant['name']}"}
        ]
        return render_template(
            'data_entry.html',
            participant=participant,
            group=group,
            breadcrumbs=breadcrumbs,
            prompts=prompt_files
        )

    flash("Teilnehmer nicht gefunden.", "error")
    return redirect(url_for('manage_participants'))


@app.route('/participant/<int:participant_id>/report')
def show_report(participant_id):
    """Zeigt den generierten Bericht für einen Teilnehmer an."""
    participant = db.get_participant_by_id(participant_id)
    group = db.get_group_by_id(participant['group_id'])
    breadcrumbs = [
        {"link": url_for('dashboard'), "text": "Dashboard"},
        {"link": url_for('manage_groups'), "text": "Gruppen"},
        {
            "link": url_for('show_group_participants', group_id=group['id']),
            "text": group['name']
        },
        {"text": f"Bericht: {participant['name']}"}
    ]
    return render_template(
        'staerkenanalyse_bericht_vorlage3.html',
        participant=participant,
        group=group,
        breadcrumbs=breadcrumbs
    )

# --- API-Endpunkte für asynchrone Aktionen ---


@app.route('/save_observations/<int:participant_id>', methods=['POST'])
def save_observations(participant_id):
    """
    Speichert Beobachtungen asynchron. Erwartet ein flaches JSON-Objekt
    vom Browser, z.B. {'social': '...', 'verbal': '...'}, und formt es um.
    """
    data_from_browser = request.get_json()

    # Prüfung, ob die erwarteten Daten vorhanden sind
    if data_from_browser and 'social' in data_from_browser and 'verbal' in data_from_browser:
        # Die flachen Daten werden serverseitig in die korrekte Struktur für die DB umgeformt
        data_for_db = {
            'observations': {
                'social': data_from_browser.get('social', ''),
                'verbal': data_from_browser.get('verbal', '')
            }
        }
        # Die korrekt strukturierten Daten werden an die Datenbankfunktion übergeben
        db.save_participant_data(participant_id, data_for_db)
        return jsonify({"status": "success", "message": "Beobachtungen erfolgreich gespeichert!"})

    # Fallback, falls die Daten im falschen Format ankommen
    return jsonify({"status": "error", "message": "Ungültige oder unvollständige Daten empfangen."}), 400


@app.route('/save_report/<int:participant_id>', methods=['POST'])
def save_report(participant_id):
    """Speichert den gesamten bearbeiteten Bericht."""
    report_data = request.get_json()
    db.save_participant_data(participant_id, report_data)
    return jsonify({"status": "success", "message": "Bericht erfolgreich gespeichert!"})


@app.route('/run_ki_analysis/<int:participant_id>', methods=['POST'])
def run_ki_analysis(participant_id):
    """Führt die KI-Analyse für einen Teilnehmer durch."""
    participant = db.get_participant_by_id(participant_id)
    final_prompt = request.form.get('ki_prompt', '')
    ki_model = request.form.get('ki_model', 'mistral')

    final_prompt = final_prompt.replace('{{name}}', participant.get('name', ''))

    social_obs = request.form.get('social_observations', '')
    verbal_obs = request.form.get('verbal_observations', '')

    final_prompt = final_prompt.replace('{{social_observations}}', social_obs)
    final_prompt = final_prompt.replace('{{verbal_observations}}', verbal_obs)

    additional_content = ""
    if 'additional_files' in request.files:
        file = request.files.get('additional_files')
        if file and file.filename != '':
            additional_content = get_file_content(file)
    final_prompt = final_prompt.replace('{{additional_content}}', additional_content)

    ki_response_str = generate_report_with_ai(final_prompt, ki_model)
    db.save_ki_raw_response(participant_id, ki_response_str)

    try:
        cleaned_response = clean_json_response(ki_response_str)
        ki_data = json.loads(cleaned_response)

        if "error" in ki_data:
            return jsonify({
                "status": "error", "message": f"KI-Fehler: {ki_data['error']}"
            })

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
        return jsonify({
            "status": "error",
            "message": f"Fehler beim Verarbeiten der KI-Antwort: {e}",
            "raw_response": ki_response_str
        })


@app.route('/prompts/<path:filename>')
def get_prompt_content(filename):
    """Liefert den Inhalt einer Prompt-Datei sicher als JSON zurück."""
    prompts_dir = os.path.join(app.root_path, 'prompts')
    safe_filename = secure_filename(filename)

    safe_path = os.path.normpath(os.path.join(prompts_dir, safe_filename))
    if not safe_path.startswith(os.path.normpath(prompts_dir)):
        return jsonify({"error": "Ungültiger Dateipfad"}), 400

    try:
        with open(safe_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content})
    except FileNotFoundError:
        return jsonify({'error': 'Datei nicht gefunden.'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Info-Seite ---


@app.route('/info')
def info():
    """Zeigt die Info-Seite an."""
    breadcrumbs = [
        {"link": url_for('dashboard'), "text": "Dashboard"},
        {"text": "Info"}
    ]
    return render_template('info.html', breadcrumbs=breadcrumbs)


if __name__ == '__main__':
    app.run(port=5001, debug=True)
