#!/bin/bash
# Quick-Test-Script für lokale Entwicklung mit ISOLATIONS-GUARDS
# Usage: ./run_tests.sh [options]
#
# 🛡️ WICHTIG: Dieses Script erzwingt Test-DB-Isolation!
# Tests laufen IMMER mit temporärer Datenbank, nie mit Production-DB.

set -e  # Exit on error

# Farben für Output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛡️  Stärkenanalyse-App Test-Suite (mit DB-Isolation)${NC}\n"

# ============================================================================
# 🛡️ SAFETY LAYER 1: Pre-Test Environment Validation
# ============================================================================

# Prüfe ob venv aktiviert ist
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${YELLOW}⚠️  Virtual Environment nicht aktiviert!${NC}"
    echo -e "Aktiviere mit: ${GREEN}source venv/bin/activate${NC}\n"
    exit 1
fi

# Prüfe ob Test-Dependencies installiert sind
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${RED}❌ pytest nicht installiert!${NC}"
    echo -e "Installiere Dependencies: ${GREEN}pip install -r requirements-test.txt${NC}\n"
    exit 1
fi

# 🛡️ Prüfe dass Production-DB NICHT verwendet wird
echo -e "${BLUE}🛡️ Validiere Test-Isolation...${NC}"
DB_URL=$(grep "DATABASE_URL" .env 2>/dev/null || echo "")
if [[ -z "$DB_URL" ]]; then
    echo -e "${RED}❌ .env nicht gefunden oder DATABASE_URL nicht gesetzt!${NC}"
    echo -e "   → Erstelle .env mit: ${GREEN}cp .env.example .env${NC}"
    exit 1
fi

# Warnung wenn Production-DB in .env konfiguriert ist
if [[ "$DB_URL" == *"instance/database.db"* ]]; then
    echo -e "${YELLOW}⚠️  Warnung: Production-DB in .env konfiguriert${NC}"
    echo -e "   → Tests nutzen TROTZDEM isolierte Datenbank (via conftest.py)"
    echo -e "   → Production-DB wird NICHT modifiziert\n"
fi

echo -e "${GREEN}✅ Environment-Checks bestanden\n${NC}"

# ============================================================================
# 🛡️ SAFETY LAYER 2: Database State Verification
# ============================================================================

# Prüfe dass Production-DB vor Tests existiert (als Backup-Punkt)
PROD_DB="instance/database.db"
if [[ ! -f "$PROD_DB" ]]; then
    echo -e "${YELLOW}⚠️  Warnung: Production-DB existiert nicht ($PROD_DB)${NC}"
    echo -e "   → Das ist OK, wenn Tests zum ersten Mal laufen${NC}\n"
fi

# Merke Production-DB Hash VOR Tests (zum Vergleich nach Tests)
PROD_DB_HASH_BEFORE=""
if [[ -f "$PROD_DB" ]]; then
    PROD_DB_HASH_BEFORE=$(md5sum "$PROD_DB" | awk '{print $1}')
    echo -e "${BLUE}📋 Production-DB Hash (VOR Tests): ${PROD_DB_HASH_BEFORE:0:8}...${NC}\n"
fi

# Parse Optionen
TEST_TYPE=${1:-all}

case $TEST_TYPE in
    unit)
        echo -e "${YELLOW}▶️  Running Unit Tests...${NC}\n"
        pytest tests/unit/ -v --tb=short
        ;;
    integration)
        echo -e "${YELLOW}▶️  Running Integration Tests...${NC}\n"
        pytest tests/integration/ -v --tb=short
        ;;
    fast)
        echo -e "${YELLOW}▶️  Running Fast Tests (no slow/API)...${NC}\n"
        pytest -m "not slow and not requires_api" -v --tb=short
        ;;
    coverage)
        echo -e "${YELLOW}▶️  Running Tests with Coverage Report...${NC}\n"
        pytest --cov=. --cov-report=html --cov-report=term -v
        echo -e "\n${GREEN}✅ Coverage-Report erstellt: ${BLUE}htmlcov/index.html${NC}"
        ;;
    rbac)
        echo -e "${YELLOW}▶️  Running RBAC Permission Tests...${NC}\n"
        pytest tests/integration/test_rbac_permissions.py -v --tb=short
        ;;
    *)
        echo -e "${YELLOW}▶️  Running ALL Tests...${NC}\n"
        pytest tests/ -v --tb=short
        ;;
esac

# 🛡️ SAFETY LAYER 3: Post-Test Database Integrity Check
# ============================================================================
echo -e "\n${BLUE}🛡️ Verifiziere dass Production-DB NICHT modifiziert wurde...${NC}"

if [[ -n "$PROD_DB_HASH_BEFORE" && -f "$PROD_DB" ]]; then
    PROD_DB_HASH_AFTER=$(md5sum "$PROD_DB" | awk '{print $1}')
    if [[ "$PROD_DB_HASH_BEFORE" == "$PROD_DB_HASH_AFTER" ]]; then
        echo -e "${GREEN}✅ Production-DB intakt (Hash: ${PROD_DB_HASH_AFTER:0:8}...)${NC}"
    else
        echo -e "${RED}❌ FEHLER: Production-DB wurde modifiziert!${NC}"
        echo -e "   Hash VOR Tests: $PROD_DB_HASH_BEFORE"
        echo -e "   Hash NACH Tests: $PROD_DB_HASH_AFTER"
        echo -e "   Dies sollte NICHT passieren - conftest.py Isolation fehlgeschlagen!"
        exit 1
    fi
elif [[ ! -f "$PROD_DB" ]]; then
    echo -e "${GREEN}✅ Keine Production-DB vorhanden (tests laufen mit Isolation)${NC}"
fi

echo -e "\n${GREEN}✅ Tests abgeschlossen - DB-Isolation validiert!${NC}"
    quick)
        echo -e "${YELLOW}▶️  Quick Test (parallel, no output)...${NC}\n"
        pytest -n auto -q
        ;;
    failed)
        echo -e "${YELLOW}▶️  Re-running Failed Tests...${NC}\n"
        pytest --lf -v
        ;;
    debug)
        echo -e "${YELLOW}▶️  Running Tests in Debug Mode...${NC}\n"
        pytest -vv --tb=long -s
        ;;
    all)
        echo -e "${YELLOW}▶️  Running Full Test Suite...${NC}\n"
        pytest -v
        ;;
    *)
        echo -e "${RED}❌ Unbekannte Option: $TEST_TYPE${NC}\n"
        echo "Usage: ./run_tests.sh [unit|integration|fast|coverage|quick|failed|debug|all]"
        echo ""
        echo "Optionen:"
        echo "  unit         - Nur Unit-Tests"
        echo "  integration  - Nur Integration-Tests"
        echo "  fast         - Nur schnelle Tests (keine slow/API)"
        echo "  coverage     - Mit Coverage-Report"
        echo "  quick        - Parallel ohne Output"
        echo "  failed       - Nur fehlgeschlagene Tests"
        echo "  debug        - Verbose Debug-Modus"
        echo "  all          - Alle Tests (Standard)"
        exit 1
        ;;
esac

# Exit-Code ausgeben
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✅ Alle Tests erfolgreich!${NC}"
else
    echo -e "\n${RED}❌ Tests fehlgeschlagen! Exit Code: $EXIT_CODE${NC}"
fi

exit $EXIT_CODE
