"""
Decorator-Funktionen für Autorisierung und Zugriffskontrolle.
Implementiert RBAC (Role-Based Access Control) und gruppenbasierte Zugriffskontrolle.
"""

from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user

import models
from extensions import db


def admin_required(f):
    """
    Decorator: Erfordert Admin-Rolle.
    Verwendung: @login_required @admin_required
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user or not current_user.is_admin:
            flash("Sie haben keine Berechtigung für diesen Bereich.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)

    return decorated_function


def permission_required(codename):
    """
    Decorator: Erfordert eine bestimmte Berechtigung.
    Admin (is_system-Rolle) hat automatisch alle Berechtigungen.

    Verwendung: @login_required @permission_required("groups.edit")
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user or not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            if not current_user.has_permission(codename):
                flash("Sie haben keine Berechtigung für diese Aktion.", "error")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def group_access_required(f):
    """
    Decorator: Prüft ob der User Zugriff auf die Gruppe hat (über group_id Parameter).
    Verwendung: @login_required @group_access_required
    
    Erwartet einen group_id-Parameter in der Route:
      @app.route('/group/<int:group_id>/view')
      @login_required
      @group_access_required
      def view_group(group_id):
          ...
    
    Admin: Immer Zugriff
    Beobachter: Nur auf eigene zugeordnete Gruppen
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extrahiere group_id aus kwargs
        group_id = kwargs.get("group_id") or kwargs.get("id")

        if not group_id:
            # Manche Routes haben gid statt group_id
            group_id = kwargs.get("gid")

        if not group_id:
            abort(400)  # Bad Request

        # Admin hat immer Zugriff
        if current_user.is_admin:
            return f(*args, **kwargs)

        # Beobachter: Prüfe ob die Gruppe in den zugewiesenen Gruppen ist
        group = db.session.get(models.Group, int(group_id))
        if not group:
            abort(404)

        # Prüfe ob der User auf diese Gruppe Zugriff hat
        if not current_user.groups.filter_by(id=group_id).first():
            flash(
                "Sie haben keinen Zugriff auf diese Gruppe.",
                "error",
            )
            return redirect(url_for("dashboard"))

        return f(*args, **kwargs)

    return decorated_function


def participant_access_required(f):
    """
    Decorator: Prüft ob der User auf den Teilnehmer (und dessen Gruppe) zugreifen darf.
    Ähnlich wie group_access_required, aber mit participant_id.
    
    Verwendung: @login_required @participant_access_required
    
    Erwartet participant_id in der Route:
      @app.route('/participant/<int:participant_id>/edit')
      @login_required
      @participant_access_required
      def edit_participant(participant_id):
          ...
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        participant_id = kwargs.get("participant_id") or kwargs.get("id")

        if not participant_id:
            abort(400)

        # Lade Teilnehmer
        participant = db.session.get(models.Participant, int(participant_id))
        if not participant:
            abort(404)

        # Admin hat immer Zugriff
        if current_user.is_admin:
            return f(*args, **kwargs)

        # Beobachter: Prüfe Gruppen-Zugehörigkeit
        if not current_user.groups.filter_by(id=participant.group_id).first():
            flash(
                "Sie haben keinen Zugriff auf diesen Teilnehmer.",
                "error",
            )
            return redirect(url_for("dashboard"))

        return f(*args, **kwargs)

    return decorated_function


def get_accessible_groups(user):
    """
    Hilfsfunktion: Gibt alle Gruppen zurück, auf die der User Zugriff hat.
    
    Admin: Alle Gruppen
    Beobachter: Nur zugeordnete Gruppen
    """
    if not user:
        return []

    if user.is_admin:
        return db.session.scalars(db.select(models.Group)).all()

    return db.session.scalars(user.groups).all()


def filter_participants_by_group(user, query=None):
    """
    Hilfsfunktion: Filtert eine Participant-Query auf zugängliche Gruppen.
    
    Admin: Alle
    Beobachter: Nur Teilnehmer aus zugewiesenen Gruppen
    """
    if query is None:
        query = db.select(models.Participant)

    if not user:
        return query.where(models.Participant.id == -1)  # Keine Treffer

    if user.is_admin:
        return query

    # Beobachter: Nur Teilnehmer aus zugewiesenen Gruppen
    accessible_group_ids = [g.id for g in get_accessible_groups(user)]
    if not accessible_group_ids:
        return query.where(models.Participant.id == -1)  # Keine Treffer

    return query.where(models.Participant.group_id.in_(accessible_group_ids))


def filter_groups_by_access(user, query=None):
    """
    Hilfsfunktion: Filtert eine Group-Query auf zugängliche Gruppen.
    
    Admin: Alle
    Beobachter: Nur zugeordnete
    """
    if query is None:
        query = db.select(models.Group)

    if not user:
        return query.where(models.Group.id == -1)  # Keine Treffer

    if user.is_admin:
        return query

    # Beobachter
    accessible_group_ids = [g.id for g in get_accessible_groups(user)]
    if not accessible_group_ids:
        return query.where(models.Group.id == -1)

    return query.where(models.Group.id.in_(accessible_group_ids))
