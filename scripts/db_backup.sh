#!/bin/bash
# scripts/db_backup.sh
#
# Automatisiertes Backup-Skript für PostgreSQL-Datenbank.
# Erstellt komprimierte Backups und verwaltet die letzten 30 Backups.

# Konfiguration
DB_USER="stark"
DB_NAME="stark"
BACKUP_DIR="/var/backups/app"
MAX_BACKUPS=30
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

# Backup-Verzeichnis erstellen (falls nicht vorhanden)
mkdir -p "${BACKUP_DIR}"

# Backup erstellen
echo "🔄 Erstelle Backup von Datenbank ${DB_NAME}..."
if pg_dump -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${BACKUP_FILE}"; then
    echo "✅ Backup erfolgreich erstellt: ${BACKUP_FILE}"
else
    echo "❌ Fehler beim Erstellen des Backups!" >&2
    rm -f "${BACKUP_FILE}"
    exit 1
fi

# Alte Backups löschen (mehr als MAX_BACKUPS)
echo "🗑️  Lösche alte Backups (mehr als ${MAX_BACKUPS})..."
(cd "${BACKUP_DIR}" && ls -t | grep "${DB_NAME}_.*\.sql\.gz" | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f)

echo "📁 Aktuelle Backups in ${BACKUP_DIR}:"
ls -lh "${BACKUP_DIR}" | grep "${DB_NAME}_.*\.sql\.gz" | head -n 5