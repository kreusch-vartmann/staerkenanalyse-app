"""
Admin Blueprint: Benutzerverwaltung (CRUD), Rollen, Gruppen-Zuordnung.
Alle Routes sind Admin-only.
"""

from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_required

import models
from decorators import admin_required
from extensions import db
from utils import generate_secure_password

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/users", methods=["GET"])
@login_required
@admin_required
def manage_users():
    """Admin: Übersicht aller Benutzer."""
    users = db.session.scalars(db.select(models.User)).all()
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Benutzerverwaltung"},
    ]
    return render_template(
        "admin/manage_users.html",
        users=users,
        breadcrumbs=breadcrumbs,
    )


@admin_bp.route("/user/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_user():
    """Admin: Neuen Benutzer erstellen."""
    
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        role_name = request.form.get("role", "beobachter").strip()
        group_ids = request.form.getlist("groups")

        # Validierung
        if not email or not first_name or not last_name:
            flash("E-Mail, Vor- und Nachname erforderlich.", "error")
            return redirect(url_for("admin.add_user"))

        if "@" not in email:
            flash("Ungültige E-Mail-Adresse.", "error")
            return redirect(url_for("admin.add_user"))

        # Prüfe ob E-Mail bereits existiert
        existing_user = db.session.scalar(
            db.select(models.User).where(models.User.email == email)
        )
        if existing_user:
            flash(f"Benutzer mit E-Mail {email} existiert bereits.", "error")
            return redirect(url_for("admin.add_user"))

        # Finde Rolle
        role = db.session.scalar(
            db.select(models.Role).where(models.Role.name == role_name)
        )
        if not role:
            flash(f"Rolle {role_name} nicht gefunden.", "error")
            return redirect(url_for("admin.add_user"))

        # Generiere sicheres Passwort
        password = generate_secure_password()

        # Erstelle User
        new_user = models.User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role_id=role.id,
            is_active=True,
            force_password_change=True,
        )
        new_user.set_password(password)

        # Zuordne Gruppen
        if group_ids and role_name == "beobachter":
            for group_id in group_ids:
                try:
                    group = db.session.get(models.Group, int(group_id))
                    if group:
                        new_user.groups.append(group)
                except (ValueError, TypeError):
                    pass

        db.session.add(new_user)
        db.session.commit()

        session["_temp_password"] = password
        flash(
            f"Benutzer {email} erstellt. Initiales Passwort wird einmalig angezeigt.",
            "success",
        )
        return redirect(url_for("admin.manage_users"))

    # GET: Formular anzeigen
    roles = db.session.scalars(db.select(models.Role)).all()
    groups = db.session.scalars(db.select(models.Group)).all()
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("admin.manage_users"), "text": "Benutzerverwaltung"},
        {"text": "Neuer Benutzer"},
    ]
    return render_template(
        "admin/user_form.html",
        user=None,
        roles=roles,
        groups=groups,
        breadcrumbs=breadcrumbs,
    )


@admin_bp.route("/user/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id: int):
    """Admin: Benutzer bearbeiten."""
    user = db.session.get(models.User, user_id)
    if not user:
        flash("Benutzer nicht gefunden.", "error")
        return redirect(url_for("admin.manage_users"))

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        role_name = request.form.get("role", user.role.name).strip()
        group_ids = request.form.getlist("groups")
        new_password = request.form.get("new_password", "").strip()

        # Validierung
        if not first_name or not last_name:
            flash("Vor- und Nachname erforderlich.", "error")
            return redirect(url_for("admin.edit_user", user_id=user_id))

        # Rolle ändern
        if role_name != user.role.name:
            role = db.session.scalar(
                db.select(models.Role).where(models.Role.name == role_name)
            )
            if not role:
                flash(f"Rolle {role_name} nicht gefunden.", "error")
                return redirect(url_for("admin.edit_user", user_id=user_id))
            user.role_id = role.id

        # Gruppen neu zuordnen (nur für Observer)
        if role_name == "beobachter":
            user.groups.clear()
            for group_id in group_ids:
                try:
                    group = db.session.get(models.Group, int(group_id))
                    if group:
                        user.groups.append(group)
                except (ValueError, TypeError):
                    pass
        else:
            user.groups.clear()

        # Passwort neu setzen (optional)
        if new_password and len(new_password) >= 8:
            user.set_password(new_password)
        elif new_password and len(new_password) < 8:
            flash("Neues Passwort muss mindestens 8 Zeichen lang sein.", "error")
            return redirect(url_for("admin.edit_user", user_id=user_id))

        user.first_name = first_name
        user.last_name = last_name
        user.updated_at = datetime.now(timezone.utc)

        db.session.commit()
        flash(f"Benutzer {user.email} aktualisiert.", "success")
        return redirect(url_for("admin.manage_users"))

    # GET: Formular anzeigen
    roles = db.session.scalars(db.select(models.Role)).all()
    groups = db.session.scalars(db.select(models.Group)).all()
    user_group_ids = [g.id for g in user.groups]
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("admin.manage_users"), "text": "Benutzerverwaltung"},
        {"text": f"Bearbeiten: {user.email}"},
    ]
    return render_template(
        "admin/user_form.html",
        user=user,
        roles=roles,
        groups=groups,
        user_group_ids=user_group_ids,
        breadcrumbs=breadcrumbs,
    )


@admin_bp.route("/user/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id: int):
    """Admin: Benutzer löschen."""
    user = db.session.get(models.User, user_id)
    if not user:
        flash("Benutzer nicht gefunden.", "error")
        return redirect(url_for("admin.manage_users"))

    email = user.email
    db.session.delete(user)
    db.session.commit()

    flash(f"Benutzer {email} gelöscht.", "success")
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/user/<int:user_id>/reset-password", methods=["POST"])
@login_required
@admin_required
def reset_password(user_id: int):
    """Admin: Passwort eines Benutzers zurücksetzen."""
    user = db.session.get(models.User, user_id)
    if not user:
        flash("Benutzer nicht gefunden.", "error")
        return redirect(url_for("admin.manage_users"))

    # Generiere neues Passwort
    password = generate_secure_password()
    user.set_password(password)
    user.force_password_change = True
    user.updated_at = datetime.now(timezone.utc)

    db.session.commit()

    session["_temp_password"] = password
    flash(
        f"Passwort für {user.email} zurückgesetzt. Neues Passwort wird einmalig angezeigt.",
        "success",
    )
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/user/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@admin_required
def toggle_active(user_id: int):
    """Admin: Account aktivieren/deaktivieren."""
    user = db.session.get(models.User, user_id)
    if not user:
        flash("Benutzer nicht gefunden.", "error")
        return redirect(url_for("admin.manage_users"))

    user.is_active = not user.is_active
    user.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    status = "aktiviert" if user.is_active else "deaktiviert"
    flash(f"Benutzer {user.email} {status}.", "success")
    return redirect(url_for("admin.manage_users"))


# =============================================================================
# KI-GYM: TRAINING & ANALYTICS
# =============================================================================

@admin_bp.route("/ki-gym", methods=["GET"])
@login_required
@admin_required
def ki_gym_dashboard():
    """KI-Gym Dashboard: Training-Status, Analytics, Manuelle Steuerung."""
    import ai_gym
    from models import LearnedPromptRule
    
    # Status für Tasks
    task_status = ai_gym.get_training_status('task')
    task_status_social = ai_gym.get_training_status('task', 'Soziale Kompetenzen')
    task_status_verbal = ai_gym.get_training_status('task', 'Verbale Kompetenzen')
    
    # Status für Reports
    report_status = ai_gym.get_training_status('report')
    
    # Active Rules
    active_task_rules = LearnedPromptRule.query.filter_by(type='task', is_active=True).count()
    active_report_rules = LearnedPromptRule.query.filter_by(type='report', is_active=True).count()
    
    # All rules for management
    all_rules = LearnedPromptRule.query.order_by(
        LearnedPromptRule.trained_at.desc()
    ).all()
    
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "KI-Gym Training"},
    ]
    
    return render_template(
        "admin/ki_gym.html",
        task_status=task_status,
        task_status_social=task_status_social,
        task_status_verbal=task_status_verbal,
        report_status=report_status,
        active_task_rules=active_task_rules,
        active_report_rules=active_report_rules,
        all_rules=all_rules,
        breadcrumbs=breadcrumbs,
    )


@admin_bp.route("/ki-gym/train/<response_type>", methods=["POST"])
@login_required
@admin_required
def ki_gym_train(response_type):
    """Trigger Training für Tasks oder Reports."""
    import ai_gym
    from flask_login import current_user
    
    if response_type not in ['task', 'report']:
        flash("Ungültiger Typ", "error")
        return redirect(url_for("admin.ki_gym_dashboard"))
    
    observation_area = request.form.get('observation_area', None)
    if observation_area == '':
        observation_area = None
    
    result = ai_gym.apply_training(
        response_type=response_type,
        observation_area=observation_area,
        created_by_id=current_user.id
    )
    
    if result['status'] == 'success':
        flash(result['message'], "success")
    else:
        flash(result['message'], "error")
    
    return redirect(url_for("admin.ki_gym_dashboard"))


@admin_bp.route("/ki-gym/rule/<int:rule_id>/toggle", methods=["POST"])
@login_required
@admin_required
def ki_gym_toggle_rule(rule_id):
    """Aktiviere/Deaktiviere eine LearnedPromptRule."""
    from models import LearnedPromptRule
    
    rule = db.session.get(LearnedPromptRule, rule_id)
    if not rule:
        flash("Rule nicht gefunden", "error")
        return redirect(url_for("admin.ki_gym_dashboard"))
    
    rule.is_active = not rule.is_active
    db.session.commit()
    
    status = "aktiviert" if rule.is_active else "deaktiviert"
    flash(f"Rule '{rule.rule_type}' {status}", "success")
    
    return redirect(url_for("admin.ki_gym_dashboard"))


@admin_bp.route("/ki-gym/rule/<int:rule_id>/delete", methods=["POST"])
@login_required
@admin_required
def ki_gym_delete_rule(rule_id):
    """Lösche eine LearnedPromptRule."""
    from models import LearnedPromptRule
    
    rule = db.session.get(LearnedPromptRule, rule_id)
    if not rule:
        flash("Rule nicht gefunden", "error")
        return redirect(url_for("admin.ki_gym_dashboard"))
    
    db.session.delete(rule)
    db.session.commit()
    
    flash(f"Rule '{rule.rule_type}' gelöscht", "success")
    
    return redirect(url_for("admin.ki_gym_dashboard"))
