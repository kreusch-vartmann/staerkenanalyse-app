# app.py - FINALE MODULARISIERTE VERSION
"""Dieses Modul initialisiert die Flask-Anwendung und registriert alle Blueprints."""

# NEU: .env Datei laden, damit FLASK_APP und DATABASE_URL bekannt sind
from dotenv import load_dotenv
load_dotenv()

import os
from datetime import UTC, datetime
from flask import Flask, render_template, url_for

# NEU: Wir importieren unsere neuen Erweiterungen
from extensions import db, migrate
# NEU: Wir importieren die Models, damit Flask-Migrate sie findet
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

# --- NEUE KONFIGURATION FÜR POSTGRESQL & SQLAlchemy ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# NEU: Initialisierung der Erweiterungen mit der App
db.init_app(app)
migrate.init_app(app, db)


# ENTFERNT: Die alte `database.py`-Datei wird hier nicht mehr importiert.
# import database as db

# Blueprints registrieren
app.register_blueprint(groups_bp)
app.register_blueprint(participants_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(data_io_bp)
app.register_blueprint(prompts_bp)


# --- ZENTRALE FUNKTIONEN ---

# ENTFERNT: Die alte Funktion zum Schließen der DB-Verbindung wird nicht mehr benötigt.
# SQLAlchemy verwaltet die Verbindungen automatisch.
# @app.teardown_appcontext
# def close_connection(_exception):
#     """Schließt die Datenbankverbindung am Ende jeder Anfrage."""
#     db.close_db()

@app.context_processor
def inject_now():
    """Fügt das aktuelle Jahr in alle Templates ein."""
    return {"current_year": datetime.now(UTC).year}

@app.template_filter("datetimeformat")
def datetimeformat(value, fmt="%d.%m.%Y"):
    """Formatiert ein Datum in ein lesbares Format."""
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, str):
        try:
            # Versucht, verschiedene String-Formate zu parsen
            dt = datetime.fromisoformat(value)
            return dt.strftime(fmt)
        except (ValueError, TypeError):
            # Fallback, falls das Format nicht passt
            return value
    return value


# --- ZENTRALE ROUTE & INFOSEITE ---

@app.route("/")
def dashboard():
    """Zeigt das Dashboard mit Statistiken und kürzlich aktualisierten Teilnehmern an."""
    # VORÜBERGEHEND: Die alten DB-Aufrufe werden wir später ersetzen.
    # Für den Moment verwenden wir Platzhalter, damit die App startet.
    stats = {
        'total_groups': models.Group.query.count(),
        'total_participants': models.Participant.query.count(),
        'completed_analyses': 0  # Diese Logik müssen wir neu definieren
    }
    recently_updated = models.Participant.query.order_by(models.Participant.updated_at.desc()).limit(5).all()

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

