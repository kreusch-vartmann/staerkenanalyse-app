#!/bin/bash
# run_dev.sh - Flask-App mit venv Python starten

set -e

cd "$(dirname "$0")"

# Aktiviere venv
source venv/bin/activate

# Starte Flask
echo "🚀 Flask starten mit venv Python..."
echo "Python: $(which python)"
echo "Flask: $(which flask)"
echo ""

flask run --host=127.0.0.1 --port=5002
