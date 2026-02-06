# 🚀 Stärkennanalyse-App Startup-Anleitung

## Überblick

Es gibt **drei verschiedene Modi**, um die App zu starten, je nach Verwendungszweck:

---

## 📍 Modus 1: Lokale Entwicklung (empfohlen für Entwicklung)

**Wann verwenden?** Für tägliche Entwicklungsarbeit, schnelles Testen, Debugging

**Datenbank:** SQLite (lokal im `instance/` Ordner)  
**Port:** 5001  
**Debug-Modus:** An

### Schritte:

```bash
# 1. In das Projektverzeichnis wechseln
cd /home/timok/kDrive/Dokumente/staerkenanalyse-app

# 2. Virtual Environment aktivieren
source venv/bin/activate

# 3. Umgebungsvariablen prüfen (.env sollte existieren)
cat .env

# 4. Flask-App starten
python app.py
```

**App läuft unter:** http://localhost:5001

**Vorteile:**
- ✅ Schneller Start ohne Docker
- ✅ Hot-Reload bei Code-Änderungen
- ✅ Debug-Modus für detaillierte Fehlermeldungen
- ✅ SQLite-Datenbank einfach zu sichern/wiederherstellen

**Stoppen:** `Ctrl+C`

---

## 🐳 Modus 2: Docker (PostgreSQL-Testing & Produktions-Vorbereitung)

**Wann verwenden?** Testing mit PostgreSQL, Produktions-Setup testen, Performance-Tests

**Datenbank:** PostgreSQL 16 (Docker-Container)  
**Port:** 5000  
**Debug-Modus:** Aus (Production Mode)

### Schritte:

```bash
# 1. In das Projektverzeichnis wechseln
cd /home/timok/kDrive/Dokumente/staerkenanalyse-app

# 2. Docker-Container starten (baut automatisch beim ersten Mal)
docker-compose up -d

# 3. Status prüfen (beide Container sollten "healthy" sein)
docker-compose ps

# 4. Logs anschauen (bei Problemen)
docker-compose logs -f web
```

**App läuft unter:** http://localhost:5000

**Vorteile:**
- ✅ Exakt gleiche Umgebung wie Produktion
- ✅ PostgreSQL statt SQLite (produktionsreif)
- ✅ Gunicorn mit 4 Worker-Prozessen
- ✅ Automatische Migrations
- ✅ Health-Checks

**Wichtige Docker-Befehle:**

```bash
# Container stoppen
docker-compose down

# Container stoppen UND Datenbank löschen
docker-compose down -v

# Logs ansehen (live)
docker-compose logs -f

# Nur Web-Container neu starten
docker-compose restart web

# Rebuild bei Code-Änderungen
docker-compose up -d --build

# PostgreSQL-Datenbank direkt zugreifen
docker-compose exec db psql -U staerkenanalyse -d staerkenanalyse_db
```

**Health-Check testen:**
```bash
curl http://localhost:5000/health
# Erwartete Ausgabe: {"status": "healthy", "database": "connected"}
```

---

## 🌐 Modus 3: Produktion (Infomaniak oder andere Hosting-Anbieter)

**Wann verwenden?** Für echte Produktions-Deployments mit 5-20 Benutzern

**Datenbank:** Managed PostgreSQL  
**Port:** Nach Konfiguration (meist 80/443 via Reverse Proxy)  
**Debug-Modus:** Aus

### Schritte:

Siehe die vollständige Anleitung in **[DEPLOYMENT.md](DEPLOYMENT.md)**

Kurz zusammengefasst:
1. PostgreSQL-Datenbank auf Infomaniak erstellen
2. `.env.production` mit echten Credentials ausfüllen
3. Code auf Server deployen (Git, FTP, oder Infomaniak Git)
4. Dependencies installieren: `pip install -r requirements.txt`
5. Migrations ausführen: `flask db upgrade`
6. Gunicorn mit Supervisor/Systemd starten

---

## 🔄 Datenbank-Migration zwischen Modi

### SQLite → PostgreSQL (Lokal → Docker)

**Option A: Daten migrieren (empfohlen bei echten Daten)**

```bash
# 1. SQLite-Daten exportieren
python -c "
from app import app, db
from models import Group, Participant, Prompt, SelfAssessment
import json

with app.app_context():
    data = {
        'groups': [{'id': g.id, 'name': g.name, 'beschreibung': g.beschreibung} for g in Group.query.all()],
        'participants': [{'id': p.id, 'name': p.name, 'email': p.email, 'gruppe_id': p.gruppe_id} for p in Participant.query.all()],
        'prompts': [{'id': pr.id, 'name': pr.name, 'content': pr.content} for pr in Prompt.query.all()],
    }
    
    with open('data_export.json', 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
"

# 2. Docker starten
docker-compose up -d

# 3. Daten importieren
docker-compose exec web python3 -c "
from app import app, db
from models import Group, Participant, Prompt
import json

with app.app_context():
    with open('data_export.json', 'r') as f:
        data = json.load(f)
    
    for g in data['groups']:
        db.session.add(Group(**g))
    for p in data['participants']:
        db.session.add(Participant(**p))
    for pr in data['prompts']:
        db.session.add(Prompt(**pr))
    
    db.session.commit()
    print('✅ Daten erfolgreich importiert!')
"
```

**Option B: Frisch starten (empfohlen bei Entwicklung)**

```bash
# Docker mit leerer Datenbank starten
docker-compose up -d

# Alembic erstellt automatisch die Tabellen
```

---

## 🎯 Zusammenfassung: Welchen Modus wann?

| Szenario | Empfohlener Modus | Befehl |
|----------|------------------|--------|
| Code schreiben & testen | Lokale Entwicklung | `python app.py` |
| PostgreSQL testen | Docker | `docker-compose up -d` |
| Deployment vorbereiten | Docker | `docker-compose up -d` |
| Echte Benutzer (Produktion) | Infomaniak | Siehe [DEPLOYMENT.md](DEPLOYMENT.md) |

---

## 🔍 Troubleshooting

### Problem: "Port 5000 already in use"

**Bei lokaler Entwicklung:**
```bash
# Anderen Prozess finden und beenden
lsof -ti:5000 | xargs kill -9
```

**Bei Docker:**
```bash
# Docker-Container stoppen
docker-compose down
```

### Problem: "Database connection failed" (Docker)

```bash
# PostgreSQL-Container-Status prüfen
docker-compose ps

# PostgreSQL-Logs ansehen
docker-compose logs db

# Datenbank neu erstellen
docker-compose down -v
docker-compose up -d
```

### Problem: Migration-Fehler

```bash
# Bei lokaler Entwicklung:
rm -rf migrations/
flask db init
flask db migrate -m "Reset migrations"
flask db upgrade

# Bei Docker:
docker-compose down -v
docker-compose up -d --build
```

### Problem: WeasyPrint/PDF-Generierung funktioniert nicht

**Lokal:** System-Dependencies installieren
```bash
sudo apt-get install -y libcairo2 libpango-1.0-0 libgdk-pixbuf-2.0-0
```

**Docker:** Sollte automatisch funktionieren (im Dockerfile enthalten)

---

## 📊 Port-Übersicht

| Service | Port | Verwendung |
|---------|------|------------|
| Flask (lokal, Entwicklung) | 5001 | `python app.py` |
| Flask (Docker) | 5000 | `docker-compose up` |
| PostgreSQL (Docker) | 5432 | Datenbank-Zugriff von außen |

---

## 📝 Nächste Schritte nach Docker-Start

1. **Dashboard aufrufen:** http://localhost:5000
2. **Gruppen anlegen:** Navigiere zu "Gruppen verwalten"
3. **Teilnehmer hinzufügen:** Erstelle Teilnehmer in den Gruppen
4. **Prompts erstellen:** Definiere die KI-Analyse-Prompts
5. **Erste Analyse durchführen:** Starte eine Batch-AI-Analyse

---

**Status:** ✅ Docker Setup erfolgreich getestet (06.02.2026)
