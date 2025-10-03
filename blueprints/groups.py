# /blueprints/groups.py
"""Dieses Modul enthält Routen und Funktionen für die Gruppenverwaltung."""

from flask import Blueprint, request, redirect, url_for, flash, render_template
from datetime import datetime

from extensions import db
from models import Group, Participant

groups_bp = Blueprint('groups', __name__)


@groups_bp.route("/groups")
def manage_groups():
    """Zeigt die Seite zur Verwaltung von Gruppen an."""
    page = request.args.get("page", 1, type=int)
    
    pagination = db.paginate(db.select(Group).order_by(Group.name), page=page, per_page=10)
    groups = pagination.items

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

@groups_bp.route("/group/<int:group_id>/participants")
def show_group_participants(group_id):
    """Zeigt die Teilnehmer einer bestimmten Gruppe an."""
    group = db.get_or_404(Group, group_id)
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
def add_group():
    """Verarbeitet das Hinzufügen einer neuen Gruppe aus dem Formular auf der Hauptseite."""
    date_str = request.form.get("date")
    group_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None

    new_group = Group(
        name=request.form.get("name"),
        date=group_date,
        location=request.form.get("location"),
        leitung_fremdeinschatzung=request.form.get("leitung_fremdeinschatzung"),
        leitung_selbsteinschatzung=request.form.get("leitung_selbsteinschatzung"),
        beobachter1=request.form.get("beobachter1"),
        beobachter2=request.form.get("beobachter2"),
    )
    
    db.session.add(new_group)
    db.session.commit()
    
    flash(f'Gruppe "{new_group.name}" wurde erfolgreich hinzugefügt.', "success")
    return redirect(url_for("groups.manage_groups"))

@groups_bp.route("/group/edit/<int:group_id>", methods=["POST"])
def edit_group(group_id):
    """Verarbeitet die Aktualisierung einer bestehenden Gruppe aus dem Modal."""
    group_to_edit = db.get_or_404(Group, group_id)

    date_str = request.form.get("group_date")
    group_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
    
    group_to_edit.name = request.form.get("group_name")
    group_to_edit.date = group_date
    group_to_edit.location = request.form.get("group_location")
    group_to_edit.leitung_fremdeinschatzung = request.form.get("leitung_fremdeinschatzung")
    group_to_edit.leitung_selbsteinschatzung = request.form.get("leitung_selbsteinschatzung")
    group_to_edit.beobachter1 = request.form.get("beobachter1")
    group_to_edit.beobachter2 = request.form.get("beobachter2")
    
    db.session.commit()

    flash("Gruppe erfolgreich aktualisiert.", "success")
    return redirect(url_for("groups.manage_groups"))

@groups_bp.route("/group/delete/<int:group_id>", methods=["POST"])
def delete_group(group_id):
    """Entfernt eine Gruppe und alle zugehörigen Teilnehmer."""
    group_to_delete = db.get_or_404(Group, group_id)
    
    db.session.delete(group_to_delete)
    db.session.commit()
    
    flash("Gruppe und alle zugehörigen Teilnehmer wurden gelöscht.", "success")
    return redirect(url_for("groups.manage_groups"))

