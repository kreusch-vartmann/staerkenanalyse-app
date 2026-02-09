#!/usr/bin/env python3
"""
Automatisches Backup-System für die Stärkenanalyse-App Datenbank.

Erstellt Backups der SQLite-Datenbank in einen sicheren Backup-Ordner.
Kann manuell, als Flask-CLI-Command oder automatisch beim App-Start ausgeführt werden.

Usage:
    # Manuell:
    python backup_database.py

    # Als Flask-Command:
    flask backup-db
    flask backup-db --keep 30    # Nur letzte 30 Backups behalten

    # Prompts exportieren (als zusätzliche Sicherung):
    flask export-prompts
"""

import os
import shutil
import json
from datetime import datetime, timezone
from pathlib import Path

import click
from flask.cli import with_appcontext

from extensions import db
from models import Prompt


# --- KONFIGURATION ---
BACKUP_DIR = Path(__file__).parent / "backups"
PROMPT_EXPORT_DIR = BACKUP_DIR / "prompts_export"
MAX_BACKUPS = 50  # Maximale Anzahl aufbewahrter Backups


def get_db_path():
    """Ermittelt den aktuellen Datenbankpfad."""
    instance_dir = Path(__file__).parent / "instance"
    return instance_dir / "database.db"


def create_backup(reason="manual"):
    """
    Erstellt ein Backup der Datenbank.
    
    Args:
        reason: Grund für das Backup (z.B. 'startup', 'manual', 'before_migration')
    
    Returns:
        Path zum erstellten Backup oder None bei Fehler.
    """
    db_path = get_db_path()
    
    if not db_path.exists():
        print(f"⚠️  Datenbank nicht gefunden: {db_path}")
        return None
    
    if db_path.stat().st_size == 0:
        print(f"⚠️  Datenbank ist leer (0 bytes): {db_path}")
        return None
    
    # Backup-Verzeichnis erstellen
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Backup-Dateiname mit Zeitstempel und Grund
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"database_{timestamp}_{reason}.db"
    backup_path = BACKUP_DIR / backup_name
    
    # Kopie erstellen
    shutil.copy2(str(db_path), str(backup_path))
    
    # Verifizierung: Größe vergleichen
    if backup_path.stat().st_size != db_path.stat().st_size:
        print(f"❌ FEHLER: Backup-Größe stimmt nicht überein!")
        return None
    
    size_kb = backup_path.stat().st_size / 1024
    print(f"✅ Backup erstellt: {backup_name} ({size_kb:.1f} KB)")
    
    return backup_path


def cleanup_old_backups(keep=MAX_BACKUPS):
    """Löscht alte Backups, behält die neuesten 'keep' Stück."""
    if not BACKUP_DIR.exists():
        return
    
    backups = sorted(
        BACKUP_DIR.glob("database_*.db"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    
    if len(backups) <= keep:
        return
    
    for old_backup in backups[keep:]:
        old_backup.unlink()
        print(f"🗑️  Altes Backup gelöscht: {old_backup.name}")


def export_prompts_to_files():
    """
    Exportiert alle Prompts als einzelne Textdateien UND als JSON.
    Dies ist eine zusätzliche Sicherung, unabhängig von der Datenbank.
    """
    PROMPT_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_subdir = PROMPT_EXPORT_DIR / f"export_{timestamp}"
    export_subdir.mkdir(parents=True, exist_ok=True)
    
    prompts = Prompt.query.order_by(Prompt.name).all()
    
    if not prompts:
        print("⚠️  Keine Prompts in der Datenbank gefunden.")
        return None
    
    # JSON-Export (komplett mit allen Metadaten)
    prompts_data = []
    for p in prompts:
        prompt_dict = {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "content": p.content,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        prompts_data.append(prompt_dict)
        
        # Einzelne Textdatei pro Prompt
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in p.name)
        txt_path = export_subdir / f"{safe_name}.txt"
        txt_path.write_text(p.content, encoding="utf-8")
    
    # Gesamt-JSON
    json_path = export_subdir / "alle_prompts.json"
    json_path.write_text(
        json.dumps(prompts_data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    print(f"✅ {len(prompts)} Prompts exportiert nach: {export_subdir}")
    print(f"   📄 JSON: {json_path.name}")
    for p in prompts:
        print(f"   📝 {p.name}")
    
    return export_subdir


def startup_backup():
    """
    Wird beim App-Start ausgeführt. Erstellt ein Backup,
    aber nur wenn sich die DB seit dem letzten Backup geändert hat.
    """
    db_path = get_db_path()
    if not db_path.exists() or db_path.stat().st_size == 0:
        return
    
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Prüfe ob sich die DB seit dem letzten Backup geändert hat
    existing_backups = sorted(
        BACKUP_DIR.glob("database_*.db"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    
    if existing_backups:
        latest_backup = existing_backups[0]
        # Nur wenn Größe unterschiedlich oder DB neuer als letztes Backup
        if (latest_backup.stat().st_size == db_path.stat().st_size and 
            latest_backup.stat().st_mtime >= db_path.stat().st_mtime):
            return  # Kein Backup nötig
    
    backup_path = create_backup(reason="startup")
    if backup_path:
        cleanup_old_backups()


# --- FLASK CLI COMMANDS ---

@click.command("backup-db")
@click.option("--keep", default=MAX_BACKUPS, help=f"Anzahl aufzubewahrender Backups (Standard: {MAX_BACKUPS})")
@with_appcontext
def backup_db_command(keep):
    """Erstellt ein manuelles Backup der Datenbank."""
    click.echo("=" * 60)
    click.echo("💾 Datenbank-Backup")
    click.echo("=" * 60)
    
    backup_path = create_backup(reason="manual")
    if backup_path:
        cleanup_old_backups(keep=keep)
        
        # Zeige alle Backups
        backups = sorted(BACKUP_DIR.glob("database_*.db"), key=lambda f: f.stat().st_mtime, reverse=True)
        click.echo(f"\n📂 Backup-Ordner: {BACKUP_DIR}")
        click.echo(f"📊 Anzahl Backups: {len(backups)}")
        for b in backups[:5]:
            size = b.stat().st_size / 1024
            click.echo(f"   • {b.name} ({size:.1f} KB)")
        if len(backups) > 5:
            click.echo(f"   ... und {len(backups) - 5} weitere")


@click.command("export-prompts")
@with_appcontext
def export_prompts_command():
    """Exportiert alle Prompts als Textdateien und JSON (zusätzliche Sicherung)."""
    click.echo("=" * 60)
    click.echo("📝 Prompt-Export")
    click.echo("=" * 60)
    
    export_prompts_to_files()


@click.command("restore-db")
@click.argument("backup_file", required=False)
@with_appcontext
def restore_db_command(backup_file):
    """Stellt die Datenbank aus einem Backup wieder her."""
    click.echo("=" * 60)
    click.echo("♻️  Datenbank-Wiederherstellung")
    click.echo("=" * 60)
    
    if not BACKUP_DIR.exists():
        click.echo("❌ Kein Backup-Ordner gefunden!")
        return
    
    backups = sorted(BACKUP_DIR.glob("database_*.db"), key=lambda f: f.stat().st_mtime, reverse=True)
    
    if not backups:
        click.echo("❌ Keine Backups gefunden!")
        return
    
    if backup_file:
        backup_path = BACKUP_DIR / backup_file
        if not backup_path.exists():
            click.echo(f"❌ Backup nicht gefunden: {backup_file}")
            return
    else:
        # Zeige verfügbare Backups
        click.echo("\nVerfügbare Backups:")
        for i, b in enumerate(backups):
            size = b.stat().st_size / 1024
            mtime = datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            click.echo(f"  [{i+1}] {b.name} ({size:.1f} KB, {mtime})")
        
        choice = click.prompt("Welches Backup wiederherstellen? (Nummer)", type=int)
        if choice < 1 or choice > len(backups):
            click.echo("❌ Ungültige Auswahl!")
            return
        backup_path = backups[choice - 1]
    
    db_path = get_db_path()
    
    # Sicherheitsbackup der aktuellen DB vor dem Restore
    if db_path.exists() and db_path.stat().st_size > 0:
        create_backup(reason="before_restore")
    
    # Restore durchführen
    if click.confirm(f"\n⚠️  {backup_path.name} → instance/database.db\nAktuelle DB wird überschrieben! Fortfahren?"):
        shutil.copy2(str(backup_path), str(db_path))
        click.echo(f"✅ Datenbank wiederhergestellt aus: {backup_path.name}")
    else:
        click.echo("❌ Abgebrochen.")


def register_backup_commands(app):
    """Registriert alle Backup-CLI-Commands bei der Flask-App."""
    app.cli.add_command(backup_db_command)
    app.cli.add_command(export_prompts_command)
    app.cli.add_command(restore_db_command)


# --- STANDALONE AUSFÜHRUNG ---
if __name__ == "__main__":
    print("=" * 60)
    print("💾 Manuelles Datenbank-Backup")
    print("=" * 60)
    create_backup(reason="manual_standalone")
    cleanup_old_backups()
