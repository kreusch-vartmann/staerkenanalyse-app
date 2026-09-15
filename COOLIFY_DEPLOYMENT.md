# Coolify Deployment Guide

## 🚀 Voraussetzungen
- **Coolify-Instanz** (z. B. bei [Infomaniak](https://www.infomaniak.com/de/coolify) oder selbst gehostet).
- **Git-Repository** (GitHub/GitLab) mit der Stärkenanalyse-App.
- **Domain** (optional, für HTTPS).

---

## ⚙️ Schritt 1: Projekt in Coolify erstellen
1. **Coolify-UI öffnen** (z. B. `https://coolify.deine-domain.de`).
2. **Neues Projekt erstellen**:
   - Name: `Stärkenanalyse-App`
   - Environment: `Production`
3. **Git-Repository hinzufügen**:
   - Repository-URL: `https://github.com/kreusch-vartmann/staerkenanalyse-app`
   - Branch: `main`
   - Build-Methode: `Docker Compose`
   - Compose-Datei: `coolify.yml`

---

## 🔐 Schritt 2: Umgebungsvariablen setzen
1. **Gehe zu `Environment Variables`** im Coolify-Projekt.
2. **Füge die Secrets aus `.env.coolify` hinzu**:
   | Variable            | Wert (Beispiel)               | Typ      |
   |--------------------|-------------------------------|----------|
   | `SECRET_KEY`       | `dein_geheimes_passwort`      | **Secret** |
   | `POSTGRES_PASSWORD`| `stark`                       | **Secret** |
   | `MISTRAL_API_KEY`  | `dein_mistral_api_key`        | **Secret** |
3. **Öffentliche Variablen** (Standardwerte):
   ```ini
   POSTGRES_USER=stark
   POSTGRES_DB=stark
   ```

---

## 🚢 Schritt 3: Deployment starten
1. **Klicke auf `Deploy`** in der Coolify-UI.
2. **Logs überwachen**:
   - PostgreSQL/Redis müssen **`healthy`** werden.
   - Die App sollte nach ~2 Minuten **`healthy`** sein.
3. **Domain zuweisen** (optional):
   - Gehe zu `Domains` und füge deine Domain hinzu (z. B. `app.deine-domain.de`).
   - Coolify richtet automatisch **HTTPS (Let's Encrypt)** ein.

---

## 🧪 Schritt 4: Testen
1. **App-URL öffnen** (z. B. `https://app.deine-domain.de`).
2. **Login testen**:
   - E-Mail: `admin@local.de`
   - Passwort: `admin` (oder das in `seed_permissions.py` generierte Passwort).
3. **Datenbank prüfen**:
   - Gehe zu `/admin/participants` und prüfe, ob die Testdaten (Laura Becker, Marie Koch) vorhanden sind.

---

## 🛠️ Troubleshooting

### Fehler: "Deployment fehlgeschlagen"
- **Lösung**: Logs prüfen:
  ```bash
  # Coolify-Logs anzeigen
  docker logs coolify-app-1
  ```
- **Häufige Ursachen**:
  - Falsche `DATABASE_URL` (PostgreSQL nicht erreichbar).
  - Fehlende `SECRET_KEY`.

### Fehler: "502 Bad Gateway"
- **Lösung**: Healthcheck prüfen:
  ```bash
  # App-Healthcheck manuell testen
  curl http://localhost:5000/health
  ```
- **Erwartet**: `{"status": "healthy"}`

### Fehler: "Permission denied" (Datenbank)
- **Lösung**: PostgreSQL-Berechtigungen prüfen:
  ```bash
  # PostgreSQL-Container betreten
  docker exec -it coolify-postgres-1 psql -U stark -d stark
  ```
  ```sql
  -- Berechtigungen prüfen
  \du
  ```

### Fehler: "WeasyPrint fehlgeschlagen"
- **Lösung**: Systempakete im Container installieren (bereits in `Dockerfile` enthalten).