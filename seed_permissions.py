#!/usr/bin/env python
"""Seed default permissions and assign them to roles."""

from app import app, db
import models

DEFAULT_PERMISSIONS = [
    # Gruppen
    ("groups.view", "Gruppen anzeigen", "Gruppen"),
    ("groups.edit", "Gruppen erstellen/bearbeiten", "Gruppen"),
    ("groups.delete", "Gruppen löschen", "Gruppen"),
    # Teilnehmer
    ("participants.view", "Teilnehmer anzeigen", "Teilnehmer"),
    ("participants.edit", "Teilnehmer bearbeiten/hinzufügen", "Teilnehmer"),
    ("participants.delete", "Teilnehmer löschen", "Teilnehmer"),
    # Beobachtungsdaten
    ("data_entry.view", "Beobachtungsdaten ansehen", "Daten"),
    ("data_entry.edit", "Beobachtungsdaten eingeben/bearbeiten", "Daten"),
    # KI-Analyse
    ("analysis.run", "KI-Analyse ausführen", "Analyse"),
    ("analysis.view_reports", "Berichte ansehen", "Analyse"),
    ("analysis.edit_reports", "Berichte bearbeiten", "Analyse"),
    # Beobachtungsaufgaben
    ("observation_tasks.view", "Beobachtungsaufgaben ansehen", "Aufgaben"),
    ("observation_tasks.manage", "Beobachtungsaufgaben verwalten", "Aufgaben"),
    # Prompts
    ("prompts.view", "Prompts ansehen", "Verwaltung"),
    ("prompts.manage", "Prompts verwalten", "Verwaltung"),
    # Textbausteine
    ("explanation_blocks.view", "Textbausteine ansehen", "Verwaltung"),
    ("explanation_blocks.manage", "Textbausteine verwalten", "Verwaltung"),
    # Import/Export
    ("import.run", "Daten importieren", "Datenübertragung"),
    ("export.run", "Daten exportieren", "Datenübertragung"),
    # User-Verwaltung
    ("users.manage", "Benutzer verwalten", "Administration"),
    ("roles.manage", "Rollen verwalten", "Administration"),
]

ROLE_TEMPLATES = {
    "admin": None,
    "beobachter": [
        "groups.view",
        "participants.view",
        "participants.edit",
        "data_entry.view",
        "data_entry.edit",
        "analysis.view_reports",
        "observation_tasks.view",
    ],
}


with app.app_context():
    for codename, description, category in DEFAULT_PERMISSIONS:
        existing = db.session.scalar(
            db.select(models.Permission).where(models.Permission.codename == codename)
        )
        if not existing:
            db.session.add(
                models.Permission(codename=codename, description=description, category=category)
            )
            print(f"  ✅ Permission '{codename}' erstellt")
    db.session.commit()

    for role_name, perm_codes in ROLE_TEMPLATES.items():
        role = db.session.scalar(
            db.select(models.Role).where(db.func.lower(models.Role.name) == role_name.lower())
        )
        if not role:
            print(f"  ⚠️ Rolle '{role_name}' nicht gefunden, wird übersprungen")
            continue

        if perm_codes is None:
            role.is_system = True
            print(f"  ✅ Rolle '{role_name}' als System-Rolle markiert")
        else:
            role.is_system = False
            role.permissions = []
            for code in perm_codes:
                perm = db.session.scalar(
                    db.select(models.Permission).where(models.Permission.codename == code)
                )
                if perm:
                    role.permissions.append(perm)
            print(f"  ✅ Rolle '{role_name}' → {len(perm_codes)} Permissions zugewiesen")

    db.session.commit()
    print("✅ Alle Permissions und Rollen-Zuordnungen erstellt!")
