# Stärkenanalyse-App

[![Tests](https://github.com/kreusch-vartmann/staerkenanalyse-app/actions/workflows/tests.yml/badge.svg)](https://github.com/kreusch-vartmann/staerkenanalyse-app/actions/workflows/tests.yml)

**Version:** 1.3.1  
**Status:** Phase 3 Stabilisierung in Arbeit 🟡  
**Neue Features:** Security-Härtung, Auth/RBAC-Tests, Admin-Flow-Tests

Eine lokale Flask-Webanwendung zur Verwaltung von Gruppen und Teilnehmenden mit rollenbasierter Zugriffskontrolle und zur Durchführung von KI-gestützten Stärkenanalysen.

## Kurze Zusammenfassung
- Backend: Flask (Blueprint-basierte Struktur in `blueprints/`)
- Datenbank: SQLite (`database.db`, Schema in `schema.sql`)
- Templates: Jinja2 Vorlagen im Ordner `templates/`
- Statische Dateien: `static/`
- KI-Integration: optional über mehrere SDKs (Google Generative AI, Mistral, OpenAI, u. a.)

Wichtig: Einige KI-Bibliotheken sind optional und/oder haben schwerere Abhängigkeiten. Sie sind in `requirements.txt` gelistet, können aber Konflikte (z. B. `protobuf` Version) mit anderen Paketen aufweisen. Siehe Abschnitt "Troubleshooting / bekannte Probleme".

## Projektstruktur (wichtigste Dateien)

- `app.py` — App-Initialisierung und zentrale Routen; registriert Blueprints
- `models.py` — SQLAlchemy-Modelle (Group, Participant, Prompt, SelfAssessment)
- `extensions.py` — db, migrate Objekte (verhindert circular imports)
- `database.py` — Legacy-DB-Verbindung und Abfragemethoden (SQLite)
- `ki_services.py` — Hilfsfunktionen für KI-Aufrufe (Modelle sind optional)
- `utils.py` — Hilfsroutinen für Dateitypen, PDFs, DOCX usw.
- `blueprints/` — modulare Routengruppen (groups, participants, analysis, data_io, prompts, explanation_blocks)
- `templates/` — Jinja2 HTML-Vorlagen für UI
- `static/` — statische Assets
- `requirements.txt` — vollständige Liste der Python-Abhängigkeiten

## Voraussetzungen

- Python 3.11+ (in der Entwicklung wurde Python 3.11 / 3.13 verwendet)
- `pip`
- Optional: Systempakete für `weasyprint` und ähnliche Bibliotheken (z. B. libpango, libcairo). Wenn Sie keine PDF-Generierung benötigen, können Sie `weasyprint` weglassen.

Empfohlene Vorgehensweise: Arbeiten Sie in einer virtuellen Umgebung (`venv`).

## Schnellstart (empfohlen)

1. Repository klonen und in das Verzeichnis wechseln

```bash
git clone <repo-url>
cd staerkenanalyse-app
```

2. Virtuelle Umgebung erstellen und aktivieren

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

Hinweis: Bei Problemen mit Abhängigkeitskonflikten (siehe unten) lesen Sie bitte den Abschnitt "Troubleshooting".

4. Datenbank initialisieren

Das Projekt erwartet eine SQLite-Datenbank (`database.db`). Falls ein CLI-Kommando `flask init-db` nicht vorhanden ist, können Sie das SQL-Skript `schema.sql` verwenden:

```bash
sqlite3 database.db < schema.sql
```

Prüfen Sie anschließend `database.db` im Projektverzeichnis.

5. Anwendung starten

Sie können die App direkt starten:

```bash
# Standard (Port 5001 in app.py)
python app.py

# Alternativ mit Flask-CLI
export FLASK_APP=app.py
flask run --port 5001
```

Wenn Port 5001 bereits belegt ist, starten Sie auf einem anderen Port:

```bash
python -m flask run --port 5002
```

Öffnen Sie dann http://localhost:5001 (oder 5002) im Browser.

## Konfiguration und Umgebungsvariablen

- `FLASK_ENV` bzw. `FLASK_DEBUG` (für Debug/Prod-Modus)
- KI-Provider: Je nach eingesetzten Services benötigen Sie API-Schlüssel (z. B. `OPENAI_API_KEY`, `GOOGLE_API_KEY` usw.). Diese werden in `ki_services.py` bzw. in den Blueprints genutzt — prüfen Sie dort die genaue Erkennung und Umgebungsvariablen.

## Troubleshooting / bekannte Probleme

- Port belegt
  - Fehlermeldung: `Address already in use` → starten Sie die App auf einem anderen Port (siehe Schnellstart).

- Fehlende KI-Bibliotheken
  - Laufzeitwarnungen wie `WARNUNG: google-generativeai nicht installiert` oder `mistralai nicht installiert` bedeuten, dass die entsprechenden SDKs nicht in der Umgebung verfügbar sind. Diese Bibliotheken sind optional — die App fängt fehlende SDKs an vielen Stellen ab und deaktiviert nur die betreffenden Features.

- protobuf / Abhängigkeitskonflikte
  - `google-generativeai` und andere Google-/gRPC-Pakete hängen von `protobuf` ab. Aktuell steht in `requirements.txt` `protobuf==5.29.5`, was zu Konflikten mit anderen Paketen (z. B. ältere Streamlit-Versionen) führen kann.
  - Wenn Sie auf Konflikte stoßen, zwei Optionen:
    1. Versuchen Sie, `protobuf` auf eine kompatible 4.x-Version zu fixieren, z. B. `protobuf==4.23.4`, und `pip install -r requirements.txt --force-reinstall` auszuführen. Testen Sie sorgfältig, weil einige Packages 5.x verlangen könnten.
    2. Entfernen Sie optional die problematischen KI-Pakete aus `requirements.txt` und installieren Sie nur die für Ihre Nutzung notwendigen Bibliotheken.

- System-abhängige Bibliotheken für PDF (WeasyPrint)
  - `weasyprint` benötigt unter Linux zusätzliche Systembibliotheken (libcairo, libpango, gdk-pixbuf). Wenn PDF-Generierung nicht benötigt wird, entfernen Sie `weasyprint` aus `requirements.txt` oder installieren Sie die Systemabhängigkeiten.

## Code-Hinweise / wichtige Stellen

- `blueprints/` enthält die modularen Routen. Schauen Sie in diese Dateien, wenn Sie Features erweitern möchten:
  - `blueprints/groups.py` — Gruppen anlegen/anzeigen
  - `blueprints/participants.py` — Teilnehmer CRUD, Dateneingabe & Selbsteinschätzung
  - `blueprints/analysis.py` — KI-Analyse, Fremdeinschätzung & Abschlussberichte
  - `blueprints/data_io.py` — Import/Export-Funktionen & Beobachtungsdaten
  - `blueprints/prompts.py` — Verwaltung von KI-Prompts
  - `blueprints/explanation_blocks.py` — Erklärungstexte für Abschlussberichte
  - `blueprints/reports.py` — **NEUE** Report-Konfiguration, Vorschau & PDF-Generierung
  - `blueprints/observation_tasks.py` — **NEU v1.1.0** Beobachtungsaufgaben-Verwaltung mit KI-Generierung
  - `blueprints/admin.py` — **NEU v1.1.0** Admin-Bereich mit KI-Gym Training

- `services/report_generator.py` — **NEUE** ReportGenerator-Klasse für HTML-Rendering und PDF-Export mit konfigurierbarem Sidebar-Layout
- `ai_gym.py` — **NEU v1.1.0** KI-Gym Service für Pattern-Extraktion und automatisches Prompt-Learning

## Neu in Version 1.3.1 ✅

### Stabilisierung & Tests
- **Auth/RBAC Test-Suite**: Login, Logout, Passwortwechsel, Gruppen-/Teilnehmerzugriff
- **Admin-Flow Tests**: User anlegen, editieren, deaktivieren, Reset, löschen
- **RBAC Edge-Cases**: Unzugewiesene Gruppen, fehlende Ressourcen, Observer ohne Gruppen

## Neu in Version 1.2.1 ✅

### Chat-Refinement Stabilisierung
- **Deterministische Sektionen**: Ausgabe wird auf die 4 Standard-Sektionen normalisiert
- **HTML-Cleanup**: Markdown-Artefakte (z. B. `**`) werden entfernt
- **Auto-Save + Reload**: Chat-Änderungen werden direkt gespeichert und korrekt geladen
- **Konsistente Darstellung**: Generierung und Chat liefern identische Struktur

## Neu in Version 1.2.0 🚀

### Assessment-Center Knowledge Base
- **Strukturierte Wissensbasis**: 12 Aufgabentypen, 10 Kompetenzdimensionen, 6 Zielgruppen
- **Zielgruppen-Differenzierung**: KI-Prompts variieren nach Zielgruppe (Schüler, Azubis, Führungskräfte, etc.)
- **Intelligente Prompt-Injection**: AC-Fachwissen wird automatisch in System-Prompts eingebettet

## Neu in Version 1.1.0 🚀

### KI-Gym Learning System 🧠
Automatisches Machine Learning-System, das aus manuellen Bearbeitungen lernt und KI-Prompts optimiert:

#### Features
- **Content-Edit-Tracking**: Automatische Erfassung aller manuellen Änderungen an KI-generierten Inhalten
- **Pattern-Extraktion**: Analyse von Edit-Metriken (Länge, Magnitude, Ähnlichkeit)
- **Automatische Rule-Generierung**: Erstellung von Prompt-Verbesserungsregeln basierend auf User-Edits
- **Confidence-Scoring**: Bewertung der Regeln nach Datenqualität
- **Training Dashboard**: Admin-UI zur Verwaltung und Aktivierung von gelernten Regeln

#### Status ✅
- ✅ `AIRawResponse` & `ContentEdit` Models für Tracking
- ✅ `LearnedPromptRule` Model für generierte Regeln
- ✅ `ai_gym.py` Service mit Pattern-Extraktion und Rule-Generierung
- ✅ Admin KI-Gym Dashboard (`/admin/ki-gym`)
- ✅ Automatische Integration von Task-Rules in Prompts
- ✅ Manuelle Integration von Report-Rules (mit Bestätigung)

### Beobachtungsaufgaben-Verwaltung 📋
Vollständige Task-Library mit KI-gestützter Generierung für Assessment-Center:

#### Features
- **KI-Task-Generierung**: Automatische Erstellung von AC-Aufgaben basierend auf Beobachtungsbereichen
- **Rich-Text-Editor**: Quill.js-basierter Editor mit HTML-Unterstützung
- **Chat-basierte Iterationen**: Verfeinern von Tasks durch Chat mit der KI
- **Versions-Management**: Vollständige Versionierung aller Task-Änderungen
- **Referenz-Aufgaben**: Hardcoded Best-Practice-Beispiele für KI-Training
- **KI-Modell-Auswahl**: Wählbare KI-Modelle (Mistral Large / Google Gemini) mit visuellem Modal

#### Status ✅
- ✅ `Task` & `TaskVersion` Models mit circular dependency handling
- ✅ `observation_tasks` Blueprint mit Create/Edit/Generate Workflow
- ✅ KI-Generierung mit Context-Data und Example-Tasks
- ✅ Quill.js Editor mit Chat-Seitenleiste
- ✅ Task-Library mit Filterung und Pagination
- ✅ KI-Modell-Auswahl-Modal mit Mistral/Gemini Logos

### Weitere Verbesserungen 🔧
- **Report-Metadaten**: Anzeige von Erstellungsdatum, verwendetem KI-Modell und Edit-Status in Berichten
- **Group-Tasks API-Fix**: Korrigierte JSON-Response-Struktur für Aufgaben-Zuordnung zu Gruppen
- **Batch-Analysen-Stabilität**: Links öffnen in neuen Tabs, verhindert Unterbrechung der Batch-Verarbeitung
- **Modal-System Fixes**: Verbessertes CSS z-index Handling und Callback-Execution Order

## Report-Generierung & Konfiguration ✅

Das System unterstützt flexible Report-Generierung mit HTML-Vorschau und PDF-Export:

### Features
- **Konfigurierbare Report-Module**: Deckblatt, Selbsteinschätzung, Fremdeinschätzung, Abschlussblatt, Hinweisblatt
- **Report-Konfiguration pro Gruppe**: Template-Auswahl, Logo-Upload, Modul-Aktivierung
- **Sidebar-Layout**: Zwei Modi — "full" (mit Metadaten, für Standalone-PDFs) und "minimal" (nur Design, für Gesamtbericht)
- **HTML-Vorschau mit iframe**: Verhindert CSS-Leakage zwischen App und Report
- **PDF-Export**: WeasyPrint-basiert mit konfigurierbaren Designs (Farben, Schriften, Logos)
- **Unterschriften-Verwaltung**: Global verwaltete JPG-Bilder für Leitung FE und Leitung SE
- **Radardiagramme**: Automatisch generierte matplotlib-Charts für Social & Verbal Competencies

### Status ✅ Vollständig
- ✅ `ReportGenerator` Service vollständig implementiert
- ✅ Report-Konfiguration UI mit Tailwind CSS Accordions
- ✅ Sidebar-Component mit Auto-Seitenzählung
- ✅ Standalone-Routes für SE- und FE-PDF
- ✅ Unterschriften-Upload & Verwaltung im Abschlussblatt-Bereich
- ✅ PDF-Druck-Buttons in Verwaltungs-Templates
- ✅ Form-Validierung & CSRF-Schutz aktiv

### Routen (Reports-Blueprint)

```
GET/POST  /reports/<group_id>/configure         → Report-Konfiguration
GET       /reports/<group_id>/preview/<pid>     → HTML-Vorschau (Gesamt)
GET       /reports/<group_id>/generate-pdf/<pid> → PDF-Download (Gesamt)
GET       /reports/standalone/self-assessment/<pid>/pdf  → SE-PDF
GET       /reports/standalone/foreign-assessment/<pid>/pdf → FE-PDF
GET       /reports/standalone/self-assessment/<pid>/preview     → SE-Vorschau
GET       /reports/standalone/foreign-assessment/<pid>/preview  → FE-Vorschau
POST      /reports/signatures/upload            → Unterschrift hochladen
POST      /reports/signatures/delete/<sig_id>   → Unterschrift löschen
```

### Neue Datenbank-Modelle
- `ReportTemplate` — Design-Vorlagen (Farben, Schriften, Layout)
- `ReportConfiguration` — Gruppe-spezifische Einstellungen (aktive Module, Logos, Metadaten)
- `CompanyLogo` — Zentral verwaltetes Firmenlogo
- `ClientLogo` — Pro-Gruppe Kunden-Logos
- `SignatureImage` — Unterschriftensbilder (Leitung FE/SE)

`database.py` enthält helper-Funktionen zum Zugriff und zur Paginierung. Falls Sie Probleme mit Such- oder Pagination-Features haben, beginnen Sie hier.

## Backup-System (NEU in v0.4.0) 🔒

Automatisches Backup-System für die SQLite-Datenbank mit Prompts-Export:

### Features
- **Automatische Backups**: Beim App-Start werden automatisch Backups erstellt
- **Manuelle Backups**: Via Flask-CLI oder Python-Skript
- **Retention-Management**: Alte Backups werden automatisch bereinigt (max. 50 Backups)
- **Prompts-Export**: Zusätzliche JSON-Sicherung aller Prompts mit Metadaten
- **Verifizierung**: Größencheck nach jedem Backup

### Usage

```bash
# Manuelles Backup
python backup_database.py

# Als Flask-Command
flask backup-db
flask backup-db --keep 30    # Nur letzte 30 Backups behalten

# Prompts exportieren
flask export-prompts
```

### Backup-Struktur

```
backups/
├── database_20260208_143022_startup.db        # Timestamp + Grund
├── database_20260208_150033_manual.db
└── prompts_export/
    ├── prompt_1_staerkenanalyse.json          # Einzelne Prompt-Dateien
    ├── prompt_2_fremdeinschaetzung.json
    └── all_prompts_20260208_143055.json       # Alle Prompts kombiniert
```

### Integration

Backup-System ist direkt in `app.py` integriert:
```python
from backup_database import create_backup

# Beim App-Start
with app.app_context():
    create_backup(reason="startup")
```

## Entwickeln & Tests

- Verwenden Sie `python -m venv .venv` und `pip install -r requirements.txt` wie oben beschrieben.
- Linter/Formatters: `black`, `flake8`, `pylint` sind in `requirements.txt` gelistet. Sie können `pre-commit`-Hooks hinzufügen, falls gewünscht.

### Automatisierte Tests (NEU in v0.3.0)

Das Projekt enthält nun eine **umfassende Test-Suite** mit 170 Tests:

#### Tests ausführen

```bash
# Alle Tests laufen
pytest tests/ -v

# Tests mit Coverage-Bericht
coverage run -m pytest tests/ -v
coverage report --skip-empty
coverage html  # Generiert HTML-Report in htmlcov/

# Nur Unit-Tests
pytest tests/unit/ -v

# Nur Integration-Tests
pytest tests/integration/ -v

# Specific Test File
pytest tests/unit/test_models.py -v
```

#### Test-Struktur

```
tests/
├── unit/                          # Unit Tests für einzelne Module
│   ├── test_models.py            # SQLAlchemy Models & Validierungen
│   ├── test_ki_services.py       # KI-API Integration
│   └── test_utils.py             # Hilfsfunktionen
└── integration/                   # Integration Tests für Blueprints
    ├── test_groups_blueprint.py
    ├── test_participants_blueprint.py
    ├── test_analysis_blueprint.py
    ├── test_data_io_blueprint.py
    ├── test_prompts_blueprint.py
    ├── test_explanation_blocks_blueprint.py
    ├── test_reports_blueprint.py
    └── test_workflows.py
```

#### Coverage-Bericht (v0.3.0)

- **Gesamt-Coverage**: 46.90%
- **Best**: models.py (100%), groups.py (100%), extensions.py (100%)
- **Report**: `htmlcov/index.html` nach `coverage html`

#### Test-Features

- ✅ **170 Tests** gesammelt
- ✅ **100% Coverage** für Core-Module (models, extensions, services)
- ✅ **Fixtures** für Testdaten-Generierung
- ✅ **Mocking** für externe APIs (Mistral, Google)
- ✅ **DB-Isolation** mit in-memory SQLite für Tests

## Nächste Schritte / Empfehlungen

1. Entfernen oder optionalisieren Sie große KI-Abhängigkeiten in `requirements.txt`, wenn Sie die App lokal mit eingeschränkten Features betreiben möchten.
2. Falls Sie PDF-Generierung benötigen, installieren Sie die Systempakete für `weasyprint` (distribution-spezifisch).
3. Fügen Sie ein CLI-Kommando `flask init-db` (oder ein kleines `manage.py`) hinzu, das `schema.sql` benutzt, damit die DB-Initialisierung benutzerfreundlicher wird.

## GitHub Actions & CI/CD

Dieses Projekt nutzt GitHub Actions für automatische Code-Qualitätsprüfungen, Tests und Dokumentations-Updates:

### Workflows

1. **Tests & Coverage** (`.github/workflows/tests.yml`) - ⭐ **NEU in v0.3.0**
   - Läuft bei jedem Push auf `main` oder `feature/*` Branches
  - Führt komplette Test-Suite aus (170 Tests)
   - Generiert Coverage-Report (HTMLCov + Codecov)
   - Prüft Coverage-Schwellwerte (≥ 40%)
   - Uploaded Coverage Artifacts für Review

2. **CI - Code Quality** (`.github/workflows/ci-quality.yml`)
   - Läuft bei jedem Push auf `main` oder `feature/*` Branches
   - Prüft Code-Formatierung mit `black`, `isort`, `flake8`, `pylint`
   - Security-Checks mit `bandit` und `pip-audit`
   - Code-Komplexitäts-Analyse mit `radon`

3. **Context Generator** (`.github/workflows/context-generator.yml`)
   - Erstellt automatisch `CONTEXT.md` und `PROJECT_OVERVIEW.md`
   - Analysiert Projektstruktur, Routen, Modelle
   - Erstellt PR mit aktualisierten Kontext-Dateien

3. **AI Code Review** (`.github/workflows/ai-code-review.yml`)
   - Läuft bei Pull Requests auf `main`
   - Nutzt Mistral AI für intelligente Code-Reviews
   - Postet Review-Kommentare direkt im PR

4. **Documentation Updater** (`.github/workflows/docs-updater.yml`)
   - Synchronisiert `requirements.txt` mit `pip freeze`
   - Aktualisiert Projekt-Statistiken in README.md

### GitHub Secrets Konfiguration

Für die Workflows werden folgende Secrets benötigt (in Repository Settings → Secrets and variables → Actions):

| Secret Name | Beschreibung | Benötigt für |
|-------------|--------------|--------------|
| `MISTRAL_API_KEY` | Mistral AI API Key | AI Code Review Workflow |
| `GITHUB_TOKEN` | Automatisch verfügbar | PR-Erstellung (kein Setup nötig) |

**Setup-Anleitung**:
1. Gehe zu Repository Settings → Secrets and variables → Actions
2. Klicke "New repository secret"
3. Name: `MISTRAL_API_KEY`
4. Value: Dein Mistral API Key (aus `.env`)
5. Speichern

### Lokale Umgebung

Für die lokale Entwicklung benötigst du eine `.env`-Datei:

```bash
# Kopiere die Beispiel-Konfiguration
cp .env.example .env

# Fülle die Werte aus:
# - DATABASE_URL (z.B. sqlite:///instance/database.db)
# - MISTRAL_API_KEY (optional, für KI-Analysen)
# - SECRET_KEY (generiere mit: python -c "import os; print(os.urandom(24).hex())")
```

**⚠️ Wichtig**: Die `.env`-Datei **NIEMALS** in Git committen! Sie ist bereits in `.gitignore` gelistet.

### Workflow-Trigger

- **Push auf `main` oder `feature/*`**: Alle Quality-Checks + Context-Generator laufen
- **Pull Request auf `main`**: AI Code Review + Quality-Checks laufen
- **Manuell**: Context Generator kann manuell in Actions-Tab gestartet werden

## Versionierung

Diese App verwendet **Semantic Versioning** (0.MAJOR.MINOR im Pre-Release):

### App-Version (aktuell: `1.3.1`)

**Pre-Release (0.x.y):**
- `0.MINOR.PATCH` - Breaking Changes zwischen Minor-Versions erlaubt
- `1.0.0` - Erster stabiler Production-Release

**Nach 1.0.0:**
- `MAJOR` - Breaking Changes (Datenbank-Schema-Umbruch)
- `MINOR` - Neue Features (abwärtskompatibel)
- `PATCH` - Bugfixes

### Export-Schema-Version (aktuell: `1.0`)

Unabhängig von der App-Version. Ändert sich nur bei CSV/Excel-Export-Struktur:
- `MAJOR` - Inkompatible Änderungen (Spalten entfernt/umbenannt)
- `MINOR` - Kompatible Erweiterungen (neue Spalten)

### Version ändern

**Manuell in `version.py` hochzählen:**

```python
# version.py
APP_VERSION = "0.2.0"  # Bei neuen Features
EXPORT_SCHEMA_VERSION = "1.1"  # Bei Export-Erweiterungen
```

**Dann in README aktualisieren:**
```markdown
**Version:** 0.2.0 (Pre-Release)
```

### Changelog

**1.3.1** (2026-02-11) - Phase 3 Stabilisierung
- ✅ Auth/RBAC- und Admin-Flow-Tests ergänzt
- ✅ RBAC-Edge-Cases für Gruppen/Teilnehmer abgedeckt
- ✅ Stabilitätsfix bei Gruppenbereinigung im Admin-Edit

**0.4.0** (2026-02-08) - Report-Konfiguration & Backup-System ✅
- ✅ **Report-Konfiguration UI**: Tailwind CSS Accordions mit 6 konfigurierbaren Bereichen
- ✅ **Backup-System**: Automatische SQLite-Backups beim App-Start + Flask-CLI-Commands
- ✅ **Prompts-Export**: JSON-Sicherung aller Prompts mit Metadaten
- ✅ **Retention-Management**: Automatische Bereinigung alter Backups (max. 50)
- ✅ **Prompt-Management**: Unique-Constraint für Prompt-Namen, Default-Prompts-Loader
- ✅ **Form-Fixes**: CSRF-Token-Integration, verschachtelte Forms behoben
- ✅ **UI-Improvements**: Unterschriften-Upload im Abschlussblatt-Bereich integriert
- ✅ **Migration**: Neue DB-Migration für Prompt-Unique-Constraint

**0.3.0** (2026-02-07) - Umfassende Test-Suite & CI/CD-Integration
- ✅ **Test-Suite**: 91 Tests (Unit + Integration), 46.90% Code-Coverage
- ✅ **GitHub Actions**: Neuer Tests & Coverage Workflow (`.github/workflows/tests.yml`)
- ✅ **Code-Quality**: Black + isort Formatierung, CI-Checks aktiv
- ✅ **ReportGenerator Service** mit Sidebar-Layout
- ✅ **HTML-Vorschau** mit iframe-Isolation (kein CSS-Leakage)
- ✅ **Standalone-Routes** für SE- und FE-PDF
- ✅ **Unterschriften-Management** (JPG-Bilder für Leitung FE/SE)
- ✅ **Radardiagramme** (matplotlib) für Social & Verbal Competencies
- ✅ **Auto-Seitenzählung** & konfigurierbarer Content-Mix
- ✅ **PDF-Druck-Buttons** in Verwaltungs-Templates

**0.2.0** (2026-02-07) - Report-System & PDF-Generierung
- ✅ ReportGenerator Service vollständig implementiert
- ✅ WeasyPrint-Integration für PDF-Export
- ✅ Template-System für flexible Reports
- ✅ Signature-Image-Model für Unterschriften

**0.1.0** (2026-01-31) - Initial Pre-Release
- ✅ Export/Import-Funktion mit Schema-Versionierung
- ✅ CSRF-Schutz für alle Formulare
- ✅ Modernisiertes UI (Tailwind CSS)
- ✅ Robuste Datenbank-Migrationen

## Kontakt

Bei Fragen oder wenn ich die `README.md` weiter anpassen soll (z. B. Beispiele für API-Nutzung, Screenshots, oder CI/CD-Integration), sag kurz Bescheid — ich kann die Datei erweitern.
