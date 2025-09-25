"""
Hauptanwendung für das Stärkenanalyse-Tool.
"""

import io
import json
import os
from datetime import UTC, datetime

import pandas as pd
from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

import database as db
from ki_services import generate_report_with_ai
from utils import clean_json_response, get_file_content

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.teardown_appcontext
def close_connection(_exception):
    """Schließt die Datenbankverbindung am Ende der Anfrage."""
    db.close_db()


@app.context_processor
def inject_now():
    """Fügt das aktuelle Jahr zur Vorlage hinzu."""
    return {"current_year": datetime.now(UTC).year}


@app.template_filter("datetimeformat")
def datetimeformat(value, fmt="%d.%m.%Y"):
    """Formatiert ein Datum gemäß dem angegebenen Format."""
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, str):
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            return dt.strftime(fmt)
        except ValueError:
            try:
                dt = datetime.strptime(value, "%d.%m.%Y")
                return dt.strftime(fmt)
            except ValueError:
                return value
    return value


@app.route("/")
def dashboard():
    """Zeigt das Dashboard mit Statistiken und kürzlich aktualisierten Teilnehmern an."""
    stats = db.get_dashboard_stats()
    recently_updated = db.get_recently_updated_participants()
    breadcrumbs = [{"text": "Dashboard"}]
    return render_template(
        "dashboard.html",
        breadcrumbs=breadcrumbs,
        stats=stats,
        recently_updated_participants=recently_updated,
    )

@app.route("/import")
def import_page():
    """Zeigt die Import-Seite an."""
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Daten importieren"},
    ]
    return render_template("import_page.html", breadcrumbs=breadcrumbs)


@app.route("/import/names", methods=["POST"])
def import_names():
    """Importiert Namen aus einer Datei in eine Gruppe."""
    group_name = request.form.get("group_name")
    file = request.files.get("name_file")

    if not group_name or not file or file.filename == "":
        flash(
            "Bitte geben Sie einen Gruppennamen an und wählen Sie eine Datei aus.",
            "warning",
        )
        return redirect(url_for("import_page"))

    try:
        content = file.read().decode("utf-8")
        names = [name.strip() for name in content.splitlines() if name.strip()]

        if not names:
            flash("Die ausgewählte Datei enthält keine gültigen Namen.", "warning")
            return redirect(url_for("import_page"))

        new_group_id = db.add_group_and_get_id(group_name)
        count = db.add_multiple_participants_to_group(new_group_id, names)

        flash(
            f'Gruppe "{group_name}" wurde erfolgreich mit {count} Teilnehmern erstellt.',
            "success",
        )
        return redirect(url_for("show_group_participants", group_id=new_group_id))

    except Exception as e:
        flash(f"Ein Fehler ist beim Verarbeiten der Datei aufgetreten: {e}", "error")
        return redirect(url_for("import_page"))


@app.route("/import/full", methods=["POST"])
def import_full():
    """Importiert vollständige Teilnehmer- und Gruppendaten aus einer Excel- oder CSV-Datei."""
    file = request.files.get("full_export_file")

    if not file or file.filename == "":
        flash("Bitte wählen Sie eine Datei aus.", "warning")
        return redirect(url_for("import_page"))

    try:
        if file.filename.endswith(".xlsx"):
            df = pd.read_excel(file)
        elif file.filename.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            flash(
                "Ungültiges Dateiformat. Bitte eine .xlsx oder .csv Datei hochladen.",
                "warning",
            )
            return redirect(url_for("import_page"))

        all_groups = {dict(g)["name"]: g["id"] for g in db.get_all_groups()}
        participants_to_add = []
        groups_added_count = 0

        for index, row in df.iterrows():
            group_name = row.get("Gruppe")
            if pd.isna(group_name):
                continue

            if group_name not in all_groups:
                new_group_id = db.add_group_and_get_id(
                    group_name,
                    date=row.get("Gruppen-Datum"),
                    location=row.get("Gruppen-Ort"),
                )
                all_groups[group_name] = new_group_id
                groups_added_count += 1

            group_id = all_groups[group_name]

            # Beobachtungen als JSON vorbereiten
            observations_json = json.dumps(
                {
                    "social": (
                        str(row.get("Beobachtung (Sozial)", ""))
                        if pd.notna(row.get("Beobachtung (Sozial)"))
                        else ""
                    ),
                    "verbal": (
                        str(row.get("Beobachtung (Verbal)", ""))
                        if pd.notna(row.get("Beobachtung (Verbal)"))
                        else ""
                    ),
                }
            )

            # SK-Ratings als JSON vorbereiten
            sk_ratings_json = json.dumps(
                {
                    "flexibility": row.get("SK - Flexibilität"),
                    "team_orientation": row.get("SK - Teamorientierung"),
                    "process_orientation": row.get("SK - Prozessorientierung"),
                    "results_orientation": row.get("SK - Ergebnisorientierung"),
                }
            )

            # VK-Ratings als JSON vorbereiten
            vk_ratings_json = json.dumps(
                {
                    "flexibility": row.get("VK - Flexibilität"),
                    "consulting": row.get("VK - Beratung"),
                    "objectivity": row.get("VK - Sachlichkeit"),
                    "goal_orientation": row.get("VK - Zielorientierung"),
                }
            )

            # KI-Texte als JSON vorbereiten
            ki_texts_json = json.dumps(
                {
                    "social_text": (
                        str(row.get("KI-Text (Sozial)", ""))
                        if pd.notna(row.get("KI-Text (Sozial)"))
                        else ""
                    ),
                    "verbal_text": (
                        str(row.get("KI-Text (Verbal)", ""))
                        if pd.notna(row.get("KI-Text (Verbal)"))
                        else ""
                    ),
                    "summary_text": (
                        str(row.get("KI-Text (Zusammenfassung)", ""))
                        if pd.notna(row.get("KI-Text (Zusammenfassung)"))
                        else ""
                    ),
                }
            )

            participant_data = (
                group_id,
                row.get("Name"),
                observations_json,
                sk_ratings_json,
                vk_ratings_json,
                ki_texts_json,
            )
            participants_to_add.append(participant_data)

        if participants_to_add:
            db_conn = db.get_db()
            cursor = db_conn.cursor()
            cursor.executemany(
                """INSERT INTO participants 
                   (group_id, name, observations, sk_ratings, vk_ratings, ki_texts) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                participants_to_add,
            )
            db_conn.commit()

        flash(
            f"Import erfolgreich! {groups_added_count} neue Gruppen und "
            f"{len(participants_to_add)} Teilnehmer hinzugefügt.",
            "success",
        )
        return redirect(url_for("manage_groups"))

    except Exception as e:
        flash(f"Ein Fehler ist beim Importieren der Datei aufgetreten: {e}", "error")
        return redirect(url_for("import_page"))


@app.route("/groups")
def manage_groups():
    """Zeigt die Seite zur Verwaltung von Gruppen an."""
    page = request.args.get("page", 1, type=int)
    pagination, groups = db.get_paginated_groups(page)
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Gruppen"},
    ]
    return render_template(
        "manage_groups.html",
        groups=groups,
        pagination=pagination,
        breadcrumbs=breadcrumbs,
    )


@app.route("/participants")
def manage_participants():
    """Zeigt die Seite zur Verwaltung von Teilnehmern an."""
    page = request.args.get("page", 1, type=int)
    search_query = request.args.get("q", "")
    sort_order = request.args.get("sort", "name_asc")
    pagination, participants = db.get_paginated_participants(
        page, search_query, sort_order
    )
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Teilnehmer"},
    ]
    return render_template(
        "manage_participants.html",
        participants=participants,
        pagination=pagination,
        breadcrumbs=breadcrumbs,
    )


@app.route("/group/<int:group_id>/participants")
def show_group_participants(group_id):
    """Zeigt die Teilnehmer einer bestimmten Gruppe an."""
    group = db.get_group_by_id(group_id)
    participants = db.get_participants_by_group(group_id)
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("manage_groups"), "text": "Gruppen"},
        {"text": group["name"]},
    ]
    return render_template(
        "participants.html",
        group=group,
        participants=participants,
        breadcrumbs=breadcrumbs,
    )


@app.route("/group/add", methods=["POST"])
def add_group():
    """fügt eine neue Gruppe hinzu."""
    details = {
        k: request.form.get(k)
        for k in ["name", "date", "location", "leitung", "beobachter1", "beobachter2"]
    }
    db.add_group(**details)
    flash(f'Gruppe "{details["name"]}" wurde erfolgreich hinzugefügt.', "success")
    return redirect(url_for("manage_groups"))


@app.route("/group/edit/<int:group_id>", methods=["POST"])
def edit_group(group_id):
    """Aktualisiert die Details einer bestehenden Gruppe."""
    details = {
        "name": request.form.get("group_name"),
        "date": request.form.get("group_date"),
        "location": request.form.get("group_location"),
        "leitung": request.form.get("group_leitung"),
        "beobachter1": request.form.get("beobachter1"),
        "beobachter2": request.form.get("beobachter2"),
    }
    db.update_group_details(group_id, details)
    flash("Gruppe erfolgreich aktualisiert.", "success")
    return redirect(url_for("manage_groups"))


@app.route("/group/delete/<int:group_id>", methods=["POST"])
def delete_group(group_id):
    """Entfernt eine Gruppe und alle zugehörigen Teilnehmer."""
    db.delete_group_by_id(group_id)
    flash("Gruppe und alle zugehörigen Teilnehmer wurden gelöscht.", "success")
    return redirect(url_for("manage_groups"))


@app.route("/group/<int:group_id>/participant/add", methods=["POST"])
def add_participant(group_id):
    """Fügt mehrere Teilnehmer zu einer Gruppe hinzu."""
    names_input = request.form.get("participant_names", "")
    valid_names = [name.strip() for name in names_input.splitlines() if name.strip()]
    if valid_names:
        count = db.add_multiple_participants_to_group(group_id, valid_names)
        flash(f"{count} Teilnehmer wurden hinzugefügt.", "success")
    else:
        flash("Keine gültigen Namen eingegeben.", "warning")
    return redirect(url_for("show_group_participants", group_id=group_id))


@app.route("/participant/edit/<int:participant_id>", methods=["POST"])
def edit_participant(participant_id):
    """Aktualisiert den Namen eines Teilnehmers."""
    new_name, group_id = request.form["new_name"], request.form["group_id"]
    if new_name:
        db.update_participant_name(participant_id, new_name)
        flash("Teilnehmername wurde aktualisiert.", "success")
    return redirect(url_for("show_group_participants", group_id=group_id))


@app.route("/participant/delete/<int:participant_id>", methods=["POST"])
def delete_participant(participant_id):
    """Löscht einen Teilnehmer."""
    group_id = request.form["group_id"]
    db.delete_participant_by_id(participant_id)
    flash("Teilnehmer wurde gelöscht.", "success")
    return redirect(url_for("show_group_participants", group_id=group_id))


@app.route("/participant/<int:participant_id>/data_entry")
def show_data_entry(participant_id):
    """Zeigt die Dateneingabeseite für einen Teilnehmer an."""
    participant = db.get_participant_by_id(participant_id)
    if participant:
        group = db.get_group_by_id(participant["group_id"])
        breadcrumbs = [
            {"link": url_for("dashboard"), "text": "Dashboard"},
            {"link": url_for("manage_groups"), "text": "Gruppen"},
            {
                "link": url_for("show_group_participants", group_id=group["id"]),
                "text": group["name"],
            },
            {"text": f"Dateneingabe: {participant['name']}"},
        ]
        return render_template(
            "data_entry.html",
            participant=participant,
            group=group,
            breadcrumbs=breadcrumbs,
            prompts=db.get_all_prompts(),
        )
    flash("Teilnehmer nicht gefunden.", "error")
    return redirect(url_for("manage_participants"))


@app.route("/participant/<int:participant_id>/report")
def show_report(participant_id):
    """Zeigt den Bericht für einen bestimmten Teilnehmer an."""
    participant = db.get_participant_by_id(participant_id)
    if not participant:
        flash("Teilnehmer nicht gefunden.", "error")
        return redirect(url_for("manage_participants"))

    group = db.get_group_by_id(participant["group_id"])
    full_name = participant.get("name", "")
    participant["first_name"] = full_name.split(" ")[0] if full_name else ""

    current_location_for_footer = "Lingen (Ems)"
    current_date_for_footer = datetime.now().strftime("%d.%m.%Y")

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("manage_groups"), "text": "Gruppen"},
        {
            "link": url_for("show_group_participants", group_id=group["id"]),
            "text": group["name"],
        },
        {"text": f"Bericht: {participant['name']}"},
    ]

    return render_template(
        "staerkenanalyse_bericht_vorlage3.html",
        participant=participant,
        group=group,
        breadcrumbs=breadcrumbs,
        current_date=current_date_for_footer,
        current_location=current_location_for_footer,
    )


@app.route("/entry")
def data_entry_rework():
    """Zeigt die Seite zur Auswahl der Gruppe für die Dateneingabe an."""
    groups = db.get_all_groups()
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Dateneingabe"},
    ]
    return render_template(
        "data_entry_rework.html", groups=groups, breadcrumbs=breadcrumbs
    )


@app.route("/ai_analysis/select_group")
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


@app.route("/ai_analysis/group/<int:group_id>")
def ai_analysis_select_participants(group_id):
    """Zeigt die Seite zur Auswahl der Teilnehmer für die KI-Analyse an."""
    group = db.get_group_by_id(group_id)
    participants = db.get_participants_by_group(group_id)
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("ai_analysis_select_group"), "text": "KI-Analyse"},
        {"text": f"Auswahl für: {group['name']}"},
    ]
    return render_template(
        "ai_analysis_select_participants.html",
        group=group,
        participants=participants,
        breadcrumbs=breadcrumbs,
    )


@app.route("/ai_analysis/configure", methods=["POST"])
def configure_batch_ai_analysis():
    """Zeigt die Seite zur Konfiguration der KI-Analyse für ausgewählte Teilnehmer an."""
    participant_ids = request.form.getlist("participant_ids")
    if not participant_ids:
        flash("Keine Teilnehmer ausgewählt.", "warning")
        return redirect(url_for("ai_analysis_select_group"))

    participants = [db.get_participant_by_id(pid) for pid in participant_ids]
    group = db.get_group_by_id(participants[0]["group_id"]) if participants else None
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("ai_analysis_select_group"), "text": "KI-Analyse"},
        {
            "link": url_for("ai_analysis_select_participants", group_id=group["id"]),
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


@app.route("/ai_analysis/execute", methods=["POST"])
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
        {"link": url_for("ai_analysis_select_group"), "text": "KI-Analyse"},
        {"text": "Analyse-Status"},
    ]

    return render_template(
        "ai_analysis_status.html",
        participants=participants,
        group=group,
        analysis_data=analysis_data,
        breadcrumbs=breadcrumbs,
    )


@app.route("/export_selection")
def export_selection():
    """Zeigt die Seite zur Auswahl der zu exportierenden Teilnehmer an."""
    groups_with_participants = []
    # Datenbankverbindung holen
    db_conn = db.get_db()

    # Alle Gruppen zählen und abfragen
    group_count = db_conn.execute("SELECT COUNT(id) FROM groups").fetchone()[0]
    print(f"DEBUG: Insgesamt {group_count} Gruppen in der Datenbank gefunden")
    all_groups_rows = db_conn.execute("SELECT * FROM groups").fetchall()
    print(f"DEBUG: {len(all_groups_rows)} Gruppen abgefragt")

    # Gruppen und Teilnehmer aufbereiten
    for group_row in all_groups_rows:
        group_dict = dict(group_row)
        print(
            f"DEBUG: Gruppe gefunden - ID: {group_dict['id']}, "
            f"Name: {group_dict['name']}"
        )

        # Teilnehmer für diese Gruppe holen
        participants_query = """
            SELECT * FROM participants 
            WHERE group_id = ?
        """
        participants_rows = db_conn.execute(
            participants_query, (group_dict["id"],)
        ).fetchall()

        print(
            f"DEBUG: {len(participants_rows)} Teilnehmer für Gruppe "
            f"{group_dict['name']} gefunden"
        )

        # Teilnehmer in Dictionaries umwandeln
        participants_list = [dict(p) for p in participants_rows]

        # Gruppe mit Teilnehmern zur Liste hinzufügen
        groups_with_participants.append(
            {
                "id": group_dict["id"],
                "name": group_dict["name"],
                "participants": participants_list,
            }
        )

    print(
        f"DEBUG: Insgesamt {len(groups_with_participants)} Gruppen "
        f"für Template aufbereitet"
    )

    # Template rendern
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Datenexport"},
    ]
    return render_template(
        "export_selection.html",
        groups_with_participants=groups_with_participants,
        breadcrumbs=breadcrumbs,
    )


@app.route("/export_data", methods=["POST"])
def export_data():
    """Exportiert die ausgewählten Teilnehmerdaten als Excel oder CSV."""
    select_all = request.form.get("select_all_data") == "true"
    export_format = request.form.get("format", "xlsx")

    try:
        # Debug-Information ausgeben
        print(
            f"Export angefordert - Format: {export_format}, "
            f"Alle auswählen: {select_all}"
        )

        # Alle Teilnehmer oder nur ausgewählte laden
        if select_all:
            # Alle Teilnehmer direkt aus der Datenbank holen
            db_conn = db.get_db()
            all_participants = db_conn.execute("SELECT id FROM participants").fetchall()
            participant_ids = [p["id"] for p in all_participants]
            print(f"Alle Teilnehmer ausgewählt: {len(participant_ids)} gefunden")
        else:
            # Nur die ausgewählten IDs aus dem Formular nehmen
            participant_ids = request.form.getlist("participant_ids")
            # Umwandlung in Integer, da Formularwerte als Strings kommen
            participant_ids = [int(pid) for pid in participant_ids if pid.isdigit()]
            print(f"Ausgewählte Teilnehmer-IDs: {participant_ids}")

        if not participant_ids:
            flash("Bitte wählen Sie mindestens einen Teilnehmer aus.", "error")
            return redirect(url_for("export_selection"))

        # Daten für jede ausgewählte ID laden
        db_conn = db.get_db()
        participants_data = []
        for pid in participant_ids:
            participant_row = db.get_participant_by_id(pid)
            if participant_row:
                # WICHTIG: Row in Dictionary umwandeln!
                participant = dict(participant_row)

                # Gruppendaten hinzufügen
                group_row = db.get_group_by_id(participant["group_id"])
                if group_row:
                    # WICHTIG: Row in Dictionary umwandeln!
                    group = dict(group_row)
                    participant["group_name"] = group["name"]
                    participant["group_date"] = group.get("date")
                    participant["group_location"] = group.get("location")
                    # Weitere Gruppendaten
                    participant["group_leitung"] = group.get("leitung")
                    participant["group_beobachter1"] = group.get("beobachter1")
                    participant["group_beobachter2"] = group.get("beobachter2")

                # KI-Rohdaten laden
                try:
                    ki_query = """
                        SELECT response FROM ki_responses 
                        WHERE participant_id = ? 
                        ORDER BY timestamp DESC LIMIT 1
                    """
                    ki_raw_response = db_conn.execute(
                        ki_query, (pid,)
                    ).fetchone()
                    if ki_raw_response:
                        participant["ki_raw_response"] = ki_raw_response["response"]
                except Exception as e:
                    print(
                        f"Fehler beim Laden der KI-Rohdaten für "
                        f"Teilnehmer {pid}: {e}"
                    )

                participants_data.append(participant)
                print(
                    f"Teilnehmer {pid} ({participant.get('name')}) "
                    f"erfolgreich geladen"
                )
            else:
                print(f"Teilnehmer {pid} nicht gefunden")

        if not participants_data:
            flash("Konnte keine Daten für die ausgewählten Teilnehmer laden.", "error")
            return redirect(url_for("export_selection"))

        # Export als Excel oder CSV erzeugen
        if export_format == "xlsx":
            output = generate_excel_export(participants_data)
            mimetype = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            extension = "xlsx"
        else:  # csv
            output = generate_csv_export(participants_data)
            mimetype = "text/csv"
            extension = "csv"

        # Dateinamen generieren
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        filename = f"staerkenanalyse_export_{timestamp}.{extension}"

        # Als Download zurückgeben
        return Response(
            output,
            mimetype=mimetype,
            headers={"Content-Disposition": f"attachment;filename={filename}"},
        )

    except Exception as e:
        import traceback

        print(f"Fehler beim Exportieren: {str(e)}")
        print(traceback.format_exc())
        flash(f"Fehler beim Exportieren der Daten: {str(e)}", "error")
        return redirect(url_for("export_selection"))


def generate_excel_export(participants_data):
    """Generiert eine Excel-Datei aus den Teilnehmerdaten."""
    try:
        from io import BytesIO
        import pandas as pd

        # Datenstruktur für den Export erstellen
        export_data = []

        for p in participants_data:
            # Grunddaten
            participant_export = {
                "Name": p.get("name"),
                "Gruppe": p.get("group_name"),
                "Datum": p.get("group_date"),
                "Ort": p.get("group_location"),
                # Gruppenleitungsdaten
                "Leitung": p.get("group_leitung", ""),
                "Beobachter 1": p.get("group_beobachter1", ""),
                "Beobachter 2": p.get("group_beobachter2", ""),
            }

            # Allgemeine Daten
            general = p.get("general_data", {})
            if general:
                participant_export.update(
                    {
                        "Position": general.get("position", ""),
                        "Alter": general.get("age", ""),
                        "Geschlecht": general.get("gender", ""),
                    }
                )

            # Beobachtungstexte
            observations = p.get("observations", {})
            if observations:
                # Wenn observations ein String ist, versuchen wir es zu parsen
                if isinstance(observations, str):
                    try:
                        import json
                        observations = json.loads(observations)
                    except:
                        observations = {}

                participant_export.update(
                    {
                        "Beobachtung (Sozial)": observations.get("social", ""),
                        "Beobachtung (Verbal)": observations.get("verbal", ""),
                    }
                )

            # Kompetenzbewertungen
            sk_ratings = p.get("sk_ratings", {})
            if sk_ratings:
                # Wenn sk_ratings ein String ist, versuchen wir es zu parsen
                if isinstance(sk_ratings, str):
                    try:
                        import json
                        sk_ratings = json.loads(sk_ratings)
                    except:
                        sk_ratings = {}

                participant_export.update(
                    {
                        "SK Flexibilität": sk_ratings.get("flexibility", 0),
                        "SK Teamorientierung": sk_ratings.get("team_orientation", 0),
                        "SK Prozessorientierung": sk_ratings.get(
                            "process_orientation", 0
                        ),
                        "SK Ergebnisorientierung": sk_ratings.get(
                            "results_orientation", 0
                        ),
                    }
                )

            vk_ratings = p.get("vk_ratings", {})
            if vk_ratings:
                # Wenn vk_ratings ein String ist, versuchen wir es zu parsen
                if isinstance(vk_ratings, str):
                    try:
                        import json
                        vk_ratings = json.loads(vk_ratings)
                    except:
                        vk_ratings = {}

                participant_export.update(
                    {
                        "VK Flexibilität": vk_ratings.get("flexibility", 0),
                        "VK Beratung": vk_ratings.get("consulting", 0),
                        "VK Sachlichkeit": vk_ratings.get("objectivity", 0),
                        "VK Zielorientierung": vk_ratings.get("goal_orientation", 0),
                    }
                )

            # KI-generierte Texte, falls vorhanden
            ki_texts = p.get("ki_texts", {})
            if ki_texts:
                # Wenn ki_texts ein String ist, versuchen wir es zu parsen
                if isinstance(ki_texts, str):
                    try:
                        import json
                        ki_texts = json.loads(ki_texts)
                    except:
                        ki_texts = {}

                participant_export.update(
                    {
                        "KI SK-Stärken": ki_texts.get("sk_strengths", ""),
                        "KI SK-Potenziale": ki_texts.get("sk_potentials", ""),
                        "KI VK-Stärken": ki_texts.get("vk_strengths", ""),
                        "KI VK-Potenziale": ki_texts.get("vk_potentials", ""),
                        # Zusammenfassungstext
                        "KI-Text (Zusammenfassung)": ki_texts.get("summary_text", ""),
                        "KI-Text (Sozial)": ki_texts.get("social_text", ""),
                        "KI-Text (Verbal)": ki_texts.get("verbal_text", ""),
                    }
                )

            # KI-Rohdaten
            if p.get("ki_raw_response"):
                participant_export["KI-Rohdaten"] = p.get("ki_raw_response", "")

            export_data.append(participant_export)

        # Excel-Datei erstellen
        df = pd.DataFrame(export_data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Teilnehmer", index=False)

        output.seek(0)
        return output.getvalue()

    except ImportError:
        flash(
            "Pandas und openpyxl sind erforderlich für Excel-Exporte. "
            "Bitte installieren Sie diese Pakete.",
            "error",
        )
        raise Exception("Fehlende Abhängigkeiten für Excel-Export")


def generate_csv_export(participants_data):
    """Generiert eine CSV-Datei aus den Teilnehmerdaten."""
    import csv
    from io import StringIO

    output = StringIO()

    # Alle möglichen Felder ermitteln (für die Kopfzeile)
    fieldnames = set()
    for p in participants_data:
        # Grundfelder
        fieldnames.update(
            [
                "Name",
                "Gruppe",
                "Datum",
                "Ort",
                # Leitungsdaten
                "Leitung",
                "Beobachter 1",
                "Beobachter 2",
            ]
        )

        # Allgemeine Daten
        if p.get("general_data"):
            fieldnames.update(["Position", "Alter", "Geschlecht"])

        # Beobachtungsfelder
        if p.get("observations"):
            fieldnames.update(["Beobachtung (Sozial)", "Beobachtung (Verbal)"])

        # Kompetenzfelder
        if p.get("sk_ratings"):
            fieldnames.update(
                [
                    "SK Flexibilität",
                    "SK Teamorientierung",
                    "SK Prozessorientierung",
                    "SK Ergebnisorientierung",
                ]
            )

        if p.get("vk_ratings"):
            fieldnames.update(
                [
                    "VK Flexibilität",
                    "VK Beratung",
                    "VK Sachlichkeit",
                    "VK Zielorientierung",
                ]
            )

        # KI-Texte
        if p.get("ki_texts"):
            fieldnames.update(
                [
                    "KI SK-Stärken",
                    "KI SK-Potenziale",
                    "KI VK-Stärken",
                    "KI VK-Potenziale",
                    # Zusätzliche KI-Textfelder
                    "KI-Text (Zusammenfassung)",
                    "KI-Text (Sozial)",
                    "KI-Text (Verbal)",
                ]
            )

        # KI-Rohdaten
        if p.get("ki_raw_response"):
            fieldnames.add("KI-Rohdaten")

    # Sortierte Liste der Feldnamen erstellen
    sorted_fields = sorted(fieldnames)

    # CSV-Writer erstellen
    writer = csv.DictWriter(
        output, fieldnames=sorted_fields, delimiter=";", quoting=csv.QUOTE_MINIMAL
    )
    writer.writeheader()

    # Daten schreiben
    for p in participants_data:
        row = {
            "Name": p.get("name"),
            "Gruppe": p.get("group_name"),
            "Datum": p.get("group_date"),
            "Ort": p.get("group_location"),
            # Leitungsdaten
            "Leitung": p.get("group_leitung", ""),
            "Beobachter 1": p.get("group_beobachter1", ""),
            "Beobachter 2": p.get("group_beobachter2", ""),
        }

        # Allgemeine Daten
        general = p.get("general_data", {})
        if general:
            row.update(
                {
                    "Position": general.get("position", ""),
                    "Alter": general.get("age", ""),
                    "Geschlecht": general.get("gender", ""),
                }
            )

        # Beobachtungstexte
        observations = p.get("observations", {})
        if observations:
            # Wenn observations ein String ist, versuchen wir es zu parsen
            if isinstance(observations, str):
                try:
                    import json
                    observations = json.loads(observations)
                except:
                    observations = {}

            row.update(
                {
                    "Beobachtung (Sozial)": observations.get("social", ""),
                    "Beobachtung (Verbal)": observations.get("verbal", ""),
                }
            )

        # Kompetenzbewertungen
        sk_ratings = p.get("sk_ratings", {})
        if sk_ratings:
            # Wenn sk_ratings ein String ist, versuchen wir es zu parsen
            if isinstance(sk_ratings, str):
                try:
                    import json
                    sk_ratings = json.loads(sk_ratings)
                except:
                    sk_ratings = {}

            row.update(
                {
                    "SK Flexibilität": sk_ratings.get("flexibility", 0),
                    "SK Teamorientierung": sk_ratings.get("team_orientation", 0),
                    "SK Prozessorientierung": sk_ratings.get("process_orientation", 0),
                    "SK Ergebnisorientierung": sk_ratings.get("results_orientation", 0),
                }
            )

        vk_ratings = p.get("vk_ratings", {})
        if vk_ratings:
            # Wenn vk_ratings ein String ist, versuchen wir es zu parsen
            if isinstance(vk_ratings, str):
                try:
                    import json
                    vk_ratings = json.loads(vk_ratings)
                except:
                    vk_ratings = {}

            row.update(
                {
                    "VK Flexibilität": vk_ratings.get("flexibility", 0),
                    "VK Beratung": vk_ratings.get("consulting", 0),
                    "VK Sachlichkeit": vk_ratings.get("objectivity", 0),
                    "VK Zielorientierung": vk_ratings.get("goal_orientation", 0),
                }
            )

        # KI-generierte Texte
        ki_texts = p.get("ki_texts", {})
        if ki_texts:
            # Wenn ki_texts ein String ist, versuchen wir es zu parsen
            if isinstance(ki_texts, str):
                try:
                    import json
                    ki_texts = json.loads(ki_texts)
                except:
                    ki_texts = {}

            row.update(
                {
                    "KI SK-Stärken": ki_texts.get("sk_strengths", ""),
                    "KI SK-Potenziale": ki_texts.get("sk_potentials", ""),
                    "KI VK-Stärken": ki_texts.get("vk_strengths", ""),
                    "KI VK-Potenziale": ki_texts.get("vk_potentials", ""),
                    # Zusammenfassungstext und weitere KI-Texte
                    "KI-Text (Zusammenfassung)": ki_texts.get("summary_text", ""),
                    "KI-Text (Sozial)": ki_texts.get("social_text", ""),
                    "KI-Text (Verbal)": ki_texts.get("verbal_text", ""),
                }
            )

        # KI-Rohdaten
        if p.get("ki_raw_response"):
            row["KI-Rohdaten"] = p.get("ki_raw_response", "")

        writer.writerow(row)

    return output.getvalue().encode(
        "utf-8-sig"  # UTF-8 mit BOM für Excel-Kompatibilität
    )


@app.route("/prompts")
def manage_prompts():
    """Zeigt die Seite zur Verwaltung von Prompts an."""
    prompts = db.get_all_prompts()
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Prompt-Verwaltung"},
    ]
    return render_template(
        "manage_prompts.html", prompts=prompts, breadcrumbs=breadcrumbs
    )


@app.route("/prompt/add", methods=["GET", "POST"])
def add_prompt():
    """Fügt einen neuen Prompt hinzu."""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        content = request.form.get("content")
        
        if not name or not content:
            flash("Name und Inhalt des Prompts dürfen nicht leer sein.", "warning")
            return render_template("prompt_form.html", title="Neuen Prompt erstellen")
            
        db.add_prompt(name, description, content)
        flash(f'Prompt "{name}" wurde erfolgreich erstellt.', "success")
        return redirect(url_for("manage_prompts"))
        
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("manage_prompts"), "text": "Prompt-Verwaltung"},
        {"text": "Neuen Prompt erstellen"},
    ]
    return render_template(
        "prompt_form.html", title="Neuen Prompt erstellen", breadcrumbs=breadcrumbs
    )


@app.route("/prompt/edit/<int:prompt_id>", methods=["GET", "POST"])
def edit_prompt(prompt_id):
    """Bearbeitet einen bestehenden Prompt."""
    prompt = db.get_prompt_by_id(prompt_id)
    if not prompt:
        flash("Prompt nicht gefunden.", "error")
        return redirect(url_for("manage_prompts"))
        
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        content = request.form.get("content")
        
        if not name or not content:
            flash("Name und Inhalt des Prompts dürfen nicht leer sein.", "warning")
            return render_template(
                "prompt_form.html",
                title=f"Prompt bearbeiten: {prompt['name']}",
                prompt=prompt,
            )
            
        db.update_prompt(prompt_id, name, description, content)
        flash(f'Prompt "{name}" wurde erfolgreich aktualisiert.', "success")
        return redirect(url_for("manage_prompts"))
        
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("manage_prompts"), "text": "Prompt-Verwaltung"},
        {"text": f"Prompt bearbeiten: {prompt['name']}"},
    ]
    return render_template(
        "prompt_form.html",
        title=f"Prompt bearbeiten: {prompt['name']}",
        prompt=prompt,
        breadcrumbs=breadcrumbs,
    )


@app.route("/prompt/delete/<int:prompt_id>", methods=["POST"])
def delete_prompt(prompt_id):
    """Löscht einen Prompt."""
    db.delete_prompt_by_id(prompt_id)
    flash("Prompt wurde gelöscht.", "success")
    return redirect(url_for("manage_prompts"))


@app.route("/api/group/<int:group_id>/participants")
def get_participants_for_group(group_id):
    """Gibt die Teilnehmer einer bestimmten Gruppe zurück."""
    return jsonify([dict(p) for p in db.get_participants_by_group(group_id)])


@app.route("/api/participant/<int:participant_id>/observations")
def get_participant_observations(participant_id):
    """Gibt die Beobachtungen eines bestimmten Teilnehmers zurück."""
    p = db.get_participant_by_id(participant_id)
    return jsonify(p.get("observations", {"social": "", "verbal": ""}))


@app.route("/api/prompt/<int:prompt_id>")
def get_prompt_content_api(prompt_id):
    """Gibt den Inhalt eines bestimmten Prompts zurück."""
    prompt = db.get_prompt_by_id(prompt_id)
    if prompt:
        return jsonify({"content": prompt["content"]})
    return jsonify({"error": "Prompt not found"}), 404


@app.route("/save_observations/<int:participant_id>", methods=["POST"])
def save_observations(participant_id):
    """Speichert die Beobachtungen für einen bestimmten Teilnehmer."""
    data = request.get_json()
    if data and "social" in data:
        db.save_participant_data(participant_id, {"observations": data})
        return jsonify({"status": "success", "message": "Beobachtungen gespeichert!"})
    return jsonify({"status": "error", "message": "Ungültige Daten."}), 400


@app.route("/save_report/<int:participant_id>", methods=["POST"])
def save_report(participant_id):
    """Speichert die Berichtsdaten für einen bestimmten Teilnehmer."""
    data = request.get_json()
    db.save_participant_data(
        participant_id,
        {
            "sk_ratings": data.get("sk_ratings"),
            "vk_ratings": data.get("vk_ratings"),
            "ki_texts": data.get("ki_texts"),
        },
    )
    db.save_report_details(
        participant_id, data.get("group_details"), data.get("footer_data")
    )
    return jsonify({"status": "success", "message": "Bericht erfolgreich gespeichert!"})


@app.route("/run_ki_analysis/<int:participant_id>", methods=["POST"])
def run_ki_analysis(participant_id):
    """Führt die KI-Analyse für einen bestimmten Teilnehmer durch."""
    participant = db.get_participant_by_id(participant_id)
    final_prompt = request.form.get("ki_prompt", "")
    ki_model = request.form.get("ki_model", "mistral")
    
    # Namen für den Prompt vorbereiten
    full_name = participant.get("name", "")
    first_name = full_name.split(" ")[0] if full_name else ""
    
    # Platzhalter ersetzen
    final_prompt = (
        final_prompt.replace("{{name}}", first_name)
        .replace("{{vorname}}", first_name)
        .replace("{{first_name}}", first_name)
        .replace("{{ganzer_name}}", full_name)
    )
    
    # Beobachtungen einfügen
    observations = participant.get("observations", {})
    social_obs = observations.get("social", "")
    verbal_obs = observations.get("verbal", "")
    final_prompt = (
        final_prompt.replace("{{social_observations}}", social_obs)
        .replace("{{verbal_observations}}", verbal_obs)
    )
    
    # Zusätzliche Inhalte hinzufügen
    additional_content = ""
    if "additional_files" in request.files:
        file = request.files.get("additional_files")
        if file and file.filename != "":
            additional_content = get_file_content(file)
    final_prompt = final_prompt.replace("{{additional_content}}", additional_content)
    
    # KI-Analyse durchführen
    ki_response_str = generate_report_with_ai(final_prompt, ki_model)
    db.save_ki_raw_response(participant_id, ki_response_str)
    
    try:
        ki_data = json.loads(clean_json_response(ki_response_str))
        if "error" in ki_data:
            return jsonify(
                {"status": "error", "message": f"KI-Fehler: {ki_data['error']}"}
            )
            
        # Daten speichern und Erfolgsnachricht zurückgeben
        db.save_participant_data(
            participant_id,
            {
                "sk_ratings": ki_data.get("sk_ratings", {}),
                "vk_ratings": ki_data.get("vk_ratings", {}),
                "ki_texts": ki_data.get("ki_texts", {}),
            },
        )
        return jsonify(
            {
                "status": "success",
                "message": "KI-Analyse erfolgreich. Bericht wird geladen...",
                "redirect_url": url_for("show_report", participant_id=participant_id),
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


@app.route("/api/run_single_analysis/<int:participant_id>", methods=["POST"])
def run_single_analysis_api(participant_id):
    """Führt die KI-Analyse für einen bestimmten Teilnehmer durch (API-Version)."""
    data = request.get_json()
    participant = db.get_participant_by_id(participant_id)
    if not participant:
        return (
            jsonify({"status": "error", "message": "Teilnehmer nicht gefunden."}),
            404,
        )
        
    # Daten für den Kontext vorbereiten
    full_name = participant.get("name", "")
    first_name = full_name.split(" ")[0] if full_name else ""
    obs = participant.get("observations", {})
    
    # Kontext-Block erstellen
    context_block = (
        f"ANALYSE-SUBJEKT:\n"
        f"- Vorname: {first_name}\n"
        f"- Ganzer Name: {full_name}\n\n"
        f"BEOBACHTUNGEN ZUM VERHALTEN DES ANALYSE-SUBJEKTS:\n"
        f"- Soziale Kompetenzen: {obs.get('social', '')}\n"
        f"- Verbale Kompetenzen: {obs.get('verbal', '')}\n\n"
        f"ZUSÄTZLICHER KONTEXT:\n{data.get('additional_content', '')}"
    )
    
    # Prompt vorbereiten
    prompt = data.get("prompt_template", "")
    prompt = prompt.replace("{{context}}", context_block)
    prompt = (
        prompt.replace("{{name}}", first_name)
        .replace("{{vorname}}", first_name)
        .replace("{{first_name}}", first_name)
        .replace("{{ganzer_name}}", full_name)
    )
    prompt = (
        prompt.replace("{{social_observations}}", obs.get("social", ""))
        .replace("{{verbal_observations}}", obs.get("verbal", ""))
    )
    prompt = prompt.replace(
        "{{additional_content}}", data.get("additional_content", "")
    )
    
    print(f"--- FINALER PROMPT AN DIE KI ---\n{prompt}\n--- ENDE PROMPT ---")
    
    # KI-Analyse durchführen
    response_str = generate_report_with_ai(prompt, data.get("ki_model"))
    db.save_ki_raw_response(participant_id, response_str)
    
    try:
        ki_data = json.loads(clean_json_response(response_str))
        if "error" in ki_data:
            return jsonify(
                {"status": "error", "message": f"KI-Fehler: {ki_data['error']}"}
            )
            
        # Daten speichern und Erfolgsnachricht zurückgeben
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
        return jsonify(
            {
                "status": "error",
                "message": f"Formatfehler: {e}",
                "raw_response": response_str,
            }
        )


@app.route("/info")
def info():
    """Zeigt die Info-Seite an."""
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Info"},
    ]
    return render_template("info.html", breadcrumbs=breadcrumbs)


if __name__ == "__main__":
    app.run(port=5001, debug=True)
