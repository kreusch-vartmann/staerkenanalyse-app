# /blueprints/groups.py
"""Dieses Modul enthält Routen und Funktionen für die Gruppenverwaltung."""

from flask import Blueprint, request, redirect, url_for, flash, render_template
import database as db

# Ein Blueprint-Objekt erstellen, das als unsere "Fachabteilung" dient
groups_bp = Blueprint('groups', __name__)


# --- ROUTEN FÜR DIE GRUPPENVERWALTUNG ---

@groups_bp.route("/groups")
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

@groups_bp.route("/group/<int:group_id>/participants")
def show_group_participants(group_id):
    """Zeigt die Teilnehmer einer bestimmten Gruppe an."""
    group = db.get_group_by_id(group_id)
    participants = db.get_participants_by_group(group_id)
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("groups.manage_groups"), "text": "Gruppen"},
        {"text": group["name"]},
    ]
    return render_template(
        "participants.html",
        group=group,
        participants=participants,
        breadcrumbs=breadcrumbs,
    )

@groups_bp.route("/group/add", methods=["POST"])
def add_group():
    """Fügt eine neue Gruppe hinzu."""
    details = {
        "name": request.form.get("name"),
        "date": request.form.get("date"),
        "location": request.form.get("location"),
        "leitung": request.form.get("leitung"),
        "beobachter1": request.form.get("beobachter1"),
        "beobachter2": request.form.get("beobachter2"),
    }
    db.add_group(details)
    flash(f'Gruppe "{details["name"]}" wurde erfolgreich hinzugefügt.', "success")
    return redirect(url_for("groups.manage_groups"))

@groups_bp.route("/group/edit/<int:group_id>", methods=["POST"])
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
    return redirect(url_for("groups.manage_groups"))

@groups_bp.route("/group/delete/<int:group_id>", methods=["POST"])
def delete_group(group_id):
    """Entfernt eine Gruppe und alle zugehörigen Teilnehmer."""
    db.delete_group_by_id(group_id)
    flash("Gruppe und alle zugehörigen Teilnehmer wurden gelöscht.", "success")
    return redirect(url_for("groups.manage_groups"))
