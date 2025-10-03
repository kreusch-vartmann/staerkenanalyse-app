# blueprints/participants.py
"""Dieses Modul enthält Routen und Funktionen für die Teilnehmerverwaltung."""

import json
from flask import Blueprint, request, redirect, url_for, flash, render_template, jsonify
from datetime import datetime

from extensions import db
from models import Participant, Group

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
        query = query.filter(db.or_(Participant.name.like(search_term), Group.name.like(search_term)))

    sort_map = {
        'name_asc': Participant.name.asc(),
        'name_desc': Participant.name.desc(),
        'group_asc': Group.name.asc(),
        'group_desc': Group.name.desc(),
    }
    order_clause = sort_map.get(sort_order, Participant.name.asc())
    query = query.order_by(order_clause)

    pagination = db.paginate(query, page=page, per_page=15)
    participants = pagination.items
    
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Teilnehmer"},
    ]
    return render_template(
        "manage_participants.html",
        participants=participants,
        pagination=pagination,
        search_query=search_query,
        sort_order=sort_order,
        breadcrumbs=breadcrumbs,
    )


@participants_bp.route('/add')
@participants_bp.route('/add/<int:group_id>')
def add_participant(group_id=None):
    """
    Zeigt das Formular zum Hinzufügen eines neuen Teilnehmers.
    """
    group = None
    if group_id:
        group = Group.query.get_or_404(group_id)
    
    breadcrumbs = [
        {'text': 'Dashboard', 'link': url_for('dashboard')},
    ]
    
    if group:
        breadcrumbs.extend([
            {'text': 'Gruppen verwalten', 'link': url_for('groups.manage_groups')},
            {'text': group.name, 'link': url_for('groups.show_group_participants', group_id=group.id)},
            {'text': 'Teilnehmer hinzufügen', 'link': ''}
        ])
    else:
        breadcrumbs.extend([
            {'text': 'Teilnehmer verwalten', 'link': url_for('participants.manage_participants')},
            {'text': 'Teilnehmer hinzufügen', 'link': ''}
        ])
    
    return render_template('participants.html', group=group, breadcrumbs=breadcrumbs)


@participants_bp.route("/create", methods=["POST"])
def create_participant():
    """
    Erstellt einen neuen Teilnehmer.
    """
    try:
        group_id = request.form.get('group_id')
        vorname = request.form.get('vorname')
        nachname = request.form.get('nachname')
        email = request.form.get('email')
        telefon = request.form.get('telefon')
        geburtsdatum = request.form.get('geburtsdatum')
        geschlecht = request.form.get('geschlecht')
        notizen = request.form.get('notizen')
        
        # Vollständigen Namen erstellen
        name = f"{vorname} {nachname}".strip()
        
        # Neuen Teilnehmer erstellen
        participant = Participant(
            group_id=int(group_id) if group_id else None,
            name=name,  # Verwenden Sie 'name' statt 'vorname'/'nachname'
            email=email if email else None,
            telefon=telefon if telefon else None,
            geburtsdatum=datetime.strptime(geburtsdatum, '%Y-%m-%d').date() if geburtsdatum else None,
            geschlecht=geschlecht if geschlecht else None,
            notizen=notizen if notizen else None
        )
        
        db.session.add(participant)
        db.session.commit()
        
        flash(f'Teilnehmer {name} wurde erfolgreich hinzugefügt.', 'success')
        
        # Zurück zur entsprechenden Übersicht
        if group_id:
            return redirect(url_for('groups.show_group_participants', group_id=group_id))
        else:
            return redirect(url_for('participants.manage_participants'))
            
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Hinzufügen des Teilnehmers: {str(e)}', 'error')
        if group_id:
            return redirect(url_for('participants.add_participant', group_id=group_id))
        else:
            return redirect(url_for('participants.add_participant'))


@participants_bp.route("/participant/edit/<int:participant_id>", methods=["POST"])
def edit_participant(participant_id):
    """Aktualisiert den Namen eines Teilnehmers."""
    participant = db.get_or_404(Participant, participant_id)
    new_name = request.form.get("new_name")
    
    if new_name and new_name.strip():
        participant.name = new_name.strip()
        db.session.commit()
        flash("Teilnehmername wurde aktualisiert.", "success")
    else:
        flash("Der Name darf nicht leer sein.", "warning")

    # Redirect zurück zur Gruppenseite des Teilnehmers
    return redirect(url_for("groups.show_group_participants", group_id=participant.group_id))


@participants_bp.route("/participant/delete/<int:participant_id>", methods=["POST"])
def delete_participant(participant_id):
    """Löscht einen Teilnehmer."""
    participant = db.get_or_404(Participant, participant_id)
    group_id = participant.group_id
    
    db.session.delete(participant)
    db.session.commit()
    
    flash("Teilnehmer wurde gelöscht.", "success")
    return redirect(url_for("groups.show_group_participants", group_id=group_id))


# --- Routen für Dateneingabe und Berichte (müssen später noch angepasst werden) ---

@participants_bp.route("/participant/<int:participant_id>/data_entry")
def show_data_entry(participant_id):
    """Zeigt die Dateneingabeseite für einen Teilnehmer an."""
    # Diese Funktion muss noch vollständig auf SQLAlchemy umgebaut werden
    participant = db.get_or_404(Participant, participant_id)
    group = participant.group
    
    # Temporäre Konvertierung der JSON-Daten für die alte Vorlage
    participant_dict = {
        'id': participant.id,
        'name': participant.name,
        'group_id': participant.group_id,
        'general_data': json.loads(participant.general_data) if participant.general_data else {},
        'observations': json.loads(participant.observations) if participant.observations else {},
        # ... weitere Felder bei Bedarf ...
    }

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("groups.manage_groups"), "text": "Gruppen"},
        {"link": url_for("groups.show_group_participants", group_id=group.id), "text": group.name},
        {"text": f"Dateneingabe: {participant.name}"},
    ]
    # HINWEIS: Die 'data_entry.html' Vorlage muss noch auf das neue Design umgestellt werden
    return render_template(
        "data_entry.html",
        participant=participant_dict,
        group=group,
        breadcrumbs=breadcrumbs,
        prompts=[] # Platzhalter, da Prompts noch nicht umgestellt sind
    )
