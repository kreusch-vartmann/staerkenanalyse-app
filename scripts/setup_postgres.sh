#!/bin/bash
# scripts/setup_postgres.sh

# PostgreSQL 16 installieren (falls nicht vorhanden)
if ! command -v psql &> /dev/null; then
    echo "📦 PostgreSQL 16 installieren..."
    sudo apt update && sudo apt install -y postgresql-16
fi

# Datenbank und Benutzer erstellen
echo "🛠️  PostgreSQL-Datenbank einrichten..."
sudo -u postgres psql -c "CREATE USER stark WITH PASSWORD 'stark';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE stark OWNER stark;" 2>/dev/null || true
sudo -u postgres psql -d stark -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" 2>/dev/null || true

echo "✅ PostgreSQL bereit: postgresql://stark:stark@localhost:5432/stark"