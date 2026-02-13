#!/usr/bin/env python3
"""
Migration Script: SQLite → PostgreSQL
======================================

Migriert alle Daten von der lokalen SQLite-Datenbank zu einer ProductionPostgreSQL-Datenbank.

Verwendung:
  python migrate_sqlite_to_postgresql.py <target_postgresql_url>

Beispiel:
  python migrate_sqlite_to_postgresql.py postgresql://user:pass@localhost/dbname
  python migrate_sqlite_to_postgresql.py postgresql://staerkenanalyse_user:password@db:5432/staerkenanalyse_db
"""

import os
import sys
import json
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# SQLite source
SQLITE_DB = "sqlite:///instance/database.db"

def confirm_action(message):
    """Ask user for confirmation."""
    response = input(f"\n⚠️  {message} (y/n) ").strip().lower()
    return response == 'y'

def get_all_tables(engine):
    """Get list of all tables in database."""
    inspector = inspect(engine)
    return inspector.get_table_names()

def copy_table_data(source_engine, target_engine, table_name):
    """Copy data from one table to another."""
    # Read from source
    with source_engine.connect() as source_conn:
        result = source_conn.execute(text(f"SELECT * FROM {table_name}"))
        rows = result.fetchall()
        columns = [col[0] for col in result.keys()]
    
    if not rows:
        print(f"  ℹ️  {table_name}: Keine Daten")
        return 0
    
    # Write to target
    with target_engine.begin() as target_conn:
        # Insert data
        insert_sql = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({', '.join([':' + col for col in columns])})
        """
        
        for row in rows:
            row_dict = {}
            for i, col in enumerate(columns):
                row_dict[col] = row[i]
            
            try:
                target_conn.execute(text(insert_sql), row_dict)
            except Exception as e:
                print(f"    ❌ Error inserting row: {e}")
                return 0
    
    print(f"  ✅ {table_name}: {len(rows)} Zeilen kopiert")
    return len(rows)

def migrate_database(postgresql_url):
    """Main migration function."""
    
    print("=" * 80)
    print("SQLite → PostgreSQL Migration Tool")
    print("=" * 80)
    
    # Check SQLite exists
    if not os.path.exists("instance/database.db"):
        print("\n❌ SQLite database nicht gefunden: instance/database.db")
        sys.exit(1)
    
    print("\n📊 MIGRATION PLAN:")
    print(f"  Source: {SQLITE_DB}")
    print(f"  Target: {postgresql_url}")
    
    if not confirm_action("Möchtest du wirklich fortfahren?"):
        print("Migration abgebrochen.")
        sys.exit(0)
    
    # Connect to databases
    print("\n🔌 Verbinde zu Datenbanken...")
    try:
        sqlite_engine = create_engine(SQLITE_DB, echo=False)
        pg_engine = create_engine(postgresql_url, echo=False)
        
        # Test connections
        with sqlite_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        print("  ✅ SQLite verbunden")
        print("  ✅ PostgreSQL verbunden")
    except Exception as e:
        print(f"\n❌ Verbindungsfehler: {e}")
        sys.exit(1)
    
    # Get table list
    print("\n📋 Tabellen-Inventar:")
    try:
        sqlite_tables = get_all_tables(sqlite_engine)
        pg_tables = get_all_tables(pg_engine)
        
        print(f"  SQLite: {len(sqlite_tables)} Tabellen")
        print(f"  PostgreSQL: {len(pg_tables)} Tabellen")
        
        # Check compatibility
        missing_tables = set(sqlite_tables) - set(pg_tables)
        if missing_tables:
            print(f"\n  ⚠️  Fehlende Tabellen in PostgreSQL: {missing_tables}")
            print("  → PostgreSQL-Migrationen müssen zuerst ausgeführt werden!")
            sys.exit(1)
        
        extra_tables = set(pg_tables) - set(sqlite_tables)
        if extra_tables:
            print(f"  ℹ️  Zusätzliche Tabellen in PostgreSQL (werden ignoriert): {extra_tables}")
    
    except Exception as e:
        print(f"\n❌ Fehler beim Laden der Tabellen: {e}")
        sys.exit(1)
    
    if not confirm_action("Mit Datenkopie weitermachen?"):
        print("Migration abgebrochen.")
        sys.exit(0)
    
    # Copy data
    print("\n📤 Kopiere Daten...\n")
    total_rows = 0
    
    # Disable foreign key constraints during copy (if needed)
    try:
        with pg_engine.connect() as conn:
            conn.execute(text("SET session_replication_role = 'replica'"))
            conn.commit()
    except:
        pass  # Not critical
    
    for table in sqlite_tables:
        try:
            rows = copy_table_data(sqlite_engine, pg_engine, table)
            total_rows += rows
        except Exception as e:
            print(f"  ❌ {table}: {e}")
    
    # Re-enable constraints
    try:
        with pg_engine.connect() as conn:
            conn.execute(text("SET session_replication_role = 'origin'"))
            conn.commit()
    except:
        pass
    
    print(f"\n✅ MIGRATION COMPLETE!")
    print(f"   Total Zeilen kopiert: {total_rows}")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    
    # Verification
    print("\n🔍 Verifizierung:")
    for table in sqlite_tables:
        with sqlite_engine.connect() as sqlite_conn:
            sqlite_count = sqlite_conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        
        with pg_engine.connect() as pg_conn:
            pg_count = pg_conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        
        status = "✅" if sqlite_count == pg_count else "❌"
        print(f"   {status} {table}: SQLite={sqlite_count}, PostgreSQL={pg_count}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        print("\n❌ Fehler: PostgreSQL URL erforderlich")
        print("\nBeispiel:")
        print("  python migrate_sqlite_to_postgresql.py postgresql://user:pass@localhost/dbname")
        sys.exit(1)
    
    postgresql_url = sys.argv[1]
    migrate_database(postgresql_url)
