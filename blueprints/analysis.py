# blueprints/analysis.py - KOMPLETTE DATEI
"""Dieses Modul enthält Routen und Funktionen für die Analyse, KI-Integration und Berichtserstellung."""

import base64
import io
import json
from io import BytesIO
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from flask import (Blueprint, request, redirect, url_for, flash, render_template,
                   jsonify, Response)
from weasyprint import HTML

import database as db
from ki_services import generate_report_with_ai
from utils import clean_json_response, get_file_content

# Ein Blueprint-Objekt für Analyse, KI und Berichte
analysis_bp = Blueprint('analysis', __name__)


# --- HILFSFUNKTION FÜR DIAGRAMME ---

def create_radar_chart(ratings_dict, keys, labels, color, title):
    """Erzeugt ein Radardiagramm und gibt es als Base64-Bild zurück."""
    values = [ratings_dict.get(key, 0) for key in keys]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    values_plot = values + values[:1]
    angles_plot = angles + angles[:1]
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.fill(angles_plot, values_plot, color=color, alpha=0.2)
    ax.plot(angles_plot, values_plot, color=color, linewidth=2)
    ax.grid(color='#E0E0E0', linestyle='-', linewidth=0.7)
    ax.spines['polar'].set_edgecolor('#E0E0EE')
    ax.set_yticklabels([])
    ax.set_rlim(0, 10)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, size=12, fontfamily='sans-serif')
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.tick_params(axis='x', pad=15)
    
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True, pad_inches=0.2)
    plt.close(fig)
    buf.seek(0)
    
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"


# --- ROUTEN FÜR BERICHTE (HTML & PDF) ---

@analysis_bp.route('/edit_report/<int:participant_id>')
def edit_report(participant_id):
    """Zeigt die bearbeitbare Version des Berichts an."""
    participant = db.get_participant_by_id(participant_id)
    if not participant:
        return "Teilnehmer nicht gefunden", 404
    group = db.get_group_by_id(participant['group_id'])

    current_date = datetime.now().strftime("%d.%m.%Y")
    current_location = group['location'] if group else "Unbekannter Ort"

    return render_template('staerkenanalyse_bericht_vorlage3.html', 
                           participant=participant, 
                           group=group,
                           current_date=current_date,
                           current_location=current_location)

@analysis_bp.route('/bericht/<int:participant_id>/pdf')
def bericht_pdf(participant_id):
    """Generiert eine PDF-Version des Berichts serverseitig."""
    participant = db.get_participant_by_id(participant_id)
    if not participant:
        return "Teilnehmer nicht gefunden", 404
    
    group = db.get_group_by_id(participant['group_id'])
    current_date = datetime.now().strftime("%d.%m.%Y")
    current_location = "Lingen (Ems)"

    sk_ratings = participant.get('sk_ratings', {})
    sk_labels = ['Flexibilität', 'Team-\norientierung', 'Prozess-\norientierung', 'Ergebnis-\norientierung']
    sk_keys = ['flexibility', 'team_orientation', 'process_orientation', 'results_orientation']
    
    vk_ratings = participant.get('vk_ratings', {})
    vk_labels = ['Flexibilität', 'Beratung', 'Sachlichkeit', 'Ziel-\norientierung']
    vk_keys = ['flexibility', 'consulting', 'objectivity', 'goal_orientation']
    
    sk_chart_image = create_radar_chart(sk_ratings, sk_keys, sk_labels, '#5A7D7C', 'Soziale Kompetenzen')
    vk_chart_image = create_radar_chart(vk_ratings, vk_keys, vk_labels, '#2F4F4F', 'Verbale Kompetenzen')

    html_string = render_template('bericht_pdf_vorlage.html', 
                                   participant=participant, 
                                   group=group,
                                   current_date=current_date,
                                   current_location=current_location,
                                   sk_chart_image=sk_chart_image,
                                   vk_chart_image=vk_chart_image,
                                   _external=True)
    
    pdf_bytes = HTML(string=html_string, base_url=request.base_url).write_pdf()
    
    safe_name = "".join(c for c in participant.get('name', 'Unbekannt') if c.isalnum() or c in (' ', '_')).rstrip()
    filename = f"Staerkenanalyse_{safe_name.replace(' ', '_')}.pdf"
    
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-disposition": f"attachment; filename=\"{filename}\""}
    )

# --- ROUTEN FÜR KI-ANALYSE (EINZELN & BATCH) ---

@analysis_bp.route("/ai_analysis/select_group")
def ai_analysis_select_group():
    """Zeigt die Seite zur Auswahl der Gruppe für die KI-Analyse an."""
    groups = db.get_all_groups()
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "KI-Analyse"},
    ]
    return render_template(
        "ai_analysis_select_group.html", groups=groups, breadcrumbs=breadcrumbs
    )

@analysis_bp.route("/ai_analysis/group/<int:group_id>")
def ai_analysis_select_participants(group_id):
    """Zeigt die Seite zur Auswahl der Teilnehmer für die KI-Analyse an."""
    group = db.get_group_by_id(group_id)
    participants = db.get_participants_by_group(group_id)
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("analysis.ai_analysis_select_group"), "text": "KI-Analyse"},
        {"text": f"Auswahl für: {group['name']}"},
    ]
    return render_template(
        "ai_analysis_select_participants.html",
        group=group,
        participants=participants,
        breadcrumbs=breadcrumbs,
    )

@analysis_bp.route("/ai_analysis/configure", methods=["POST"])
def configure_batch_ai_analysis():
    """Zeigt die Seite zur Konfiguration der KI-Analyse für ausgewählte Teilnehmer."""
    participant_ids = request.form.getlist("participant_ids")
    if not participant_ids:
        flash("Keine Teilnehmer ausgewählt.", "warning")
        return redirect(url_for("analysis.ai_analysis_select_group"))

    participants = [db.get_participant_by_id(pid) for pid in participant_ids]
    group = db.get_group_by_id(participants[0]["group_id"]) if participants else None
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("analysis.ai_analysis_select_group"), "text": "KI-Analyse"},
        {
            "link": url_for("analysis.ai_analysis_select_participants", group_id=group["id"]),
            "text": f"Auswahl für: {group['name']}",
        },
        {"text": "Analyse konfigurieren"},
    ]

    return render_template(
        "run_batch_ai.html",
        participants=participants,
        group=group,
        prompts=db.get_all_prompts(),
        breadcrumbs=breadcrumbs,
    )

@analysis_bp.route("/ai_analysis/execute", methods=["POST"])
def execute_batch_ai_analysis():
    """Zeigt den Status der KI-Analyse für ausgewählte Teilnehmer an."""
    participant_ids = request.form.getlist("participant_ids")
    analysis_data = {
        "prompt_template": request.form.get("ki_prompt", ""),
        "ki_model": request.form.get("ki_model", "mistral"),
        "additional_content": "\n\n---\n\n".join(
            [
                get_file_content(file)
                for file in request.files.getlist("additional_files")
                if file and file.filename != ""
            ]
        ),
    }

    participants = [db.get_participant_by_id(pid) for pid in participant_ids]
    group = db.get_group_by_id(participants[0]["group_id"]) if participants else None

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("analysis.ai_analysis_select_group"), "text": "KI-Analyse"},
        {"text": "Analyse-Status"},
    ]

    return render_template(
        "ai_analysis_status.html",
        participants=participants,
        group=group,
        analysis_data=analysis_data,
        breadcrumbs=breadcrumbs,
    )

# --- API-Endpunkte für die KI ---

@analysis_bp.route("/run_ki_analysis/<int:participant_id>", methods=["POST"])
def run_ki_analysis(participant_id):
    """Führt die KI-Analyse für einen einzelnen Teilnehmer durch (aus der Dateneingabe)."""
    participant = db.get_participant_by_id(participant_id)
    final_prompt = request.form.get("ki_prompt", "")
    ki_model = request.form.get("ki_model", "mistral")
    
    full_name = participant.get("name", "")
    first_name = full_name.split(" ")[0] if full_name else ""
    
    final_prompt = final_prompt.replace("{{name}}", first_name).replace("{{vorname}}", first_name)
    
    observations = participant.get("observations", {})
    social_obs = observations.get("social", "")
    verbal_obs = observations.get("verbal", "")
    final_prompt = final_prompt.replace("{{social_observations}}", social_obs).replace("{{verbal_observations}}", verbal_obs)
    
    additional_content = ""
    if "additional_files" in request.files:
        file = request.files.get("additional_files")
        if file and file.filename != "":
            additional_content = get_file_content(file)
    final_prompt = final_prompt.replace("{{additional_content}}", additional_content)
    
    ki_response_str = generate_report_with_ai(final_prompt, ki_model)
    db.save_ki_raw_response(participant_id, ki_response_str)
    
    try:
        ki_data = json.loads(clean_json_response(ki_response_str))
        if "error" in ki_data:
            return jsonify({"status": "error", "message": f"KI-Fehler: {ki_data['error']}"})
            
        db.save_participant_data(
            participant_id,
            {
                "sk_ratings": ki_data.get("sk_ratings", {}),
                "vk_ratings": ki_data.get("vk_ratings", {}),
                "ki_texts": ki_data.get("ki_texts", {}),
            },
        )
        return jsonify({
            "status": "success",
            "message": "KI-Analyse erfolgreich. Bericht wird geladen...",
            "redirect_url": url_for("participants.show_report", participant_id=participant_id),
        })
    except json.JSONDecodeError as e:
        return jsonify({
            "status": "error",
            "message": f"Fehler beim Verarbeiten der KI-Antwort: {e}",
            "raw_response": ki_response_str,
        })

@analysis_bp.route("/api/run_single_analysis/<int:participant_id>", methods=["POST"])
def run_single_analysis_api(participant_id):
    """API-Endpunkt, um die KI-Analyse für die Batch-Verarbeitung auszuführen."""
    data = request.get_json()
    participant = db.get_participant_by_id(participant_id)
    if not participant:
        return jsonify({"status": "error", "message": "Teilnehmer nicht gefunden."}), 404
        
    full_name = participant.get("name", "")
    first_name = full_name.split(" ")[0] if full_name else ""
    obs = participant.get("observations", {})
    
    context_block = (
        f"ANALYSE-SUBJEKT:\n- Vorname: {first_name}\n- Ganzer Name: {full_name}\n\n"
        f"BEOBACHTUNGEN ZUM VERHALTEN:\n- Soziale Kompetenzen: {obs.get('social', '')}\n"
        f"- Verbale Kompetenzen: {obs.get('verbal', '')}\n\n"
        f"ZUSÄTZLICHER KONTEXT:\n{data.get('additional_content', '')}"
    )
    
    prompt = data.get("prompt_template", "").replace("{{context}}", context_block)
    
    response_str = generate_report_with_ai(prompt, data.get("ki_model"))
    db.save_ki_raw_response(participant_id, response_str)
    
    try:
        ki_data = json.loads(clean_json_response(response_str))
        if "error" in ki_data:
            return jsonify({"status": "error", "message": f"KI-Fehler: {ki_data['error']}"})
            
        db.save_participant_data(
            participant_id,
            {
                "sk_ratings": ki_data.get("sk_ratings", {}),
                "vk_ratings": ki_data.get("vk_ratings", {}),
                "ki_texts": ki_data.get("ki_texts", {}),
            },
        )
        return jsonify({"status": "success", "message": "Analyse erfolgreich."})
    except json.JSONDecodeError as e:
        return jsonify({
            "status": "error",
            "message": f"Formatfehler: {e}",
            "raw_response": response_str,
        })