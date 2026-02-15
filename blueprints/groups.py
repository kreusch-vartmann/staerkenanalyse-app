# /blueprints/groups.py
"""Dieses Modul enthält Routen und Funktionen für die Gruppenverwaltung."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify
from flask_login import current_user, login_required

from extensions import db
from models import Group, Participant, Task
from utils import log_activity
from decorators import permission_required, filter_groups_by_access

groups_bp = Blueprint("groups", __name__)


@groups_bp.route("/groups")
@login_required
@permission_required("groups.view")
def manage_groups():
    """Zeigt die Seite zur Verwaltung von Gruppen an."""
    # Filter based on user role: Beobachter only sees assigned groups
    query = filter_groups_by_access(current_user)
    groups = db.session.scalars(query.order_by(Group.name)).all()

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Gruppen"},
    ]
    return render_template(
        "manage_groups.html",
        groups=groups,
        breadcrumbs=breadcrumbs,
    )


@groups_bp.route("/group/<int:group_id>/participants")
@login_required
@permission_required("groups.view")
def show_group_participants(group_id):
    """Zeigt die Teilnehmer einer bestimmten Gruppe an."""
    group = db.get_or_404(Group, group_id)
    
    # Check permission: Admin always allowed, Beobachter only for assigned groups
    if not current_user.role.is_system:
        if not current_user.groups.filter_by(id=group_id).first():
            flash("Sie haben keinen Zugriff auf diese Gruppe.", "error")
            return redirect(url_for("dashboard"))
    
    participants = group.participants.order_by(Participant.name).all()

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("groups.manage_groups"), "text": "Gruppen"},
        {"text": group.name},
    ]
    return render_template(
        "participants.html",
        group=group,
        participants=participants,
        breadcrumbs=breadcrumbs,
    )


@groups_bp.route("/group/add", methods=["POST"])
@login_required
@permission_required("groups.edit")
def add_group():
    """Verarbeitet das Hinzufügen einer neuen Gruppe aus dem Formular auf der Hauptseite."""
    date_from_str = request.form.get("date_from")
    date_to_str = request.form.get("date_to")
    group_date_from = (
        datetime.strptime(date_from_str, "%Y-%m-%d").date() if date_from_str else None
    )
    group_date_to = (
        datetime.strptime(date_to_str, "%Y-%m-%d").date() if date_to_str else None
    )

    new_group = Group(
        name=request.form.get("name"),
        date_from=group_date_from,
        date_to=group_date_to,
        location=request.form.get("location"),
        leitung_fremdeinschatzung=request.form.get("leitung_fremdeinschatzung"),
        leitung_selbsteinschatzung=request.form.get("leitung_selbsteinschatzung"),
        beobachter1=request.form.get("beobachter1"),
        beobachter2=request.form.get("beobachter2"),
    )

    db.session.add(new_group)
    db.session.commit()

    log_activity(
        user_id=current_user.id,
        action="group_created",
        action_label="Gruppe erstellt",
        entity_type="group",
        entity_id=new_group.id,
        entity_label=new_group.name,
        target_url=url_for("groups.show_group_participants", group_id=new_group.id),
    )
    db.session.commit()

    flash(f'Gruppe "{new_group.name}" wurde erfolgreich hinzugefügt.', "success")
    return redirect(url_for("groups.manage_groups"))


@groups_bp.route("/group/edit/<int:group_id>", methods=["POST"])
@login_required
@permission_required("groups.edit")
def edit_group(group_id):
    """Verarbeitet die Aktualisierung einer bestehenden Gruppe aus dem Modal."""
    group_to_edit = db.get_or_404(Group, group_id)

    date_from_str = request.form.get("group_date_from")
    date_to_str = request.form.get("group_date_to")
    group_date_from = (
        datetime.strptime(date_from_str, "%Y-%m-%d").date() if date_from_str else None
    )
    group_date_to = (
        datetime.strptime(date_to_str, "%Y-%m-%d").date() if date_to_str else None
    )

    group_to_edit.name = request.form.get("group_name")
    group_to_edit.date_from = group_date_from
    group_to_edit.date_to = group_date_to
    group_to_edit.location = request.form.get("group_location")
    group_to_edit.leitung_fremdeinschatzung = request.form.get(
        "leitung_fremdeinschatzung"
    )
    group_to_edit.leitung_selbsteinschatzung = request.form.get(
        "leitung_selbsteinschatzung"
    )
    group_to_edit.beobachter1 = request.form.get("beobachter1")
    group_to_edit.beobachter2 = request.form.get("beobachter2")

    db.session.commit()

    flash("Gruppe erfolgreich aktualisiert.", "success")
    return redirect(url_for("groups.manage_groups"))


@groups_bp.route("/group/delete/<int:group_id>", methods=["POST"])
@login_required
@permission_required("groups.delete")
def delete_group(group_id):
    """Entfernt eine Gruppe und alle zugehörigen Teilnehmer."""
    group_to_delete = db.get_or_404(Group, group_id)

    db.session.delete(group_to_delete)
    db.session.commit()

    flash("Gruppe und alle zugehörigen Teilnehmer wurden gelöscht.", "success")
    return redirect(url_for("groups.manage_groups"))


# ============================================================================
# API Routes für Task-Zuordnung per Drag & Drop
# ============================================================================

@groups_bp.route("/api/tasks/available")
@login_required
@permission_required("groups.view")
def get_available_tasks():
    """Gibt alle verfügbaren Aufgaben als JSON zurück (für Drag & Drop UI)."""
    tasks = db.session.scalars(db.select(Task).filter_by(is_active=True).order_by(Task.observation_area, Task.title)).all()
    
    return jsonify({
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "observation_area": task.observation_area,
                "participant_count": task.participant_count,
                "duration_minutes": task.duration_minutes,
                "is_example": task.is_example,
            }
            for task in tasks
        ]
    })


@groups_bp.route("/api/groups/<int:group_id>/tasks", methods=["POST"])
@login_required
@permission_required("groups.edit")
def assign_task_to_group(group_id):
    """Ordnet eine Aufgabe einer Gruppe zu. Max. 1 pro Beobachtungsbereich."""
    group = db.get_or_404(Group, group_id)
    data = request.get_json()
    task_id = data.get("task_id")
    
    if not task_id:
        return jsonify({"error": "task_id ist erforderlich"}), 400
    
    task = db.get_or_404(Task, task_id)
    
    # Prüfe ob die Aufgabe bereits zugeordnet ist
    if task in group.tasks:
        return jsonify({"error": "Aufgabe ist bereits dieser Gruppe zugeordnet"}), 400
    
    # Prüfe ob bereits eine Aufgabe für diesen Beobachtungsbereich zugeordnet ist
    existing_task = group.tasks.filter_by(observation_area=task.observation_area).first()
    if existing_task:
        return jsonify({
            "error": f"Für den Beobachtungsbereich '{task.observation_area}' ist bereits die Aufgabe '{existing_task.title}' zugeordnet. Pro Bereich kann nur eine Aufgabe zugewiesen werden."
        }), 400
    
    # Ordne zu
    group.tasks.append(task)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "task": {
            "id": task.id,
            "title": task.title,
            "observation_area": task.observation_area,
            "participant_count": task.participant_count,
            "duration_minutes": task.duration_minutes,
        }
    })


@groups_bp.route("/api/groups/<int:group_id>/tasks/<int:task_id>", methods=["DELETE"])
@login_required
@permission_required("groups.edit")
def unassign_task_from_group(group_id, task_id):
    """Entfernt die Zuordnung einer Aufgabe von einer Gruppe."""
    group = db.get_or_404(Group, group_id)
    task = db.get_or_404(Task, task_id)
    
    if task not in group.tasks:
        return jsonify({"error": "Diese Aufgabe ist nicht dieser Gruppe zugeordnet"}), 404
    
    group.tasks.remove(task)
    db.session.commit()
    
    return jsonify({"success": True})


@groups_bp.route("/api/groups/<int:group_id>/tasks")
@login_required
@permission_required("groups.view")
def get_group_tasks(group_id):
    """Gibt alle Aufgaben einer Gruppe als JSON zurück."""
    group = db.get_or_404(Group, group_id)
    tasks = group.tasks.all()
    
    return jsonify({
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "observation_area": task.observation_area,
                "participant_count": task.participant_count,
                "duration_minutes": task.duration_minutes,
            }
            for task in tasks
        ]
    })
