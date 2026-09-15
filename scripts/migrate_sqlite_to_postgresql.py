#!/usr/bin/env -S .venv/bin/python3
"""
Migration von SQLite zu PostgreSQL mit:
- Topologischer Tabellenreihenfolge (Foreign Keys)
- Sequence-Resets für Auto-Increment-Spalten
- Identifier-Quoting für PostgreSQL-Keywords
- Fail-Fast bei Fehlern
- Umgebungsvariablen aus .env
"""

import os
import sys
import json
from dotenv import load_dotenv
import sqlite3
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

# Lade .env
load_dotenv()

# Konfiguration
SQLITE_DB = os.getenv("SQLITE_DATABASE_URL", "sqlite:///instance/database.db").replace("sqlite:///", "")
POSTGRES_DB = os.getenv("DATABASE_URL", "postgresql://stark:stark@localhost:5432/stark")

# Topologische Tabellenreihenfolge (Foreign Keys beachten)
TABLE_ORDER = [
    "roles", "permissions", "role_permissions",  # RBAC
    "users", "groups", "user_groups",           # Benutzer/Gruppen
    "prompts", "report_templates",              # Vorlagen
    "company_logos", "client_logos",            # Logos
    "tasks", "task_versions",                   # Aufgaben
    "group_tasks",                              # Gruppen-Aufgaben-Zuordnung
    "participants", "self_assessments",         # Teilnehmer
    "explanation_blocks",                       # Erklärungsblöcke
    "report_configurations",                    # Report-Konfigurationen
    "signature_images",                         # Unterschriften
    "activity_log", "ai_raw_responses",         # Logs
    "content_edits"                             # Inhaltsänderungen
]

# PostgreSQL-Keywords, die gequotet werden müssen
PG_KEYWORDS = {"order", "type"}

def get_sqlite_connection():
    """SQLite-Verbindung herstellen."""
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_postgres_connection():
    """PostgreSQL-Verbindung herstellen."""
    return psycopg2.connect(POSTGRES_DB)

def reset_postgres_sequences(conn):
    """Setze PostgreSQL-Sequences auf den höchsten Wert + 1."""
    with conn.cursor() as cur:
        for table in TABLE_ORDER:
            # Prüfe, ob die Tabelle eine Auto-Increment-Spalte hat
            cur.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s AND column_default LIKE 'nextval%%'
            """, (table,))
            auto_inc_cols = [row[0] for row in cur.fetchall()]
            for col in auto_inc_cols:
                cur.execute(f"""
                    SELECT setval(
                        pg_get_serial_sequence(%s, %s),
                        COALESCE(MAX({col}), 1)
                    )
                    FROM {table}
                """, (table, col))

def migrate_table(sqlite_conn, pg_conn, table):
    """Migriere eine einzelne Tabelle von SQLite zu PostgreSQL."""
    with sqlite_conn.cursor() as sqlite_cur, pg_conn.cursor() as pg_cur:
        # Tabellenstruktur abrufen
        sqlite_cur.execute(f"PRAGMA table_info({table})")
        columns = [row["name"] for row in sqlite_cur.fetchall()]

        # Daten abrufen
        sqlite_cur.execute(f"SELECT * FROM {table}")
        rows = sqlite_cur.fetchall()

        if not rows:
            print(f"⏭️  {table}: Keine Daten zum Migrieren")
            return

        # Spalten für INSERT vorbereiten (Identifier-Quoting)
        quoted_columns = [
            sql.Identifier(col) if col.lower() in PG_KEYWORDS else sql.Identifier(col)
            for col in columns
        ]
        insert_query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
            sql.Identifier(table),
            sql.SQL(", ").join(quoted_columns)
        )

        # Daten konvertieren (SQLite → PostgreSQL)
        data = []
        for row in rows:
            row_data = []
            for col in columns:
                value = row[col]
                # JSON-Felder als Text belassen (PostgreSQL parst sie automatisch)
                if isinstance(value, str) and (value.startswith("{") or value.startswith("[")):
                    row_data.append(value)
                # SQLite-BLOB → PostgreSQL BYTEA
                elif isinstance(value, bytes):
                    row_data.append(value)
                # None → NULL
                elif value is None:
                    row_data.append(None)
                else:
                    row_data.append(value)
            data.append(row_data)

        # Daten einfügen
        execute_values(pg_cur, insert_query, data)
        print(f"✅ {table}: {len(rows)} Zeilen migriert")

def main():
    """Hauptfunktion: Migration durchführen."""
    print("🔄 Migration von SQLite zu PostgreSQL")
    print(f"   SQLite: {SQLITE_DB}")
    print(f"   PostgreSQL: {POSTGRES_DB}")

    # Verbindungen herstellen
    sqlite_conn = get_sqlite_connection()
    pg_conn = get_postgres_connection()

    try:
        # Tabellen migrieren (topologische Reihenfolge)
        for table in TABLE_ORDER:
            try:
                migrate_table(sqlite_conn, pg_conn, table)
            except Exception as e:
                print(f"❌ {table}: Fehler - {e}")
                raise

        # Sequences zurücksetzen
        reset_postgres_sequences(pg_conn)
        pg_conn.commit()
        print("🎉 Migration erfolgreich abgeschlossen!")

    except Exception as e:
        pg_conn.rollback()
        print(f"💥 Migration fehlgeschlagen: {e}")
        sys.exit(1)
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    main()