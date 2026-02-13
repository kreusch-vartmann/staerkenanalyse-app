# Database Auto-Recovery System

## 🎯 Zweck

Schützt die Produktions-Datenbank vor Korruption durch automatische Validierung und Wiederherstellung beim App-Start.

## 🔍 Problem

Die Datenbank kann durch verschiedene Ursachen korrupt werden:
1. **Fehlgeschlagene Migrations:** `flask db upgrade` auf einer nicht-migrierten DB
2. **Test-Runs:** Tests die versehentlich die Produktions-DB modifizieren
3. **Manuelle SQL-Befehle:** Direkte Änderungen die die DB-Struktur beschädigen
4. **Crashes während Writes:** App-Absturz während DB-Schreiboperation

**Symptom:** `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such table: users`

## ✅ Lösung

### Automatischer Startup-Check

Das Modul `database_validator.py` wird **vor allen anderen Imports** in `app.py` geladen und prüft:

1. ✅ **Existenz:** Ist die `instance/database.db` vorhanden?
2. ✅ **Integrität:** Enthält die DB alle erforderlichen Haupt-Tabellen?
3. ✅ **Korruptionserkennung:** Nur `alembic_version` Tabelle = kaputte Migration

Wenn die DB korrupt ist:
- 🔄 Neuestes valides Backup wird automatisch wiederhergestellt
- 💾 Korrupte DB wird als `database_BROKEN_TIMESTAMP.db` gesichert
- ✅ Wiederhergestellte DB wird validiert

### Integration

```python
# app.py (Zeilen 1-13)
from dotenv import load_dotenv
load_dotenv()

# === CRITICAL: Database Validation BEFORE any DB imports ===
import database_validator  # noqa: F401

# Erst danach kommen normale Imports
import os
from flask import Flask
# ...
```

## 📋 Erwartete Tabellen

Das System prüft auf folgende kritische Tabellen:

```python
REQUIRED_TABLES = {
    'users', 'roles', 'permissions', 'role_permissions',
    'groups', 'participants', 'tasks', 'prompts',
    'explanation_blocks', 'report_templates', 'report_configurations'
}
```

**Hinweis:** Diese Liste muss aktualisiert werden, wenn neue Haupt-Models hinzugefügt werden!

## 🧪 Manuelle Validierung

```bash
# Test der DB-Integrität
python database_validator.py

# Erwartete Ausgabe bei valider DB:
# ======================================================================
# 🔍 DATABASE INTEGRITY CHECK
# ======================================================================
# ✅ Database is valid
# ======================================================================

# Erwartete Ausgabe bei korrupter DB:
# ❌ Missing tables: users, roles
# 🔄 Attempting automatic recovery...
# ✅ Database restored from backup: database_20260213_154544_startup.db
# ✅ DATABASE RECOVERY SUCCESSFUL
```

## 🔧 Backup-Strategie

### Automatische Backups

Die App erstellt automatisch Backups:
- **Beim Startup:** `backup_database.py` → `backups/database_TIMESTAMP_startup.db`
- **Vor Migrations:** Manuelle Backups empfohlen (siehe unten)

### Manuelle Backups

```bash
# Vor wichtigen Änderungen
flask backup-db

# Backups auflisten
ls -lh backups/*.db

# Altes Backup wiederherstellen
cp backups/database_20260213_154544_startup.db instance/database.db
flask db stamp head  # Alembic synchronisieren!
```

## 🛡️ Best Practices

### Bei Migrations

```bash
# 1. IMMER Backup vor Migration erstellen
flask backup-db

# 2. Migration erstellen
flask db migrate -m "beschreibung"

# 3. Migration prüfen (WICHTIG!)
cat migrations/versions/LATEST_FILE.py

# 4. Migration anwenden
flask db upgrade

# 5. App testen
flask run
```

### Bei Test-Entwicklung

```bash
# Tests immer mit dem Safe-Wrapper ausführen
./run_tests.sh

# NIEMALS direkt pytest ausführen ohne Isolation-Check!
# BAD:  pytest tests/
# GOOD: ./run_tests.sh
```

### Bei DB-Problemen

```bash
# 1. Prüfe Status
python database_validator.py

# 2. Wenn korrupt: Automatische Recovery lässt die App laufen
#    Korrupte DB wurde gesichert als database_BROKEN_TIMESTAMP.db

# 3. Optional: Manuelles Rollback auf spezifisches Backup
ls -lht backups/*.db  # Neueste Backups
cp backups/GEWÜNSCHTES_BACKUP.db instance/database.db
flask db stamp head   # Alembic synchronisieren
```

## 🚨 Fehlerbehebung

### Problem: App startet nicht trotz Recovery

**Ursache:** Backup ist veraltet oder ebenfalls korrupt

**Lösung:**
```bash
# Prüfe alle Backups
for f in backups/*.db; do
    echo "Checking $f..."
    sqlite3 "$f" "SELECT COUNT(*) FROM users;" 2>&1 | head -1
done

# Finde valides Backup, stelle manuell wieder her
cp backups/VALIDES_BACKUP.db instance/database.db
flask db stamp head
```

### Problem: "no such table: alembic_version"

**Ursache:** DB wurde mit `db.create_all()` erstellt, nicht durch Migrations

**Lösung:**
```bash
# Synchronisiere Alembic mit existierender DB
flask db stamp head

# Dies markiert die DB als "auf aktueller Migration" ohne Änderungen
```

### Problem: Migration schlägt fehl

**Ursache:** Migration erwartet Tabellen/Spalten die nicht existieren

**Lösung:**
```bash
# 1. Backup wiederherstellen
cp backups/PRE_MIGRATION_BACKUP.db instance/database.db

# 2. DB-Schema mit Models vergleichen
flask shell
>>> from extensions import db
>>> from sqlalchemy import inspect
>>> inspector = inspect(db.engine)
>>> inspector.get_table_names()

# 3. Migration anpassen oder neu erstellen
flask db migrate -m "neue_migration"
```

## 📊 Monitoring

### Startup-Logs überwachen

```python
# Bei jedem App-Start in Logs sichtbar:
======================================================================
🔍 DATABASE INTEGRITY CHECK
======================================================================
✅ Database is valid
======================================================================

# Bei Problemen:
❌ Missing tables: users
🔄 Attempting automatic recovery...
✅ Database restored from backup: database_20260213_154544_startup.db
✅ DATABASE RECOVERY SUCCESSFUL
```

### Backup-Health-Check

```bash
# Prüfe ob Backups aktuell sind
ls -lht backups/*.db | head -5

# Backup-Größe überwachen (sollte > 100KB sein für Produktions-DB)
du -h backups/*.db | tail -5
```

## 🎓 Architektur

```
┌─────────────────────────────────────────────────────────────┐
│ 1. App-Start (python app.py oder flask run)                │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. load_dotenv() - Lade Umgebungsvariablen                 │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. import database_validator - AUTOMATISCHER CHECK         │
│    ├─ check_database_integrity()                           │
│    │   ├─ Prüfe Tabellen-Existenz                          │
│    │   └─ Erkenne Migration-Corruption                     │
│    └─ restore_database_from_backup() [bei Fehler]          │
│        ├─ Sichere korrupte DB                              │
│        ├─ Kopiere neuestes valides Backup                  │
│        └─ Validiere Wiederherstellung                      │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Normale Flask-Initialisierung                           │
│    ├─ db.init_app(app)                                     │
│    ├─ migrate.init_app(app, db)                            │
│    └─ Blueprint-Registrierung                              │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. @app.before_request: startup_backup()                   │
│    └─ Erstelle Backup bei erstem Request                   │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. App läuft mit validierter, intakter Datenbank           │
└─────────────────────────────────────────────────────────────┘
```

## 🔗 Verwandte Systeme

- **Test-Isolation:** [`TEST_DATABASE_ISOLATION_SAFETY.md`](TEST_DATABASE_ISOLATION_SAFETY.md)
- **Backup-System:** [`backup_database.py`](backup_database.py)
- **Migrations:** [`migrations/versions/`](migrations/versions/)

## ✨ Zusammenfassung

Das Database Auto-Recovery System bietet:

✅ **Automatische Validierung** bei jedem App-Start  
✅ **Zero-Downtime Recovery** aus neuesten Backups  
✅ **Korrupte-DB-Archivierung** für Forensik  
✅ **Manuelle Validierung** für Debugging  
✅ **Integration** mit bestehendem Backup-System  

**Ergebnis:** Die App ist vor Datenbank-Korruption geschützt und kann sich selbst heilen! 🎉
