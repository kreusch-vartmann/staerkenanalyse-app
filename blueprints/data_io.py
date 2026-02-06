# blueprints/data_io.py
"""Dieses Modul enthält Routen und Funktionen für den Datenimport, -export und die Dateneingabe."""

import json
import csv
from datetime import UTC, datetime
from io import BytesIO, StringIO
import pandas as pd

from flask import (Blueprint, request, redirect, url_for, flash, render_template,
                   Response, jsonify)

from extensions import db
from models import Participant, Group

data_io_bp = Blueprint('data_io', __name__)


# --- HILFSFUNKTIONEN FÜR EXPORT (ANGEPASST AN SQLAlchemy-OBJEKTE) ---

def _format_date_range(group):
    """Formatiert den Datumszeitraum einer Gruppe für den Export."""
    if not group:
        return ""

    if group.date_from and group.date_to:
        return f"{group.date_from.strftime('%Y-%m-%d')} - {group.date_to.strftime('%Y-%m-%d')}"
    elif group.date_from:
        return f"ab {group.date_from.strftime('%Y-%m-%d')}"
    elif group.date_to:
        return f"bis {group.date_to.strftime('%Y-%m-%d')}"
    else:
        return ""


def _create_participant_export_dict(participant):
    """Erstellt ein flaches Dictionary für einen Teilnehmer für den Export."""
    # TODO: Diese Funktion muss noch angepasst werden, wenn Export getestet wird
    # PROBLEM: Felder 'leitung', 'analysis_results', 'raw_analysis_response' existieren nicht im Model
    # Siehe models.py für korrekte Feldnamen
    group = participant.group

    participant_export = {
        "Name": participant.name,
        "Gruppe": group.name if group else "",
        "Zeitraum": _format_date_range(group) if group else "",
        "Ort": group.location if group else "",
        # TODO: Entscheiden zwischen leitung_fremdeinschatzung / leitung_selbsteinschatzung
        "Leitung (Fremd)": group.leitung_fremdeinschatzung if group else "",
        "Leitung (Selbst)": group.leitung_selbsteinschatzung if group else "",
        "Beobachter 1": group.beobachter1 if group else "",
        "Beobachter 2": group.beobachter2 if group else "",
    }

    observations = json.loads(participant.observations) if participant.observations else {}
    participant_export.update({
        "Beobachtung (Sozial)": observations.get("social", ""),
        "Beobachtung (Verbal)": observations.get("verbal", "")
    })

    # TODO: Klären welches Feld für analysis_results verwendet werden soll
    # Vermutlich ki_texts? Struktur muss geprüft werden
    ki_texts = json.loads(participant.ki_texts) if participant.ki_texts else {}
    participant_export.update({
        "KI SK-Stärken": ki_texts.get("sk_strengths", ""),
        "KI SK-Potenziale": ki_texts.get("sk_potentials", ""),
        "KI VK-Stärken": ki_texts.get("vk_strengths", ""),
        "KI VK-Potenziale": ki_texts.get("vk_potentials", ""),
        "KI-Text (Zusammenfassung)": ki_texts.get("summary_text", ""),
    })
    
    if participant.ki_raw_response:
        participant_export["KI-Rohdaten"] = participant.ki_raw_response

    return participant_export


def generate_excel_export(participants):
    """Generiert eine Excel-Datei aus den Teilnehmerdaten."""
    export_data = [_create_participant_export_dict(p) for p in participants]
    df = pd.DataFrame(export_data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Teilnehmer", index=False)
    output.seek(0)
    return output.getvalue()


def generate_csv_export(participants):
    """Generiert eine CSV-Datei aus den Teilnehmerdaten."""
    if not participants:
        return "".encode("utf-8-sig")

    export_data = [_create_participant_export_dict(p) for p in participants]
    all_fieldnames = set()
    for item in export_data:
        all_fieldnames.update(item.keys())
    fieldnames = sorted(list(all_fieldnames))

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(export_data)
    return output.getvalue().encode("utf-8-sig")


# --- ROUTEN FÜR DATENEINGABE ---

@data_io_bp.route("/data-entry/rework")
def data_entry_rework():
    """Zeigt die kombinierte Auswahl- und Eingabeseite für Beobachtungen."""
    groups = db.session.execute(db.select(Group).order_by(Group.name)).scalars().all()
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Beobachtungsdaten"},
    ]
    return render_template("data_entry_rework.html", groups=groups, breadcrumbs=breadcrumbs)


@data_io_bp.route("/data-entry/search", methods=['GET'])
def data_entry_search():
    """Zeigt eine Suchseite für Teilnehmer an und verarbeitet die Suche."""
    search_query = request.args.get('query', '').strip()
    results = []
    if search_query:
        search_term = f"%{search_query}%"
        results = db.session.execute(
            db.select(Participant).join(Group).filter(Participant.name.ilike(search_term)).order_by(Participant.name)
        ).scalars().all()
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Teilnehmer suchen"},
    ]
    return render_template(
        "data_entry_search.html",
        search_query=search_query,
        results=results,
        breadcrumbs=breadcrumbs
    )


# --- API ROUTEN FÜR DATENEINGABE ---

@data_io_bp.route("/api/group/<int:group_id>/participants")
def api_get_participants_by_group(group_id):
    """Liefert Teilnehmer einer Gruppe als JSON."""
    group = db.get_or_404(Group, group_id)
    participants_list = [{"id": p.id, "name": p.name} for p in group.participants]
    return jsonify(participants_list)


@data_io_bp.route("/api/participant/<int:participant_id>/observations")
def api_get_observations(participant_id):
    """Liefert die Beobachtungen eines Teilnehmers als JSON."""
    participant = db.get_or_404(Participant, participant_id)
    if participant.observations:
        return jsonify(json.loads(participant.observations))
    return jsonify({})


@data_io_bp.route("/save_observations/<int:participant_id>", methods=["POST"])
def save_observations_api(participant_id):
    """Speichert die Beobachtungen für einen Teilnehmer (API-Endpunkt)."""
    participant = db.get_or_404(Participant, participant_id)
    data = request.get_json()
    if data:
        participant.observations = json.dumps(data)
        db.session.commit()
        return jsonify({"status": "success", "message": "Beobachtungen gespeichert!"})
    return jsonify({"status": "error", "message": "Keine Daten erhalten."}), 400


# --- ROUTEN FÜR IMPORT & EXPORT (ANGEPASST AN SQLAlchemy) ---

@data_io_bp.route("/import")
def import_page():
    """Zeigt die Import-Seite an."""
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Import"}
    ]
    return render_template("import_page.html", breadcrumbs=breadcrumbs)


@data_io_bp.route("/import/names", methods=["POST"])
def import_names():
    """Importiert Namen aus einer Datei in eine neue Gruppe."""
    group_name = request.form.get("group_name")
    file = request.files.get("name_file")
    if not group_name or not file or file.filename == "":
        flash("Bitte Gruppennamen angeben und eine Datei auswählen.", "warning")
        return redirect(url_for("data_io.import_page"))
    try:
        content = file.read().decode("utf-8")
        names = [name.strip() for name in content.splitlines() if name.strip()]
        if not names:
            flash("Die ausgewählte Datei enthält keine gültigen Namen.", "warning")
            return redirect(url_for("data_io.import_page"))

        new_group = Group(name=group_name, date=datetime.now(UTC).date())
        db.session.add(new_group)
        db.session.flush()

        for name in names:
            new_participant = Participant(name=name, group_id=new_group.id)
            db.session.add(new_participant)
        
        db.session.commit()
        flash(f'Gruppe "{group_name}" mit {len(names)} Teilnehmern erstellt.', "success")
        return redirect(url_for("groups.show_group_participants", group_id=new_group.id))
    except Exception as e:
        flash(f"Ein Fehler ist beim Verarbeiten der Datei aufgetreten: {e}", "error")
        return redirect(url_for("data_io.import_page"))


@data_io_bp.route("/export_selection")
def export_selection():
    """Zeigt die Seite zur Auswahl der zu exportierenden Teilnehmer an."""
    groups = db.session.execute(
        db.select(Group).order_by(Group.name)
    ).scalars().all()
    
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Export"}
    ]
    return render_template("export_selection.html",
                           groups=groups,
                           breadcrumbs=breadcrumbs)


@data_io_bp.route("/export_data", methods=["POST"])
def export_data():
    """Exportiert die ausgewählten Teilnehmerdaten als Excel oder CSV."""
    select_all = request.form.get("select_all_data") == "true"
    export_format = request.form.get("format", "xlsx")
    try:
        query = db.select(Participant)
        if not select_all:
            participant_ids = [
                int(pid) for pid in request.form.getlist("participant_ids") if pid.isdigit()
            ]
            if not participant_ids:
                flash("Bitte wählen Sie mindestens einen Teilnehmer aus.", "error")
                return redirect(url_for("data_io.export_selection"))
            query = query.filter(Participant.id.in_(participant_ids))

        participants_to_export = db.session.execute(query).scalars().all()

        if not participants_to_export:
            flash("Keine Daten für die Auswahl gefunden.", "error")
            return redirect(url_for("data_io.export_selection"))

        if export_format == "xlsx":
            output = generate_excel_export(participants_to_export)
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            extension = "xlsx"
        else:
            output = generate_csv_export(participants_to_export)
            mimetype = "text/csv"
            extension = "csv"

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"staerkenanalyse_export_{timestamp}.{extension}"
        return Response(
            output,
            mimetype=mimetype,
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
    except Exception as e:
        flash(f"Fehler beim Exportieren der Daten: {str(e)}", "error")
        return redirect(url_for("data_io.export_selection"))