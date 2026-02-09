#!/bin/bash
# Quick-Test-Script für lokale Entwicklung
# Usage: ./run_tests.sh [options]

set -e  # Exit on error

# Farben für Output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Stärkenanalyse-App Test-Suite${NC}\n"

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

# Parse Optionen
TEST_TYPE=${1:-all}

case $TEST_TYPE in
    unit)
        echo -e "${YELLOW}▶️  Running Unit Tests...${NC}\n"
        pytest tests/unit/ -v
        ;;
    integration)
        echo -e "${YELLOW}▶️  Running Integration Tests...${NC}\n"
        pytest tests/integration/ -v
        ;;
    fast)
        echo -e "${YELLOW}▶️  Running Fast Tests (no slow/API)...${NC}\n"
        pytest -m "not slow and not requires_api" -v
        ;;
    coverage)
        echo -e "${YELLOW}▶️  Running Tests with Coverage Report...${NC}\n"
        pytest --cov=. --cov-report=html --cov-report=term -v
        echo -e "\n${GREEN}✅ Coverage-Report erstellt: ${BLUE}htmlcov/index.html${NC}"
        ;;
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
