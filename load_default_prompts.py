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
    "copilotsozverbv2.txt": {
        "name": "CopilotSozVerbv2",
        "description": "Optimierte Version mit verstärktem Polaritäts-Enforcement, Soft-Damping, "
                        "persönlicheren Texten und reiner Stärkenorientierung",
    },
    "reubelriemannv1.txt": {
        "name": "ReubelRiemannV1",
        "description": "Fachlich fundiert auf Basis der 13 LEB/Ferdinand-Reubel-Beobachtungsdimensionen "
                        "(BAKQER-Verfahren) auf die 8 Riemann-Kreuz-Dimensionen abgebildet. "
                        "Einheitliche, widerspruchsfreie Punkte-/Polaritäts-Logik (ersetzt die "
                        "sich überschneidenden Regeln von CopilotSozVerbv2), ausführlichere, "
                        "beobachtungsbasierte Texte, Halo-Effekt-Vermeidung bei VK.",
        "is_default": True,
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

            # Nur EIN Prompt darf is_default=True haben (siehe blueprints/prompts.py)
            if metadata.get("is_default"):
                Prompt.query.update({Prompt.is_default: False}, synchronize_session=False)

            # Erstelle Prompt
            new_prompt = Prompt(
                name=metadata["name"],
                description=metadata["description"],
                content=content,
                is_default=metadata.get("is_default", False),
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
    """Registriert die Commands in der Flask-App."""
    app.cli.add_command(load_default_prompts)
    app.cli.add_command(sync_prompt)


@click.command("sync-prompt")
@click.argument("filename")
@with_appcontext
def sync_prompt(filename):
    """Aktualisiert den Inhalt EINES konkret benannten Standard-Prompts.

    Hintergrund: `load-default-prompts` überspringt Prompts, die per Name
    bereits existieren, ABSICHTLICH (Schutz vor Überschreiben manueller
    Admin-UI-Bearbeitungen). Das führt aber dazu, dass Änderungen an einer
    Prompt-Datei im Repo (z.B. prompts/reubelriemannv1.txt) NICHT
    automatisch in eine bereits laufende Produktions-DB (z.B. Coolify +
    PostgreSQL) übernommen werden, selbst nach `git push` + Redeploy - der
    Docker-Entrypoint ruft weiterhin nur `load-default-prompts` auf, das
    den bestehenden Eintrag stillschweigend überspringt.

    Dieser Befehl aktualisiert GEZIELT nur den einen angegebenen,
    bekannten Standard-Prompt (Content + Description) - alle anderen
    Prompts (inkl. eventueller Admin-Anpassungen an ANDEREN Prompts)
    bleiben unberührt. Legt den Prompt neu an, falls er noch gar nicht
    existiert (z.B. bei einem frischen Deploy).

    Usage (z.B. via Coolify-Terminal/Exec in den laufenden Container):
        flask sync-prompt reubelriemannv1.txt
    """
    if filename not in PROMPT_FILES:
        click.echo(f"❌ '{filename}' ist kein bekannter Standard-Prompt.")
        click.echo(f"   Bekannte Dateien: {', '.join(PROMPT_FILES.keys())}")
        raise SystemExit(1)

    metadata = PROMPT_FILES[filename]
    filepath = Path(__file__).parent / "prompts" / filename
    if not filepath.exists():
        click.echo(f"❌ Datei nicht gefunden: {filepath}")
        raise SystemExit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    existing = Prompt.query.filter_by(name=metadata["name"]).first()
    if existing:
        if existing.content == content:
            click.echo(
                f"ℹ️  '{metadata['name']}' ist bereits aktuell "
                f"({len(existing.content)} Zeichen) - keine Änderung nötig."
            )
            return
        old_len = len(existing.content)
        existing.content = content
        existing.description = metadata["description"]
        db.session.commit()
        click.echo(
            f"✅ Aktualisiert: '{metadata['name']}' "
            f"({old_len} -> {len(content)} Zeichen)"
        )
    else:
        if metadata.get("is_default"):
            Prompt.query.update({Prompt.is_default: False}, synchronize_session=False)
        new_prompt = Prompt(
            name=metadata["name"],
            description=metadata["description"],
            content=content,
            is_default=metadata.get("is_default", False),
        )
        db.session.add(new_prompt)
        db.session.commit()
        click.echo(f"✅ Neu angelegt: '{metadata['name']}' ({len(content)} Zeichen)")
