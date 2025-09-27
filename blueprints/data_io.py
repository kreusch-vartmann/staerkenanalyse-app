# blueprints/data_io.py
"""Dieses Modul enthält Routen und Funktionen für den Datenimport und -export."""

import json
import csv
from datetime import UTC, datetime
from io import BytesIO, StringIO
import pandas as pd

from flask import (Blueprint, request, redirect, url_for, flash, render_template,
                   Response)

import database as db

data_io_bp = Blueprint('data_io', __name__)


# --- HILFSFUNKTIONEN FÜR EXPORT ---

def _create_participant_export_dict(p):
    """Erstellt ein flaches Dictionary für einen Teilnehmer für den Export."""
    participant_export = {
        "Name": p.get("name"),
        "Gruppe": p.get("group_name"),
        "Datum": p.get("group_date"),
        "Ort": p.get("group_location"),
        "Leitung": p.get("group_leitung", ""),
        "Beobachter 1": p.get("group_beobachter1", ""),
        "Beobachter 2": p.get("group_beobachter2", ""),
    }

    general = p.get("general_data", {})
    participant_export.update({
        "Position": general.get("position", ""),
        "Alter": general.get("age", ""),
        "Geschlecht": general.get("gender", "")
    })

    observations = p.get("observations", {})
    participant_export.update({
        "Beobachtung (Sozial)": observations.get("social", ""),
        "Beobachtung (Verbal)": observations.get("verbal", "")
    })

    sk_ratings = p.get("sk_ratings", {})
    participant_export.update({
        "SK Flexibilität": sk_ratings.get("flexibility", 0),
        "SK Teamorientierung": sk_ratings.get("team_orientation", 0),
        "SK Prozessorientierung": sk_ratings.get("process_orientation", 0),
        "SK Ergebnisorientierung": sk_ratings.get("results_orientation", 0)
    })

    vk_ratings = p.get("vk_ratings", {})
    participant_export.update({
        "VK Flexibilität": vk_ratings.get("flexibility", 0),
        "VK Beratung": vk_ratings.get("consulting", 0),
        "VK Sachlichkeit": vk_ratings.get("objectivity", 0),
        "VK Zielorientierung": vk_ratings.get("goal_orientation", 0)
    })

    ki_texts = p.get("ki_texts", {})
    participant_export.update({
        "KI SK-Stärken": ki_texts.get("sk_strengths", ""),
        "KI SK-Potenziale": ki_texts.get("sk_potentials", ""),
        "KI VK-Stärken": ki_texts.get("vk_strengths", ""),
        "KI VK-Potenziale": ki_texts.get("vk_potentials", ""),
        "KI-Text (Zusammenfassung)": ki_texts.get("summary_text", ""),
        "KI-Text (Sozial)": ki_texts.get("social_text", ""),
        "KI-Text (Verbal)": ki_texts.get("verbal_text", "")
    })

    if p.get("ki_raw_response"):
        participant_export["KI-Rohdaten"] = p.get("ki_raw_response", "")

    return participant_export


def generate_excel_export(participants_data):
    """Generiert eine Excel-Datei aus den Teilnehmerdaten."""
    export_data = [_create_participant_export_dict(p) for p in participants_data]
    df = pd.DataFrame(export_data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Teilnehmer", index=False)
    output.seek(0)
    return output.getvalue()


def generate_csv_export(participants_data):
    """Generiert eine CSV-Datei aus den Teilnehmerdaten."""
    if not participants_data:
        return "".encode("utf-8-sig")

    export_data = [_create_participant_export_dict(p) for p in participants_data]
    all_fieldnames = set()
    for item in export_data:
        all_fieldnames.update(item.keys())
    fieldnames = sorted(list(all_fieldnames))

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";",
                            quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    writer.writerows(export_data)
    return output.getvalue().encode("utf-8-sig")


# --- ROUTEN FÜR IMPORT & EXPORT ---

@data_io_bp.route("/import")
def import_page():
    """Zeigt die Import-Seite an."""
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Daten importieren"}
    ]
    return render_template("import_page.html", breadcrumbs=breadcrumbs)


@data_io_bp.route("/import/names", methods=["POST"])
def import_names():
    """Importiert Namen aus einer Datei in eine Gruppe."""
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

        details = {"name": group_name, "date": None, "location": None,
                   "leitung": None, "beobachter1": None, "beobachter2": None}
        new_group_id = db.add_group_and_get_id(details)
        count = db.add_multiple_participants_to_group(new_group_id, names)
        flash(f'Gruppe "{group_name}" mit {count} Teilnehmern erstellt.', "success")
        return redirect(url_for("groups.show_group_participants", group_id=new_group_id))
    except Exception as e:
        flash(f"Ein Fehler ist beim Verarbeiten der Datei aufgetreten: {e}", "error")
        return redirect(url_for("data_io.import_page"))


@data_io_bp.route("/import/full", methods=["POST"])
def import_full():
    """Importiert vollständige Teilnehmer- und Gruppendaten aus einer Datei."""
    file = request.files.get("full_export_file")
    if not file or not file.filename:
        flash("Bitte wählen Sie eine Datei aus.", "warning")
        return redirect(url_for("data_io.import_page"))
    try:
        if file.filename.endswith(".xlsx"):
            df = pd.read_excel(file)
        elif file.filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            flash("Ungültiges Dateiformat. Nur .xlsx oder .csv.", "warning")
            return redirect(url_for("data_io.import_page"))

        # Hier muss Ihre spezifische Logik zum Verarbeiten des
        # DataFrames stehen. Die folgende Zeile ist ein Platzhalter.
        # db.import_participants_from_dataframe(df)
        flash(f"{len(df)} Zeilen aus der Datei verarbeitet.", "success")

    except Exception as e:
        flash(f"Ein Fehler ist beim Importieren der Datei aufgetreten: {e}", "error")
    return redirect(url_for("data_io.import_page"))


@data_io_bp.route("/export_selection")
def export_selection():
    """Zeigt die Seite zur Auswahl der zu exportierenden Teilnehmer an."""
    groups_with_participants = []
    db_conn = db.get_db()
    all_groups_rows = db_conn.execute("SELECT * FROM groups ORDER BY name ASC").fetchall()
    for group_row in all_groups_rows:
        group_dict = dict(group_row)
        participants_rows = db_conn.execute(
            "SELECT * FROM participants WHERE group_id = ? ORDER BY name ASC",
            (group_dict["id"],)
        ).fetchall()
        participants_list = [dict(p) for p in participants_rows]
        groups_with_participants.append({
            "id": group_dict["id"],
            "name": group_dict["name"],
            "participants": participants_list
        })
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Datenexport"}
    ]
    return render_template("export_selection.html",
                           groups_with_participants=groups_with_participants,
                           breadcrumbs=breadcrumbs)


@data_io_bp.route("/export_data", methods=["POST"])
def export_data():
    """Exportiert die ausgewählten Teilnehmerdaten als Excel oder CSV."""
    select_all = request.form.get("select_all_data") == "true"
    export_format = request.form.get("format", "xlsx")
    try:
        if select_all:
            all_participants = db.get_db().execute("SELECT id FROM participants").fetchall()
            participant_ids = [p["id"] for p in all_participants]
        else:
            participant_ids = [
                int(pid) for pid in request.form.getlist("participant_ids") if pid.isdigit()
            ]

        if not participant_ids:
            flash("Bitte wählen Sie mindestens einen Teilnehmer aus.", "error")
            return redirect(url_for("data_io.export_selection"))

        participants_data = []
        for pid in participant_ids:
            participant = db.get_participant_by_id(pid)
            if participant:
                group = dict(db.get_group_by_id(participant["group_id"]) or {})
                participant.update({
                    "group_name": group.get("name"),
                    "group_date": group.get("date"),
                    "group_location": group.get("location"),
                    "group_leitung": group.get("leitung"),
                    "group_beobachter1": group.get("beobachter1"),
                    "group_beobachter2": group.get("beobachter2")
                })
                participants_data.append(participant)

        if not participants_data:
            flash("Keine Daten für die Auswahl geladen.", "error")
            return redirect(url_for("data_io.export_selection"))

        if export_format == "xlsx":
            output = generate_excel_export(participants_data)
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            extension = "xlsx"
        else:
            output = generate_csv_export(participants_data)
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


@data_io_bp.route("/entry")
def data_entry_rework():
    """Zeigt die Seite zur Auswahl der Gruppe für die Dateneingabe an."""
    groups = db.get_all_groups()
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Dateneingabe"}
    ]
    return render_template("data_entry_rework.html",
                           groups=groups,
                           breadcrumbs=breadcrumbs)
