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

# Standard-Prompt-Vorlagen synchronisieren (rein additiv: überspringt
# bereits vorhandene Prompts nach Name, ändert/löscht nie Bestehendes -
# daher sicher bei JEDEM Start. Verhindert, dass neue Standard-Prompts
# in einer laufenden Produktions-DB fehlen, nur weil der manuelle
# Terminal-Schritt nach einem Deploy vergessen wurde.)
flask load-default-prompts || echo "⚠️  load-default-prompts fehlgeschlagen (nicht kritisch, App startet trotzdem)"

# HINWEIS: seed_permissions.py wird bewusst NICHT automatisch ausgeführt -
# es überschreibt Rollen-Berechtigungen unbedingt neu und würde manuelle
# Anpassungen über die Admin-UI bei jedem Neustart zerstören. Einmalig
# manuell im Terminal ausführen (siehe Deployment-Doku).

exec "$@"