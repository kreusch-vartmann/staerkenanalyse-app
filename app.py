# app.py - FINALE MODULARISIERTE VERSION
"""Dieses Modul initialisiert die Flask-Anwendung und registriert alle Blueprints."""

import os
from datetime import UTC, datetime
from flask import Flask, render_template, url_for

import database as db

# Blueprints importieren
from blueprints.groups import groups_bp
from blueprints.participants import participants_bp
from blueprints.analysis import analysis_bp
from blueprints.data_io import data_io_bp
from blueprints.prompts import prompts_bp # <-- NEU

# App-Initialisierung
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Blueprints registrieren
app.register_blueprint(groups_bp)
app.register_blueprint(participants_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(data_io_bp)
app.register_blueprint(prompts_bp) # <-- NEU


# --- ZENTRALE FUNKTIONEN ---

@app.teardown_appcontext
def close_connection(_exception):
    """schließt die Datenbankverbindung am Ende jeder Anfrage."""
    db.close_db()

@app.context_processor
def inject_now():
    """Fügt das aktuelle Jahr in alle Templates ein."""
    return {"current_year": datetime.now(UTC).year}

@app.template_filter("datetimeformat")
def datetimeformat(value, fmt="%d.%m.%Y"):
    """Formatiert ein Datum in ein lesbares Format."""
    if not value: return ""
    if isinstance(value, datetime): return value.strftime(fmt)
    if isinstance(value, str):
        try:
            dt = datetime.strptime(value, "%Y-%m-%d"); return dt.strftime(fmt)
        except ValueError:
            try:
                dt = datetime.strptime(value, "%d.%m.%Y"); return dt.strftime(fmt)
            except ValueError: return value
    return value


# --- ZENTRALE ROUTE & INFOSEITE ---

@app.route("/")
def dashboard():
    """Zeigt das Dashboard mit Statistiken und kürzlich aktualisierten Teilnehmern an."""
    stats = db.get_dashboard_stats()
    recently_updated = db.get_recently_updated_participants()
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