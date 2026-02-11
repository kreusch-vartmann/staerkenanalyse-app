# 🚀 Deployment-Anleitung: Stärkenanalyse-Tool

## 📋 Übersicht

Dieses Dokument beschreibt zwei Deployment-Optionen:
1. **Docker (lokal + VPS)** - Für Entwicklung und Server mit Docker-Support
2. **Infomaniak Web Hosting** - Für Production ohne Docker (empfohlen für 5-20 User)

---

## 🐳 Option 1: Docker-Deployment

### Voraussetzungen
- Docker & Docker Compose installiert
- `.env` Datei konfiguriert

### Schritt-für-Schritt Setup

**1. Environment-Variablen in `.env` prüfen:**
```bash
# Prüfe ob SECRET_KEY gesetzt ist
grep SECRET_KEY .env

# Falls nicht, generiere einen:
python -c "import os; print('SECRET_KEY=' + os.urandom(24).hex())"
# Kopiere Output in .env
```

**2. Docker Container starten:**
```bash
docker-compose up -d
```

**3. Logs prüfen:**
```bash
docker-compose logs -f web
```

**4. App öffnen:**
```
http://localhost:5000
```

### Nützliche Docker-Befehle

```bash
# Container stoppen
docker-compose down

# Container neu starten
docker-compose restart web

# PostgreSQL Shell öffnen
docker-compose exec db psql -U staerkenanalyse_user -d staerkenanalyse_db

# Backup erstellen
docker-compose exec db pg_dump -U staerkenanalyse_user staerkenanalyse_db > backup_$(date +%Y%m%d).sql

# Backup wiederherstellen
docker-compose exec -T db psql -U staerkenanalyse_user staerkenanalyse_db < backup.sql

# Logs anzeigen
docker-compose logs -f

# Container vollständig entfernen (inkl. Daten!)
docker-compose down -v
```

---

## 🌐 Option 2: Infomaniak Web Hosting (Production)

**Empfohlen für:** 5-20 gleichzeitige User, Managed PostgreSQL

### Voraussetzungen
- Infomaniak Web Hosting mit Python-Support
- PostgreSQL-Datenbank bei Infomaniak angelegt

### Setup

**1. PostgreSQL-Datenbank erstellen:**
- Gehe zu **Infomaniak Manager** → **Web Hosting** → **Datenbanken**
- Erstelle neue PostgreSQL-Datenbank
- Notiere: Host, Port, DB-Name, Username, Passwort

**2. Code via Git/SFTP hochladen:**
```bash
# Via Git
ssh dein_user@dein_host.infomaniak.com
cd public_html
git clone https://github.com/DEIN_USERNAME/staerkenanalyse-app.git
cd staerkenanalyse-app
```

**3. Virtual Environment erstellen:**
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**4. `.env` Datei konfigurieren:**
```bash
cp .env.production .env
nano .env
```

Fülle aus:
```env
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=<generiere neuen Key>
DATABASE_URL=postgresql://user:pass@postgres.infomaniak.com:5432/dbname
GOOGLE_API_KEY=<dein_key>
MISTRAL_API_KEY=<dein_key>
BUGFENDER_APP_KEY=<dein_key>
```

**5. Datenbank-Migrationen anwenden:**
```bash
source venv/bin/activate
export FLASK_APP=app.py
flask db upgrade
```

**6. Gunicorn als Service (Systemd):**

Erstelle `/etc/systemd/system/staerkenanalyse.service`:
```ini
[Unit]
Description=Stärkenanalyse Flask App
After=network.target

[Service]
User=dein_username
WorkingDirectory=/home/dein_username/public_html/staerkenanalyse-app
Environment="PATH=/home/dein_username/public_html/staerkenanalyse-app/venv/bin"
ExecStart=/home/dein_username/public_html/staerkenanalyse-app/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable staerkenanalyse
sudo systemctl start staerkenanalyse
sudo systemctl status staerkenanalyse
```

---

## 🔒 Security Checklist (Production)

- [ ] `FLASK_DEBUG=False` in `.env`
- [ ] `SECRET_KEY` mit 48+ Zeichen generiert
- [ ] `.env` Datei geschützt (`chmod 600 .env`)
- [ ] PostgreSQL-Passwort stark (16+ Zeichen)
- [ ] HTTPS aktiviert (SSL-Zertifikat)
- [ ] `SESSION_COOKIE_SECURE=True` (nur mit HTTPS)
- [ ] Firewall: Nur Port 80/443 offen
- [ ] Regelmäßige Backups eingerichtet
- [ ] Logging aktiviert

---

## 📊 Monitoring & Wartung

### Health-Check
```bash
curl http://localhost:5000/health
# Sollte zurückgeben: {"status": "healthy", "database": "connected"}
```

### Logs prüfen
**Docker:**
```bash
docker-compose logs -f web
```

**Infomaniak:**
```bash
tail -f /home/dein_user/logs/staerkenanalyse.log
```

### Datenbank-Backup (wöchentlich empfohlen)
```bash
# Docker
docker-compose exec db pg_dump -U staerkenanalyse_user staerkenanalyse_db > backup_$(date +%Y%m%d).sql

# Infomaniak
pg_dump -h postgres.infomaniak.com -U username staerkenanalyse_db > backup_$(date +%Y%m%d).sql
```

### Updates deployen
```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
flask db upgrade
sudo systemctl restart staerkenanalyse
```

---

## 🆘 Troubleshooting

### Problem: "Database connection failed"
**Lösung:**
- Prüfe `DATABASE_URL` in `.env`
- Teste: `psql -h HOST -U USER -d DATABASE`
- Docker: `docker-compose logs db`

### Problem: "500 Internal Server Error"
**Lösung:**
- Prüfe Logs
- Prüfe `.env` (alle Keys gesetzt?)
- Prüfe Migrations: `flask db current`

### Problem: "CSRF token missing"
**Lösung:**
- Flask-WTF installiert? `pip install Flask-WTF`
- `SECRET_KEY` in `.env` gesetzt?

---

## 📈 Kostenvergleich

| Option | Kosten/Monat | Vorteile | Nachteile |
|--------|--------------|----------|-----------|
| **Infomaniak Web Hosting** | ~20-30 CHF | Einfach, Managed DB | Kein Docker |
| **Infomaniak VPS** | ~50-100 CHF | Volle Kontrolle | Mehr Wartung |
| **Docker Lokal** | Kostenlos | Entwicklung | Nicht für Production |

**Empfehlung für 5-20 User:** Infomaniak Web Hosting + Managed PostgreSQL

---

**Letzte Aktualisierung:** 11. Februar 2026
