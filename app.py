# app.py - Umbau auf SQLAlchemy
"""Dieses Modul initialisiert die Flask-Anwendung und registriert alle Blueprints."""

# .env Datei laden
from dotenv import load_dotenv

load_dotenv()

# === CRITICAL: Database Validation BEFORE any DB imports ===
# Prüft ob die Datenbank intakt ist und stellt sie bei Bedarf wieder her
# MUSS vor allen anderen Imports stehen!
import database_validator  # noqa: F401

import os
import secrets
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, url_for, g, request
from flask_login import current_user, login_required
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException

import models
from blueprints.analysis import analysis_bp
from blueprints.auth import auth_bp
from blueprints.admin import admin_bp
from blueprints.data_io import data_io_bp
from blueprints.explanation_blocks import explanation_blocks_bp
# Blueprints importieren
from blueprints.groups import groups_bp
from blueprints.participants import participants_bp
from blueprints.prompts import prompts_bp
from blueprints.reports import bp as reports_bp
from blueprints.observation_tasks import observation_tasks_bp
# Neue Imports
from config import DevelopmentConfig, ProductionConfig
from extensions import csrf, db, login_manager, migrate, limiter
from version import APP_VERSION, get_version_info

# App-Initialisierung
app = Flask(__name__)

# --- KONFIGURATION LADEN ---
env = os.getenv("FLASK_ENV", "development")
if env == "production":
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Erweiterungen initialisieren
db.init_app(app)
migrate.init_app(app, db)
csrf.init_app(app)
login_manager.init_app(app)
limiter.init_app(app)

# Flask-Login Konfiguration
login_manager.login_view = "auth.login"
login_manager.login_message = "Bitte melden Sie sich an."
login_manager.login_message_category = "warning"


# Flask-Login User Loader
@login_manager.user_loader
def load_user(user_id: str) -> models.User:
    """Lädt den aktuellen User per ID aus der Datenbank."""
    try:
        return db.session.get(models.User, int(user_id))
    except (ValueError, TypeError):
        return None


# Blueprints registrieren
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(groups_bp)
app.register_blueprint(participants_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(data_io_bp)
app.register_blueprint(prompts_bp)
app.register_blueprint(explanation_blocks_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(observation_tasks_bp)


# --- SECURITY MIDDLEWARE ---


@app.before_request
def generate_nonce():
    """Generate unique nonce for each request (CSP inline script support)."""
    g.csp_nonce = secrets.token_urlsafe(16)


@app.after_request
def set_security_headers(response):
    """
    Apply security headers to all responses:
    - Content Security Policy (CSP) with nonce support
    - X-Frame-Options (Clickjacking protection)
    - X-Content-Type-Options (MIME sniffing protection)
    - Strict-Transport-Security (HSTS for HTTPS)
    - Referrer-Policy (Privacy protection)
    """
    nonce = getattr(g, 'csp_nonce', None)
    
    # Content Security Policy
    # WICHTIG: 'unsafe-inline' OHNE nonce in script-src!
    # Laut CSP-Spec wird 'unsafe-inline' ignoriert wenn ein nonce vorhanden ist.
    # Da Templates onclick-Handler nutzen, brauchen wir unsafe-inline.
    # TODO: Alle onclick durch addEventListener ersetzen, dann auf nonce umstellen
    csp_directives = [
        "default-src 'self'",
        f"script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://code.jquery.com https://stackpath.bootstrapcdn.com https://cdn.tailwindcss.com https://cdn.quilljs.com https://js.bugfender.com",
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com https://stackpath.bootstrapcdn.com https://cdnjs.cloudflare.com https://cdn.quilljs.com",
        "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com",
        "img-src 'self' data: https:",
        "connect-src 'self' https://api.bugfender.com",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ]
    response.headers['Content-Security-Policy'] = "; ".join(csp_directives)
    
    # Additional security headers
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # HSTS (only for HTTPS in production)
    if request.is_secure and app.config.get('ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    
    return response


# --- ZENTRALE FUNKTIONEN ---


@app.context_processor
def inject_now():
    """Fügt das aktuelle Jahr, Version und CSP-Nonce in alle Templates ein."""
    return {
        "current_year": datetime.now(timezone.utc).year,
        "app_version": APP_VERSION,
        "csp_nonce": getattr(g, 'csp_nonce', ''),
        "bugfender_app_key": app.config.get("BUGFENDER_APP_KEY"),
    }


@app.template_filter("datetimeformat")
def datetimeformat_filter(value, format="%d.%m.%Y"):
    """Formatiert ein date-Objekt ins deutsche Datumsformat."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime(format)


# Die alten Filter und teardown-Funktionen sind durch SQLAlchemy nicht mehr nötig

# --- ZENTRALE ROUTE & INFOSEITE ---


@app.route("/")
@login_required
def dashboard():
    """Zeigt das Dashboard an."""
    # --- KORRIGIERT: Veraltete Abfragen durch moderne SQLAlchemy-Syntax ersetzt ---
    total_groups = db.session.scalar(db.select(db.func.count(models.Group.id)))
    total_participants = db.session.scalar(
        db.select(db.func.count(models.Participant.id))
    )

    # Für 'completed_analyses' nehmen wir an, dass eine Analyse abgeschlossen ist, wenn ki_texts nicht leer ist.
    completed_analyses = db.session.scalar(
        db.select(db.func.count(models.Participant.id)).where(
            models.Participant.ki_texts.isnot(None)
            & (models.Participant.ki_texts != "{}")
        )
    )

    recent_activities = db.session.scalars(
        db.select(models.ActivityLog)
        .order_by(models.ActivityLog.created_at.desc())
        .limit(10)
    ).all()

    stats = {
        "total_groups": total_groups,
        "total_participants": total_participants,
        "completed_analyses": completed_analyses,
    }

    # KI-Gym Statistiken (nur für Admins)
    ai_gym_stats = None
    if current_user.is_admin:
        try:
            total_raw_responses = db.session.scalar(
                db.select(db.func.count(models.AIRawResponse.id))
            )
            edited_responses = db.session.scalar(
                db.select(db.func.count(models.ContentEdit.id))
            )
            active_rules = db.session.scalar(
                db.select(db.func.count(models.LearnedPromptRule.id)).where(
                    models.LearnedPromptRule.is_active == True
                )
            )
            ai_gym_stats = {
                "total_raw_responses": total_raw_responses or 0,
                "edited_responses": edited_responses or 0,
                "active_rules": active_rules or 0,
            }
        except Exception:
            # Falls KI-Gym-Tabellen noch nicht existieren
            ai_gym_stats = None

    breadcrumbs = [{"text": "Dashboard"}]
    return render_template(
        "dashboard.html",
        breadcrumbs=breadcrumbs,
        stats=stats,
        ai_gym_stats=ai_gym_stats,
        recent_activities=recent_activities,
    )


@app.route("/info")
@login_required
def info():
    """Zeigt die Info-Seite an."""
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Info"},
    ]
    return render_template("info.html", breadcrumbs=breadcrumbs)


# --- ERROR HANDLERS ---


def _wants_json_response() -> bool:
    if request.path.startswith("/api/"):
        return True
    if request.is_json:
        return True
    accepts = request.accept_mimetypes
    return accepts["application/json"] >= accepts["text/html"]


@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    message = getattr(error, "description", "CSRF-Token fehlt oder ist ungültig.")
    if _wants_json_response():
        return jsonify({"error": "Bad Request", "message": message}), 400
    breadcrumbs = [{"link": url_for("dashboard"), "text": "Dashboard"}]
    return (
        render_template(
            "base.html",
            breadcrumbs=breadcrumbs,
            error_message=message,
        ),
        400,
    )


@app.errorhandler(HTTPException)
def handle_http_exception(error):
    code = error.code or 500
    description = error.description if getattr(error, "description", None) else error.name
    if code >= 500:
        db.session.rollback()
    if _wants_json_response():
        return jsonify({"error": error.name, "message": description}), code
    breadcrumbs = [{"link": url_for("dashboard"), "text": "Dashboard"}]
    return (
        render_template(
            "base.html",
            breadcrumbs=breadcrumbs,
            error_message=f"{description} ({code})",
        ),
        code,
    )


@app.errorhandler(Exception)
def handle_unhandled_exception(error):
    error_id = secrets.token_hex(8)
    app.logger.exception("Unhandled exception [%s]", error_id)
    db.session.rollback()
    message = f"Interner Serverfehler (500). Fehler-ID: {error_id}"
    if _wants_json_response():
        return (
            jsonify(
                {
                    "error": "Internal Server Error",
                    "message": "Ein interner Fehler ist aufgetreten.",
                    "error_id": error_id,
                }
            ),
            500,
        )
    breadcrumbs = [{"link": url_for("dashboard"), "text": "Dashboard"}]
    return (
        render_template(
            "base.html",
            breadcrumbs=breadcrumbs,
            error_message=message,
        ),
        500,
    )


@app.route("/health")
def health():
    """Health Check für Monitoring und Docker."""
    try:
        # Teste DB-Verbindung
        db.session.execute(db.select(db.func.count(models.Group.id)))
        return {"status": "healthy", "database": "connected"}, 200
    except Exception:
        app.logger.exception("Health check failed")
        return {"status": "unhealthy"}, 500


# --- CLI COMMANDS ---
from generate_test_data import register_commands
from load_default_prompts import register_command as register_prompt_command
from backup_database import register_backup_commands, startup_backup
from cli_commands import register_auth_commands

register_commands(app)
register_prompt_command(app)
register_backup_commands(app)
register_auth_commands(app)


# --- INITIALISIERUNG ---


def initialize_app_templates():
    """
    Lädt Standard-Report-Templates beim App-Start (nur wenn nötig).
    Diese Funktion kann auf der ersten Request aufgerufen werden.
    """
    from blueprints.reports import get_default_templates

    try:
        get_default_templates()
    except Exception as e:
        app.logger.warning(f"Fehler beim Laden der Standard-Templates: {e}")


# Lazy-load beim ersten Template-Request
@app.before_request
def _before_first_request():
    """Wird vor der erste Request aufgerufen"""
    if not hasattr(app, "_templates_initialized"):
        initialize_app_templates()
        app._templates_initialized = True
    # Automatisches Backup bei erstem Request (einmalig pro App-Start)
    if not hasattr(app, "_backup_done"):
        try:
            startup_backup()
        except Exception as e:
            app.logger.warning(f"Automatisches Backup fehlgeschlagen: {e}")
        app._backup_done = True


# --- ANWENDUNG STARTEN ---

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False") == "True"
    app.run(port=5001, debug=debug_mode)
