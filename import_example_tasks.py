#!/usr/bin/env python
"""
Flask-CLI-Command zum Import der Referenzaufgaben (EXAMPLE_TASKS).

Usage:
    flask import-example-tasks

Legt die beiden Referenzaufgaben ("Diskussion Erbengemeinschaft" für
Verbale Kompetenzen, "Plakat-Gestaltung" für Soziale Kompetenzen) als
Task-Einträge mit is_example=True an, damit sie in der Beobachtungs-
aufgaben-Bibliothek als Standard-Vorlagen auswählbar sind.

Rein additiv/idempotent (prüft je Titel + is_example=True), daher sicher
für automatischen Aufruf bei jedem Container-Start (docker-entrypoint.sh).
"""

import click
from flask.cli import with_appcontext

from extensions import db
from models import Task, TaskVersion, User, Role


@click.command("import-example-tasks")
@with_appcontext
def import_example_tasks_command():
    """Importiert die Referenzaufgaben (EXAMPLE_TASKS) in die Datenbank."""
    from blueprints.observation_tasks import EXAMPLE_TASKS

    click.echo("=" * 70)
    click.echo("🔍 Referenzaufgaben importieren")
    click.echo("=" * 70)

    # Irgendein Admin genügt als created_by_id (NOT NULL-Feld). Bewusst
    # NICHT auf eine feste E-Mail wie "admin@local.de" angewiesen - die
    # existiert nur in der lokalen Dev-DB, nicht in echten Deployments
    # (dort legt jeder Betreiber seinen eigenen Admin per `flask
    # create-admin --email ...` an). Kriterium spiegelt models.py
    # User.is_admin (is_system ODER Rollenname "admin").
    admin_user = db.session.scalar(
        db.select(User)
        .join(Role)
        .where(db.or_(Role.is_system.is_(True), db.func.lower(Role.name) == "admin"))
        .limit(1)
    )
    if not admin_user:
        click.echo(
            "❌ Kein Admin-Benutzer gefunden. Bitte zuerst 'flask create-admin' "
            "und 'python seed_permissions.py' ausführen."
        )
        return

    imported_count = 0
    skipped_count = 0

    for task_key, task_data in EXAMPLE_TASKS.items():
        title = task_data["title"]

        existing = db.session.scalar(
            db.select(Task).where(Task.title == title, Task.is_example.is_(True))
        )
        if existing:
            click.echo(f"⏭️  '{title}' existiert bereits (ID: {existing.id})")
            skipped_count += 1
            continue

        new_task = Task(
            title=title,
            description=task_data.get("task_description", "").strip(),
            notes=f"Beobachtungsfokus: {task_data.get('observation_focus', '')}",
            observation_area=task_data["observation_area"],
            participant_count=task_data.get("participant_count"),
            duration_minutes=task_data.get("duration_minutes"),
            is_active=True,
            is_example=True,
            ki_model=None,
            created_by_id=admin_user.id,
        )
        db.session.add(new_task)
        db.session.flush()

        version = TaskVersion(
            task_id=new_task.id,
            version_number=1.0,
            content=task_data.get("task_description", "").strip(),
            change_notes="Initiale Version (Referenzaufgabe)",
            created_by_id=admin_user.id,
        )
        db.session.add(version)
        db.session.flush()

        new_task.current_version_id = version.id
        db.session.commit()

        click.echo(f"✅ '{title}' importiert (ID: {new_task.id}, Bereich: {task_data['observation_area']})")
        imported_count += 1

    click.echo()
    click.echo(f"📊 {imported_count} importiert, {skipped_count} übersprungen")
    click.echo("=" * 70)


def register_command(app):
    """Registriert den Command in der Flask-App."""
    app.cli.add_command(import_example_tasks_command)
