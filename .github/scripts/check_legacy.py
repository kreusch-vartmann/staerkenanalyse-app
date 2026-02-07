#!/usr/bin/env python3
"""
Legacy Cleanup Script
Prüft ob database.py und schema.sql noch verwendet werden und bietet Cleanup an
"""

import os
import sys
from pathlib import Path


def check_database_py_usage():
    """Prüft ob database.py noch irgendwo importiert wird"""
    project_root = Path(__file__).parent
    python_files = list(project_root.rglob("*.py"))

    usage_found = False
    print("🔍 Prüfe database.py Usage...")

    for py_file in python_files:
        if py_file.name == "database.py" or py_file.name == "check_legacy.py":
            continue
        if (
            "venv" in str(py_file)
            or "__pycache__" in str(py_file)
            or ".github" in str(py_file)
        ):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            if "from database import" in content or "import database" in content:
                print(f"⚠️  GEFUNDEN: {py_file} importiert database.py")
                usage_found = True
        except Exception as e:
            print(f"Fehler beim Lesen von {py_file}: {e}")

    if not usage_found:
        print("✅ database.py wird NICHT mehr verwendet!")

    return usage_found


def check_schema_sql():
    """Prüft schema.sql und zeigt Diskrepanzen zu models.py"""
    print("\n🔍 Analysiere schema.sql vs. models.py...")

    schema_file = Path(__file__).parent / "schema.sql"
    models_file = Path(__file__).parent / "models.py"

    if not schema_file.exists():
        print("⚠️  schema.sql nicht gefunden")
        return

    # Lese schema.sql
    with open(schema_file, "r") as f:
        schema_content = f.read()

    # Lese models.py
    with open(models_file, "r") as f:
        models_content = f.read()

    print("\n📊 Vergleich:")

    # Prüfe groups-Tabelle
    if (
        "leitung TEXT" in schema_content
        and "leitung_fremdeinschatzung" in models_content
    ):
        print(
            "❌ DISKREPANZ: schema.sql hat 'leitung', models.py hat 'leitung_fremdeinschatzung' + 'leitung_selbsteinschatzung'"
        )
        print("   → schema.sql ist VERALTET")

    # Prüfe ob schema.sql noch für Initialisierung verwendet wird
    app_file = Path(__file__).parent / "app.py"
    with open(app_file, "r") as f:
        app_content = f.read()

    if "schema.sql" not in app_content:
        print("✅ schema.sql wird NICHT in app.py verwendet")
        print("   → Flask-Migrate (Alembic) ist das neue Migrations-System")


def main():
    print("=" * 60)
    print("LEGACY CODE CLEANUP ANALYSIS")
    print("=" * 60)

    # Prüfe database.py
    database_used = check_database_py_usage()

    # Prüfe schema.sql
    check_schema_sql()

    print("\n" + "=" * 60)
    print("EMPFEHLUNG")
    print("=" * 60)

    if not database_used:
        print("\n✅ database.py kann SICHER gelöscht werden:")
        print("   rm database.py")
    else:
        print("\n⚠️  database.py wird noch verwendet - Migration erforderlich")

    print("\n✅ schema.sql kann GELÖSCHT oder AKTUALISIERT werden:")
    print("   Option 1 (Löschen): rm schema.sql")
    print("   Option 2 (Aktualisieren): Verwende 'flask db migrate' für Schema-Updates")
    print("   → Das Projekt nutzt Flask-Migrate (Alembic), schema.sql ist obsolet")

    print("\n📝 Nächste Schritte:")
    print("   1. Bestätige dass keine Tests auf schema.sql angewiesen sind")
    print("   2. Lösche database.py und schema.sql")
    print("   3. Committe die Änderungen")


if __name__ == "__main__":
    main()
