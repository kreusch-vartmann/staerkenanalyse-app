#!/usr/bin/env python
"""Create admin user for testing."""

from app import app, db
import models

with app.app_context():
    # Ensure default roles exist
    default_roles = [
        ("admin", "Vollzugriff auf alle Funktionen"),
        ("beobachter", "Zugriff auf zugewiesene Gruppen"),
    ]
    for role_name, role_desc in default_roles:
        existing = db.session.scalar(
            db.select(models.Role).where(db.func.lower(models.Role.name) == role_name.lower())
        )
        if not existing:
            db.session.add(models.Role(name=role_name, description=role_desc))
            print(f"✅ Rolle '{role_name}' erstellt")
    db.session.commit()

    admin_role = db.session.scalar(
        db.select(models.Role).where(db.func.lower(models.Role.name) == "admin")
    )
    
    # Check if admin user exists
    admin_email = "admin@testlocal.de"
    admin = db.session.scalar(db.select(models.User).where(models.User.email == admin_email))
    
    if not admin:
        admin = models.User(
            email=admin_email,
            first_name="Admin",
            last_name="User",
            role=admin_role,
            is_active=True,
            force_password_change=False
        )
        admin.set_password("AdminPassword123")
        db.session.add(admin)
        db.session.commit()
        print(f"✅ Admin-User erstellt: {admin_email}")
        print(f"   Passwort: AdminPassword123")
    else:
        print(f"ℹ️  Admin-User existiert bereits: {admin_email}")
