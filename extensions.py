# extensions.py
"""
Initialisiert Flask-Erweiterungen, um zirkuläre Importe zu vermeiden.
"""
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# SQLAlchemy- und Migrate-Objekte erstellen
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
