# PostgreSQL Backup & Wiederherstellung

## Backup-Skript (`scripts/db_backup.sh`)

### Manueller Aufruf
```bash
chmod +x scripts/db_backup.sh
sudo ./scripts/db_backup.sh
```

### Cronjob einrichten (tägliche Backups um 02:00 Uhr)
1. Öffne die Crontab:
   ```bash
   sudo crontab -e
   ```

2. Füge folgende Zeile hinzu:
   ```
   0 2 * * * /bin/bash /pfad/zum/repository/scripts/db_backup.sh >> /var/log/db_backup.log 2>&1
   ```

3. Stelle sicher, dass das Skript ausführbar ist:
   ```bash
   chmod +x /pfad/zum/repository/scripts/db_backup.sh
   ```

### Backup-Verzeichnis
Backups werden in `/var/backups/app` gespeichert und automatisch auf die letzten **30 Backups** begrenzt.

### Coolify-Task einrichten
1. Gehe in die Coolify-UI und navigiere zu **Tasks**.
2. Erstelle einen neuen Task:
   - **Name**: `db-backup`
   - **Befehl**: `/bin/bash /app/scripts/db_backup.sh`
   - **Zeitplan**: `0 2 * * *` (täglich um 02:00 Uhr)
   - **Arbeitsverzeichnis**: `/app`
   - **Benutzer**: `root` (oder ein Benutzer mit PostgreSQL-Zugriff)

---

## Wiederherstellung (manuell)
⚠️ **Wichtig**: Führe vor der Wiederherstellung ein manuelles Backup der aktuellen Datenbank durch!

### Aus einem Backup wiederherstellen
```bash
gunzip < /var/backups/app/stark_YYYYMMDD_HHMMSS.sql.gz | psql -U stark -d stark
```

### Coolify-Deployment
Stelle sicher, dass das Backup-Verzeichnis (`/var/backups/app`) in der `docker-compose.yml` als Volume eingebunden ist, damit Backups persistent bleiben:
```yaml
volumes:
  - /var/backups/app:/var/backups/app
```