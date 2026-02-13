# Development Workflow - Database Management

## Überblick

Dieses Dokument beschreibt den standardisierten Workflow zur Verwaltung von Datenbank-Migrationen zwischen SQLite (Entwicklung) und PostgreSQL (Test/Produktion).

**Kernidee:** Ein einzelner Befehl synchronisiert BEIDE Datenbanken automatisch.

---

## 🚀 Quick Start

### Neue Datenbank-Features hinzufügen

```bash
# 1. Model ändern (z.B. models.py)
# 2. Migration erstellen und beide DBs aktualisieren
python manage_db.py migrate "beschreibung der änderung"

# 3. Änderungen committen
git add .
git commit -m "feat: neue feature mit migration"
```

**Das war's!** Beide SQLite und PostgreSQL sind jetzt synchronisiert.

---

## 📋 Verfügbare Befehle

### Migration erstellen
```bash
python manage_db.py migrate "add_user_profile_table"
python manage_db.py migrate "add_is_active_column_to_users"
```

**Was passiert:**
1. ✅ Alembic-Migration wird automatisch generiert
2. ✅ SQLite wird aktualisiert
3. ✅ PostgreSQL wird aktualisiert
4. ✅ Beide werden validiert (müssen gleiche Version haben)

### Auf neueste Version upgraden
```bash
# Wenn du nur master pullst und Migrationen nachziehen willst
python manage_db.py upgrade
```

### Eine Version zurückgehen
```bash
python manage_db.py downgrade
```

**Achtung:** Downgrades können zu Datenverlust führen! Nur in Entwicklung verwenden.

### Aktuelle Versionen anzeigen
```bash
python manage_db.py current
```

**Ausgabe:**
```
================================================================================
📊 Aktuelle Datenbank-Versionen
================================================================================

📋 SQLite:
   Version: 20260213_003

📋 PostgreSQL:
   Version: 20260213_003

🔗 Status: ✅ SYNCHRONIZED
```

### Synchronisierung validieren
```bash
python manage_db.py validate
```

**Nutze das regelmäßig zur Überprüfung!**

---

## 🔄 Detaillierter Workflow

### Scenario 1: Neue Tabelle hinzufügen

```bash
# 1. Model definieren in models.py
class UserProfile(db.Model):
    __tablename__ = "user_profiles"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # ...

# 2. Migration erstellen und ausführen
python manage_db.py migrate "add_user_profiles_table"

# 3. Validieren
python manage_db.py current

# 4. Committen
git add migrations/ models.py
git commit -m "feat: add user profiles table"
```

### Scenario 2: Spalte zu existierender Tabelle hinzufügen

```bash
# 1. Model aktualisieren
class User(db.Model):
    # ... existing columns ...
    location = db.Column(db.String(100), nullable=True)  # Neu!

# 2. Migration
python manage_db.py migrate "add_location_to_users"

# 3. Fertig!
```

### Scenario 3: Team zieht neueste Changes

```bash
# Kolleg hat Migrationen gemerged → du pullst
git pull

# Deine lokalen DBs sind jetzt outdated
python manage_db.py current  # Zeigt OUT OF SYNC

# Upgrade auf neueste Version
python manage_db.py upgrade

# Validieren
python manage_db.py current  # Zeigt SYNCHRONIZED
```

---

## ⚠️ Häufige Fehler vermeiden

### ❌ FALSCH: SQLite manual ändern ohne Migration
```python
# NICHT TUN!
# SELECT * FROM users;  ← Änderung nur in einer DB

# STATTDESSEN:
python manage_db.py migrate "beschreibung"  # ← Beide DBs updated
```

### ❌ FALSCH: Model-Änderung commiten ohne Migration
```bash
# NICHT TUN!
git commit -m "Add new column"  # Ohne migrations/ änderungen

# STATTDESSEN:
python manage_db.py migrate "add new column"
git commit -m "Add new column"
```

### ❌ FALSCH: SQLAlchemy Models aus PostgreSQL importieren
```python
# NICHT:
from sqlalchemy import create_engine
engine = create_engine('postgresql://...')

# OK:
# Alembic verwaltet das!
python manage_db.py migrate "..."
```

---

## 🔍 Debugging

### „Out of Sync" Fehler

```bash
python manage_db.py current

# Output:
# SQLite:     20260213_002
# PostgreSQL: 20260213_003
# ❌ OUT OF SYNC
```

**Lösung:**
```bash
# Option 1: Upgrade SQLite
python manage_db.py upgrade

# Option 2: Downgrade PostgreSQL (bei Entwicklungs-Issue)
python manage_db.py downgrade
```

### Migration schlag fehl

```bash
python manage_db.py migrate "problematic feature"
# ❌ FEHLER: "column already exists"
```

**Debugging:**
1. Überprüfe models.py auf Fehler
2. Overprüfe die generierte Migration in `migrations/versions/`
3. Repariere die Migration-Datei manuell (selten nötig)
4. Retry: `python manage_db.py migrate "fixed"`

### PostgreSQL Connection Fehler

```bash
❌ Fehler: could not connect to postgres server
```

**Überprüfe:**
```bash
# 1. Ist Docker laufen?
docker ps | grep postgres

# 2. Ist die DB initialized?
docker logs staerkenanalyse_db

# 3. Credentials korrekt in .env?
cat .env | grep PG_
```

---

## 🛠️ Advanced: Manuelle Migration Repair

Falls ein Script-Fehler auftritt, kannst du Migrationen manuell reparieren:

### Manuelle SQLite Migration
```bash
# Einzelne sqlalchemy migration
flask db upgrade

# Oder direkt
sqlite3 instance/database.db < migrations/manual_fix.sql
```

### Manuelle PostgreSQL Migration
```bash
# Mit psql
psql -U staerkenanalyse_user -d staerkenanalyse_db < migrations/manual_fix.sql

# Oder Python
python << 'EOF'
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    database='staerkenanalyse_db',
    user='staerkenanalyse_user',
    password='staerkenanalyse_secure_2026'
)
cursor = conn.cursor()
cursor.execute("ALTER TABLE users ADD COLUMN test_column VARCHAR(50);")
conn.commit()
cursor.close()
EOF
```

---

## 📚 Best Practices

### ✅ Migration Messages

```bash
# ✅ GUT: Präzise, aussagekräftig
python manage_db.py migrate "add_email_verification_to_users"
python manage_db.py migrate "create_activities_log_table"
python manage_db.py migrate "add_unique_constraint_to_prompt_names"

# ❌ NICHT: Zu vage
python manage_db.py migrate "fix stuff"
python manage_db.py migrate "update"
```

### ✅ Häufig committen

```bash
# Nach jedem Datenbankänderung:
python manage_db.py migrate "..."
git add .
git commit -m "..." 

# Nicht mehrere Migrationen sammeln!
```

### ✅ Vor dem Push validieren

```bash
git status  # Nur migrate und models.py geändert?
python manage_db.py validate  # Beide DBs synchronized?
pytest tests/  # Tests bestanden?
git push
```

---

## 🚨 Production Notes

Dieser Workflow ist für **entwicklung mit SQLite + lokale PostgreSQL**.

Auf dem **Production Server**:
- ✅ `python manage_db.py upgrade` wird vor Deployment ausgeführt
- ✅ Backups vorher automatisch genommen
- ✅ Downgrade wird gespeichert für Rollback
- ✅ Monitoring & Alerting überwacht Schema

Details siehe: `POSTGRESQL_PRODUCTION_GUIDE.md`

---

## 📞 Support

Bei Fragen zum Workflow:
1. `python manage_db.py --help` (zeigt alle Befehle)
2. Überprüfe `migrations/versions/` für generierte SQL
3. Siehe Alembic-Doku: https://alembic.sqlalchemy.org/

---

**Letzte Aktualisierung:** 13. Februar 2026  
**Version:** 1.0
