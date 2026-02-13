# PostgreSQL Testing Guide (Lokal mit Docker)

**Ziel:** PostgreSQL-Setup lokal testen bevor Production-Deployment

---

## Schritt 1: Docker Compose starten

```bash
cd /home/timok/kDrive/Dokumente/staerkenanalyse-app

# Starte PostgreSQL + Web Container
docker-compose up -d

# Verifiziere Container
docker-compose ps

# Output sollte zeigen:
# NAME                  STATUS
# staerkenanalyse_db    Up (healthy)
# staerkenanalyse_web   Up (healthy)
```

## Schritt 2: Initializing Migrations

```bash
# Die Migrations sind bereits in PostgreSQL gelaufen!
# Aber du kannst neu initialisieren mit:

docker exec staerkenanalyse_web flask db upgrade heads

# Verifiziere
docker exec staerkenanalyse_db psql -U staerkenanalyse_user -d staerkenanalyse_db -c "\dt"
```

## Schritt 3: Daten von SQLite → PostgreSQL migrieren

```bash
# Zunächst: Backup erstellen
cp instance/database.db instance/database.db.backup.$(date +%Y%m%d)

# Aktiviere venv
source venv/bin/activate

# Hole die Connection String von Docker Compose
# Find in docker-compose.yml:
# - Host: db (im Netzwerk) oder localhost (von außen)
# - Port: 5432
# - User: staerkenanalyse_user
# - Password: (aus env.POSTGRES_PASSWORD oder changeme_secure_password)
# - Database: staerkenanalyse_db

# Führe Migration durch (von außen auf Container):
python migrate_sqlite_to_postgresql.py \
  "postgresql://staerkenanalyse_user:changeme_secure_password@localhost:5432/staerkenanalyse_db"

# Interaktive Bestätigungen folgen
```

## Schritt 4: Verifizierung

```bash
# Check Datencounts
docker exec staerkenanalyse_db psql -U staerkenanalyse_user -d staerkenanalyse_db << 'EOF'
SELECT 
  tablename,
  (SELECT count(*) FROM ONLY pg_class 
   WHERE relname = tablename) as row_estimate
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
EOF

# Beispiel Output:
#     tablename     | row_estimate
# ----------------+---------------
#  groups          |            2
#  participants    |            5
#  prompts         |           10
#  ...
```

## Schritt 5: App gegen PostgreSQL testen

```bash
# Option A: Mit Docker Compose
docker-compose logs -f staerkenanalyse_web

# Option B: Lokal mit PostgreSQL Connection
export DATABASE_URL="postgresql://staerkenanalyse_user:changeme_secure_password@localhost:5432/staerkenanalyse_db"

source venv/bin/activate
flask run --port 5002

# Visit http://localhost:5002 und teste Features
```

## Schritt 6: Cleanup

```bash
# Wenn fertig mit Testing:

# Option: Nur Daten löschen (Schema behalten)
docker exec staerkenanalyse_db psql -U staerkenanalyse_user -d staerkenanalyse_db << 'EOF'
TRUNCATE groups CASCADE;
TRUNCATE participants CASCADE;
TRUNCATE prompts CASCADE;
-- etc
EOF

# Option: Komplettes Teardown
docker-compose down -v

# Volumes werden gelöscht! Backup erstellen falls nötig.
```

---

## Wichtige Umgebungsvariablen

**Docker Compose (für Container):**
```yaml
# docker-compose.yml
environment:
  - DATABASE_URL=postgresql://staerkenanalyse_user:password@db:5432/staerkenanalyse_db
```

**Lokal (für Testing von außen):**
```bash
# .env oder Export
DATABASE_URL=postgresql://staerkenanalyse_user:changeme_secure_password@localhost:5432/staerkenanalyse_db
```

**Production:**
```bash
# .env.production
DATABASE_URL=postgresql://staerkenanalyse_prod_user:SECURE_PASSWORD@db.your-domain.com:5432/staerkenanalyse_prod
```

---

## Troubleshooting

### Container starten nicht
```bash
# Logs anschauen
docker-compose logs staerkenanalyse_db

# Volumes cleanen und neu starten
docker-compose down -v
docker-compose up -d
```

### Migrations fehlgeschlagen
```bash
# Einzelne Migration zurückfahren
docker exec staerkenanalyse_web flask db downgrade -1

# Und Upgrade wiederholen
docker exec staerkenanalyse_web flask db upgrade heads
```

### Datenmigration fehlgeschlagen
```bash
# SQLite Backup wiederherstellen
cp instance/database.db.backup instance/database.db

# PostgreSQL Reset
docker-compose down -v
docker-compose up -d

# Und nochmal versuchen
python migrate_sqlite_to_postgresql.py postgresql://...
```

---

## Performance Testing

```bash
# Installiere Load-Testing Tool (optional)
pip install locust

# Einfacher Performance Check
# Öffne mehrere Browser-Tabs mit http://localhost:5002
# Beobachte Docker-Logs:

docker-compose logs --tail=20 -f staerkenanalyse_web

# oder

docker stats staerkenanalyse_db  # Watch CPU/Memory
```

---

**Status:** ✅ Ready for local testing before production
