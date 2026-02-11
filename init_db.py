#!/usr/bin/env python
"""Create all database tables from models."""

from app import app, db
import models

with app.app_context():
    db.create_all()
    print("✅ Alle Tabellen erfolgreich erstellt!")
