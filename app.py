# app.py - Umbau auf SQLAlchemy
"""Dieses Modul initialisiert die Flask-Anwendung und registriert alle Blueprints."""

# .env Datei laden
from dotenv import load_dotenv
load_dotenv()

import os
from datetime import UTC, datetime
from flask import Flask, render_template, url_for

# Neue Imports
from extensions import db, migrate
import models

# Blueprints importieren
from blueprints.groups import groups_bp
from blueprints.participants import participants_bp
from blueprints.analysis import analysis_bp
from blueprints.data_io import data_io_bp
from blueprints.prompts import prompts_bp

# App-Initialisierung
app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- NEUE KONFIGURATION ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Erweiterungen initialisieren
db.init_app(app)
migrate.init_app(app, db)


# Blueprints registrieren
app.register_blueprint(groups_bp)
app.register_blueprint(participants_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(data_io_bp)
app.register_blueprint(prompts_bp)


# --- ZENTRALE FUNKTIONEN ---

@app.context_processor
def inject_now():
    """Fügt das aktuelle Jahr in alle Templates ein."""
    return {"current_year": datetime.now(UTC).year}

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


# --- ANWENDUNG STARTEN ---

if __name__ == "__main__":
    app.run(port=5001, debug=True)

