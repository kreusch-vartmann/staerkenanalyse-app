# PostgreSQL Migration Guide

## 🚀 Schnellstart

### 1. PostgreSQL einrichten
Führe das Setup-Skript aus, um PostgreSQL 16 zu installieren und die Datenbank zu erstellen:

```bash
chmod +x scripts/setup_postgres.sh
sudo ./scripts/setup_postgres.sh
```

### 2. `.env` anpassen
Stelle sicher, dass `DATABASE_URL` auf PostgreSQL zeigt:

```ini
DATABASE_URL=postgresql://stark:stark@localhost:5432/stark
```

### 3. Daten migrieren
Führe das Migrationsskript aus:

```bash
python scripts/migrate_sqlite_to_postgresql.py
```

### 4. App starten
Starte die App mit PostgreSQL:

```bash
flask run --port 5001
```

## 🔄 Migration im Detail

### Tabellenreihenfolge
Das Skript migriert Tabellen in folgender Reihenfolge (Foreign Keys beachten):

```text
roles → permissions → role_permissions → users → groups → user_groups → ...
```

### Sequence-Resets
Auto-Increment-Sequences werden auf den höchsten Wert + 1 gesetzt.

### Identifier-Quoting
PostgreSQL-Keywords wie `order` und `type` werden automatisch gequotet.

### Fehlerbehandlung
Das Skript bricht bei Fehlern ab (Fail-Fast) und gibt eine klare Fehlermeldung aus.

## 🛠️ Troubleshooting

### Fehler: "password authentication failed"
- Stelle sicher, dass der Benutzer `stark` existiert:
  ```bash
  sudo -u postgres psql -c "\du"
  ```
- Falls nicht, erstelle ihn:
  ```bash
  sudo -u postgres psql -c "CREATE USER stark WITH PASSWORD 'stark';"
  ```

### Fehler: "Datenbank existiert nicht"
- Erstelle die Datenbank:
  ```bash
  sudo -u postgres psql -c "CREATE DATABASE stark OWNER stark;"
  ```

### Fehler: "uuid-ossp-Extension fehlt"
- Aktiviere die Extension:
  ```bash
  sudo -u postgres psql -d stark -c "CREATE EXTENSION \"uuid-ossp\";"
  ```

## 🚀 Coolify-spezifische Migration

### 1. PostgreSQL in Coolify einrichten
1. **Coolify-UI öffnen** → Projekt → `Add Service` → `PostgreSQL`.
2. **Konfiguration**:
   - **Image**: `postgres:16-alpine`
   - **Umgebungsvariablen**:
     ```ini
     POSTGRES_USER=stark
     POSTGRES_PASSWORD=stark
     POSTGRES_DB=stark
     ```
   - **Volumes**: `postgres_data:/var/lib/postgresql/data`
3. **Deployen**.

### 2. Daten migrieren
1. **SQLite-Backup erstellen** (lokal):
   ```bash
   flask backup-db
   ```
2. **Backup nach Coolify übertragen**:
   ```bash
   scp backups/database_*.db coolify-server:/tmp/
   ```
3. **Coolify-App-Container betreten**:
   ```bash
   docker exec -it coolify-app-1 bash
   ```
4. **Migration ausführen**:
   ```bash
   python scripts/migrate_sqlite_to_postgresql.py
   ```

### 3. App neustarten
- **Coolify-UI** → App → `Redeploy`.

---

## 🔄 Backup & Restore in Coolify
- **Backup erstellen**: `flask backup-db` (im App-Container).
- **Wiederherstellen**: `flask restore-db /backups/database_*.sql`.