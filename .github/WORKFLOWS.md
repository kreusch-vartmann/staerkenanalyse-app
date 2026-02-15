# 🔄 GitHub Actions - Workflow-Dokumentation

**Zuletzt aktualisiert**: 15. Februar 2026

---

## 📊 Workflow-Übersicht

| Workflow       | Trigger                | Status        | Zweck                                       |
| -------------- | ---------------------- | ------------- | ------------------------------------------- |
| **tests.yml** | Push/PR (Main)        | ✅ AKTIV      | Unit + Integration Tests mit Coverage       |
| **ci-quality.yml** | Push/PR (Main)    | ✅ AKTIV      | Linting (Black, Flake8, Pylint) + Security  |
| **context-generator.yml** | Täglich 3 Uhr UTC | ✅ AKTIV | Auto-generiert CONTEXT.md                  |
| **docs-updater.yml** | Manuell (workflow_dispatch) | ✅ AKTIV | Sync requirements.txt + README Stats   |
| **ai-code-review.yml** | PR opens/updates | ⚠️ CONDITIONAL | PR-Reviews mit Mistral (nur mit Secret) |
| **run-tests.yml** | KEINE              | ❌ DISABLED    | Ersetzt durch tests.yml                     |

---

## 🚀 Hauptarbeitsflows

### 1️⃣ tests.yml - Automatische Tests

**Trigger**:

- Push auf `main`, `develop`, `feature/*` Branches
- Pull Requests gegen `main`, `develop`

**Was wird getestet**:

1. ✅ Checkout & Python 3.12 Setup
2. ✅ System-Dependencies installieren (Cairo für WeasyPrint)
3. ✅ Unit Tests (`tests/unit/`)
4. ✅ Integration Tests (`tests/integration/`)
5. ✅ Coverage Report (Ziel: 40%+)

**Fehler-Behebung** (15.02.2026):

- ✅ Doppelte `run-tests.yml` entfernt (nur `tests.yml` aktiv)
- ✅ `init_test_db.py` Referenz durch inline Python-Init ersetzt
- ✅ System-Dependencies für WeasyPrint added
- ✅ FLASK_ENV + DATABASE_URL Env-Vars gesetzt

### 2️⃣ ci-quality.yml - Code Quality Checks

**Was wird geprüft**:

- Black (Code Formatting) - Version 24.1.1 (stabil, nicht 25.9.0)
- isort (Import Sorting)
- Flake8 (PEP8 Style)
- Pylint (Deep Analysis)
- Bandit (Security Vulnerabilities)
- pip-audit (Dependency Security)
- Radon (Cyclomatic Complexity)

**Status**: `continue-on-error: true` → Warnungen brechen nicht den Build

### 3️⃣ context-generator.yml - Auto-Documentation

**Trigger**:

- Täglich um 3:00 UTC (Cron: `0 3 * * *`)
- Manuell via `workflow_dispatch`

**Generiert automatisch**:

- `CONTEXT.md` - KI-Agent-optimierte Kontext-Datei
- `PROJECT_OVERVIEW.md` - Projekt-Überblick

**Erstellt PRs** für manuelle Review (nicht Auto-Merge!)

### 4️⃣ docs-updater.yml - Dokumentation Sync

**Trigger**: Manuell (`workflow_dispatch`)

**Führt aus**:

1. Requirements-Synchronisation: `pip freeze` vs `requirements.txt`
2. README.md Statistik-Update (Python-Dateien, Templates, etc.)

**Erstellt PRs** für Review + Merge

### 5️⃣ ai-code-review.yml - Mistral PR Reviews

**Trigger**: PR opened/updates (Main-Branch) mit Python-Änderungen

**Status**: 🔧 CONDITIONAL

- ✅ Läuft NUR wenn `MISTRAL_API_KEY` Secret gesetzt ist
- ⚠️ Überspringt automatisch wenn Secret fehlt (kein Fehler)

**Was wird gemacht**:

- Liest geänderte Python-Dateien
- Sendet zu Mistral API zur KI-Code-Review
- Schreibt Review-Kommentare zur PR

**Setup erforderlich**:

```bash
GitHub Settings → Secrets → MISTRAL_API_KEY = "sk-..."
```

---

## 🔧 Fehlerbehebung und Fixes (15.02.2026)

### Problem 1: Doppelte Test-Workflows

**Symptom**: Beide `tests.yml` und `run-tests.yml` laufen parallel
**Ursache**: Redundante Konfigurationen
**Lösung**: `run-tests.yml` auf `on: {}` gesetzt (disabled)

### Problem 2: Black Version Inkompatibilität

**Symptom**: CI Fehler mit `black==25.9.0`
**Ursache**: Zu neue Version mit Breaking Changes
**Lösung**: Downgrade auf `black==24.1.1` (stabil)

### Problem 3: Fehlende init_test_db.py

**Symptom**: `run-tests.yml` bricht bei `scripts/init_test_db.py`
**Ursache**: Script existiert nicht
**Lösung**: Inline Python-DB-Init in `tests.yml`

### Problem 4: MISTRAL_API_KEY Secret nicht gesetzt

**Symptom**: `ai-code-review.yml` schlägt fehl
**Ursache**: Secret nicht in GitHub konfiguriert
**Lösung**: Conditional Check `&& secrets.MISTRAL_API_KEY != ''` added

---

## 🛠️ Workflow-Validierung

### Lokal Workflows testen

```bash
pip install pyyaml
python .github/scripts/validate_workflows.py
```

**Output**: ✅ Alle Workflows gültig!

---

## 📋 Checkliste für zukünftige Workflows

Beim Hinzufügen neuer Workflows:

- [ ] `on` Trigger definiert (nicht leer)
- [ ] `runs-on: ubuntu-latest` oder spezifische OS
- [ ] Python 3.12 oder kompatible Version
- [ ] Dependencies in `requirements.txt` gelistet
- [ ] System-Packages (z.B. libcairo2) documented
- [ ] Env-Vars gesetzt (FLASK_ENV, DATABASE_URL, SECRET_KEY)
- [ ] `continue-on-error: true` für non-blocking Jobs
- [ ] Secrets korrekt referenziert (z.B. `${{ secrets.API_KEY }}`)
- [ ] Artifacts geuploadet falls benchmark/reports generiert
- [ ] Dokumentation in diesem README updated

---

## 🚨 Bekannte Begrenzungen

1. **Mistral API**: Nur verfügbar wenn Secret konfiguriert
2. **Context Generator**: Täglich 3 Uhr UTC (könnte bei Overnight-Changes verzögert sein)
3. **WeasyPrint**: Braucht system libraries (libcairo2, libpango1.0) → nur ubuntu-latest
4. **Coverage Threshold**: Aktuell 40% (zu niedrig, sollte auf 60%+ erhöht werden)

---

## 📞 Support

Für Workflow-Probleme:

1. GitHub Actions Tab → Workflow → Klick auf Failed Run
2. Logs lesen (Step-by-Step Fehler)
3. Siehe Fehler-Behebung oben
4. Oder: `python .github/scripts/validate_workflows.py` lokal ausführen

