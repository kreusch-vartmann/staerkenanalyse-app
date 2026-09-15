# PostgreSQL-Migration Testanleitung

## 🧪 Voraussetzungen
- **PostgreSQL 16** läuft lokal oder in Docker.
- **Testdatenbank** existiert:
  ```bash
  sudo -u postgres psql -c "CREATE DATABASE stark OWNER stark;"
  sudo -u postgres psql -d stark -c "CREATE EXTENSION \"uuid-ossp\";"
  ```

---

## 🚀 Migration testen

### 1. Testdatenbank erstellen (SQLite)
```bash
mkdir -p /tmp/staerkenanalyse_test
cd /tmp/staerkenanalyse_test
sqlite3 test.db <<EOF
CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT);
INSERT INTO test (data) VALUES ('testdata');
EOF
```

### 2. Migration ausführen
```bash
cd /home/timok/kDrive/Dokumente/staerkenanalyse-app
DATABASE_URL="postgresql://stark:stark@localhost:5432/stark" \
SQLITE_DATABASE_URL="sqlite:////tmp/staerkenanalyse_test/test.db" \
python scripts/migrate_sqlite_to_postgresql.py
```

**Erwartete Ausgabe**:
```text
🔄 Migration von SQLite zu PostgreSQL
   SQLite: /tmp/staerkenanalyse_test/test.db
   PostgreSQL: postgresql://stark:stark@localhost:5432/stark
✅ test: 1 Zeilen migriert
🎉 Migration erfolgreich abgeschlossen!
```

### 3. Ergebnis prüfen
```bash
sudo -u postgres psql -d stark -c "SELECT * FROM test;"
```

**Erwartet**:
```text
 id |   data
----+----------
  1 | testdata
```

---

## 🛠️ Troubleshooting

### Fehler: "connection to server failed"
- **Lösung**: PostgreSQL starten:
  ```bash
  sudo systemctl start postgresql
  ```

### Fehler: "password authentication failed"
- **Lösung**: Passwort prüfen:
  ```bash
  sudo -u postgres psql -c "ALTER USER stark WITH PASSWORD 'stark';"
  ```

### Fehler: "Tabelle nicht gefunden"
- **Lösung**: Migration erneut ausführen (Tabellenreihenfolge beachten).