# app.py - Umbau auf SQLAlchemy
"""Dieses Modul initialisiert die Flask-Anwendung und registriert alle Blueprints."""

# .env Datei laden
from dotenv import load_dotenv
load_dotenv()

import os
from datetime import UTC, datetime
from flask import Flask, render_template, url_for

# Neue Imports
from extensions import db, migrate, csrf
import models
from version import APP_VERSION, get_version_info

# Blueprints importieren
from blueprints.groups import groups_bp
from blueprints.participants import participants_bp
from blueprints.analysis import analysis_bp
from blueprints.data_io import data_io_bp
from blueprints.prompts import prompts_bp
from blueprints.explanation_blocks import explanation_blocks_bp
from blueprints.reports import bp as reports_bp

# App-Initialisierung
app = Flask(__name__)

# --- NEUE KONFIGURATION ---
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = True

# Erweiterungen initialisieren
db.init_app(app)
migrate.init_app(app, db)
csrf.init_app(app)


# Blueprints registrieren
app.register_blueprint(groups_bp)
app.register_blueprint(participants_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(data_io_bp)
app.register_blueprint(prompts_bp)
app.register_blueprint(explanation_blocks_bp)
app.register_blueprint(reports_bp)


# --- ZENTRALE FUNKTIONEN ---

@app.context_processor
def inject_now():
    """Fügt das aktuelle Jahr und Version in alle Templates ein."""
    return {
        "current_year": datetime.now(UTC).year,
        "app_version": APP_VERSION
    }

@app.template_filter('datetimeformat')
def datetimeformat_filter(value, format='%d.%m.%Y'):
    """Formatiert ein date-Objekt ins deutsche Datumsformat."""
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    return value.strftime(format)

# Die alten Filter und teardown-Funktionen sind durch SQLAlchemy nicht mehr nötig

# --- ZENTRALE ROUTE & INFOSEITE ---

@app.route("/")
def dashboard():
    """Zeigt das Dashboard an."""
    # --- KORRIGIERT: Veraltete Abfragen durch moderne SQLAlchemy-Syntax ersetzt ---
    total_groups = db.session.scalar(db.select(db.func.count(models.Group.id)))
    total_participants = db.session.scalar(db.select(db.func.count(models.Participant.id)))
    
    # Für 'completed_analyses' nehmen wir an, dass eine Analyse abgeschlossen ist, wenn ki_texts nicht leer ist.
    completed_analyses = db.session.scalar(
        db.select(db.func.count(models.Participant.id)).where(models.Participant.ki_texts.isnot(None) & (models.Participant.ki_texts != '{}'))
    )

    recently_updated = db.session.scalars(
        db.select(models.Participant).order_by(models.Participant.updated_at.desc()).limit(5)
    ).all()

    stats = {
        'total_groups': total_groups,
        'total_participants': total_participants,
        'completed_analyses': completed_analyses
    }
    
    breadcrumbs = [{"text": "Dashboard"}]
    return render_template(
        "dashboard.html",
        breadcrumbs=breadcrumbs,
        stats=stats,
        recently_updated_participants=recently_updated,
    )

@app.route("/info")
def info():
    """Zeigt die Info-Seite an."""
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Info"},
    ]
    return render_template("info.html", breadcrumbs=breadcrumbs)


# --- ERROR HANDLERS ---

@app.errorhandler(404)
def not_found(error):
    """404 Not Found Handler."""
    breadcrumbs = [{"link": url_for("dashboard"), "text": "Dashboard"}]
    return render_template('base.html', breadcrumbs=breadcrumbs, 
                         error_message="Seite nicht gefunden (404)"), 404

@app.errorhandler(500)
def internal_error(error):
    """500 Internal Server Error Handler."""
    db.session.rollback()
    breadcrumbs = [{"link": url_for("dashboard"), "text": "Dashboard"}]
    return render_template('base.html', breadcrumbs=breadcrumbs,
                         error_message="Interner Serverfehler (500)"), 500

@app.route('/health')
def health():
    """Health Check für Monitoring und Docker."""
    try:
        # Teste DB-Verbindung
        db.session.execute(db.select(db.func.count(models.Group.id)))
        return {'status': 'healthy', 'database': 'connected'}, 200
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500


# --- CLI COMMANDS ---
from generate_test_data import register_commands
register_commands(app)


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
    if not hasattr(app, '_templates_initialized'):
        initialize_app_templates()
        app._templates_initialized = True


# --- ANWENDUNG STARTEN ---

if __name__ == "__main__":
    debug_mode = os.getenv('FLASK_DEBUG', 'False') == 'True'
    app.run(port=5001, debug=debug_mode)

