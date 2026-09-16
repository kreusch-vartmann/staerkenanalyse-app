#!/bin/bash
# scripts/safe_migrate.sh
#
# Sichere Datenbank-Migration mit Pre-Backup und Fehlerbehandlung.
# Führt ein Backup der aktuellen DB durch, bevor die Migration gestartet wird.
# Bricht bei Fehlern ab und verhindert Schema-Beschädigungen.

# Konfiguration
DB_USER="stark"
DB_NAME="stark"
BACKUP_DIR="/var/backups/app"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/pre_migrate_${DB_NAME}_${TIMESTAMP}.sql.gz"

# Backup-Verzeichnis prüfen und erstellen (falls nicht vorhanden)
mkdir -p "${BACKUP_DIR}"
if [ ! -d "${BACKUP_DIR}" ]; then
    echo "❌ Fehler: Backup-Verzeichnis ${BACKUP_DIR} konnte nicht erstellt werden!" >&2
    exit 1
fi

# Pre-Migration-Backup erstellen
echo "🔄 Erstelle Pre-Migration-Backup von Datenbank ${DB_NAME}..."
if ! pg_dump -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${BACKUP_FILE}"; then
    echo "❌ Fehler: Backup fehlgeschlagen! Migration wird abgebrochen." >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi

echo "✅ Backup erfolgreich erstellt: ${BACKUP_FILE}"

# Migration ausführen
echo "🔄 Führe Datenbank-Migration durch..."
if ! flask db upgrade; then
    echo "❌ Fehler: Migration fehlgeschlagen!" >&2
    echo "ℹ️  Ein Backup der Datenbank vor der Migration wurde erstellt:"
    echo "    ${BACKUP_FILE}"
    echo "ℹ️  Sie können die Datenbank mit folgendem Befehl wiederherstellen:"
    echo "    gunzip < ${BACKUP_FILE} | psql -U ${DB_USER} -d ${DB_NAME}"
    exit 1
fi

echo "✅ Migration erfolgreich abgeschlossen!"