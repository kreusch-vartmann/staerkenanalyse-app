#!/bin/sh
set -e

: "${DATABASE_URL:?DATABASE_URL muss gesetzt sein}"
: "${SECRET_KEY:?SECRET_KEY muss gesetzt sein}"

export SKIP_DB_VALIDATION=1  # database_validator ist SQLite-only

# Warte auf PostgreSQL
until pg_isready -h "$(echo "$DATABASE_URL" | cut -d'@' -f2 | cut -d':' -f1)" -p "$(echo "$DATABASE_URL" | cut -d':' -f4 | cut -d'/' -f1)" -U "$(echo "$DATABASE_URL" | cut -d':' -f2 | cut -d'/' -f3)"; do
  echo "Warte auf PostgreSQL..."
  sleep 2
done

# Datenbank migrieren
flask db upgrade

exec "$@"