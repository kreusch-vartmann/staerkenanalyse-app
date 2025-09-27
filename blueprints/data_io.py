# blueprints/data_io.py
"""Dieses Modul enthält Routen und Funktionen für den Datenimport und -export."""

import json
from datetime import UTC, datetime
from io import BytesIO
import pandas as pd
import csv
from io import StringIO

from flask import (Blueprint, request, redirect, url_for, flash, render_template,
                   jsonify, Response)

import database as db

# Ein Blueprint-Objekt für Daten-Import und -Export
data_io_bp = Blueprint('data_io', __name__)


# --- HILFSFUNKTIONEN FÜR EXPORT ---

def generate_excel_export(participants_data):
    """Generiert eine Excel-Datei aus den Teilnehmerdaten."""
    try:
        export_data = []
        for p in participants_data:
            participant_export = {
                "Name": p.get("name"), "Gruppe": p.get("group_name"), "Datum": p.get("group_date"),
                "Ort": p.get("group_location"), "Leitung": p.get("group_leitung", ""),
                "Beobachter 1": p.get("group_beobachter1", ""), "Beobachter 2": p.get("group_beobachter2", ""),
            }
            general = p.get("general_data", {}); participant_export.update({"Position": general.get("position", ""), "Alter": general.get("age", ""), "Geschlecht": general.get("gender", "")})
            observations = p.get("observations", {}); participant_export.update({"Beobachtung (Sozial)": observations.get("social", ""), "Beobachtung (Verbal)": observations.get("verbal", "")})
            sk_ratings = p.get("sk_ratings", {}); participant_export.update({"SK Flexibilität": sk_ratings.get("flexibility", 0), "SK Teamorientierung": sk_ratings.get("team_orientation", 0), "SK Prozessorientierung": sk_ratings.get("process_orientation", 0), "SK Ergebnisorientierung": sk_ratings.get("results_orientation", 0)})
            vk_ratings = p.get("vk_ratings", {}); participant_export.update({"VK Flexibilität": vk_ratings.get("flexibility", 0), "VK Beratung": vk_ratings.get("consulting", 0), "VK Sachlichkeit": vk_ratings.get("objectivity", 0), "VK Zielorientierung": vk_ratings.get("goal_orientation", 0)})
            ki_texts = p.get("ki_texts", {}); participant_export.update({"KI SK-Stärken": ki_texts.get("sk_strengths", ""), "KI SK-Potenziale": ki_texts.get("sk_potentials", ""), "KI VK-Stärken": ki_texts.get("vk_strengths", ""), "KI VK-Potenziale": ki_texts.get("vk_potentials", ""), "KI-Text (Zusammenfassung)": ki_texts.get("summary_text", ""), "KI-Text (Sozial)": ki_texts.get("social_text", ""), "KI-Text (Verbal)": ki_texts.get("verbal_text", "")})
            if p.get("ki_raw_response"): participant_export["KI-Rohdaten"] = p.get("ki_raw_response", "")
            export_data.append(participant_export)

        df = pd.DataFrame(export_data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Teilnehmer", index=False)
        output.seek(0)
        return output.getvalue()
    except ImportError:
        flash("Pandas und openpyxl sind erforderlich für Excel-Exporte.", "error")
        raise Exception("Fehlende Abhängigkeiten für Excel-Export")


def generate_csv_export(participants_data):
    """Generiert eine CSV-Datei aus den Teilnehmerdaten."""
    output = StringIO()
    fieldnames = set(["Name", "Gruppe", "Datum", "Ort", "Leitung", "Beobachter 1", "Beobachter 2"])
    for p in participants_data:
        if p.get("general_data"): fieldnames.update(["Position", "Alter", "Geschlecht"])
        if p.get("observations"): fieldnames.update(["Beobachtung (Sozial)", "Beobachtung (Verbal)"])
        if p.get("sk_ratings"): fieldnames.update(["SK Flexibilität", "SK Teamorientierung", "SK Prozessorientierung", "SK Ergebnisorientierung"])
        if p.get("vk_ratings"): fieldnames.update(["VK Flexibilität", "VK Beratung", "VK Sachlichkeit", "VK Zielorientierung"])
        if p.get("ki_texts"): fieldnames.update(["KI SK-Stärken", "KI SK-Potenziale", "KI VK-Stärken", "KI VK-Potenziale", "KI-Text (Zusammenfassung)", "KI-Text (Sozial)", "KI-Text (Verbal)"])
        if p.get("ki_raw_response"): fieldnames.add("KI-Rohdaten")
    
    sorted_fields = sorted(list(fieldnames))
    writer = csv.DictWriter(output, fieldnames=sorted_fields, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()

    for p in participants_data:
        row = {"Name": p.get("name"), "Gruppe": p.get("group_name"),"Datum": p.get("group_date"), "Ort": p.get("group_location"), "Leitung": p.get("group_leitung", ""), "Beobachter 1": p.get("group_beobachter1", ""), "Beobachter 2": p.get("group_beobachter2", "")}
        general = p.get("general_data", {}); row.update({"Position": general.get("position", ""), "Alter": general.get("age", ""), "Geschlecht": general.get("gender", "")})
        observations = p.get("observations", {}); row.update({"Beobachtung (Sozial)": observations.get("social", ""), "Beobachtung (Verbal)": observations.get("verbal", "")})
        sk_ratings = p.get("sk_ratings", {}); row.update({"SK Flexibilität": sk_ratings.get("flexibility", 0), "SK Teamorientierung": sk_ratings.get("team_orientation", 0), "SK Prozessorientierung": sk_ratings.get("process_orientation", 0), "SK Ergebnisorientierung": sk_ratings.get("results_orientation", 0)})
        vk_ratings = p.get("vk_ratings", {}); row.update({"VK Flexibilität": vk_ratings.get("flexibility", 0), "VK Beratung": vk_ratings.get("consulting", 0), "VK Sachlichkeit": vk_ratings.get("objectivity", 0), "VK Zielorientierung": vk_ratings.get("goal_orientation", 0)})
        ki_texts = p.get("ki_texts", {}); row.update({"KI SK-Stärken": ki_texts.get("sk_strengths", ""), "KI SK-Potenziale": ki_texts.get("sk_potentials", ""), "KI VK-Stärken": ki_texts.get("vk_strengths", ""), "KI VK-Potenziale": ki_texts.get("vk_potentials", ""),"KI-Text (Zusammenfassung)": ki_texts.get("summary_text", ""), "KI-Text (Sozial)": ki_texts.get("social_text", ""), "KI-Text (Verbal)": ki_texts.get("verbal_text", "")})
        if p.get("ki_raw_response"): row["KI-Rohdaten"] = p.get("ki_raw_response", "")
        writer.writerow(row)
        
    return output.getvalue().encode("utf-8-sig")


# --- ROUTEN FÜR IMPORT & EXPORT ---

@data_io_bp.route("/import")
def import_page():
    """Zeigt die Import-Seite an."""
    breadcrumbs = [{"link": url_for("dashboard"), "text": "Dashboard"}, {"text": "Daten importieren"}]
    return render_template("import_page.html", breadcrumbs=breadcrumbs)

@data_io_bp.route("/import/names", methods=["POST"])
def import_names():
    """Importiert Namen aus einer Datei in eine Gruppe."""
    group_name = request.form.get("group_name")
    file = request.files.get("name_file")
    if not group_name or not file or file.filename == "":
        flash("Bitte geben Sie einen Gruppennamen an und wählen Sie eine Datei aus.", "warning")
        return redirect(url_for("data_io.import_page"))
    try:
        content = file.read().decode("utf-8")
        names = [name.strip() for name in content.splitlines() if name.strip()]
        if not names:
            flash("Die ausgewählte Datei enthält keine gültigen Namen.", "warning")
            return redirect(url_for("data_io.import_page"))
        new_group_id = db.add_group_and_get_id(group_name)
        count = db.add_multiple_participants_to_group(new_group_id, names)
        flash(f'Gruppe "{group_name}" wurde erfolgreich mit {count} Teilnehmern erstellt.', "success")
        return redirect(url_for("groups.show_group_participants", group_id=new_group_id))
    except Exception as e:
        flash(f"Ein Fehler ist beim Verarbeiten der Datei aufgetreten: {e}", "error")
        return redirect(url_for("data_io.import_page"))

@data_io_bp.route("/import/full", methods=["POST"])
def import_full():
    """Importiert vollständige Teilnehmer- und Gruppendaten aus einer Excel- oder CSV-Datei."""
    file = request.files.get("full_export_file")
    if not file or file.filename == "":
        flash("Bitte wählen Sie eine Datei aus.", "warning")
        return redirect(url_for("data_io.import_page"))
    try:
        if file.filename.endswith(".xlsx"): df = pd.read_excel(file)
        elif file.filename.endswith(".csv"): df = pd.read_csv(file)
        else:
            flash("Ungültiges Dateiformat. Bitte eine .xlsx oder .csv Datei hochladen.", "warning")
            return redirect(url_for("data_io.import_page"))

        all_groups = {dict(g)["name"]: g["id"] for g in db.get_all_groups()}
        participants_to_add = []
        groups_added_count = 0
        for index, row in df.iterrows():
            group_name = row.get("Gruppe")
            if pd.isna(group_name): continue
            if group_name not in all_groups:
                new_group_id = db.add_group_and_get_id(group_name, date=row.get("Gruppen-Datum"), location=row.get("Gruppen-Ort"))
                all_groups[group_name] = new_group_id; groups_added_count += 1
            group_id = all_groups[group_name]
            observations_json = json.dumps({"social": str(row.get("Beobachtung (Sozial)", "")) if pd.notna(row.get("Beobachtung (Sozial)")) else "", "verbal": str(row.get("Beobachtung (Verbal)", "")) if pd.notna(row.get("Beobachtung (Verbal)")) else ""})
            sk_ratings_json = json.dumps({"flexibility": row.get("SK - Flexibilität"), "team_orientation": row.get("SK - Teamorientierung"), "process_orientation": row.get("SK - Prozessorientierung"), "results_orientation": row.get("SK - Ergebnisorientierung")})
            vk_ratings_json = json.dumps({"flexibility": row.get("VK - Flexibilität"), "consulting": row.get("VK - Beratung"), "objectivity": row.get("VK - Sachlichkeit"), "goal_orientation": row.get("VK - Zielorientierung")})
            ki_texts_json = json.dumps({"social_text": str(row.get("KI-Text (Sozial)", "")) if pd.notna(row.get("KI-Text (Sozial)")) else "", "verbal_text": str(row.get("KI-Text (Verbal)", "")) if pd.notna(row.get("KI-Text (Verbal)")) else "", "summary_text": str(row.get("KI-Text (Zusammenfassung)", "")) if pd.notna(row.get("KI-Text (Zusammenfassung)")) else ""})
            participants_to_add.append((group_id, row.get("Name"), observations_json, sk_ratings_json, vk_ratings_json, ki_texts_json))
        
        if participants_to_add:
            db_conn = db.get_db(); cursor = db_conn.cursor()
            cursor.executemany("INSERT INTO participants (group_id, name, observations, sk_ratings, vk_ratings, ki_texts) VALUES (?, ?, ?, ?, ?, ?)", participants_to_add)
            db_conn.commit()

        flash(f"Import erfolgreich! {groups_added_count} neue Gruppen und {len(participants_to_add)} Teilnehmer hinzugefügt.", "success")
        return redirect(url_for("groups.manage_groups"))
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
        participants_rows = db_conn.execute("SELECT * FROM participants WHERE group_id = ? ORDER BY name ASC", (group_dict["id"],)).fetchall()
        participants_list = [dict(p) for p in participants_rows]
        groups_with_participants.append({"id": group_dict["id"], "name": group_dict["name"], "participants": participants_list})
    breadcrumbs = [{"link": url_for("dashboard"), "text": "Dashboard"}, {"text": "Datenexport"}]
    return render_template("export_selection.html", groups_with_participants=groups_with_participants, breadcrumbs=breadcrumbs)


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
            participant_ids = [int(pid) for pid in request.form.getlist("participant_ids") if pid.isdigit()]

        if not participant_ids:
            flash("Bitte wählen Sie mindestens einen Teilnehmer aus.", "error")
            return redirect(url_for("data_io.export_selection"))

        participants_data = []
        for pid in participant_ids:
            participant = db.get_participant_by_id(pid)
            if participant:
                group_row = db.get_group_by_id(participant["group_id"])
                if group_row:
                    # KORREKTUR: Wandle das 'sqlite3.Row'-Objekt in ein Dictionary um
                    group = dict(group_row)
                    
                    # Jetzt sind alle Zugriffe sicher
                    participant["group_name"] = group.get("name")
                    participant["group_date"] = group.get("date")
                    participant["group_location"] = group.get("location")
                    participant["group_leitung"] = group.get("leitung")
                    participant["group_beobachter1"] = group.get("beobachter1")
                    participant["group_beobachter2"] = group.get("beobachter2")
                
                participants_data.append(participant)
        
        if not participants_data:
            flash("Konnte keine Daten für die ausgewählten Teilnehmer laden.", "error")
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
        return Response(output, mimetype=mimetype, headers={"Content-Disposition": f"attachment;filename={filename}"})

    except Exception as e:
        flash(f"Fehler beim Exportieren der Daten: {str(e)}", "error")
        return redirect(url_for("data_io.export_selection"))

@data_io_bp.route("/entry")
def data_entry_rework():
    """Zeigt die Seite zur Auswahl der Gruppe für die Dateneingabe an."""
    groups = db.get_all_groups()
    breadcrumbs = [{"link": url_for("dashboard"), "text": "Dashboard"}, {"text": "Dateneingabe"}]
    return render_template("data_entry_rework.html", groups=groups, breadcrumbs=breadcrumbs)