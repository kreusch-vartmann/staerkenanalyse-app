# version.py
"""Zentrale Versions-Verwaltung für die Stärkenanalyse-App."""

# App-Version (Semantic Versioning: MAJOR.MINOR.PATCH)
# PRE-RELEASE (0.x.y): Noch nicht produktiv im Einsatz
# - 0.MINOR.PATCH: Breaking Changes erlaubt zwischen Minor-Versionen
# - 1.0.0: Erster stabiler Release
#
# Versionshistorie:
# - 0.1.0 (2026-02-07): Initial Release mit Export/Import-Funktion
# - 0.2.0-WIP (2026-02-07): Report-System mit PDF-Generierung (Work in Progress)
APP_VERSION = "0.2.0-WIP"

# Export-Schema-Version (unabhängig von App-Version)
# Ändert sich nur bei Änderungen der CSV/Excel-Export-Struktur
# Format: "MAJOR.MINOR"
# - MAJOR: Inkompatible Änderungen (Spalten entfernt/umbenannt)
# - MINOR: Kompatible Erweiterungen (neue Spalten hinzugefügt)
#
# Schema-Historie:
# - 1.0 (2026-02-07): Initiales Schema mit 27 Spalten
EXPORT_SCHEMA_VERSION = "1.0"

# Datenbank-Migrations-Version (automatisch durch Alembic verwaltet)
# Siehe migrations/versions/ für Details
# Aktuelle Heads (Stand Feb 2026):
# - ffbd6aad0758 (Initial migration)
# - b4c7ad2a2bbc (Group date_from/date_to)
# - 37910f5c8ff0 (ExplanationBlock model)

def get_version_info():
    """Gibt Version-Infos als Dictionary zurück."""
    return {
        "app_version": APP_VERSION,
        "export_schema_version": EXPORT_SCHEMA_VERSION,
    }

def get_version_string():
    """Gibt formatierte Version für UI zurück."""
    return f"v{APP_VERSION}"
