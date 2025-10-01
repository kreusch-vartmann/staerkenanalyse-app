# blueprints/participants.py
"""Dieses Modul enthält Routen und Funktionen für die Teilnehmerverwaltung."""

from datetime import datetime
import pytz
from flask import Blueprint, request, redirect, url_for, flash, render_template, jsonify
import database as db

participants_bp = Blueprint('participants', __name__)


@participants_bp.route("/participants")
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


@participants_bp.route("/group/<int:group_id>/participant/add", methods=["POST"])
def add_participant(group_id):
    """Fügt mehrere Teilnehmer zu einer Gruppe hinzu."""
    names_input = request.form.get("participant_names", "")
    valid_names = [name.strip() for name in names_input.splitlines() if name.strip()]
    if valid_names:
        count = db.add_multiple_participants_to_group(group_id, valid_names)
        flash(f"{count} Teilnehmer wurden hinzugefügt.", "success")
    else:
        flash("Keine gültigen Namen eingegeben.", "warning")
    return redirect(url_for("groups.show_group_participants", group_id=group_id))


@participants_bp.route("/participant/edit/<int:participant_id>", methods=["POST"])
def edit_participant(participant_id):
    """Aktualisiert den Namen eines Teilnehmers."""
    new_name = request.form["new_name"]
    group_id = request.form["group_id"]
    if new_name:
        db.update_participant_name(participant_id, new_name)
        flash("Teilnehmername wurde aktualisiert.", "success")
    return redirect(url_for("groups.show_group_participants", group_id=group_id))


@participants_bp.route("/participant/delete/<int:participant_id>", methods=["POST"])
def delete_participant(participant_id):
    """Löscht einen Teilnehmer."""
    group_id = request.form["group_id"]
    db.delete_participant_by_id(participant_id)
    flash("Teilnehmer wurde gelöscht.", "success")
    return redirect(url_for("groups.show_group_participants", group_id=group_id))


@participants_bp.route("/participant/<int:participant_id>/data_entry")
def show_data_entry(participant_id):
    """Zeigt die Dateneingabeseite für einen Teilnehmer an."""
    participant = db.get_participant_by_id(participant_id)
    if participant:
        group = db.get_group_by_id(participant["group_id"])
        breadcrumbs = [
            {"link": url_for("dashboard"), "text": "Dashboard"},
            {"link": url_for("groups.manage_groups"), "text": "Gruppen"},
            {
                "link": url_for("groups.show_group_participants", group_id=group["id"]),
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
    return redirect(url_for("participants.manage_participants"))


@participants_bp.route("/participant/<int:participant_id>/report")
def show_report(participant_id):
    """Zeigt den Bericht für einen bestimmten Teilnehmer an."""
    participant = db.get_participant_by_id(participant_id)
    if not participant:
        flash("Teilnehmer nicht gefunden.", "error")
        return redirect(url_for("participants.manage_participants"))

    group = db.get_group_by_id(participant["group_id"])
    full_name = participant.get("name", "")
    participant["first_name"] = full_name.split(" ")[0] if full_name else ""

    # ENDGÜLTIGE LÖSUNG:
    # 1. Berechne das tagesaktuelle Datum in der korrekten Zeitzone.
    german_tz = pytz.timezone('Europe/Berlin')
    current_date_str = datetime.now(pytz.utc).astimezone(german_tz).strftime("%d.%m.%Y")
    current_location_str = "Lingen (Ems)"

    # 2. Überschreibe aktiv die Werte, die an das Template gehen.
    # Dies stellt sicher, dass immer das tagesaktuelle Datum verwendet wird,
    # egal was in der Datenbank in `footer_data` gespeichert ist.
    if 'footer_data' not in participant or not isinstance(participant['footer_data'], dict):
        participant['footer_data'] = {}
    participant['footer_data']['footer_date'] = current_date_str
    participant['footer_data']['footer_location'] = current_location_str

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("groups.manage_groups"), "text": "Gruppen"},
        {
            "link": url_for("groups.show_group_participants", group_id=group["id"]),
            "text": group["name"],
        },
        {"text": f"Bericht: {participant['name']}"},
    ]

    # 3. Übergebe die geänderten Daten an das Template.
    # Die zusätzlichen Variablen `current_date` und `current_location` werden
    # nun nur noch als Fallback für komplett neue Berichte ohne `footer_data` benötigt.
    return render_template(
        "staerkenanalyse_bericht_vorlage3.html",
        participant=participant,
        group=group,
        breadcrumbs=breadcrumbs,
        current_date=current_date_str,
        current_location=current_location_str,
    )


@participants_bp.route("/save_observations/<int:participant_id>", methods=["POST"])
def save_observations(participant_id):
    """Speichert die Beobachtungen für einen bestimmten Teilnehmer."""
    data = request.get_json()
    if data and "social" in data:
        db.save_participant_data(participant_id, {"observations": data})
        return jsonify({"status": "success", "message": "Beobachtungen gespeichert!"})
    return jsonify({"status": "error", "message": "Ungültige Daten."}), 400


@participants_bp.route("/save_report/<int:participant_id>", methods=["POST"])
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


@participants_bp.route("/api/group/<int:group_id>/participants")
def get_participants_for_group(group_id):
    """Gibt die Teilnehmer einer bestimmten Gruppe als JSON zurück."""
    participants = db.get_participants_by_group(group_id)
    return jsonify([dict(p) for p in participants])

@participants_bp.route("/api/participant/<int:participant_id>/observations")
def get_observations(participant_id):
    """Gibt die Beobachtungen für einen Teilnehmer als JSON zurück."""
    participant = db.get_participant_by_id(participant_id)
    # Stellt sicher, dass observations ein dict ist, auch wenn es null ist
    observations = participant.get("observations") if participant else None
    if isinstance(observations, dict):
        return jsonify({
            "social": observations.get("social", ""),
            "verbal": observations.get("verbal", "")
        })
    # Fallback, wenn keine Beobachtungen vorhanden sind
    return jsonify({"social": "", "verbal": ""})
