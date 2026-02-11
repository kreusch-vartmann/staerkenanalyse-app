"""
Auth Blueprint: Login, Logout, Passwort ändern.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from datetime import datetime, timezone

import models
from extensions import db, limiter

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    """Login-Route: E-Mail + Passwort."""
    
    # Wenn bereits eingeloggt → Dashboard
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("E-Mail und Passwort erforderlich.", "error")
            return redirect(url_for("auth.login"))

        # Finde User
        user = db.session.scalar(
            db.select(models.User).where(models.User.email == email)
        )

        # Validiere Passwort und Status
        if not user or not user.check_password(password):
            flash("E-Mail oder Passwort ungültig.", "error")
            return redirect(url_for("auth.login"))

        if not user.is_active:
            flash(
                "Ihr Account ist deaktiviert. Bitte kontaktieren Sie einen Administrator.",
                "error",
            )
            return redirect(url_for("auth.login"))

        # Login erfolgreich
        login_user(user, remember=True)
        
        # Update last_login
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()

        # Wenn Passwort-Änderung erzwungen → dorthin umleiten
        if user.force_password_change:
            flash("Bitte ändern Sie Ihr Passwort beim ersten Login.", "info")
            return redirect(url_for("auth.change_password"))

        # Redirect zu next oder Dashboard (nur relative Pfade erlauben)
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/") and not next_page.startswith("//"):
            return redirect(next_page)
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Logout-Route."""
    logout_user()
    flash("Sie wurden abgemeldet.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    """Passwort ändern (für eingeloggte User)."""
    
    if request.method == "POST":
        old_password = request.form.get("old_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validierung
        if not old_password or not new_password or not confirm_password:
            flash("Alle Felder erforderlich.", "error")
            return redirect(url_for("auth.change_password"))

        if not current_user.check_password(old_password):
            flash("Altes Passwort ist ungültig.", "error")
            return redirect(url_for("auth.change_password"))

        if len(new_password) < 8:
            flash("Neues Passwort muss mindestens 8 Zeichen lang sein.", "error")
            return redirect(url_for("auth.change_password"))

        if new_password != confirm_password:
            flash("Passwörter stimmen nicht überein.", "error")
            return redirect(url_for("auth.change_password"))

        # Speichere neues Passwort
        current_user.set_password(new_password)
        current_user.force_password_change = False
        db.session.commit()

        flash("Passwort erfolgreich geändert.", "success")
        return redirect(url_for("dashboard"))

    return render_template(
        "change_password.html",
        force_change=current_user.force_password_change,
    )
