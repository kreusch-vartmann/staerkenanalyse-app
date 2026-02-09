# /blueprints/groups.py
"""Dieses Modul enthält Routen und Funktionen für die Gruppenverwaltung."""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Group, Participant
from decorators import admin_required, filter_groups_by_access

groups_bp = Blueprint("groups", __name__)


@groups_bp.route("/groups")
@login_required
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
def show_group_participants(group_id):
    """Zeigt die Teilnehmer einer bestimmten Gruppe an."""
    group = db.get_or_404(Group, group_id)
    
    # Check permission: Admin always allowed, Beobachter only for assigned groups
    if not current_user.is_admin:
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
@admin_required
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

    flash(f'Gruppe "{new_group.name}" wurde erfolgreich hinzugefügt.', "success")
    return redirect(url_for("groups.manage_groups"))


@groups_bp.route("/group/edit/<int:group_id>", methods=["POST"])
@login_required
@admin_required
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
@admin_required
def delete_group(group_id):
    """Entfernt eine Gruppe und alle zugehörigen Teilnehmer."""
    group_to_delete = db.get_or_404(Group, group_id)

    db.session.delete(group_to_delete)
    db.session.commit()

    flash("Gruppe und alle zugehörigen Teilnehmer wurden gelöscht.", "success")
    return redirect(url_for("groups.manage_groups"))
