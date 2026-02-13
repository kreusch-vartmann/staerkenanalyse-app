"""
Admin Blueprint: Benutzerverwaltung (CRUD), Rollen, Gruppen-Zuordnung.
Alle Routes sind Admin-only.
"""

from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import login_required

import models
from decorators import admin_required, permission_required
from extensions import db
from utils import generate_secure_password
from validation import AdminUserCreateForm, AdminUserUpdateForm, format_validation_error, parse_form

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _clear_user_groups(user: models.User) -> None:
    """Entfernt alle Gruppen-Zuordnungen für einen User (kompatibel mit dynamic relationship)."""
    for group in list(user.groups):
        user.groups.remove(group)


@admin_bp.route("/users", methods=["GET"])
@login_required
@permission_required("users.manage")
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
@permission_required("users.manage")
def add_user():
    """Admin: Neuen Benutzer erstellen."""
    
    if request.method == "POST":
        form_data = request.form.to_dict()
        form_data["role_name"] = form_data.get("role", "beobachter")
        parsed, error = parse_form(AdminUserCreateForm, form_data)
        if error:
            flash(format_validation_error(error), "error")
            return redirect(url_for("admin.add_user"))

        email = parsed.email
        first_name = parsed.first_name
        last_name = parsed.last_name
        role_name = parsed.role_name
        group_ids = request.form.getlist("groups")

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
        if group_ids and not role.is_system:
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
@permission_required("users.manage")
def edit_user(user_id: int):
    """Admin: Benutzer bearbeiten."""
    user = db.session.get(models.User, user_id)
    if not user:
        flash("Benutzer nicht gefunden.", "error")
        return redirect(url_for("admin.manage_users"))

    if request.method == "POST":
        form_data = request.form.to_dict()
        form_data["role_name"] = form_data.get("role", user.role.name)
        parsed, error = parse_form(AdminUserUpdateForm, form_data)
        if error:
            flash(format_validation_error(error), "error")
            return redirect(url_for("admin.edit_user", user_id=user_id))

        first_name = parsed.first_name
        last_name = parsed.last_name
        role_name = parsed.role_name
        group_ids = request.form.getlist("groups")
        new_password = (parsed.new_password or "").strip()

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
        if not user.role.is_system:
            _clear_user_groups(user)
            for group_id in group_ids:
                try:
                    group = db.session.get(models.Group, int(group_id))
                    if group:
                        user.groups.append(group)
                except (ValueError, TypeError):
                    pass
        else:
            _clear_user_groups(user)

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
@permission_required("users.manage")
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
@permission_required("users.manage")
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
@permission_required("users.manage")
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


# =============================================================================
# Rollenverwaltung
# =============================================================================


@admin_bp.route("/roles", methods=["GET"])
@login_required
@permission_required("roles.manage")
def manage_roles():
    """Admin: Übersicht aller Rollen."""
    roles = db.session.scalars(db.select(models.Role).order_by(models.Role.name)).all()
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Rollenverwaltung"},
    ]
    return render_template("admin/manage_roles.html", roles=roles, breadcrumbs=breadcrumbs)


@admin_bp.route("/role/add", methods=["GET", "POST"])
@login_required
@permission_required("roles.manage")
def add_role():
    """Admin: Neue Rolle erstellen."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        perm_ids = request.form.getlist("permissions")

        if not name:
            flash("Rollenname ist erforderlich.", "error")
            return redirect(url_for("admin.add_role"))

        existing = db.session.scalar(
            db.select(models.Role).where(db.func.lower(models.Role.name) == name.lower())
        )
        if existing:
            flash(f"Rolle '{name}' existiert bereits.", "error")
            return redirect(url_for("admin.add_role"))

        new_role = models.Role(name=name, description=description, is_system=False)
        for pid in perm_ids:
            try:
                perm = db.session.get(models.Permission, int(pid))
            except (ValueError, TypeError):
                perm = None
            if perm:
                new_role.permissions.append(perm)

        db.session.add(new_role)
        db.session.commit()
        flash(f"Rolle '{name}' erfolgreich erstellt.", "success")
        return redirect(url_for("admin.manage_roles"))

    permissions = db.session.scalars(
        db.select(models.Permission).order_by(models.Permission.category, models.Permission.codename)
    ).all()

    perm_groups = {}
    for permission in permissions:
        category = permission.category or "Sonstige"
        perm_groups.setdefault(category, []).append(permission)

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("admin.manage_roles"), "text": "Rollenverwaltung"},
        {"text": "Neue Rolle"},
    ]
    return render_template(
        "admin/role_form.html",
        role=None,
        perm_groups=perm_groups,
        breadcrumbs=breadcrumbs,
    )


@admin_bp.route("/role/<int:role_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("roles.manage")
def edit_role(role_id):
    """Admin: Rolle bearbeiten."""
    role = db.session.get(models.Role, role_id)
    if not role:
        flash("Rolle nicht gefunden.", "error")
        return redirect(url_for("admin.manage_roles"))

    if role.is_system:
        flash("System-Rollen können nicht bearbeitet werden.", "warning")
        return redirect(url_for("admin.manage_roles"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        perm_ids = request.form.getlist("permissions")

        if name:
            name_conflict = db.session.scalar(
                db.select(models.Role)
                .where(db.func.lower(models.Role.name) == name.lower())
                .where(models.Role.id != role.id)
            )
            if name_conflict:
                flash(f"Rollenname '{name}' ist bereits vergeben.", "error")
                return redirect(url_for("admin.edit_role", role_id=role_id))
            role.name = name

        role.description = description
        role.permissions = []

        for pid in perm_ids:
            try:
                perm = db.session.get(models.Permission, int(pid))
            except (ValueError, TypeError):
                perm = None
            if perm:
                role.permissions.append(perm)

        db.session.commit()
        flash(f"Rolle '{role.name}' aktualisiert.", "success")
        return redirect(url_for("admin.manage_roles"))

    permissions = db.session.scalars(
        db.select(models.Permission).order_by(models.Permission.category, models.Permission.codename)
    ).all()

    perm_groups = {}
    for permission in permissions:
        category = permission.category or "Sonstige"
        perm_groups.setdefault(category, []).append(permission)

    role_perm_ids = {p.id for p in role.permissions}
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("admin.manage_roles"), "text": "Rollenverwaltung"},
        {"text": f"Rolle: {role.name}"},
    ]
    return render_template(
        "admin/role_form.html",
        role=role,
        perm_groups=perm_groups,
        role_perm_ids=role_perm_ids,
        breadcrumbs=breadcrumbs,
    )


@admin_bp.route("/role/<int:role_id>/delete", methods=["POST"])
@login_required
@permission_required("roles.manage")
def delete_role(role_id):
    """Admin: Rolle löschen (nur wenn keine User zugewiesen)."""
    role = db.session.get(models.Role, role_id)
    if not role:
        flash("Rolle nicht gefunden.", "error")
        return redirect(url_for("admin.manage_roles"))

    if role.is_system:
        flash("System-Rollen können nicht gelöscht werden.", "error")
        return redirect(url_for("admin.manage_roles"))

    if role.users:
        flash(
            f"Rolle '{role.name}' hat noch {len(role.users)} zugewiesene Benutzer. Bitte erst die Benutzer einer anderen Rolle zuweisen.",
            "error",
        )
        return redirect(url_for("admin.manage_roles"))

    db.session.delete(role)
    db.session.commit()
    flash(f"Rolle '{role.name}' gelöscht.", "success")
    return redirect(url_for("admin.manage_roles"))
