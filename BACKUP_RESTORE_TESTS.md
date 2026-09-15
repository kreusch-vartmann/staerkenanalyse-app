# Backup & Restore Tests

## 🧪 Testumgebung

### Voraussetzungen
- **PostgreSQL 16** (lokal oder Docker)
- **SQLite** (für Fallback-Tests)
- **Testdaten** (1 Gruppe, 2 Teilnehmer, 2 Selbsteinschätzungen)

### Vorbereitung
1. **PostgreSQL einrichten** (falls nicht geschehen):
   ```bash
   sudo ./scripts/setup_postgres.sh
   ```
2. **`.env` anpassen** (PostgreSQL oder SQLite):
   ```ini
   # PostgreSQL
   DATABASE_URL=postgresql://stark:stark@localhost:5432/stark
   
   # SQLite (Fallback)
   # DATABASE_URL=sqlite:////home/timok/kDrive/Dokumente/staerkenanalyse-app/instance/database.db
   ```

---

## 🔄 Backup-Tests

### 1. Manuelles Backup
```bash
flask backup-db
```
**Erwartetes Ergebnis**:
- Backup-Datei in `backups/database_*.sql` (PostgreSQL) oder `backups/database_*.db` (SQLite).
- Ausgabe: `✅ Backup erstellt: database_YYYYMMDD_HHMMSS_reason.sql (XX.X KB)`

### 2. Startup-Backup
```bash
flask run --port 5001
```
**Erwartetes Ergebnis**:
- Backup bei App-Start (nur wenn sich die DB geändert hat).
- Ausgabe: `✅ Backup erstellt: database_YYYYMMDD_HHMMSS_startup.sql (XX.X KB)`

### 3. Automatische Bereinigung
```bash
# Mehr als MAX_BACKUPS (50) Backups erstellen
for i in {1..55}; do touch backups/database_$(date +%Y%m%d_%H%M%S)_test$i.sql; done

flask backup-db
```
**Erwartetes Ergebnis**:
- Nur die neuesten 50 Backups bleiben erhalten.
- Ausgabe: `✅ Alte Backups bereinigt (50/55 behalten)`

---

## ♻️ Restore-Tests

### 1. Restore auswählen
```bash
flask restore-db
```
**Erwartetes Ergebnis**:
- Liste verfügbarer Backups.
- Auswahlmenü: `[1] database_YYYYMMDD_HHMMSS_reason.sql (XX.X KB, YYYY-MM-DD HH:MM:SS)`

### 2. Restore durchführen
```bash
flask restore-db database_YYYYMMDD_HHMMSS_reason.sql
```
**Erwartetes Ergebnis**:
- Sicherheitsbackup vor dem Restore.
- Bestätigungsdialog: `ACHTUNG! Die aktuelle Datenbank wird überschrieben mit: database_YYYYMMDD_HHMMSS_reason.sql`
- Erfolgreiche Wiederherstellung:
  - **PostgreSQL**: `✅ PostgreSQL-Datenbank wiederhergestellt aus: database_YYYYMMDD_HHMMSS_reason.sql`
  - **SQLite**: `✅ SQLite-Datenbank wiederhergestellt aus: database_YYYYMMDD_HHMMSS_reason.db`

### 3. Datenintegrität prüfen
```bash
flask shell
```
**Prüfung (Python-Shell)**:
```python
from app import db
from models import Participant

# Anzahl Teilnehmer prüfen
print(f"Teilnehmer: {Participant.query.count()}")  # Erwartet: 2

# Testdaten prüfen
p = Participant.query.first()
print(f"Name: {p.first_name} {p.last_name}")  # Erwartet: "Laura Becker" oder "Marie Koch"
```

---

## 🛠️ Troubleshooting

### Fehler: "pg_dump/psql nicht gefunden"
- **Lösung**: PostgreSQL-Client-Tools installieren:
  ```bash
  sudo apt install postgresql-client-16
  ```

### Fehler: "Datenbank nicht gefunden"
- **Lösung**: Stelle sicher, dass die Datenbank existiert:
  ```bash
  sudo -u postgres psql -c "\l"  # Liste Datenbanken auf
  ```

### Fehler: "Permission denied"
- **Lösung**: Berechtigungen prüfen:
  ```bash
  sudo -u postgres psql -c "ALTER USER stark WITH PASSWORD 'stark';"