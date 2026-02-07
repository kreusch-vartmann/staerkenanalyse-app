# blueprints/analysis.py
"""Dieses Modul enthält Routen für Analyse, KI-Integration und Berichtserstellung."""

import base64
import json
from datetime import datetime
from io import BytesIO

import matplotlib
import pytz

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from flask import (Blueprint, Response, flash, jsonify, redirect,
                   render_template, request, url_for)
from weasyprint import HTML

from extensions import csrf, db
from ki_services import generate_report_with_ai
from models import ExplanationBlock, Group, Participant, Prompt, SelfAssessment
from utils import clean_json_response, get_file_content, sanitize_html

analysis_bp = Blueprint("analysis", __name__)


# --- HILFSFUNKTION FÜR DIAGRAMME ---


def create_radar_chart(ratings_dict, keys, labels, color):
    """Erzeugt ein Radardiagramm und gibt es als Base64-Bild zurück."""
    values = [ratings_dict.get(key, 0) for key in keys]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    values_plot = values + values[:1]
    angles_plot = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"polar": True})
    ax.fill(angles_plot, values_plot, color=color, alpha=0.2)
    ax.plot(angles_plot, values_plot, color=color, linewidth=2)
    ax.grid(color="#E0E0E0", linestyle="-", linewidth=0.7)
    ax.spines["polar"].set_edgecolor("#E0E0EE")
    ax.set_yticklabels([])
    ax.set_rlim(0, 10)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, size=12, fontfamily="sans-serif")
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.tick_params(axis="x", pad=15)

    buf = BytesIO()
    plt.savefig(
        buf, format="png", bbox_inches="tight", transparent=True, pad_inches=0.2
    )
    plt.close(fig)
    buf.seek(0)

    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{img_base64}"


def _prepare_pdf_data(participant):
    """Bereitet die Daten und Diagramme für den PDF-Bericht vor."""
    sk_ratings = participant.get("sk_ratings", {})
    sk_labels = [
        "Flexibilität",
        "Team-\norientierung",
        "Prozess-\norientierung",
        "Ergebnis-\norientierung",
    ]
    sk_keys = [
        "flexibility",
        "team_orientation",
        "process_orientation",
        "results_orientation",
    ]

    vk_ratings = participant.get("vk_ratings", {})
    vk_labels = ["Flexibilität", "Beratung", "Sachlichkeit", "Ziel-\norientierung"]
    vk_keys = ["flexibility", "consulting", "objectivity", "goal_orientation"]

    sk_chart = create_radar_chart(sk_ratings, sk_keys, sk_labels, "#5A7D7C")
    vk_chart = create_radar_chart(vk_ratings, vk_keys, vk_labels, "#2F4F4F")
    return sk_chart, vk_chart


# --- ROUTEN FÜR BERICHTE (HTML & PDF) ---


@analysis_bp.route("/edit_report/<int:participant_id>")
def edit_report(participant_id):
    """Zeigt die bearbeitbare Version des Berichts an."""
    participant = db.get_or_404(Participant, participant_id)
    group = participant.group

    # Konvertiere in dict-Format für Template-Kompatibilität
    participant_dict = {
        "id": participant.id,
        "name": participant.name,
        "group_id": participant.group_id,
        "observations": (
            json.loads(participant.observations) if participant.observations else {}
        ),
        "sk_ratings": (
            json.loads(participant.sk_ratings) if participant.sk_ratings else {}
        ),
        "vk_ratings": (
            json.loads(participant.vk_ratings) if participant.vk_ratings else {}
        ),
        "ki_texts": json.loads(participant.ki_texts) if participant.ki_texts else {},
        "ki_raw_response": participant.ki_raw_response,
        "footer_data": (
            json.loads(participant.footer_data) if participant.footer_data else {}
        ),
    }

    group_dict = {
        "id": group.id if group else None,
        "name": group.name if group else "",
        "date_from": group.date_from if group else None,
        "date_to": group.date_to if group else None,
        "location": group.location if group else "",
        "leitung": group.leitung_fremdeinschatzung if group else "",
        "leitung_fremdeinschatzung": group.leitung_fremdeinschatzung if group else "",
        "leitung_selbsteinschatzung": group.leitung_selbsteinschatzung if group else "",
        "beobachter1": group.beobachter1 if group else "",
        "beobachter2": group.beobachter2 if group else "",
    }

    # KI-Original-Daten parsen für Reset-Funktion
    ki_original = {}
    if participant.ki_raw_response:
        try:
            ki_original = json.loads(clean_json_response(participant.ki_raw_response))
        except (json.JSONDecodeError, ValueError):
            ki_original = {}

    german_tz = pytz.timezone("Europe/Berlin")
    current_date = datetime.now(pytz.utc).astimezone(german_tz).strftime("%d.%m.%Y")
    current_location = group_dict["location"] if group_dict else "Unbekannter Ort"

    return render_template(
        "staerkenanalyse_bericht_vorlage3.html",
        participant=participant_dict,
        group=group_dict,
        ki_original=ki_original,
        current_date=current_date,
        current_location=current_location,
    )


@analysis_bp.route("/save_report/<int:participant_id>", methods=["POST"])
@csrf.exempt
def save_report(participant_id):
    """Speichert bearbeitete Berichtsdaten (KI-Analyse)."""
    participant = db.get_or_404(Participant, participant_id)
    data = request.get_json()

    if data:
        # Speichere die verschiedenen Berichtsteile als JSON
        if "sk_ratings" in data:
            participant.sk_ratings = json.dumps(data["sk_ratings"])
        if "vk_ratings" in data:
            participant.vk_ratings = json.dumps(data["vk_ratings"])
        if "ki_texts" in data:
            # Sanitize HTML in each text field
            sanitized_ki_texts = {
                key: sanitize_html(value) if isinstance(value, str) else value
                for key, value in data["ki_texts"].items()
            }
            participant.ki_texts = json.dumps(sanitized_ki_texts)
        if "footer_data" in data:
            participant.footer_data = json.dumps(data["footer_data"])

        db.session.commit()
        return jsonify(
            {"status": "success", "message": "Bericht erfolgreich gespeichert!"}
        )

    return jsonify({"status": "error", "message": "Keine Daten erhalten."}), 400


@analysis_bp.route("/bericht/<int:participant_id>/pdf")
def bericht_pdf(participant_id):
    """Generiert eine PDF-Version des Berichts serverseitig."""
    participant = db.get_or_404(Participant, participant_id)
    group = participant.group

    # Konvertiere für Template
    participant_dict = {
        "id": participant.id,
        "name": participant.name,
        "sk_ratings": (
            json.loads(participant.sk_ratings) if participant.sk_ratings else {}
        ),
        "vk_ratings": (
            json.loads(participant.vk_ratings) if participant.vk_ratings else {}
        ),
        "ki_texts": json.loads(participant.ki_texts) if participant.ki_texts else {},
    }

    group_dict = {
        "id": group.id if group else None,
        "name": group.name if group else "",
        "date_from": group.date_from if group else None,
        "date_to": group.date_to if group else None,
        "location": group.location if group else "",
        "leitung": group.leitung_fremdeinschatzung if group else "",
        "beobachter1": group.beobachter1 if group else "",
        "beobachter2": group.beobachter2 if group else "",
    }
    german_tz = pytz.timezone("Europe/Berlin")
    current_date = datetime.now(pytz.utc).astimezone(german_tz).strftime("%d.%m.%Y")
    current_location = group.location if group and group.location else ""

    sk_chart_image, vk_chart_image = _prepare_pdf_data(participant_dict)

    html_string = render_template(
        "bericht_pdf_vorlage.html",
        participant=participant_dict,
        group=group_dict,
        current_date=current_date,
        current_location=current_location,
        sk_chart_image=sk_chart_image,
        vk_chart_image=vk_chart_image,
        _external=True,
    )

    pdf_bytes = HTML(string=html_string, base_url=request.base_url).write_pdf()

    safe_name = "".join(
        c
        for c in participant_dict.get("name", "Unbekannt")
        if c.isalnum() or c in (" ", "_")
    ).rstrip()
    filename = f"Staerkenanalyse_{safe_name.replace(' ', '_')}.pdf"

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-disposition": f'attachment; filename="{filename}"'},
    )


# --- ROUTEN FÜR KI-ANALYSE (EINZELN & BATCH) ---


@analysis_bp.route("/ai_analysis/select_group")
def ai_analysis_select_group():
    """Zeigt die Seite zur Auswahl der Gruppe für die KI-Analyse an."""
    groups = db.session.execute(db.select(Group).order_by(Group.name)).scalars().all()
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
    group = db.get_or_404(Group, group_id)
    participants = group.participants.order_by(Participant.name).all()
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("analysis.ai_analysis_select_group"), "text": "KI-Analyse"},
        {"text": f"Auswahl für: {group.name}"},
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

    participants = (
        db.session.execute(
            db.select(Participant).filter(Participant.id.in_(participant_ids))
        )
        .scalars()
        .all()
    )
    group = participants[0].group if participants else None
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("analysis.ai_analysis_select_group"), "text": "KI-Analyse"},
        {
            "link": url_for(
                "analysis.ai_analysis_select_participants", group_id=group.id
            ),
            "text": f"Auswahl für: {group.name}",
        },
        {"text": "Analyse konfigurieren"},
    ]

    prompts = (
        db.session.execute(db.select(Prompt).order_by(Prompt.name)).scalars().all()
    )

    return render_template(
        "run_batch_ai.html",
        participants=participants,
        group=group,
        prompts=prompts,
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

    participants = (
        db.session.execute(
            db.select(Participant).filter(Participant.id.in_(participant_ids))
        )
        .scalars()
        .all()
    )
    group = participants[0].group if participants else None

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
    participant = db.get_or_404(Participant, participant_id)
    final_prompt = request.form.get("ki_prompt", "")
    ki_model = request.form.get("ki_model", "mistral")

    full_name = participant.name
    first_name = full_name.split(" ")[0] if full_name else ""

    final_prompt = final_prompt.replace("{{name}}", first_name).replace(
        "{{vorname}}", first_name
    )

    observations = (
        json.loads(participant.observations) if participant.observations else {}
    )
    social_obs = observations.get("social", "")
    verbal_obs = observations.get("verbal", "")
    final_prompt = final_prompt.replace("{{social_observations}}", social_obs).replace(
        "{{verbal_observations}}", verbal_obs
    )

    additional_content = ""
    if "additional_files" in request.files:
        file = request.files.get("additional_files")
        if file and file.filename != "":
            additional_content = get_file_content(file)
    final_prompt = final_prompt.replace("{{additional_content}}", additional_content)

    ki_response_str = generate_report_with_ai(final_prompt, ki_model)
    participant.ki_raw_response = ki_response_str
    db.session.commit()

    try:
        ki_data = json.loads(clean_json_response(ki_response_str))
        if "error" in ki_data:
            return jsonify(
                {"status": "error", "message": f"KI-Fehler: {ki_data['error']}"}
            )

        participant.sk_ratings = json.dumps(ki_data.get("sk_ratings", {}))
        participant.vk_ratings = json.dumps(ki_data.get("vk_ratings", {}))
        participant.ki_texts = json.dumps(ki_data.get("ki_texts", {}))
        db.session.commit()

        return jsonify(
            {
                "status": "success",
                "message": "KI-Analyse erfolgreich. Bericht wird geladen...",
                "redirect_url": url_for(
                    "analysis.edit_report", participant_id=participant_id
                ),
            }
        )
    except json.JSONDecodeError as e:
        return jsonify(
            {
                "status": "error",
                "message": f"Fehler beim Verarbeiten der KI-Antwort: {e}",
                "raw_response": ki_response_str,
            }
        )


@analysis_bp.route("/api/run_single_analysis/<int:participant_id>", methods=["POST"])
@csrf.exempt
def run_single_analysis_api(participant_id):
    """API-Endpunkt, um die KI-Analyse für die Batch-Verarbeitung auszuführen."""
    data = request.get_json()
    participant = db.session.get(Participant, participant_id)
    if not participant:
        return (
            jsonify({"status": "error", "message": "Teilnehmer nicht gefunden."}),
            404,
        )

    full_name = participant.name
    first_name = full_name.split(" ")[0] if full_name else ""
    obs = json.loads(participant.observations) if participant.observations else {}

    context_block = (
        f"ANALYSE-SUBJEKT:\n- Vorname: {first_name}\n- Ganzer Name: {full_name}\n\n"
        f"BEOBACHTUNGEN ZUM VERHALTEN:\n- Soziale Kompetenzen: {obs.get('social', '')}\n"
        f"- Verbale Kompetenzen: {obs.get('verbal', '')}\n\n"
        f"ZUSÄTZLICHER KONTEXT:\n{data.get('additional_content', '')}"
    )

    prompt = data.get("prompt_template", "").replace("{{context}}", context_block)

    response_str = generate_report_with_ai(prompt, data.get("ki_model"))
    participant.ki_raw_response = response_str
    db.session.commit()

    try:
        ki_data = json.loads(clean_json_response(response_str))
        if "error" in ki_data:
            return jsonify(
                {"status": "error", "message": f"KI-Fehler: {ki_data['error']}"}
            )

        participant.sk_ratings = json.dumps(ki_data.get("sk_ratings", {}))
        participant.vk_ratings = json.dumps(ki_data.get("vk_ratings", {}))
        participant.ki_texts = json.dumps(ki_data.get("ki_texts", {}))
        db.session.commit()

        return jsonify({"status": "success", "message": "Analyse erfolgreich."})
    except json.JSONDecodeError as e:
        return jsonify(
            {
                "status": "error",
                "message": f"Formatfehler: {e}",
                "raw_response": response_str,
            }
        )


# --- ROUTEN FÜR FREMDEINSCHÄTZUNG ---


@analysis_bp.route("/foreign-assessments")
def manage_foreign_assessments():
    """Zeigt die Übersicht aller Teilnehmer gruppiert nach Gruppen mit Fremdeinschätzungs-Status an."""
    groups = db.session.execute(db.select(Group).order_by(Group.name)).scalars().all()

    groups_with_participants = []
    for group in groups:
        participants_with_status = []
        group_stats = {
            "total": 0,
            "with_foreign": 0,
        }

        for participant in group.participants:
            has_foreign_assessment = bool(
                participant.ki_texts and participant.ki_texts != "{}"
            )

            participants_with_status.append(
                {
                    "participant": participant,
                    "has_foreign_assessment": has_foreign_assessment,
                }
            )

            group_stats["total"] += 1
            if has_foreign_assessment:
                group_stats["with_foreign"] += 1

        if participants_with_status:
            groups_with_participants.append(
                {
                    "group": group,
                    "participants": participants_with_status,
                    "stats": group_stats,
                }
            )

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Fremdeinschätzung"},
    ]

    return render_template(
        "manage_foreign_assessments.html",
        groups_data=groups_with_participants,
        breadcrumbs=breadcrumbs,
    )


# --- ROUTEN FÜR ABSCHLUSSBERICHTE ---


@analysis_bp.route("/final-reports")
def manage_final_reports():
    """Zeigt die Übersicht aller Teilnehmer gruppiert nach Gruppen mit Abschlussberichts-Status an."""
    groups = db.session.execute(db.select(Group).order_by(Group.name)).scalars().all()

    # Gruppiere Participants mit Status-Informationen nach Gruppen
    groups_with_participants = []
    for group in groups:
        participants_with_status = []
        group_stats = {"total": 0, "with_foreign": 0, "with_self": 0, "ready": 0}

        for participant in group.participants:
            # Prüfe ob Fremdeinschätzung (ki_texts) vorhanden
            has_foreign_assessment = bool(
                participant.ki_texts and participant.ki_texts != "{}"
            )

            # Prüfe ob Selbsteinschätzung vorhanden
            self_assessment = db.session.execute(
                db.select(SelfAssessment).where(
                    SelfAssessment.participant_id == participant.id
                )
            ).scalar_one_or_none()
            has_self_assessment = bool(
                self_assessment and self_assessment.content.strip()
            )

            can_create_report = has_foreign_assessment and has_self_assessment

            participants_with_status.append(
                {
                    "participant": participant,
                    "has_foreign_assessment": has_foreign_assessment,
                    "has_self_assessment": has_self_assessment,
                    "can_create_report": can_create_report,
                }
            )

            # Update group statistics
            group_stats["total"] += 1
            if has_foreign_assessment:
                group_stats["with_foreign"] += 1
            if has_self_assessment:
                group_stats["with_self"] += 1
            if can_create_report:
                group_stats["ready"] += 1

        # Only add groups that have participants
        if participants_with_status:
            groups_with_participants.append(
                {
                    "group": group,
                    "participants": participants_with_status,
                    "stats": group_stats,
                }
            )

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Abschlussberichte"},
    ]

    return render_template(
        "manage_final_reports.html",
        groups_data=groups_with_participants,
        breadcrumbs=breadcrumbs,
    )


@analysis_bp.route("/final_report/<int:participant_id>")
def final_report(participant_id):
    """Zeigt den Abschlussbericht für einen Teilnehmer an."""
    participant = db.get_or_404(Participant, participant_id)
    return redirect(
        url_for(
            "reports.preview_report_html",
            group_id=participant.group_id,
            participant_id=participant.id,
        )
    )


@analysis_bp.route("/final_report/<int:participant_id>/pdf", methods=["POST"])
def final_report_pdf(participant_id):
    """Generiert eine PDF-Version des Abschlussberichts."""
    participant = db.get_or_404(Participant, participant_id)
    return redirect(
        url_for(
            "reports.generate_pdf_report",
            group_id=participant.group_id,
            participant_id=participant.id,
        )
    )
