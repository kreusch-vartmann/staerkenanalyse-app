#!/usr/bin/env python3
"""
Flask CLI Command zum Laden von Standard-Prompts aus dem prompts/ Ordner.

Usage:
    flask load-default-prompts
    flask load-default-prompts --clear  # Löscht alle vorhandenen Prompts
"""

import os
from pathlib import Path

import click
from flask.cli import with_appcontext

from extensions import db
from models import Prompt


PROMPT_FILES = {
    "staerkenanalyse_prompt_final.txt": {
        "name": "Stärkenanalyse Final",
        "description": "Finale optimierte Version des Stärkenanalyse-Prompts mit Riemann-Kreuz-Polaritäten",
    },
    "bestsofar2.txt": {
        "name": "Best Performing v2",
        "description": "Experimenteller Prompt mit hoher Analysequalität (Version 2)",
    },
    "bestsofar.txt": {
        "name": "Best Performing v1",
        "description": "Experimenteller Prompt mit hoher Analysequalität (Version 1)",
    },
    "structured_report_mistral.txt": {
        "name": "Strukturierter Report (Mistral)",
        "description": "Für Mistral-API optimierter strukturierter Report-Prompt",
    },
    "structured_report_json.txt": {
        "name": "Strukturierter Report (JSON)",
        "description": "Generiert maschinenlesbare JSON-formatierte Analysen",
    },
    "structured_report.txt": {
        "name": "Strukturierter Report",
        "description": "Generiert klar strukturierte Analyseberichte",
    },
    "staerkenanalyse_prompt.txt": {
        "name": "Stärkenanalyse Original",
        "description": "Initiale Version des Stärkenanalyse-Prompts (historisch)",
    },
    "mistralsozverb4.txt": {
        "name": "MistralSozVerb4",
        "description": "Rekonstruiertes Prompt-Template für soz./verb. Stärkenanalyse (JSON-Output)",
    },
}


@click.command("load-default-prompts")
@click.option(
    "--clear",
    is_flag=True,
    help="Löscht alle vorhandenen Prompts vor dem Import (VORSICHT!)",
)
@with_appcontext
def load_default_prompts(clear):
    """Lädt Standard-Prompts aus dem prompts/ Ordner in die Datenbank."""
    click.echo("=" * 70)
    click.echo("📝 Standard-Prompts in Datenbank laden")
    click.echo("=" * 70)
    click.echo()

    prompts_dir = Path(__file__).parent / "prompts"

    if not prompts_dir.exists():
        click.echo(f"❌ Fehler: {prompts_dir} existiert nicht!")
        return

    # Optional: Vorhandene Prompts löschen
    if clear:
        if click.confirm(
            "⚠️ WARNUNG: Alle vorhandenen Prompts werden gelöscht. Fortfahren?",
            default=False,
        ):
            count = Prompt.query.delete()
            db.session.commit()
            click.echo(f"🗑️ {count} Prompts gelöscht")
            click.echo()
        else:
            click.echo("❌ Abgebrochen")
            return

    # Lade Prompts
    loaded_count = 0
    skipped_count = 0

    for filename, metadata in PROMPT_FILES.items():
        filepath = prompts_dir / filename

        if not filepath.exists():
            click.echo(f"⚠️ Datei nicht gefunden: {filename}")
            continue

        # Prüfe ob Prompt bereits existiert (nach Name)
        existing = Prompt.query.filter_by(name=metadata["name"]).first()

        if existing:
            click.echo(f"⊘ Überspringe: {metadata['name']} (existiert bereits)")
            skipped_count += 1
            continue

        # Lade Dateiinhalt
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Erstelle Prompt
            new_prompt = Prompt(
                name=metadata["name"],
                description=metadata["description"],
                content=content,
            )
            db.session.add(new_prompt)
            db.session.commit()

            click.echo(f"✅ Geladen: {metadata['name']} ({len(content)} Zeichen)")
            loaded_count += 1

        except Exception as e:
            db.session.rollback()
            click.echo(f"❌ Fehler bei {filename}: {e}")

    # Zusammenfassung
    click.echo()
    click.echo("=" * 70)
    click.echo("📊 Zusammenfassung:")
    click.echo(f"   • {loaded_count} neue Prompts geladen")
    click.echo(f"   • {skipped_count} übersprungen (bereits vorhanden)")
    click.echo(f"   • {Prompt.query.count()} Prompts gesamt in Datenbank")
    click.echo("=" * 70)
    click.echo()
    click.echo("🎯 Nächste Schritte:")
    click.echo("   1. Prompts unter /prompts verwalten")
    click.echo("   2. Bei KI-Analyse einen Prompt auswählen")
    click.echo()


def register_command(app):
    """Registriert den Command in der Flask-App."""
    app.cli.add_command(load_default_prompts)
