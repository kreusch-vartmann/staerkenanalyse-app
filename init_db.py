#!/usr/bin/env python
"""Create all database tables from models."""

from app import app, db
import models

with app.app_context():
    db.create_all()
    print("✅ Alle Tabellen erfolgreich erstellt!")

    # Seed default roles (idempotent)
    default_roles = [
        ("admin", "Vollzugriff auf alle Funktionen", True),
        ("beobachter", "Zugriff auf zugewiesene Gruppen", False),
    ]
    for role_name, role_desc, is_system in default_roles:
        existing = db.session.scalar(
            db.select(models.Role).where(db.func.lower(models.Role.name) == role_name.lower())
        )
        if not existing:
            db.session.add(models.Role(name=role_name, description=role_desc, is_system=is_system))
            print(f"  ✅ Rolle '{role_name}' erstellt")
        else:
            existing.description = existing.description or role_desc
            if role_name.lower() == "admin":
                existing.is_system = True
            elif existing.is_system is None:
                existing.is_system = False
    db.session.commit()
