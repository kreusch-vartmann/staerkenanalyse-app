# blueprints/participants.py
"""Dieses Modul enthält Routen und Funktionen für die Teilnehmerverwaltung."""

import json
from flask import Blueprint, request, redirect, url_for, flash, render_template, jsonify

from extensions import db, csrf
from models import Participant, Group, SelfAssessment
from utils import sanitize_html

participants_bp = Blueprint('participants', __name__)


@participants_bp.route("/participants")
def manage_participants():
    """Zeigt die Seite zur Verwaltung aller Teilnehmer an, gruppiert nach Gruppen."""
    groups = db.session.execute(
        db.select(Group).order_by(Group.name)
    ).scalars().all()

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Teilnehmer"},
    ]
    return render_template(
        "manage_participants.html",
        groups=groups,
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

    return redirect(url_for("groups.manage_groups"))


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
        'group_id': participant.group_id,
        'observations': json.loads(participant.observations) if participant.observations else {}
    }

    has_ki_report = bool(participant.ki_texts and participant.ki_texts != '{}')

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("groups.manage_groups"), "text": "Gruppen"},
        {"link": url_for("groups.show_group_participants", group_id=group.id), "text": group.name},
        {"text": f"Beobachtungsdaten: {participant.name}"},
    ]
    return render_template(
        "data_entry.html",
        participant=participant_data,
        group=group,
        has_ki_report=has_ki_report,
        breadcrumbs=breadcrumbs
    )

@participants_bp.route("/participant/<int:participant_id>/save_observations", methods=["POST"])
@csrf.exempt
def save_observations(participant_id):
    """Speichert die Beobachtungen für einen Teilnehmer."""
    participant = db.get_or_404(Participant, participant_id)
    data = request.get_json()
    
    if data:
        participant.observations = json.dumps(data)
        db.session.commit()
        return jsonify({"status": "success", "message": "Beobachtungen gespeichert!"})
        
    return jsonify({"status": "error", "message": "Keine Daten erhalten."}), 400


# --- ROUTEN FÜR SELBSTEINSCHÄTZUNG ---

@participants_bp.route("/self-assessments")
def manage_self_assessments():
    """Zeigt die Übersicht aller Teilnehmer mit Selbsteinschätzungsstatus an."""
    groups = db.session.execute(
        db.select(Group).order_by(Group.name)
    ).scalars().all()
    
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Selbsteinschätzung"}
    ]
    
    return render_template(
        "manage_self_assessments.html",
        groups=groups,
        breadcrumbs=breadcrumbs
    )

@participants_bp.route("/participant/<int:participant_id>/self_assessment")
def show_self_assessment(participant_id):
    """Zeigt die Selbsteinschätzungs-Eingabeseite für einen Teilnehmer an."""
    participant = db.get_or_404(Participant, participant_id)
    group = participant.group
    
    # Hole oder erstelle SelfAssessment
    self_assessment = db.session.execute(
        db.select(SelfAssessment).where(SelfAssessment.participant_id == participant_id)
    ).scalar_one_or_none()
    
    if not self_assessment:
        self_assessment = SelfAssessment(participant_id=participant_id, content='')
        db.session.add(self_assessment)
        db.session.commit()
    
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("participants.manage_self_assessments"), "text": "Selbsteinschätzung"},
        {"text": participant.name}
    ]
    
    return render_template(
        "self_assessment_entry.html",
        participant=participant,
        group=group,
        self_assessment=self_assessment,
        breadcrumbs=breadcrumbs
    )

@participants_bp.route("/save_self_assessment/<int:participant_id>", methods=["POST"])
@csrf.exempt
def save_self_assessment(participant_id):
    """Speichert die Selbsteinschätzung für einen Teilnehmer (API-Endpunkt)."""
    participant = db.get_or_404(Participant, participant_id)
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({"status": "error", "message": "Keine Daten erhalten."}), 400
    
    # Hole oder erstelle SelfAssessment
    self_assessment = db.session.execute(
        db.select(SelfAssessment).where(SelfAssessment.participant_id == participant_id)
    ).scalar_one_or_none()
    
    if not self_assessment:
        self_assessment = SelfAssessment(participant_id=participant_id)
        db.session.add(self_assessment)
    
    self_assessment.content = sanitize_html(data['content'])
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Selbsteinschätzung gespeichert!"})