# blueprints/participants.py
"""Dieses Modul enthält Routen und Funktionen für die Teilnehmerverwaltung."""

import json
from flask import Blueprint, request, redirect, url_for, flash, render_template, jsonify

from extensions import db
from models import Participant, Group, Prompt

participants_bp = Blueprint('participants', __name__)


@participants_bp.route("/participants")
def manage_participants():
    """Zeigt die Seite zur Verwaltung aller Teilnehmer an."""
    page = request.args.get("page", 1, type=int)
    search_query = request.args.get("q", "")
    sort_order = request.args.get("sort", "name_asc")

    # Basis-Abfrage mit SQLAlchemy
    query = db.select(Participant).join(Group)

    if search_query:
        search_term = f"%{search_query}%"
        # Logik für 'OR' in SQLAlchemy
        query = query.filter(db.or_(Participant.name.ilike(search_term), Group.name.ilike(search_term)))

    sort_map = {
        'name_asc': Participant.name.asc(),
        'name_desc': Participant.name.desc(),
        'group_asc': Group.name.asc(),
        'group_desc': Group.name.desc(),
    }
    order_clause = sort_map.get(sort_order, Participant.name.asc())
    query = query.order_by(order_clause)

    pagination = db.paginate(query, page=page, per_page=15)
    
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Teilnehmer"},
    ]
    return render_template(
        "manage_participants.html",
        participants=pagination.items,
        pagination=pagination,
        search_query=search_query,
        sort_order=sort_order,
        breadcrumbs=breadcrumbs,
    )


@participants_bp.route("/group/<int:group_id>/participant/add", methods=["POST"])
def add_participant(group_id):
    """Fügt einen oder mehrere Teilnehmer zu einer Gruppe hinzu."""
    group = db.get_or_404(Group, group_id)
    names_input = request.form.get("participant_names", "")
    valid_names = [name.strip() for name in names_input.splitlines() if name.strip()]

    if valid_names:
        for name in valid_names:
            # Erstelle für jeden Namen einen neuen Teilnehmer
            new_participant = Participant(name=name, group=group)
            db.session.add(new_participant)
        
        db.session.commit()
        flash(f"{len(valid_names)} Teilnehmer wurden zur Gruppe '{group.name}' hinzugefügt.", "success")
    else:
        flash("Keine gültigen Namen eingegeben.", "warning")

    return redirect(url_for("groups.show_group_participants", group_id=group_id))


@participants_bp.route("/participant/edit/<int:participant_id>", methods=["POST"])
def edit_participant(participant_id):
    """Aktualisiert den Namen eines Teilnehmers."""
    participant = db.get_or_404(Participant, participant_id)
    new_name = request.form.get("participant_name")
    
    if new_name and new_name.strip():
        participant.name = new_name.strip()
        db.session.commit()
        flash("Teilnehmername wurde aktualisiert.", "success")
    else:
        flash("Der Name darf nicht leer sein.", "warning")

    # Leitet zur vorherigen Seite zurück (entweder Gruppen- oder Gesamtübersicht)
    redirect_url = request.form.get('redirect_url') or url_for("groups.show_group_participants", group_id=participant.group_id)
    return redirect(redirect_url)


@participants_bp.route("/participant/delete/<int:participant_id>", methods=["POST"])
def delete_participant(participant_id):
    """Löscht einen Teilnehmer."""
    participant = db.get_or_404(Participant, participant_id)
    group_id = participant.group_id
    
    db.session.delete(participant)
    db.session.commit()
    
    flash("Teilnehmer wurde gelöscht.", "success")

    # Leitet ebenfalls zur vorherigen Seite zurück
    redirect_url = request.form.get('redirect_url') or url_for("groups.show_group_participants", group_id=group_id)
    return redirect(redirect_url)


# --- Routen für Dateneingabe und Berichte ---

@participants_bp.route("/participant/<int:participant_id>/data_entry")
def show_data_entry(participant_id):
    """Zeigt die Dateneingabeseite für einen Teilnehmer an."""
    participant = db.get_or_404(Participant, participant_id)
    group = participant.group
    
    # JSON-Daten im Backend parsen, damit das Template damit arbeiten kann
    participant_data = {
        'id': participant.id,
        'name': participant.name,
        'general_data': json.loads(participant.general_data) if participant.general_data else {},
        'observations': json.loads(participant.observations) if participant.observations else {}
    }

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("groups.manage_groups"), "text": "Gruppen"},
        {"link": url_for("groups.show_group_participants", group_id=group.id), "text": group.name},
        {"text": f"Dateneingabe: {participant.name}"},
    ]
    return render_template(
        "data_entry.html",
        participant=participant_data,
        group=group,
        breadcrumbs=breadcrumbs
    )

@participants_bp.route("/participant/<int:participant_id>/save_general_data", methods=["POST"])
def save_general_data(participant_id):
    """Speichert die allgemeinen Stammdaten eines Teilnehmers."""
    participant = db.get_or_404(Participant, participant_id)
    data = request.get_json()
    
    if data:
        participant.general_data = json.dumps(data)
        db.session.commit()
        return jsonify({"status": "success", "message": "Stammdaten gespeichert!"})
        
    return jsonify({"status": "error", "message": "Keine Daten erhalten."}), 400


@participants_bp.route("/participant/<int:participant_id>/save_observations", methods=["POST"])
def save_observations(participant_id):
    """Speichert die Beobachtungen für einen Teilnehmer."""
    participant = db.get_or_404(Participant, participant_id)
    data = request.get_json()
    
    if data:
        participant.observations = json.dumps(data)
        db.session.commit()
        return jsonify({"status": "success", "message": "Beobachtungen gespeichert!"})
        
    return jsonify({"status": "error", "message": "Keine Daten erhalten."}), 400

