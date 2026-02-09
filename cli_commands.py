"""CLI Commands für initiale Admin-Erstellung."""

import click
from datetime import datetime, timezone
import models
from extensions import db
from utils import generate_secure_password


def register_auth_commands(app):
    """Registriert Auth-bezogene CLI Commands."""

    @app.cli.command("create-admin")
    @click.option(
        "--email",
        prompt="Admin E-Mail",
        help="E-Mail des Admin-Benutzers",
    )
    @click.option(
        "--password",
        default=None,
        help="Admin-Passwort (wenn nicht angegeben: wird generiert)",
    )
    @click.option(
        "--first-name",
        prompt="Vorname",
        default="Admin",
        help="Vorname des Admins",
    )
    @click.option(
        "--last-name",
        prompt="Nachname",
        default="User",
        help="Nachname des Admins",
    )
    def create_admin(email, password, first_name, last_name):
        """Erstellt einen Admin-Benutzer (idempotent)."""

        email = email.strip().lower()

        # Prüfe ob Rollen existieren
        admin_role = db.session.scalar(
            db.select(models.Role).where(models.Role.name == "admin")
        )
        if not admin_role:
            click.echo("⚠️  Admin-Rolle nicht gefunden. Bitte 'flask db upgrade' ausführen.")
            return

        # Prüfe ob Admin bereits existiert
        existing_admin = db.session.scalar(
            db.select(models.User).where(models.User.email == email)
        )
        if existing_admin:
            click.echo(
                f"✓ Admin mit E-Mail '{email}' existiert bereits. Keine Änderung."
            )
            return

        # Generiere oder nutze Passwort
        if not password:
            password = generate_secure_password()
            click.echo(f"🔑 Generiertes Passwort: {password}")
        else:
            if len(password) < 8:
                click.echo("❌ Passwort muss mindestens 8 Zeichen lang sein.")
                return

        # Erstelle Admin-User
        admin_user = models.User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role_id=admin_role.id,
            is_active=True,
            force_password_change=True,  # Security Best Practice: PW-Änderung nach Erstlogin
        )
        admin_user.set_password(password)

        db.session.add(admin_user)
        db.session.commit()

        click.echo(f"✅ Admin-Benutzer '{email}' erfolgreich erstellt.")
        click.echo(f"   Vorname: {first_name}")
        click.echo(f"   Nachname: {last_name}")
        click.echo(f"   Passwort: {password}")
        click.echo("\n⚠️  Diese Angaben sollten sicher aufbewahrt werden!")
