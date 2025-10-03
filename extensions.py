# extensions.py
"""
Initialisiert Flask-Erweiterungen, um zirkuläre Importe zu vermeiden.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# SQLAlchemy- und Migrate-Objekte erstellen
db = SQLAlchemy()
migrate = Migrate()
