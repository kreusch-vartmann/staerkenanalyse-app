# Docker-Build Testanleitung

## 🧪 Voraussetzungen
- **Docker** und **Docker Compose** installiert.
- **Ports `5000` (App), `5432` (PostgreSQL), `6379` (Redis)** frei.

---

## 🚀 Build testen

### 1. Docker-Image bauen
```bash
cd /home/timok/kDrive/Dokumente/staerkenanalyse-app
docker build -t staerkenanalyse-app:latest .
```

**Erwartete Ausgabe**:
```text
[+] Building 2.4s (15/15) FINISHED
 => [internal] load build definition from Dockerfile
 => => transferring dockerfile: 32B
 => [internal] load .dockerignore
 => => transferring context: 2B
 => [1/9] FROM docker.io/library/python:3.12-slim
 => [2/9] RUN apt-get update && apt-get install -y --no-install-recommends ...
 => [3/9] COPY --from=builder /wheels /wheels
 => [4/9] RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*
 => [5/9] RUN useradd -m -u 1000 appuser
 => [6/9] WORKDIR /app
 => [7/9] COPY --chown=appuser:appuser . .
 => [8/9] USER appuser
 => [9/9] RUN mkdir -p /app/instance && chown appuser:appuser /app/instance
 => exporting to image
 => => exporting layers
 => => writing image sha256:...
```

### 2. Container starten
```bash
docker compose --env-file .env.docker up -d
```

**Erwartete Ausgabe**:
```text
[+] Running 3/3
 ✔ Network staerkenanalyse-app_app_network  Created
 ✔ Container staerkenanalyse-app-postgres-1  Healthy
 ✔ Container staerkenanalyse-app-app-1       Started
```

### 3. Logs prüfen
```bash
docker compose logs -f app
```

**Erwartet**:
```text
app-1  | 🔄 Warte auf PostgreSQL...
app-1  | ✅ PostgreSQL erreichbar
app-1  | INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
app-1  | INFO  [alembic.runtime.migration] Will assume transactional DDL.
app-1  | INFO  [alembic.runtime.migration] Running upgrade  -> 20260213_001, Initial migration
app-1  | [2026-09-13 12:00:00 +0000] [1] [INFO] Starting gunicorn 21.2.0
app-1  | [2026-09-13 12:00:00 +0000] [1] [INFO] Listening at: http://0.0.0.0:5000 (1)
```

### 4. App testen
- **URL**: [http://localhost:5000](http://localhost:5000)
- **Erwartet**: Login-Seite (`/login`).

### 5. Monitoring prüfen
```bash
curl http://localhost:5000/health
curl http://localhost:5000/metrics
```

**Erwartet**:
```json
{"status": "healthy"}
```

**Metriken**:
```text
# HELP flask_request_count App Request Count
# TYPE flask_request_count counter
flask_request_count{endpoint="/login",method="GET",http_status="200"} 1.0
```

---

## 🛠️ Troubleshooting

### Fehler: "Permission denied" (Docker)
- **Lösung**: Nutzer zur `docker`-Gruppe hinzufügen:
  ```bash
  sudo usermod -aG docker $USER
  newgrp docker
  ```

### Fehler: "Port already in use"
- **Lösung**: Ports freigeben oder `docker-compose.yml` anpassen:
  ```yaml
  ports:
    - "5001:5000"  # App auf Port 5001 mappen
  ```

### Fehler: "flask db upgrade fehlgeschlagen"
- **Lösung**: Logs prüfen:
  ```bash
docker compose logs app
  ```
- **Häufige Ursache**: Falsche `DATABASE_URL` in `.env.docker`.

### Fehler: "WeasyPrint fehlgeschlagen"
- **Lösung**: Systempakete im Container installieren (bereits in `Dockerfile` enthalten).