#!/usr/bin/env python3
"""
Database Management Tool - Synchronisiert SQLite und PostgreSQL Migrationen

Verwendung:
    python manage_db.py migrate "beschreibung"  # Neue Migration erstellen und auf beide DBs anwenden
    python manage_db.py upgrade                 # Auf neueste Version upgraden
    python manage_db.py downgrade              # Eine Version zurückgehen
    python manage_db.py current                # Aktuelle Versionen anzeigen
    python manage_db.py validate               # Beide DBs überprüfen
"""

import os
import sys
import subprocess
from pathlib import Path
import sqlite3
import psycopg2
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

# App Setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instance/database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# PostgreSQL Config
PG_CONFIG = {
    'host': os.environ.get('PG_HOST', 'localhost'),
    'database': os.environ.get('PG_DB', 'staerkenanalyse_db'),
    'user': os.environ.get('PG_USER', 'staerkenanalyse_user'),
    'password': os.environ.get('PG_PASSWORD', 'staerkenanalyse_secure_2026'),
}

class DatabaseManager:
    """Verwaltet SQLite und PostgreSQL Migrationen"""
    
    def __init__(self):
        self.alembic_config = Config('migrations/alembic.ini')
        self.script = ScriptDirectory.from_config(self.alembic_config)
    
    def get_current_version(self, db_url):
        """Hole aktuelle Alembic-Version aus Datenbank"""
        try:
            from sqlalchemy import create_engine
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                row = result.fetchone()
                if row:
                    return row[0]
                return None
        except Exception as e:
            return f"ERROR: {str(e)}"
    
    def migrate(self, message):
        """Erstelle neue Alembic-Migration"""
        print("\n" + "=" * 80)
        print(f"🔄 Erstelle Migration: {message}")
        print("=" * 80)
        
        with app.app_context():
            try:
                # Alembic Migration erstellen
                print(f"\n📝 Erstelle Alembic-Migration...")
                result = subprocess.run(
                    [sys.executable, '-m', 'flask', 'db', 'migrate', '-m', message],
                    capture_output=True,
                    text=True,
                    cwd=str(Path(__file__).parent)
                )
                
                if result.returncode != 0:
                    print(f"❌ Migration erstellen fehlgeschlagen:")
                    print(result.stderr)
                    return False
                
                print("✅ Migration erstellt")
                print(result.stdout)
                
                # Upgrade beide DBs
                print(f"\n🚀 Wende Migration an on beiden Datenbanken...")
                return self.upgrade()
                
            except Exception as e:
                print(f"❌ Fehler: {e}")
                return False
    
    def upgrade(self):
        """Upgrade beide Datenbanken auf newest version"""
        print("\n" + "=" * 80)
        print("🚀 Upgrade Datenbanken")
        print("=" * 80)
        
        with app.app_context():
            try:
                # SQLite upgrade
                print(f"\n1️⃣  SQLite upgraden...")
                result = subprocess.run(
                    [sys.executable, '-m', 'flask', 'db', 'upgrade'],
                    capture_output=True,
                    text=True,
                    cwd=str(Path(__file__).parent)
                )
                
                if result.returncode != 0:
                    print(f"❌ SQLite Upgrade fehlgeschlagen:")
                    print(result.stderr)
                    return False
                
                print("✅ SQLite aktualisiert")
                sqlite_version = self.get_current_version('sqlite:///instance/database.db')
                print(f"   Version: {sqlite_version}")
                
                # PostgreSQL upgrade direkt mit Alembic
                print(f"\n2️⃣  PostgreSQL upgraden...")
                pg_url = f"postgresql://{PG_CONFIG['user']}:{PG_CONFIG['password']}@{PG_CONFIG['host']}:5432/{PG_CONFIG['database']}"
                
                self.alembic_config.set_main_option('sqlalchemy.url', pg_url)
                
                from alembic.command import upgrade as alembic_upgrade
                
                try:
                    alembic_upgrade(self.alembic_config, 'head')
                    print("✅ PostgreSQL aktualisiert")
                    pg_version = self.get_current_version(pg_url)
                    print(f"   Version: {pg_version}")
                except Exception as e:
                    print(f"❌ PostgreSQL Upgrade fehlgeschlagen: {e}")
                    return False
                
                # Validate
                print(f"\n3️⃣  Validiere Synchronisierung...")
                return self.validate()
                
            except Exception as e:
                print(f"❌ Fehler: {e}")
                return False
    
    def downgrade(self):
        """Downgrade beide Datenbanken um eine Version"""
        print("\n" + "=" * 80)
        print("⬇️  Downgrade Datenbanken (eine Version zurück)")
        print("=" * 80)
        
        with app.app_context():
            try:
                # Get current version
                sqlite_version = self.get_current_version('sqlite:///instance/database.db')
                pg_url = f"postgresql://{PG_CONFIG['user']}:{PG_CONFIG['password']}@{PG_CONFIG['host']}:5432/{PG_CONFIG['database']}"
                pg_version = self.get_current_version(pg_url)
                
                print(f"\nAktuelle Versionen:")
                print(f"   SQLite:     {sqlite_version}")
                print(f"   PostgreSQL: {pg_version}")
                
                if sqlite_version != pg_version:
                    print(f"\n⚠️  Versionen stimmen nicht überein!")
                    return False
                
                # Find previous revision
                revisions = list(self.script.walk_revisions(rev='heads'))
                if len(revisions) < 2:
                    print(f"\n❌ Keine vorherige Version vorhanden")
                    return False
                
                previous_rev = revisions[1].revision
                
                print(f"\nDowngrade zu: {previous_rev}")
                
                # SQLite downgrade
                print(f"\n1️⃣  SQLite downgraden...")
                result = subprocess.run(
                    [sys.executable, '-m', 'flask', 'db', 'downgrade'],
                    capture_output=True,
                    text=True,
                    cwd=str(Path(__file__).parent)
                )
                
                if result.returncode != 0:
                    print(f"❌ SQLite Downgrade fehlgeschlagen")
                    return False
                
                print("✅ SQLite downgegradet")
                
                # PostgreSQL downgrade
                print(f"\n2️⃣  PostgreSQL downgraden...")
                self.alembic_config.set_main_option('sqlalchemy.url', pg_url)
                
                from alembic.command import downgrade as alembic_downgrade
                
                try:
                    alembic_downgrade(self.alembic_config, '-1')
                    print("✅ PostgreSQL downgegradet")
                except Exception as e:
                    print(f"❌ PostgreSQL Downgrade fehlgeschlagen: {e}")
                    return False
                
                return self.validate()
                
            except Exception as e:
                print(f"❌ Fehler: {e}")
                return False
    
    def current(self):
        """Zeige aktuelle Versionen beider Datenbanken"""
        print("\n" + "=" * 80)
        print("📊 Aktuelle Datenbank-Versionen")
        print("=" * 80)
        
        sqlite_version = self.get_current_version('sqlite:///instance/database.db')
        pg_url = f"postgresql://{PG_CONFIG['user']}:{PG_CONFIG['password']}@{PG_CONFIG['host']}:5432/{PG_CONFIG['database']}"
        pg_version = self.get_current_version(pg_url)
        
        print(f"\n📋 SQLite:")
        print(f"   Version: {sqlite_version}")
        
        print(f"\n📋 PostgreSQL:")
        print(f"   Version: {pg_version}")
        
        match = "✅ SYNCHRONIZED" if sqlite_version == pg_version else "⚠️  OUT OF SYNC"
        print(f"\n🔗 Status: {match}")
        
        return sqlite_version == pg_version
    
    def validate(self):
        """Validiere dass beide DBs identische Versionen haben"""
        print(f"\n🔍 Validiere Synchronisierung...")
        
        sqlite_version = self.get_current_version('sqlite:///instance/database.db')
        pg_url = f"postgresql://{PG_CONFIG['user']}:{PG_CONFIG['password']}@{PG_CONFIG['host']}:5432/{PG_CONFIG['database']}"
        pg_version = self.get_current_version(pg_url)
        
        if sqlite_version == pg_version:
            print(f"✅ Beide Datenbanken sind synchronisiert")
            print(f"   Version: {sqlite_version}")
            return True
        else:
            print(f"❌ Datenbanken sind NICHT synchronisiert!")
            print(f"   SQLite:     {sqlite_version}")
            print(f"   PostgreSQL: {pg_version}")
            return False

def main():
    manager = DatabaseManager()
    
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Help commands
    if command in ['-h', '--help', 'help']:
        print(__doc__)
        sys.exit(0)
    
    if command == 'migrate':
        if len(sys.argv) < 3:
            print("❌ Fehler: Migration message erforderlich")
            print("   Verwendung: python manage_db.py migrate \"beschreibung\"")
            sys.exit(1)
        
        message = ' '.join(sys.argv[2:])
        success = manager.migrate(message)
        
    elif command == 'upgrade':
        success = manager.upgrade()
        
    elif command == 'downgrade':
        success = manager.downgrade()
        
    elif command == 'current':
        success = manager.current()
        
    elif command == 'validate':
        success = manager.validate()
        
    else:
        print(f"❌ Unbekannter Befehl: {command}")
        print(__doc__)
        sys.exit(1)
    
    print("\n" + "=" * 80)
    if success:
        print("✅ ERFOLGREICH ABGESCHLOSSEN")
    else:
        print("❌ FEHLER - Siehe oben für Details")
    print("=" * 80 + "\n")
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
