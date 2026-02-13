# PostgreSQL Production Deployment Guide

**Status:** ✅ Production Ready  
**Database:** PostgreSQL 16 (Alpine)  
**Migrations:** Alembic 1.13.1  
**Last Updated:** 2026-02-13

---

## Phase 1: PostgreSQL Setup (Ubuntu Server)

### 1.1 PostgreSQL Installation

```bash
# Installiere PostgreSQL 16
sudo apt update
sudo apt install -y postgresql-16 postgresql-contrib-16

# Starte PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verifiziere Installation
postgres --version
```

### 1.2 Database & User erstellen

```bash
# Connect zu PostgreSQL
sudo -u postgres psql

# Erstelle Database
CREATE DATABASE staerkenanalyse_prod;

# Erstelle User mit Passwort
CREATE USER staerkenanalyse_prod_user WITH PASSWORD 'YOUR_SECURE_PASSWORD_HERE';

# Gib Permissions
ALTER ROLE staerkenanalyse_prod_user SET client_encoding TO 'utf8';
ALTER ROLE staerkenanalyse_prod_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE staerkenanalyse_prod_user SET default_transaction_deferrable TO on;
ALTER ROLE staerkenanalyse_prod_user SET default_time_zone TO 'UTC';

# Gib Datenbank-Permissions
GRANT ALL PRIVILEGES ON DATABASE staerkenanalyse_prod TO staerkenanalyse_prod_user;
```

### 1.3 Connection String erzeugen

```
postgresql://staerkenanalyse_prod_user:YOUR_SECURE_PASSWORD@localhost:5432/staerkenanalyse_prod
```

---

## Phase 2: Datenbank-Migrationen

### 2.1 Remote Datenbank initialisieren (leere Struktur)

```bash
# Auf dem Ubuntu Server
export DATABASE_URL="postgresql://staerkenanalyse_prod_user:password@localhost:5432/staerkenanalyse_prod"

# Aktiviere venv
source venv/bin/activate

# Führe Migrationen aus
flask db upgrade heads

# Verifiziere (sollte alle Tabellen show)
psql $DATABASE_URL -c "\dt"
```

### 2.2 Struktur-Überprüfung

```bash
# Check Alembic Version
psql $DATABASE_URL -c "SELECT * FROM alembic_version;"

# Sollte zeigen: 422c5ca23883 (oder aktuelle head revision)
```

---

## Phase 3: Datenmigration (SQLite → PostgreSQL)

### 3.1 Backup erstellen

```bash
# Lokales SQLite Backup
cp instance/database.db instance/database.db.backup.$(date +%Y%m%d_%H%M%S)

# PostgreSQL Backup (nach Migration)
pg_dump staerkenanalyse_prod > backup_prod_$(date +%Y%m%d_%H%M%S).sql
```

### 3.2 Migration Script ausführen

```bash
# Das Script befindet sich in: migrate_sqlite_to_postgresql.py

# Mache es executable
chmod +x migrate_sqlite_to_postgresql.py

# Führe Migration durch
python migrate_sqlite_to_postgresql.py \
  "postgresql://staerkenanalyse_prod_user:password@localhost:5432/staerkenanalyse_prod"

# Das Script wird:
# 1. SQLite und PostgreSQL verbinden
# 2. Tabellen-Struktur verifizieren
# 3. Bestätigung abfragen
# 4. Alle Daten kopieren
# 5. Verifizieren dass Zeilencounts stimmen
```

### 3.3 Daten verifizieren

```bash
# Zähle Datensätze in PostgreSQL
psql $DATABASE_URL -c "
SELECT 
  tablename,
  (SELECT count(*) FROM information_schema.tables WHERE table_name = tablename) as row_count
FROM pg_catalog.pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;"
```

---

## Phase 4: Production Environment Setup

### 4.1 .env für Production erstellen

```bash
# Create .env.production (NICHT in Git committen!)

cat > .env.production << 'EOF'
# Database (PostgreSQL Production)
DATABASE_URL=postgresql://staerkenanalyse_prod_user:YOUR_SECURE_PASSWORD@db.your-domain.com:5432/staerkenanalyse_prod

# Flask Config
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=YOUR_VERY_SECURE_RANDOM_STRING

# API Keys (behalte diese geheim!)
GOOGLE_API_KEY=xxx
MISTRAL_API_KEY=xxx
BUGFENDER_APP_KEY=xxx

# Session Security (production-grade)
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
REMEMBER_COOKIE_SECURE=True
REMEMBER_COOKIE_HTTPONLY=True

# Ratelimiting
RATELIMIT_STORAGE_URI=postgresql+psycopg2://staerkenanalyse_prod_user:password@db.your-domain.com:5432/staerkenanalyse_prod
EOF
```

### 4.2 Gunicorn Config (Production WSGI Server)

```bash
# Installiere Gunicorn (falls noch nicht)
source venv/bin/activate
pip install gunicorn

# Teste Gunicorn
gunicorn --bind localhost:5000 --workers 4 --timeout 120 app:app --env-file .env.production
```

### 4.3 Systemd Service (Auto-Start + Restart)

```bash
# Erstelle Service-Datei
sudo tee /etc/systemd/system/staerkenanalyse.service << 'EOF'
[Unit]
Description=Stärkenanalyse Flask Application
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data

WorkingDirectory=/var/www/staerkenanalyse

Environment="PATH=/var/www/staerkenanalyse/venv/bin"
EnvironmentFile=/var/www/staerkenanalyse/.env.production

ExecStart=/var/www/staerkenanalyse/venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 4 \
    --timeout 120 \
    --error-logfile /var/log/staerkenanalyse/error.log \
    --access-logfile /var/log/staerkenanalyse/access.log \
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Aktiviere Service
sudo systemctl daemon-reload
sudo systemctl enable staerkenanalyse
sudo systemctl start staerkenanalyse
sudo systemctl status staerkenanalyse
```

---

## Phase 5: Nginx Reverse Proxy Setup

### 5.1 Nginx Config

```bash
# Erstelle Nginx Config
sudo tee /etc/nginx/sites-available/staerkenanalyse << 'EOF'
upstream staerkenanalyse {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirect HTTP → HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL Best Practices
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    client_max_body_size 16M;
    
    location / {
        proxy_pass http://staerkenanalyse;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
    
    location /static/ {
        alias /var/www/staerkenanalyse/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/staerkenanalyse /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5.2 Let's Encrypt SSL Certificate

```bash
# Installiere Certbot
sudo apt install -y certbot python3-certbot-nginx

# Hole Certificate
sudo certbot certonly --nginx -d your-domain.com -d www.your-domain.com

# Auto-Renewal aktivieren
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## Phase 6: Backup & Monitoring Strategy

### 6.1 Automated Backups

```bash
# Erstelle Backup-Script
cat > /usr/local/bin/backup-staerkenanalyse.sh << 'EOF'
#!/bin/bash

BACKUP_DIR="/var/backups/staerkenanalyse"
DB_NAME="staerkenanalyse_prod"
DB_USER="staerkenanalyse_prod_user"

mkdir -p $BACKUP_DIR

# PostgreSQL Backup
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sql.gz

# Uploads Backup
tar -czf $BACKUP_DIR/uploads_$(date +%Y%m%d_%H%M%S).tar.gz /var/www/staerkenanalyse/uploads/

# Cleanup alte Backups (älter als 30 Tage)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "✅ Backup completed: $(date)"
EOF

chmod +x /usr/local/bin/backup-staerkenanalyse.sh

# Cron Job (täglich um 02:00)
sudo tee -a /etc/crontab << 'EOF'
0 2 * * * /usr/local/bin/backup-staerkenanalyse.sh >> /var/log/staerkenanalyse/backup.log 2>&1
EOF
```

### 6.2 Monitoring

```bash
# Installiere Tools (optional)
sudo apt install -y htop nethogs

# PostgreSQL Monitoring
psql $DATABASE_URL -c "SELECT datname, numbackends FROM pg_stat_database WHERE datname = 'staerkenanalyse_prod';"

# Logs überwachen
tail -f /var/log/staerkenanalyse/error.log
tail -f /var/log/staerkenanalyse/access.log
```

---

## Checkliste vor Go-Live

- [ ] PostgreSQL 16 Installation überprüft
- [ ] Database & User erstellt
- [ ] Alembic Migrationen erfolgreich ausgeführt
- [ ] Datenmigration SQLite → PostgreSQL getestet
- [ ] Datenintegrität verifiziert (Zeilencounts)
- [ ] .env.production erstellt (geheim gehalten)
- [ ] Gunicorn testet lädt App
- [ ] Systemd Service läuft
- [ ] Nginx Reverse Proxy konfiguriert
- [ ] SSL/HTTPS mit Let's Encrypt aktiv
- [ ] Backup-Scripts getestet
- [ ] Monitoring eingerichtet
- [ ] DB-Verbindung von Gunicorn aus funktioniert
- [ ] Statische Assets laden
- [ ] API Endpoints ansprechbar

---

## Troubleshooting

### Verbindungsfehler

```bash
# Check PostgreSQL läuft
sudo systemctl status postgresql

# Test Connection
psql -U staerkenanalyse_prod_user -h localhost -d staerkenanalyse_prod

# Check Firewall
sudo ufw allow 5432/tcp
```

### Migrations schlagen fehl

```bash
# Check aktuelle Migration
psql $DATABASE_URL -c "SELECT version FROM alembic_version;"

# Reset zu bestimmtem Version (nur falls nötig!)
# WARNUNG: Dies löscht Daten!
flask db downgrade <previous_version>
```

### Performance Probleme

```bash
# Check DB-Verbindungen
psql $DATABASE_URL -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"

# Optimiere PostgreSQL Config (/etc/postgresql/16/main/postgresql.conf)
# - shared_buffers = 256MB (für 4GB RAM)
# - effective_cache_size = 1GB
# - work_mem = 50MB
```

---

## Rollback Plan

Falls etwas schief geht:

```bash
# 1. Stop Gunicorn Application
sudo systemctl stop staerkenanalyse

# 2. Restore PostgreSQL von Backup
psql -U postgres << 'EOF'
DROP DATABASE staerkenanalyse_prod;
CREATE DATABASE staerkenanalyse_prod OWNER staerkenanalyse_prod_user;
EOF

# 3. Restore Daten
gunzip < backup_prod_YYYYMMDD_HHMMSS.sql.gz | psql -U staerkenanalyse_prod_user staerkenanalyse_prod

# 4. Starte App
sudo systemctl start staerkenanalyse
```

---

## Production Connection String

Nach allem Setup, die Connection String für Production:

```
postgresql://staerkenanalyse_prod_user:YOUR_PASSWORD@your-domain.com:5432/staerkenanalyse_prod
```

---

**Status:** Ready for Production Deployment ✅
