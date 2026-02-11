#!/usr/bin/env python
"""Create admin user for testing."""

from app import app, db
import models

with app.app_context():
    # Check if admin role exists
    admin_role = db.session.scalar(db.select(models.Role).where(models.Role.name == "Admin"))
    if not admin_role:
        admin_role = models.Role(name="Admin", description="Administrator mit vollen Rechten")
        db.session.add(admin_role)
        db.session.commit()
        print("✅ Admin-Rolle erstellt")
    
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
