# Docker-Setup Test Guide

## 🧪 Voraussetzungen
- **Docker** und **Docker Compose** installiert.
- **Ports `5000` (App), `5432` (PostgreSQL), `6379` (Redis)** frei.

---

## 🚀 Schnellstart

### 1. `.env` für Docker anpassen
Erstelle eine `.env.docker`-Datei mit:

```ini
# .env.docker
SECRET_KEY=dein_geheimes_passwort
POSTGRES_USER=stark
POSTGRES_PASSWORD=stark
POSTGRES_DB=stark
```

### 2. Docker-Container starten
```bash
# Build und Start (im Hintergrund)
docker compose --env-file .env.docker up -d --build
```

### 3. Logs prüfen
```bash
# App-Logs anzeigen
docker compose logs -f app
```

**Erwartete Ausgabe**:
```text
app_1       | 🔄 Warte auf PostgreSQL...
app_1       | ✅ PostgreSQL erreichbar
app_1       | INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
app_1       | INFO  [alembic.runtime.migration] Will assume transactional DDL.
app_1       | INFO  [alembic.runtime.migration] Running upgrade  -> 20260213_001, Initial migration
app_1       | [2026-09-13 12:00:00 +0000] [1] [INFO] Starting gunicorn 21.2.0
app_1       | [2026-09-13 12:00:00 +0000] [1] [INFO] Listening at: http://0.0.0.0:5000 (1)
```

### 4. App testen
- **URL**: [http://localhost:5000](http://localhost:5000)
- **Erwartet**: Login-Seite (`/login`).

### 5. Datenbank prüfen
```bash
# PostgreSQL-Container betreten
docker compose exec postgres psql -U stark -d stark
```

**SQL-Abfragen**:
```sql
-- Tabellen prüfen
\dt

-- Teilnehmer zählen
SELECT COUNT(*) FROM participants;

-- Erwartet: 2 (Testdaten)
```

---

## 🛠️ Troubleshooting

### Fehler: "Port already in use"
- **Lösung**: Ports freigeben oder `docker-compose.yml` anpassen:
  ```yaml
  ports:
    - "5001:5000"  # App auf Port 5001 mappen
  ```

### Fehler: "Permission denied" (Docker)
- **Lösung**: Nutzer zur `docker`-Gruppe hinzufügen:
  ```bash
  sudo usermod -aG docker $USER
  newgrp docker  # Gruppe neu laden
  ```

### Fehler: "flask db upgrade fehlgeschlagen"
- **Lösung**: Logs prüfen:
  ```bash
  docker compose logs app
  ```
- **Häufige Ursache**: Falsche `DATABASE_URL` in `.env.docker`.

### Fehler: "WeasyPrint fehlgeschlagen"
- **Lösung**: Systempakete im Container installieren (bereits in `Dockerfile` enthalten).