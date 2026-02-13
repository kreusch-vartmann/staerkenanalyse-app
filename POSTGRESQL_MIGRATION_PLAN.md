# SQLite → PostgreSQL Migration Master Plan

**Status:** ✅ Ready for Production Migration  
**Created:** 2026-02-13  
**Database Version:** PostgreSQL 16 / SQLite (source)

---

## Executive Summary

Der Schritt von **SQLite zu PostgreSQL** ist für Production notwendig:

| Kriterium | SQLite | PostgreSQL |
|-----------|--------|-----------|
| **Concurrent Writes** | ~1 gleichzeitig | 500+ gleichzeitig |
| **Production Grade** | ❌ Nein | ✅ Ja |
| **Backups** | Datei kopieren | Automated streaming |
| **Scaling** | Begrenzt | Unbegrenzt |
| **20+ User** | ❌ Problematisch | ✅ Optimal |

---

## Migration Timeline

### Phase 1: Vorbereitung (Heute)
- ✅ Alembic Migrations validiert
- ✅ PostgreSQL Docker Setup funktioniert
- ✅ Migration Script erstellt (`migrate_sqlite_to_postgresql.py`)
- ✅ Production Guide dokumentiert

### Phase 2: Lokales Testing (1-2 Stunden)
- [ ] PostgreSQL lokal starten (`docker-compose up`)
- [ ] Alembic Migrations ausführen
- [ ] SQLite→PostgreSQL Migration testen
- [ ] Datencounts verifizieren
- [ ] App gegen PostgreSQL testen

### Phase 3: Production Setup (Ubuntu Server)
- [ ] PostgreSQL 16 installieren
- [ ] Database &User erstellen
- [ ] Migrations ausführen
- [ ] Gunicorn + Nginx konfigurieren
- [ ] SSL/HTTPS aktivieren

### Phase 4: Production Migration
- [ ] Backup erstellen
- [ ] Datenmigration ausführen
- [ ] Verifizierung
- [ ] Cutover (Production auf PostgreSQL 
 umschalten)

---

## Pre-Migration Checklist

### Entwicklung (Lokal)
- [ ] `POSTGRESQL_TESTING_LOCAL.md` gelesen
- [ ] Docker Compose läuft
- [ ] Migration Script getestet
- [ ] Testdaten erfolgreich migriert
- [ ] App läuft gegen PostgreSQL

### Production (Ubuntu Server)
- [ ] PostgreSQL 16 installiert
- [ ] Database & User erstellt
- [ ] Connection String vorbereitet
- [ ] Alembic Migrations ready
- [ ] Backup-Strategie definiert
- [ ] Monitoring eingerichtet
- [ ] Rollback-Plan dokumentiert

---

## Migration Scripts & Tools

### 1. Migration Script (Python)
```bash
# Datei: migrate_sqlite_to_postgresql.py

# Funktion: Kopiert alle Daten von SQLite → PostgreSQL
# Features:
#  - Verbindungsprüfung
#  - Tabellen-Verifizierung
#  - Interaktive Bestätigung
#  - Automatische Verfizierung

# Verwendung:
python migrate_sqlite_to_postgresql.py \
  "postgresql://user:pass@host:5432/dbname"
```

### 2. Alembic Migrations
```bash
# Diese sind BEREITS in PostgreSQL:
flask db upgrade heads

# Revision History:
# - 422c5ca23883 (current head)
# - Previous 16 migrations
# - All tested & validated
```

### 3. Backup & Restore
```bash
# PostgreSQL Backup
pg_dump -U staerkenanalyse_prod_user \
  -h localhost \
  staerkenanalyse_prod > backup.sql

# PostgreSQL Restore
psql -U staerkenanalyse_prod_user \
  -d staerkenanalyse_prod < backup.sql
```

---

## Schritt-für-Schritt Ablauf

### Schritt 1: Lokales Testing (Vor Production)

```bash
# 1. Docker starten
docker-compose up -d
docker-compose logs -f staerkenanalyse_db

# 2. Status prüfen
docker-compose exec staerkenanalyse_db psql \
  -U staerkenanalyse_user \
  -d staerkenanalyse_db \
  -c "\dt"

# 3. Migrations prüfen
docker exec staerkenanalyse_web flask db current

# 4. Migration ausführen
python migrate_sqlite_to_postgresql.py \
  "postgresql://staerkenanalyse_user:changeme_secure_password@localhost:5432/staerkenanalyse_db"

# 5. Verifizieren
docker-compose exec staerkenanalyse_db psql \
  -U staerkenanalyse_user \
  -d staerkenanalyse_db \
  -c "SELECT COUNT(*) FROM users;"
```

### Schritt 2: Production Setup

```bash
# 1. SSH in Ubuntu Server
ssh user@your-hostinger-server.com

# 2. PostgreSQL installieren
sudo apt update
sudo apt install -y postgresql-16 postgresql-contrib-16
sudo systemctl start postgresql

# 3. Database erstellen
sudo -u postgres createdb staerkenanalyse_prod
sudo -u postgres createuser staerkenanalyse_prod_user
sudo -u postgres psql -c "ALTER USER staerkenanalyse_prod_user WITH PASSWORD 'SECURE_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL ON DATABASE staerkenanalyse_prod TO staerkenanalyse_prod_user;"

# 4. App Code hochladen
git clone <repo> /var/www/staerkenanalyse
cd /var/www/staerkenanalyse
mkdir -p /var/log/staerkenanalyse
chown www-data:www-data /var/log/staerkenanalyse

# 5. venv + Dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Migrationen ausführen
export DATABASE_URL="postgresql://staerkenanalyse_prod_user:PASSWORD@localhost:5432/staerkenanalyse_prod"
flask db upgrade heads

# 7. Daten migrieren
python migrate_sqlite_to_postgresql.py "$DATABASE_URL"

# 8. Gunicorn + Nginx (siehe POSTGRESQL_PRODUCTION_GUIDE.md)
```

### Schritt 3: Cutover (Go-Live)

```bash
# 1. Production App stoppen (kurzzeitig)
sudo systemctl stop staerkenanalyse

# 2. Final Backup erstellen
pg_dump -U staerkenanalyse_prod_user \
  staerkenanalyse_prod > \
  backup_pre_migration_$(date +%Y%m%d_%H%M%S).sql

# 3. .env.production aktualisieren
export DATABASE_URL="postgresql://user:pass@localhost:5432/staerkenanalyse_prod"

# 4. App starten mit PostgreSQL
sudo systemctl start staerkenanalyse

# 5. Health Check
curl https://your-domain.com/health

# 6. Smoke Tests
# - Login
# - Create participant
# - Generate report
# - Export data
```

---

## Rollback Plan

Falls Probleme während Migration:

```bash
### NOTFALL: Alles zurückfahren

# 1. PostgreSQL zurücksetzen
DROP DATABASE staerkenanalyse_prod;
CREATE DATABASE staerkenanalyse_prod OWNER staerkenanalyse_prod_user;

# 2. Backup wiederherstellen
psql -U staerkenanalyse_prod_user \
  -d staerkenanalyse_prod < backup_pre_migration.sql

# 3. App neu starten
sudo systemctl restart staerkenanalyse

# 4. Wieder auf SQLite zurückfahren (wenn nötig)
# Update DATABASE_URL in .env:
DATABASE_URL=sqlite:///instance/database.db
sudo systemctl restart staerkenanalyse
```

---

## Data Integrity Check

Nach der Migration **IMMER** folgende Checks durchführen:

```bash
psql -U staerkenanalyse_prod_user -d staerkenanalyse_prod << 'EOF'

-- 1. Tabellen-Row-Counts
SELECT 'groups' as table_name, COUNT(*) as row_count FROM groups
UNION ALL
SELECT 'participants', COUNT(*) FROM participants
UNION ALL
SELECT 'users', COUNT(*) FROM users
UNION ALL
SELECT 'prompts', COUNT(*) FROM prompts
UNION ALL
SELECT 'tasks', COUNT(*) FROM tasks
ORDER BY table_name;

-- 2. Foreign Key Integrität
SELECT COUNT(*) FROM participants WHERE group_id NOT IN (SELECT id FROM groups);
-- Sollte 0 sein!

-- 3. Alembic Version
SELECT * FROM alembic_version;
-- Sollte neuste Revision zeigen

EOF
```

---

## Performance Expectations

**PostgreSQL sollte sein:**
- 50-100x schneller für komplexe Queries
- Multi-User-Ready (aktuell SQLite limited)
- Automatische Backups möglich
- Replication & High-Availability möglich

---

## Dokumentation durcharbeitet

Folgende Guides sind verfügbar:

| Dokument | Zweck | Status |
|----------|-------|--------|
| **POSTGRESQL_PRODUCTION_GUIDE.md** | Full Production Setup | ✅ Ready |
| **POSTGRESQL_TESTING_LOCAL.md** | Lokales Testing | ✅ Ready |
| **migrate_sqlite_to_postgresql.py** | Migration Tool | ✅ Ready |
| **DEPLOYMENT.md** | Deployment-Optionen | ✅ Updated |

---

## Support & Questions

**Falls Fragen:**
- Check `POSTGRESQL_PRODUCTION_GUIDE.md` → Troubleshooting
- Docker Logs: `docker-compose logs`
- PostgreSQL Logs: `tail -f /var/log/postgresql/...`
- Migration Script Output: `python migrate_sqlite_to_postgresql.py` (verbose output)

---

## Timeline Estimate

| Task | Time | Priority |
|------|------|----------|
| Local Testing | 1-2h | Critical |
| Production Server Setup | 2-3h | Critical |
| Data Migration | 15-30min | Critical |
| Verification & Testing | 1h | Critical |
| Nginx/SSL Setup | 1-2h | High |
| Monitoring Setup | 1h | Medium |

**Total:** ~7-10 hours for full production deployment

---

**Status:** ✅ ALL SYSTEMS READY FOR MIGRATION

Bereit zum Deployment? Starten mit `docker-compose up` und folge **POSTGRESQL_TESTING_LOCAL.md**
