#!/usr/bin/env python3
"""
Database Validation and Auto-Recovery System

Prüft beim App-Start ob die Datenbank intakt ist und stellt automatisch
das neueste Backup wieder her, falls die DB korrupt ist.

WICHTIG: Dieses Modul wird VOR allen anderen import-Anweisungen geladen!
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
import shutil


# Erwartete Haupt-Tabellen (ohne Alembic-Metadata)
# Basierend auf den aktuellen Models (Stand: 2026-02-13)
REQUIRED_TABLES = {
    'users', 'roles', 'permissions', 'role_permissions',
    'groups', 'participants', 'tasks', 'prompts',
    'explanation_blocks', 'report_templates', 'report_configurations'
}


def log(message: str):
    """Ausgabe mit Flush für sofortige Sichtbarkeit."""
    print(message, file=sys.stderr, flush=True)


def get_db_path():
    """Ermittelt den Produktions-Datenbankpfad."""
    instance_dir = Path(__file__).parent / "instance"
    return instance_dir / "database.db"


def get_backup_dir():
    """Ermittelt das Backup-Verzeichnis."""
    return Path(__file__).parent / "backups"


def check_database_integrity():
    """
    Überprüft ob die Datenbank alle erforderlichen Tabellen enthält.
    
    Returns:
        tuple: (is_valid: bool, missing_tables: set, message: str)
    """
    db_path = get_db_path()
    
    if not db_path.exists():
        return False, REQUIRED_TABLES, "❌ Database file does not exist"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Hole alle Tabellen
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        
        # Prüfe ob kritische Tabellen fehlen
        missing_tables = REQUIRED_TABLES - existing_tables
        
        if missing_tables:
            return False, missing_tables, f"❌ Missing tables: {', '.join(sorted(missing_tables))}"
        
        # Prüfe ob NUR alembic_version existiert (Zeichen für kaputte Migration)
        if len(existing_tables) == 1 and 'alembic_version' in existing_tables:
            return False, REQUIRED_TABLES, "❌ Database only contains alembic_version (migration corruption)"
        
        return True, set(), "✅ Database is valid"
    
    except sqlite3.Error as e:
        return False, REQUIRED_TABLES, f"❌ Database error: {e}"


def find_latest_backup():
    """
    Findet das neueste Backup im Backup-Verzeichnis.
    
    Returns:
        Path | None: Pfad zum neuesten Backup oder None
    """
    backup_dir = get_backup_dir()
    
    if not backup_dir.exists():
        return None
    
    # Finde alle Backup-Dateien (sortiert nach Änderungszeit, neueste zuerst)
    backups = sorted(
        backup_dir.glob("database_*.db"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    if not backups:
        return None
    
    # Prüfe das neueste Backup auf Integrität
    for backup_path in backups:
        if validate_backup(backup_path):
            return backup_path
    
    return None


def validate_backup(backup_path: Path) -> bool:
    """
    Prüft ob ein Backup-File valide ist (enthält users-Tabelle).
    
    Args:
        backup_path: Pfad zur Backup-Datei
        
    Returns:
        bool: True wenn Backup valide ist
    """
    try:
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        result = cursor.fetchone()
        conn.close()
        return result is not None
    except sqlite3.Error:
        return False


def restore_database_from_backup():
    """
    Stellt die Datenbank aus dem neuesten validen Backup wieder her.
    
    Returns:
        bool: True wenn erfolgreich wiederhergestellt
    """
    db_path = get_db_path()
    backup_path = find_latest_backup()
    
    if not backup_path:
        log("❌ FATAL: No valid backup found! Cannot restore database.")
        return False
    
    try:
        # Erstelle Sicherungskopie der korrupten DB
        if db_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            broken_path = db_path.parent / f"database_BROKEN_{timestamp}.db"
            shutil.copy2(db_path, broken_path)
            log(f"💾 Corrupted database backed up to: {broken_path.name}")
        
        # Stelle Backup wieder her
        shutil.copy2(backup_path, db_path)
        log(f"✅ Database restored from backup: {backup_path.name}")
        
        # Validiere wiederhergestellte DB
        is_valid, _, message = check_database_integrity()
        if is_valid:
            log("✅ Restored database validated successfully")
            return True
        else:
            log(f"❌ Restored database is still invalid: {message}")
            return False
    
    except Exception as e:
        log(f"❌ Error restoring database: {e}")
        return False


def validate_and_recover():
    """
    Haupt-Funktion: Validiert DB und stellt bei Bedarf wieder her.
    
    WICHTIG: Diese Funktion wird beim App-Start automatisch ausgeführt!
    
    Returns:
        bool: True wenn DB valide ist (oder erfolgreich wiederhergestellt wurde)
    """
    log("\n" + "="*70)
    log("🔍 DATABASE INTEGRITY CHECK")
    log("="*70)
    
    is_valid, missing_tables, message = check_database_integrity()
    
    if is_valid:
        log(message)
        log("="*70 + "\n")
        return True
    
    # Database ist korrupt - versuche Wiederherstellung
    log(message)
    log(f"🔄 Attempting automatic recovery...")
    log("-"*70)
    
    success = restore_database_from_backup()
    
    if success:
        log("="*70)
        log("✅ DATABASE RECOVERY SUCCESSFUL")
        log("="*70 + "\n")
        return True
    else:
        log("="*70)
        log("❌ DATABASE RECOVERY FAILED")
        log("="*70 + "\n")
        return False


# === AUTOMATISCHER STARTUP CHECK ===
# Wird beim Import ausgeführt (vor Flask-App-Initialisierung)
if __name__ != "__main__":
    # Nur prüfen wenn nicht als Skript ausgeführt
    # NICHT prüfen wenn FLASK_ENV=testing (CI/Test-Umgebung)
    flask_env = os.environ.get('FLASK_ENV', '').lower()
    db_url = os.environ.get('DATABASE_URL', '')
    is_sqlite = 'sqlite' in db_url.lower() or not db_url
    is_not_test = 'test' not in db_url.lower()
    is_not_testing_env = flask_env != 'testing'

    if is_sqlite and is_not_test and is_not_testing_env:
        validate_and_recover()


if __name__ == "__main__":
    # Manueller Test mit print statt log
    print("Manual database validation test:")
    success = validate_and_recover()
    exit(0 if success else 1)
