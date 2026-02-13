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
from flask_login import login_required, current_user

from extensions import csrf, db
from services.ai_client import generate_report_with_ai
from models import ExplanationBlock, Group, Participant, Prompt, SelfAssessment
from utils import clean_json_response, get_file_content, sanitize_html, html_to_plaintext, log_activity
from decorators import permission_required, group_access_required, participant_access_required, filter_groups_by_access
from validation import (
    BatchAnalysisPayload,
    KiPromptForm,
    format_validation_error,
    parse_form,
    parse_id_list,
    parse_json,
)

# WeasyPrint wird lazy-loaded (unten in den Funktionen) um die App schneller zu starten
try:
    from weasyprint import HTML
    WEASYPRINT_ERROR = None
except Exception as e:
    HTML = None
    WEASYPRINT_ERROR = str(e)

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


def get_group_task_descriptions(group):
    """
    Extrahiert die Beschreibungen aller Aufgaben einer Gruppe.
    
    Sammelt für jede Aufgabe:
    - title
    - description (Kurztext)
    - Inhalt aus current_version (HTML → Plaintext)
    
    Args:
        group: Group-Objekt mit .tasks Beziehung
        
    Returns:
        str: Formatierter String mit alle Aufgabenbeschreibungen, oder leerer String wenn keine Aufgaben
        
    Beispiel:
        task_descriptions = get_group_task_descriptions(group)
        # Output:
        # AUFGABENBESCHREIBUNG 1 — Soziale Kompetenzen:
        # Titel: Brückenbau-Übung
        # ...
    """
    if not group:
        return ""
    
    # Hole alle Tasks aus der Beziehung (funktioniert mit SQLAlchemy .all() und Python-Listen)
    try:
        task_list = group.tasks.all() if hasattr(group.tasks, 'all') else group.tasks
    except:
        task_list = []
    
    if not task_list:
        return ""
    
    descriptions = []
    
    for idx, task in enumerate(task_list, 1):
        task_section = f"\nAUFGABENBESCHREIBUNG {idx} — {task.observation_area}:\n"
        task_section += f"Titel: {task.title}\n"
        
        # Kurztext-Beschreibung wenn vorhanden
        if task.description:
            task_section += f"Kurzbeschreibung: {task.description}\n"
        
        # HTML→Plaintext Konversion des Hauptinhalts
        if task.current_version and task.current_version.content:
            content_plaintext = html_to_plaintext(task.current_version.content)
            if content_plaintext:
                task_section += f"Inhaltsdetails:\n{content_plaintext}\n"
        
        descriptions.append(task_section)
    
    return "\n".join(descriptions)


def _normalize_ki_data(ki_data):
    """Normalisiert KI-JSON auf erwartete Struktur.

    Unterstützt sowohl:
    - {"ki_texts": {"social_text": "...", ...}}
    - {"social_text": "...", "verbal_text": "...", "summary_text": "..."}
    """
    sk_ratings = ki_data.get("sk_ratings") or {}
    vk_ratings = ki_data.get("vk_ratings") or {}

    # Map alternative VK keys (z.B. CopilotSozVerbv1)
    if isinstance(vk_ratings, dict):
        mapped_vk = {}
        if "flexibility" in vk_ratings:
            mapped_vk["flexibility"] = vk_ratings.get("flexibility")
        if "expression_flexibility" in vk_ratings:
            mapped_vk["flexibility"] = vk_ratings.get("expression_flexibility")
        if "consulting" in vk_ratings:
            mapped_vk["consulting"] = vk_ratings.get("consulting")
        if "consulting_competence" in vk_ratings:
            mapped_vk["consulting"] = vk_ratings.get("consulting_competence")
        if "objectivity" in vk_ratings:
            mapped_vk["objectivity"] = vk_ratings.get("objectivity")
        if "goal_orientation" in vk_ratings:
            mapped_vk["goal_orientation"] = vk_ratings.get("goal_orientation")
        if "goal_oriented_communication" in vk_ratings:
            mapped_vk["goal_orientation"] = vk_ratings.get(
                "goal_oriented_communication"
            )
        vk_ratings = mapped_vk or vk_ratings

    ki_texts = ki_data.get("ki_texts")
    if not isinstance(ki_texts, dict):
        # CopilotSozVerbv1: analysis.social_analysis.interpretation etc.
        analysis_block = ki_data.get("analysis") or {}
        social_analysis = analysis_block.get("social_analysis") or {}
        verbal_analysis = analysis_block.get("verbal_analysis") or {}

        summary_block = ki_data.get("summary") or {}
        summary_parts = [
            summary_block.get("key_strengths"),
            summary_block.get("development_areas"),
            summary_block.get("task_alignment"),
        ]
        summary_text = "\n".join([part for part in summary_parts if part])

        ki_texts = {
            "social_text": social_analysis.get("interpretation", "")
            or ki_data.get("social_text", ""),
            "verbal_text": verbal_analysis.get("interpretation", "")
            or ki_data.get("verbal_text", ""),
            "summary_text": summary_text or ki_data.get("summary_text", ""),
        }

    ki_texts = {key: (value or "") for key, value in ki_texts.items()}
    return sk_ratings, vk_ratings, ki_texts


# --- ROUTEN FÜR BERICHTE (HTML & PDF) ---


@analysis_bp.route("/edit_report/<int:participant_id>")
@login_required
@permission_required("analysis.view_reports")
@participant_access_required
def edit_report(participant_id):
    """Zeigt die bearbeitbare Version des Berichts an."""
    participant = db.get_or_404(Participant, participant_id)
    group = participant.group
    
    # KI-Report Metadata ZUERST erfassen (vom ORM-Objekt)
    german_tz = pytz.timezone("Europe/Berlin")
    ki_report_created_at = None
    ki_report_edited = False
    
    if participant.created_at:
        ki_report_created_at = participant.created_at.astimezone(german_tz).strftime("%d.%m.%Y um %H:%M Uhr")
    
    # Check if report has been edited
    try:
        from models import AIRawResponse
        raw_response = db.session.scalars(
            db.select(AIRawResponse)
            .where(AIRawResponse.type == 'report')
            .where(AIRawResponse.context_id == participant_id)
            .order_by(AIRawResponse.created_at.desc())
            .limit(1)
        ).first()
        if raw_response and raw_response.processing_status == 'edited':
            ki_report_edited = True
    except Exception as e:
        print(f"   ⚠️  Fehler beim Prüfen des Edit-Status: {e}")

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
        "ki_model": participant.ki_model,
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
    
    # KI-Report Metadata
    ki_report_created_at = None
    ki_report_edited = False
    if participant.created_at:
        ki_report_created_at = participant.created_at.astimezone(german_tz).strftime("%d.%m.%Y um %H:%M Uhr")
    
    # Check if report has been edited
    try:
        from models import AIRawResponse
        raw_response = db.session.scalars(
            db.select(AIRawResponse)
            .where(AIRawResponse.type == 'report')
            .where(AIRawResponse.context_id == participant_id)
            .order_by(AIRawResponse.created_at.desc())
            .limit(1)
        ).first()
        if raw_response and raw_response.processing_status == 'edited':
            ki_report_edited = True
    except Exception as e:
        print(f"   ⚠️  Fehler beim Prüfen des Edit-Status: {e}")

    return render_template(
        "staerkenanalyse_bericht_vorlage3.html",
        participant=participant_dict,
        group=group_dict,
        ki_original=ki_original,
        current_date=current_date,
        current_location=current_location,
        ki_report_created_at=ki_report_created_at,
        ki_report_edited=ki_report_edited,
    )


@analysis_bp.route("/save_report/<int:participant_id>", methods=["POST"])
@login_required
@permission_required("analysis.edit_reports")
@participant_access_required
def save_report(participant_id):
    """Speichert bearbeitete Berichtsdaten (KI-Analyse)."""
    participant = db.get_or_404(Participant, participant_id)
    data = request.get_json()

    if data:
        # --- KI-GYM: Track edits before saving ---
        if "ki_texts" in data:
            try:
                from models import AIRawResponse, ContentEdit
                from services.ai_client import compute_content_diff
                
                # Find the latest raw response for this participant
                raw_response = db.session.scalars(
                    db.select(AIRawResponse)
                    .where(AIRawResponse.type == 'report')
                    .where(AIRawResponse.context_id == participant_id)
                    .order_by(AIRawResponse.created_at.desc())
                    .limit(1)
                ).first()
                
                if raw_response and raw_response.processing_status != 'edited':
                    # Get old and new content
                    old_ki_texts = json.loads(participant.ki_texts) if participant.ki_texts else {}
                    new_ki_texts = data["ki_texts"]
                    
                    # Combine all text fields for comparison
                    old_content = "\n\n".join([str(v) for v in old_ki_texts.values() if v])
                    new_content = "\n\n".join([str(v) for v in new_ki_texts.values() if v])
                    
                    # Only track if content actually changed
                    if old_content != new_content:
                        diff_metrics = compute_content_diff(old_content, new_content)
                        
                        # Create ContentEdit record
                        content_edit = ContentEdit(
                            raw_response_id=raw_response.id,
                            version_type='report',
                            version_id=participant_id,
                            diff_metrics=diff_metrics,
                            edit_reason='Manuelle Verbesserungen',
                            edited_by_id=current_user.id
                        )
                        db.session.add(content_edit)
                        
                        # Update status
                        raw_response.processing_status = 'edited'
                        
                        print(f"   ✏️ KI-Gym: Report edit tracked (Magnitude: {diff_metrics['edit_magnitude']})")
            except Exception as e:
                print(f"   ⚠️  KI-Gym Edit Tracking Fehler: {e}")
                # Non-critical: continue without breaking
        
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

        log_activity(
            user_id=current_user.id,
            action="report_edited",
            action_label="Bericht bearbeitet",
            entity_type="participant",
            entity_id=participant.id,
            entity_label=participant.name,
            target_url=url_for("analysis.edit_report", participant_id=participant.id),
        )
        db.session.commit()

        return jsonify(
            {"status": "success", "message": "Bericht erfolgreich gespeichert!"}
        )

    return jsonify({"status": "error", "message": "Keine Daten erhalten."}), 400


@analysis_bp.route("/bericht/<int:participant_id>/pdf")
@login_required
@permission_required("analysis.view_reports")
@participant_access_required
def bericht_pdf(participant_id):
    """
    DEPRECATED: Alte PDF-Generierung (vor Report-System).
    Generiert eine PDF-Version des Berichts serverseitig.
    
    **Stattdessen verwenden:**
    - reports.standalone_fe_pdf - Nur Fremdeinschätzung
    - reports.standalone_se_pdf - Nur Selbsteinschätzung  
    - reports.generate_pdf_report - Vollständiger Abschlussbericht
    """
    
    # Prüfe ob WeasyPrint verfügbar ist
    if HTML is None:
        flash(
            "❌ PDF-Generierung nicht verfügbar: WeasyPrint-Abhängigkeiten fehlen. "
            "Bitte installieren Sie die erforderlichen System-Bibliotheken (Pango, Cairo). "
            "Siehe Terminal-Output für Details.",
            "error"
        )
        # Redirect zum HTML-Report
        return redirect(url_for("analysis.final_report", participant_id=participant_id))
    
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
@login_required
@permission_required("analysis.run")
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
@login_required
@permission_required("analysis.run")
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
@login_required
@permission_required("analysis.run")
def configure_batch_ai_analysis():
    """Zeigt die Seite zur Konfiguration der KI-Analyse für ausgewählte Teilnehmer."""
    participant_ids = parse_id_list(request.form.getlist("participant_ids"))
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
@login_required
@permission_required("analysis.run")
def execute_batch_ai_analysis():
    """Zeigt den Status der KI-Analyse für ausgewählte Teilnehmer an."""
    participant_ids = parse_id_list(request.form.getlist("participant_ids"))
    if not participant_ids:
        flash("Keine Teilnehmer ausgewählt.", "warning")
        return redirect(url_for("analysis.ai_analysis_select_group"))

    prompt_payload, error = parse_form(
        KiPromptForm,
        {
            "ki_prompt": request.form.get("ki_prompt", ""),
            "ki_model": request.form.get("ki_model", "mistral"),
        },
    )
    if error:
        flash(format_validation_error(error), "error")
        return redirect(url_for("analysis.ai_analysis_select_group"))

    analysis_data = {
        "prompt_template": prompt_payload.ki_prompt,
        "ki_model": prompt_payload.ki_model,
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

    for p in participants:
        log_activity(
            user_id=current_user.id,
            action="ki_analysis_started",
            action_label="KI-Analyse gestartet",
            entity_type="participant",
            entity_id=p.id,
            entity_label=p.name,
            target_url=url_for("analysis.edit_report", participant_id=p.id),
        )
    db.session.commit()

    return render_template(
        "ai_analysis_status.html",
        participants=participants,
        group=group,
        analysis_data=analysis_data,
        breadcrumbs=breadcrumbs,
    )


# --- API-Endpunkte für die KI ---


@analysis_bp.route("/run_ki_analysis/<int:participant_id>", methods=["POST"])
@login_required
@permission_required("analysis.run")
def run_ki_analysis(participant_id):
    """Führt die KI-Analyse für einen einzelnen Teilnehmer durch (aus der Dateneingabe)."""
    participant = db.get_or_404(Participant, participant_id)
    prompt_payload, error = parse_form(
        KiPromptForm,
        {
            "ki_prompt": request.form.get("ki_prompt", ""),
            "ki_model": request.form.get("ki_model", "mistral"),
        },
    )
    if error:
        return jsonify({"status": "error", "message": format_validation_error(error)}), 400

    final_prompt = prompt_payload.ki_prompt
    ki_model = prompt_payload.ki_model

    full_name = participant.name
    first_name = full_name.split(" ")[0] if full_name else ""

    final_prompt = (
        final_prompt.replace("{{name}}", first_name)
        .replace("{{vorname}}", first_name)
        .replace("{{first_name}}", first_name)
        .replace("{{ganzer_name}}", full_name)
    )

    observations = (
        json.loads(participant.observations) if participant.observations else {}
    )
    social_obs = observations.get("social", "")
    verbal_obs = observations.get("verbal", "")
    final_prompt = (
        final_prompt.replace("{{social_observations}}", social_obs)
        .replace("{{verbal_observations}}", verbal_obs)
    )

    additional_content = ""
    if "additional_files" in request.files:
        file = request.files.get("additional_files")
        if file and file.filename != "":
            additional_content = get_file_content(file)
    final_prompt = final_prompt.replace("{{additional_content}}", additional_content)

    # Hole die Aufgabenbeschreibungen aus der Gruppe des Teilnehmers
    task_descriptions = ""
    if participant.group:
        task_descriptions = get_group_task_descriptions(participant.group)
    
    # Falls keine Kontext-Platzhalter vorhanden sind, Kontextblock ergänzen
    context_block = (
        f"ANALYSE-SUBJEKT:\n- Vorname: {first_name}\n- Ganzer Name: {full_name}\n\n"
        f"BEOBACHTUNGEN ZUM VERHALTEN:\n- Soziale Kompetenzen: {social_obs}\n"
        f"- Verbale Kompetenzen: {verbal_obs}\n\n"
    )
    
    # Füge Aufgabenbeschreibungen ein wenn vorhanden
    if task_descriptions:
        context_block += f"AUFGABENBESCHREIBUNGEN:{task_descriptions}\n\n"
    
    # Füge zusätzlichen Kontext am Ende an
    context_block += f"ZUSÄTZLICHER KONTEXT:\n{additional_content}"
    
    if "{{context}}" in final_prompt:
        final_prompt = final_prompt.replace("{{context}}", context_block)
    elif (
        "{{social_observations}}" not in request.form.get("ki_prompt", "")
        and "{{verbal_observations}}" not in request.form.get("ki_prompt", "")
        and "{{context}}" not in request.form.get("ki_prompt", "")
    ):
        final_prompt = f"{final_prompt}\n\n{context_block}"

    ki_response_str = generate_report_with_ai(final_prompt, ki_model)
    participant.ki_raw_response = ki_response_str
    participant.ki_model = ki_model  # Track which KI model generated this report
    
    # --- KI-GYM: Save raw response ---
    try:
        from services.ai_client import save_ai_raw_response
        save_ai_raw_response(
            response_text=ki_response_str,
            response_type='report',
            context_id=participant_id,
            ki_model=ki_model,
            observation_area=None  # Reports don't have observation areas
        )
        print(f"   💾 KI-Gym: Raw response saved for participant {participant_id}")
    except Exception as e:
        print(f"   ⚠️  KI-Gym Save Error: {e}")
    
    db.session.commit()

    # Prüfe ob die Antwort leer ist
    if not ki_response_str or ki_response_str.strip() == "":
        return jsonify(
            {
                "status": "error",
                "message": "Die KI hat keine Antwort generiert. Bitte versuchen Sie es erneut.",
            }
        )

    try:
        cleaned_response = clean_json_response(ki_response_str)
        ki_data = json.loads(cleaned_response)
        if "error" in ki_data:
            return jsonify(
                {"status": "error", "message": f"KI-Fehler: {ki_data['error']}"}
            )

        sk_ratings, vk_ratings, ki_texts = _normalize_ki_data(ki_data)
        has_any_text = any(
            [
                ki_texts.get("social_text"),
                ki_texts.get("verbal_text"),
                ki_texts.get("summary_text"),
            ]
        )
        has_any_ratings = bool(sk_ratings) or bool(vk_ratings)

        if not has_any_text and not has_any_ratings:
            return jsonify(
                {
                    "status": "error",
                    "message": "Die KI-Antwort enthält keine verwertbaren Daten. Bitte überprüfen Sie den Prompt und versuchen Sie es erneut.",
                }
            )

        participant.sk_ratings = json.dumps(sk_ratings)
        participant.vk_ratings = json.dumps(vk_ratings)
        participant.ki_texts = json.dumps(ki_texts)
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
        print(f"JSON Parse Error: {e}")
        print(f"Raw Response (first 500 chars): {ki_response_str[:500]}")
        return jsonify(
            {
                "status": "error",
                "message": "Die KI-Antwort hat ein ungültiges Format. Bitte versuchen Sie es erneut oder kontaktieren Sie den Administrator.",
            }
        )
    except Exception as e:
        print(f"Unexpected Error in run_ki_analysis: {e}")
        return jsonify(
            {
                "status": "error",
                "message": f"Ein unerwarteter Fehler ist aufgetreten: {str(e)}",
            }
        )


@analysis_bp.route("/api/run_single_analysis/<int:participant_id>", methods=["POST"])
@login_required
@permission_required("analysis.run")
def run_single_analysis_api(participant_id):
    """API-Endpunkt, um die KI-Analyse für die Batch-Verarbeitung auszuführen."""
    data = request.get_json()
    parsed, error = parse_json(BatchAnalysisPayload, data or {})
    if error:
        return jsonify({"status": "error", "message": format_validation_error(error)}), 400
    participant = db.session.get(Participant, participant_id)
    if not participant:
        return (
            jsonify({"status": "error", "message": "Teilnehmer nicht gefunden."}),
            404,
        )

    full_name = participant.name
    first_name = full_name.split(" ")[0] if full_name else ""
    obs = json.loads(participant.observations) if participant.observations else {}

    # Hole die Aufgabenbeschreibungen aus der Gruppe des Teilnehmers
    task_descriptions = ""
    if participant.group:
        task_descriptions = get_group_task_descriptions(participant.group)
    
    # Baue den Kontextblock mit Aufgabenbeschreibungen
    context_block = (
        f"ANALYSE-SUBJEKT:\n- Vorname: {first_name}\n- Ganzer Name: {full_name}\n\n"
        f"BEOBACHTUNGEN ZUM VERHALTEN:\n- Soziale Kompetenzen: {obs.get('social', '')}\n"
        f"- Verbale Kompetenzen: {obs.get('verbal', '')}\n\n"
    )
    
    # Füge Aufgabenbeschreibungen ein wenn vorhanden
    if task_descriptions:
        context_block += f"AUFGABENBESCHREIBUNGEN:{task_descriptions}\n\n"
    
    # Füge zusätzlichen Kontext am Ende an
    context_block += f"ZUSÄTZLICHER KONTEXT:\n{parsed.additional_content}"
    
    prompt_template = parsed.prompt_template
    prompt = (
        prompt_template.replace("{{context}}", context_block)
        .replace("{{name}}", first_name)
        .replace("{{vorname}}", first_name)
        .replace("{{first_name}}", first_name)
        .replace("{{ganzer_name}}", full_name)
        .replace("{{social_observations}}", obs.get("social", ""))
        .replace("{{verbal_observations}}", obs.get("verbal", ""))
        .replace("{{additional_content}}", parsed.additional_content)
        .replace("{{participant_id}}", str(participant.id))
    )

    if "{{context}}" in prompt_template:
        prompt = prompt_template.replace("{{context}}", context_block)
    elif (
        "{{social_observations}}" not in prompt_template
        and "{{verbal_observations}}" not in prompt_template
        and "{{context}}" not in prompt_template
    ):
        prompt = f"{prompt}\n\n{context_block}"

    response_str = generate_report_with_ai(prompt, parsed.ki_model)
    participant.ki_raw_response = response_str
    participant.ki_model = parsed.ki_model  # Track which KI model generated this report
    
    # --- KI-GYM: Save raw response ---
    try:
        from services.ai_client import save_ai_raw_response
        save_ai_raw_response(
            response_text=response_str,
            response_type='report',
            context_id=participant_id,
            ki_model=parsed.ki_model,
            observation_area=None
        )
    except Exception as e:
        print(f"   ⚠️  KI-Gym Save Error: {e}")
    
    db.session.commit()

    # Prüfe ob die Antwort leer ist
    if not response_str or response_str.strip() == "":
        return jsonify(
            {
                "status": "error",
                "message": "Die KI hat keine Antwort generiert. Bitte versuchen Sie es erneut.",
            }
        )

    try:
        cleaned_response = clean_json_response(response_str)

        
        ki_data = json.loads(cleaned_response)
        if "error" in ki_data:
            return jsonify(
                {"status": "error", "message": f"KI-Fehler: {ki_data['error']}"}
            )

        sk_ratings, vk_ratings, ki_texts = _normalize_ki_data(ki_data)
        has_any_text = any(
            [
                ki_texts.get("social_text"),
                ki_texts.get("verbal_text"),
                ki_texts.get("summary_text"),
            ]
        )
        has_any_ratings = bool(sk_ratings) or bool(vk_ratings)

        if not has_any_text and not has_any_ratings:
            return jsonify(
                {
                    "status": "error",
                    "message": "Die KI-Antwort enthält keine verwertbaren Daten. Bitte überprüfen Sie den Prompt und versuchen Sie es erneut.",
                }
            )

        participant.sk_ratings = json.dumps(sk_ratings)
        participant.vk_ratings = json.dumps(vk_ratings)
        participant.ki_texts = json.dumps(ki_texts)
        db.session.commit()

        return jsonify({"status": "success", "message": "Analyse erfolgreich."})
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error (Batch): {e}")
        print(f"Raw Response (first 500 chars): {response_str[:500]}")
        return jsonify(
            {
                "status": "error",
                "message": "Die KI-Antwort hat ein ungültiges Format. Bitte versuchen Sie es erneut oder kontaktieren Sie den Administrator.",
            }
        )
    except Exception as e:
        print(f"Unexpected Error in run_single_analysis_api: {e}")
        return jsonify(
            {
                "status": "error",
                "message": f"Ein unerwarteter Fehler ist aufgetreten: {str(e)}",
            }
        )


# --- ROUTEN FÜR FREMDEINSCHÄTZUNG ---


@analysis_bp.route("/foreign-assessments")
@login_required
@permission_required("analysis.view_reports")
def manage_foreign_assessments():
    """Zeigt die Übersicht aller Teilnehmer gruppiert nach Gruppen mit Fremdeinschätzungs-Status an."""
    query = filter_groups_by_access(current_user)
    groups = db.session.scalars(query.order_by(Group.name)).all()

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
@login_required
@permission_required("analysis.view_reports")
def manage_final_reports():
    """Zeigt die Übersicht aller Teilnehmer gruppiert nach Gruppen mit Abschlussberichts-Status an."""
    query = filter_groups_by_access(current_user)
    groups = db.session.scalars(query.order_by(Group.name)).all()

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
@login_required
@permission_required("analysis.view_reports")
@participant_access_required
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
@login_required
@permission_required("analysis.view_reports")
@participant_access_required
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
