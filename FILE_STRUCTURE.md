# 📁 Vollständige Dateistruktur - Stärkenanalyse-App

**Erstellt am**: 7. Februar 2026
**Aktualisiert am**: 15. Februar 2026
**Version**: 1.5.1  
**Beschreibung**: Vollständige Übersicht aller Projektdateien mit ihren Funktionen

---

## 📋 Projektübersicht

Diese Dokumentation beschreibt **alle** Dateien des Stärkenanalyse-App Projekts. Jede Datei wird in 1-2 Sätzen erklärt.

## 🧭 Projektstruktur (Grafische Übersicht)

```tree
staerkenanalyse-app/
│
├─── 🔴 KERN-APPLICATION
│    ├─ app.py                      Flask-Haupteinstieg
│    ├─ config.py                   Umgebungs-Konfiguration
│    ├─ extensions.py               Flask-Extensions
│    ├─ models.py                   SQLAlchemy Datenbankmodelle
│    ├─ version.py                  Versions-Management
│    └─ wsgi.py                     Production WSGI-Entry
│
├─── 🟢 KI-SERVICES
│    ├─ ki_services.py              Mistral + Gemini API-Integration
│    ├─ ai_gym.py                   KI-Gym Learning System
│    └─ ki_services_backup.py       Legacy-Backup
│
├─── 🟡 BLUEPRINTS (Funktionale Module)
│    ├─ blueprints/
│    │  ├─ analysis.py              📊 KI-Analysen & Report-Editing
│    │  ├─ admin.py                 👥 Admin-Dashboard & Settings
│    │  ├─ groups.py                👨‍👩‍👧 Gruppen-Management
│    │  ├─ participants.py          👤 Teilnehmer-Management
│    │  ├─ reports.py               📋 Report-Anzeige & Verwaltung
│    │  ├─ observation_tasks.py     📝 Beobachtungsaufgaben-Library
│    │  ├─ data_import.py           📥 CSV/JSON-Import
│    │  ├─ data_io.py               💾 Daten Export/Import
│    │  ├─ explanation_blocks.py    📖 Erklärblöcke & Kompetenz-Infos
│    │  ├─ auth.py                  🔐 Authentifizierung & RBAC
│    │  └─ prompts.py               🎯 Prompt-Template-Verwaltung
│
├─── 🔵 SERVICES (Business-Logik)
│    ├─ services/
│    │  ├─ report_generator.py      📄 PDF-Report-Generierung
│    │  ├─ ai_client.py             🤖 Zentrale KI-Client-Abstraktionen
│    │  ├─ task_generator.py        🚀 Automatische Task-Generierung
│    │  ├─ task_knowledge_base.py   💡 Task-Kontext & Metadaten
│    │  └─ ... weitere Services
│
├─── 🟣 TEMPLATES (Frontend UI)
│    ├─ templates/
│    │  ├─ base.html                🎨 Basis-Layout
│    │  ├─ dashboard.html           📊 Start-Dashboard
│    │  ├─ manage_*.html            UI-Formulare & Listen
│    │  ├─ observation_tasks/       📝 Task-Library & Generierung
│    │  ├─ reports/                 📋 Report-Templates & Anzeige
│    │  ├─ admin/                   👨‍💼 Admin-Interfaces
│    │  └─ modals/                  ⚙️ Reusable Modal-Komponenten
│
├─── 📋 MIGRATIONS (Datenbank-Versionierung)
│    ├─ migrations/versions/        🔄 SQLAlchemy-Migrationen
│
├─── 🎨 STATIC ASSETS
│    ├─ static/
│    │  ├─ css/                     Tailwind + Custom Styles
│    │  ├─ js/                      Vanilla JS + Libraries
│    │  ├─ fonts/                   Schriftarten
│    │  └─ uploads/                 User-Uploads
│
├─── 🔧 SCRIPTS (Utilities & Automation)
│    ├─ scripts/
│    │  ├─ import_example_tasks.py  📥 Referenzaufgaben-Import
│    │  ├─ ... weitere Scripts
│
├─── 📚 DOCUMENTATION
│    ├─ README.md                   Projekt-Überblick
│    ├─ CONTEXT.md                  🤖 KI-Agent-optimierte Kurzfassung
│    ├─ FILE_STRUCTURE.md           📖 Diese Datei (Vollständiges Inventory)
│    ├─ DEVELOPMENT_ROADMAP.md      🗺️ Feature-Planung
│    ├─ DEPLOYMENT.md               🚀 Produktions-Deployment
│    ├─ SECURITY_AUDIT_REPORT.md    🔒 Sicherheits-Analyse
│    ├─ PROJECT_OVERVIEW.md         📘 Konzept & Architektur
│    ├─ PHASE*.md                   ✅ Implementations-Status pro Phase
│    └─ ... weitere Dokumentation
│
├─── ⚙️ KONFIGURATIONSDATEIEN
│    ├─ requirements.txt            📦 Python-Dependencies
│    ├─ requirements-test.txt       🧪 Test-Dependencies
│    ├─ .env                        🔑 Lokale Umgebungsvariablen
│    ├─ .env.example                📋 .env-Template
│    ├─ .env.production             ☁️ Production-Settings
│    ├─ pytest.ini                  🧪 Pytest-Konfiguration
│    ├─ .pylintrc                   ✨ Code-Quality-Config
│    ├─ schema.sql                  💾 SQL-Schema
│    ├─ Dockerfile                  🐳 Container-Definition
│    ├─ docker-compose.yml          🐙 Multi-Container-Setup
│    └─ .dockerignore               🚫 Docker-Ausschlüsse
│
└─── 📦 DATENORDNER
     ├─ instance/                   SQLite-Datenbankdatei
     ├─ migrations/                 Alembic-Versionierung
     ├─ uploads/                    User-Datei-Uploads
     ├─ backups/                    Datenbank-Backups
     └─ htmlcov/                    Coverage-Reports
```

### 🎯 Logische Abhängigkeiten

```tree
                    ┌──────────────────┐
                    │   Frontend UI    │
                    │  (templates/)    │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Flask Blueprints│
                    │  (blueprints/)   │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
    ┌───▼───┐        ┌──────▼──────┐      ┌─────▼─────┐
    │Analytics  │        │  KI-Services │      │  Services │
    │ (analysis)│        │(ki_services) │      │(business) │
    └───┬───┘        └──────┬──────┘      └─────┬─────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  SQLAlchemy ORM  │
                    │  (models.py)     │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   SQLite DB      │
                    │  (instance/)     │
                    └──────────────────┘
```

---

## 🔧 Root-Level Dateien

### Haupt-Python-Dateien

- **app.py**: Haupteinstieg der Flask-Anwendung. Initialisiert Flask, registriert alle Blueprints, erstellt Datenbanktabellen und startet den Development-Server auf Port 5001.

- **config.py**: Konfigurationsklassen für verschiedene Environments (Development, Production, Testing). Definiert Datenbank-URLs, Secret Keys, Upload-Ordner und Feature-Flags.

- **extensions.py**: Zentrale Instanzen von Flask-Extensions (SQLAlchemy db, Flask-Migrate). Verhindert zirkuläre Imports durch separierte Extension-Initialisierung.

- **models.py**: SQLAlchemy-Datenbankmodelle für alle Entitäten (Participant, Group, Task, SelfAssessment, Report-Modelle, KI-Gym). Enthält Beziehungen und Validierungen.

- **ki_services.py**: KI-API-Integration für Mistral AI und Google Gemini. Stellt Funktionen für strukturierte Kompetenz-Analysen, Report-Generierung und Prompt-basierte KI-Anfragen bereit.

- **ki_services_backup.py**: Backup-Version von ki_services.py vor Phase 2 Refactoring. Enthält Legacy-Implementierung für Task-Generierung.

- **ai_gym.py**: KI-Gym Learning System (NEU v1.1.0). Pattern-Extraktion aus Content-Edits, automatische Prompt-Rule-Generierung basierend auf User-Verbesserungen.

- **utils.py**: Hilfsfunktionen für Dateiverarbeitung. Extrahiert Text aus PDF/DOCX, HTML-Sanitizing, Helper für KI-Parsing.

- **version.py**: Zentrale Versionsnummer der Anwendung (aktuell: 1.5.0). Wird für Version-Display im Dashboard und für Deployment verwendet.

- **wsgi.py**: WSGI-Entry-Point für Production-Deployment. Lädt Anwendung für Gunicorn oder andere WSGI-Server.

### Test- und Migrations-Dateien

- **test_ki_original_parsing.py**: Test-Script für KI-Parsing-Funktionalität. Testet strukturierte Ausgabe-Extraktion aus Mistral-API-Responses.

- **generate_test_data.py**: Generiert Testdaten für Entwicklung und Testing. Erstellt Sample-Gruppen, Teilnehmer und Beobachtungen in der Datenbank.

- **migrate_old_data.py**: Migrations-Script für Legacy-Daten. Konvertiert alte Datenbankstrukturen in das aktuelle Schema.

- **scripts/import_example_tasks.py**: Importiert Referenzaufgaben (EXAMPLE_TASKS) als DB‑Einträge (`is_example=True`).

### Konfigurationsdateien

- **requirements.txt**: Python-Dependency-Liste für pip-Installation. Enthält alle benötigten Packages mit Versionsnummern (Flask, SQLAlchemy, Mistral, WeasyPrint, etc.).

- **.env**: Umgebungsvariablen für lokale Entwicklung (SECRET_KEY, DATABASE_URL, API-Keys). Wird nicht in Git committet (siehe .gitignore).

- **.env.example**: Template für .env-Datei. Zeigt erforderliche Umgebungsvariablen ohne sensible Werte.

- **.env.production**: Production-spezifische Umgebungsvariablen. Enthält optimierte Einstellungen für Live-Deployment.

- **.pylintrc**: Pylint-Konfiguration für Code-Quality-Checks. Definiert Regeln, Ausnahmen und Severity-Levels für Linting.

- **schema.sql**: SQL-Schema-Definition für manuelle Datenbank-Setup. Alternativ zu Flask-Migrate für direktes Database-Setup.

- **docker-compose.yml**: Docker-Compose-Konfiguration für Container-Setup. Definiert Services, Volumes und Netzwerk-Konfiguration.

- **Dockerfile**: Docker-Image-Definition für App-Containerisierung. Baut produktionsfertiges Image mit allen Dependencies.

- **.dockerignore**: Ausschluss-Liste für Docker-Build. Verhindert Copy von venv, cache und temporären Dateien ins Image.

- **.gitignore**: Git-Ignore-Regeln. Definiert Dateien/Ordner die nicht versioniert werden (venv, __pycache__, .env, instance/, uploads/).

### Log- und Report-Dateien

- **app.log**: Haupt-Logfile der Anwendung. Enthält Runtime-Logs, Errors und Debug-Informationen.

- **app_5002.log**: Sekundäres Logfile für Port 5002 (falls parallel laufend). Für Multi-Instance-Setups.

- **pylint_report.txt**: Letzter Pylint-Analyse-Report. Enthält Code-Quality-Metriken und gefundene Issues.

- **test_summary.md**: Test-Execution-Summary. Dokumentiert letzte Test-Durchläufe und Ergebnisse.

### Datenbank

- **database.db**: SQLite-Datenbankdatei. Enthält alle produktiven Daten (Teilnehmer, Gruppen, Beobachtungen, Analysen).

---

## 📚 Dokumentation (Markdown-Dateien)

- **README.md**: Projekt-Hauptdokumentation. Enthält Setup-Anleitung, Feature-Übersicht, Technologie-Stack und Quick-Start-Guide.

- **PROJECT_OVERVIEW.md**: Detaillierte Projektbeschreibung. Erklärt Architektur, Datenmodelle, Blueprints und Workflow der Anwendung.

- **CONTEXT.md**: Automatisch generierte Kontext-Dokumentation. Listet alle Routes, Modelle und Dependencies für KI-Assistenten.
- **PROMPT_DOCUMENTATION.md**: Prompt-Dokumentation (Sprint 4.1). Quellen, Platzhalter, Schema-Checks und Pflege.
- **SECURITY_AUDIT_REPORT.md**: Security Audit Report (Sprint 4.2). Schutzmaßnahmen, Tests, Findings und Empfehlungen.
- **INCIDENT_RUNBOOKS.md**: Incident-Runbooks (Sprint 4.3) inkl. Mermaid-Flows.
- **PROMPT_RECOVERY.md**: Dokumentation zur Prompt-Wiederherstellung (MistralSozVerb4).

- **STARTUP.md**: Start-Anleitung für Entwickler. Step-by-Step-Guide für lokales Setup und ersten App-Start.

- **DEPLOYMENT.md**: Deployment-Dokumentation. Erklärt Production-Deployment mit Docker, Gunicorn und Reverse-Proxy-Setup.

- **FEATURE_CHECK.md**: Feature-Checkliste. Dokumentiert implementierte Features und deren Test-Status.

- **MIGRATION_GUIDE.md**: Datenbank-Migrations-Guide. Erklärt Flask-Migrate-Workflow und Migrations-Best-Practices.

- **VERSIONING.md**: Versionierungs-Strategie. Dokumentiert Semantic-Versioning-Konventionen und Release-Prozess.

- **TODO_TESTDATA.md**: Testdaten-TODO-Liste. Offene Tasks für Testdaten-Generierung und Fixtures.

- **COMMIT_SUMMARY.md**: Git-Commit-Zusammenfassung. Dokumentiert wichtige Commits und Feature-Entwicklungen.

- **license.md**: Software-Lizenz. Definiert Nutzungsbedingungen und Copyright-Informationen.

- **FILE_STRUCTURE.md**: Diese Datei! Vollständige Übersicht aller Projektdateien mit Beschreibungen.

---

## 📦 Blueprints (`blueprints/`)

Flask-Blueprints organisieren die Anwendung in logische Module.

- **analysis.py**: Blueprint für KI-Analysen und Report-Generierung. Enthält 12 Routes für Einzel-/Batch-Analysen, PDF-Export und finale Berichte.

- **participants.py**: Blueprint für Teilnehmer-Management. 9 Routes für CRUD-Operationen, Daten-Eingabe und Selbsteinschätzungen.

- **groups.py**: Blueprint für Gruppen-Verwaltung. 5 Routes für Gruppen-CRUD und Zuordnung von Teilnehmern.

- **data_io.py**: Blueprint für Daten-Import/-Export. 9 Routes für CSV/Excel-Import, Datenexport und API-Endpoints für Frontend.

- **data_import.py**: Blueprint für erweiterte Import-Funktionalität. Spezialisierte Import-Logik für externe Datenquellen.

- **explanation_blocks.py**: Blueprint für Erklärungstexte-Management. 4 Routes zum Verwalten von Templates für Report-Abschnitte.

- **prompts.py**: Blueprint für KI-Prompt-Verwaltung. 4 Routes zum Erstellen/Bearbeiten von Prompt-Templates für verschiedene Analyse-Typen.

- **reports.py**: Blueprint für Report-System (NEU in v0.2.0). Verwaltet Report-Templates, Konfiguration, Vorschau und PDF-Generierung.

- **observation_tasks.py**: Blueprint für Beobachtungsaufgaben-Verwaltung **(NEU v1.1.0)**. 10+ Routes für Task-Library, KI-Generierung, Chat-basierte Iteration und Versions-Management.

- **admin.py**: Blueprint für Admin-Bereich **(NEU v1.1.0)**. Enthält KI-Gym Training Dashboard, Rule-Management und System-Verwaltung.

- **_tasks_deprecated.py**: Deprecated Phase 2 Task Generator Blueprint. Legacy-Code, wird nicht mehr verwendet (obsolete durch observation_tasks.py).

---

## 🗃️ Services (`services/`)

Wiederverwendbare Service-Layer für Business-Logic.

- **__init__.py**: Service-Package-Initialisierung. Macht Services importierbar und definiert Public-API für ReportGenerator und Knowledge-Base-Funktionen.

- **report_generator.py**: ReportGenerator-Service-Klasse. Kern-Logik für Report-Generierung: Template-Processing, Sidebar-Layout, Daten-Aggregation, WeasyPrint-Integration.

- **ai_client.py**: KI‑Provider‑Abstraktion (Mistral/Gemini), Fehlerbehandlung und JSON‑Response.

- **task_generator.py**: KI‑Task‑Generierung inkl. Prompt‑Knowledge‑Injection.

- **task_knowledge_base.py** (NEU v1.2.0): Assessment-Center Task Knowledge Base. Strukturierte Wissensdatenbank mit 12 AC-Aufgabentypen, 10 Kompetenzdimensionen mit Verhaltensankern, 6 Zielgruppen-Kategorien und vergleichenden Phasenmodellen. Bietet `get_knowledge_for_prompt()` für KI-Prompt-Injection und `get_target_group_options()` für UI-Rendering.

---

## 🗄️ Migrations (`migrations/`)

Alembic/Flask-Migrate Datenbank-Migrationen.

### Konfigurations-Dateien

- **alembic.ini**: Alembic-Hauptkonfiguration. Definiert Migration-Settings und Logging-Konfiguration.

- **env.py**: Alembic-Environment-Setup. Verbindet Flask-App mit Migrationen und konfiguriert Context.

- **README**: Migrations-README. Kurze Anleitung für Migrations-Workflow.

- **script.py.mako**: Mako-Template für neue Migrations-Scripts. Wird von `flask db revision` verwendet.

### Migrations-Versionen (`migrations/versions/`)

- **ffbd6aad0758_initial_migration_with_all_models.py**: Erste Migration. Erstellt alle Core-Tabellen (Participant, Group, Observation, Competency, etc.).

- **37910f5c8ff0_add_explanationblock_model.py**: Migration für ExplanationBlock-Modell. Fügt Tabelle für Report-Erklärungstexte hinzu.

- **b4c7ad2a2bbc_change_group_date_to_date_range.py**: Änderung Group-Schema. Ersetzt einzelnes Datum durch date_from/date_to Range.

- **a797fd071986_add_report_system_tables_reporttemplate_.py**: Report-System-Migration. Fügt ReportTemplate und GeneratedReport-Tabellen hinzu (v0.2.0).

- **1bb5bd2a5c04_add_signatureimage_model.py**: SignatureImage-Modell-Migration. Fügt Tabelle für digitale Unterschriften in Reports hinzu.
- **20260210_000001_add_prompt_default_flag.py**: Default-Prompt-Flag in `prompts` (is_default).
- **bfb0ecb7f36d_merge_heads.py**: Merge-Revision für Alembic-Heads.

---

## 🎨 Templates (`templates/`)

Jinja2-HTML-Templates für Frontend-Rendering.

### Core-Templates

- **base.html**: Basis-Template mit Navigation, Layout und Common-Blocks. Alle anderen Templates erben von diesem.

- **dashboard.html**: Haupt-Dashboard. Zeigt Statistiken, letzte Aktivitäten und Quick-Links.

- **info.html**: Info/About-Seite. Erklärt App-Funktionalität und Credits.

### Teilnehmer & Gruppen

- **participants.html**: Teilnehmer-Übersicht (veraltet, ersetzt durch manage_participants.html).

- **manage_participants.html**: Teilnehmer-Verwaltung. Liste mit CRUD-Funktionen und Gruppen-Zuordnung.

- **manage_groups.html**: Gruppen-Verwaltung. Erstellen, Bearbeiten, Löschen von Gruppen-Entitäten.

### Daten-Eingabe

- **data_entry.html**: Original Daten-Eingabe-Formular. Erfasst Beobachtungen für einzelnen Teilnehmer.

- **data_entry_rework.html**: Überarbeitete Daten-Eingabe. Verbesserte UX mit autosave und Validierung.

- **data_entry_search.html**: Daten-Eingabe mit Suche. Erlaubt schnelles Finden von Teilnehmern zur Bearbeitung.

- **self_assessment_entry.html**: Selbsteinschätzungs-Formular. Teilnehmer kann eigene Kompetenzen bewerten.

- **manage_self_assessments.html**: Selbsteinschätzungen-Übersicht. Liste aller Selbstbewertungen mit Management-Funktionen.

### KI-Analysen

- **ai_analysis_select_group.html**: KI-Batch-Analyse Step 1. Wähle Gruppe für Bulk-Analyse aus.

- **ai_analysis_select_participants.html**: KI-Batch-Analyse Step 2. Selektiere einzelne Teilnehmer aus gewählter Gruppe.

- **ai_analysis_status.html**: KI-Analyse-Status-Seite. Zeigt Progress und Ergebnisse der Batch-Analyse.

- **run_batch_ai.html**: Batch-KI-Execution-Interface. Startet und monitored parallele KI-Analysen.

### Fremd- und Finalbericht

- **manage_foreign_assessments.html**: Fremdeinschätzungen-Management. Verwaltet externe Bewertungen für Teilnehmer.

- **manage_final_reports.html**: Finalbericht-Übersicht. Liste aller generierten Finalberichte mit Download-Links.

- **final_report.html**: Finalbericht HTML-Ansicht. Zeigt kombinierten Report (Selbst + Fremd + KI).

- **final_report_pdf.html**: PDF-Export-Template für Finalbericht. Optimiert für WeasyPrint-Rendering.

### Report-System (v0.2.0)

- **bericht_pdf_vorlage.html**: Legacy PDF-Template (wird ersetzt durch reports/).

- **staerkenanalyse_bericht_vorlage3.html**: Legacy Report-Template v3 (wird migriert).

#### Report-Unterordner (`templates/reports/`)

- **templates_list.html**: Report-Templates-Liste. Übersicht aller verfügbaren Report-Layouts.

- **template_detail.html**: Template-Detail-Ansicht. Zeigt Template-Eigenschaften, Sections und Preview.

- **configure.html**: Report-Konfigurations-Seite. Wähle Template, anpasse Sections, setze Parameter.

- **preview.html**: Report-Vorschau. Live-Preview des konfigurierten Reports vor PDF-Generierung.

### Import/Export & Verwaltung

- **import_page.html**: Daten-Import-Interface. Upload und Mapping von CSV/Excel-Dateien.

- **export_selection.html**: Export-Konfigurations-Seite. Wähle Daten-Entitäten und Format für Export.

- **manage_prompts.html**: Prompt-Management-Übersicht. Liste aller KI-Prompts mit Edit/Delete-Actions.

- **prompt_form.html**: Prompt-Editor-Formular. Erstellen/Bearbeiten von KI-Prompt-Templates.

- **manage_explanation_blocks.html**: Erklärungstext-Management. Verwaltet wiederverwendbare Text-Bausteine für Reports.

- **explanation_block_form.html**: Erklärungstext-Editor. Formular zum Erstellen/Bearbeiten von Explanation-Blocks.

---

## 💬 Prompts (`prompts/`)

KI-Prompt-Templates für verschiedene Analyse-Typen.

- **staerkenanalyse_prompt.txt**: Original-Prompt für Stärkenanalyse. Initiale Version des KI-Analysis-Prompts.

- **staerkenanalyse_prompt_final.txt**: Finale Stärkenanalyse-Prompt-Version. Optimiert nach mehreren Iterationen.

- **bestsofar.txt**: Best-Performing-Prompt v1. Experimenteller Prompt mit hoher Qualität.

- **bestsofar2.txt**: Best-Performing-Prompt v2. Iterierte Version mit weiteren Verbesserungen.

- **structured_report.txt**: Strukturierter Report-Prompt. Generiert klar formatierte Analysen.

- **structured_report_json.txt**: JSON-Output-Prompt. Erzeugt maschinenlesbare strukturierte Outputs.

- **structured_report_mistral.txt**: Mistral-optimierter Report-Prompt. Speziell für Mistral-API angepasst.
- **mistralsozverb4.txt**: Rekonstruiertes Prompt-Template für soz./verb. Stärkenanalyse (JSON-Output).

---

## 🎨 Static Files (`static/`)

### Images (`static/images/`)

- Logos, Icons und Grafiken für UI
- (Spezifische Dateien nicht aufgelistet - enthält UI-Assets)

### Weitere Static Assets
- **static/loading-robot.webp**: Lade-Animation für KI-Generierung/Chat-Refinement

---

## 📂 Instance & Uploads

### Instance-Ordner (`instance/`)

- **database.db**: Alternative Datenbank-Location (Configuration-abhängig)
- Enthält instanzspezifische Konfig und Runtime-Daten

### Uploads-Ordner (`uploads/`)

- User-hochgeladene Dateien (PDFs, DOCX, Excel)
- Import-Dateien und Attachments
- Wird von .gitignore ausgeschlossen

---

## 🔧 GitHub Workflows (`.github/workflows/`)

CI/CD-Pipelines für Automation.

- **ci-quality.yml**: Code-Quality-Checks bei Push zu main. Führt Black, Flake8, isort und Security-Scans aus.

- **ai-code-review.yml**: Mistral-AI Code-Review bei Pull-Requests. Automatisierte KI-basierte Code-Analyse.

- **context-generator.yml**: CONTEXT.md Auto-Generator (workflow_dispatch only). Generiert Kontext-Dokumentation on-demand.

- **docs-updater.yml**: Dokumentations-Updater (workflow_dispatch only). Aktualisiert README und PROJECT_OVERVIEW automatisch.

---

## 🤖 GitHub Scripts (`.github/scripts/`)

Python-Scripts für CI/CD-Workflows.

- **ai_code_review.py**: Mistral-AI Code-Review-Script. Analysiert Diff und generiert Review-Kommentare.

- **generate_context.py**: CONTEXT.md Generator-Script. Scannt Codebase und erstellt strukturierte Kontext-Dokumentation.

- **check_legacy.py**: Legacy-Code-Detektor. Findet veraltete Patterns und schlägt Modernisierungen vor.

---

## 📝 GitHub Prompts (`.github/prompts/`)

Template-Prompts für GitHub-Actions.

- **code-review-template.txt**: Template für AI Code-Review. Definiert Review-Struktur und Focus-Areas.

- **documentation-template.txt**: Template für Dokumentations-Generierung. Format-Vorgaben für auto-generierte Docs.

- **dependency-check-template.txt**: Template für Dependency-Analyse. Prüft auf veraltete oder unsichere Dependencies.

---

## 📁 GitHub Setup (`.github/`)

- **SETUP_GUIDE.md**: GitHub-Actions-Setup-Guide. Erklärt wie Workflows konfiguriert und Secrets gesetzt werden.

---

## 🗑️ Weitere Ordner

### `__pycache__/`
- Python Bytecode-Cache (automatisch generiert, nicht in Git)

### `.vscode/`
- VS-Code Workspace-Einstellungen (Editor-spezifische Konfiguration)

### `venv/` & `venv_py313_broken/`
- Virtual Environments (nicht in Git committet)
- `venv/`: Aktive Python-Umgebung
- `venv_py313_broken/`: Legacy/Broken venv (sollte gelöscht werden)

### `Dist/`
- Build-Output-Ordner (für Packaging/Distribution)

### `sys`
- System-Dateien oder Symlink (Zweck unklar ohne genauere Inspektion)

---

## 📊 Statistiken

**Gesamt-Dateien**: ~93 Code/Config-Dateien + Templates + Assets  
**Python-Module**: 23 (Core + Blueprints + Services + Migrations)  
**Templates**: 31 HTML-Dateien  
**Blueprints**: 11 (auth, admin, analysis, participants, groups, data_io, data_import, explanation_blocks, prompts, reports, observation_tasks)  
**Routes**: 50+ HTTP-Endpoints  
**Migrations**: 5 Datenbank-Migrationen  
**CI/CD-Workflows**: 4 GitHub Actions  

---

## ✅ Status

- **Version**: 1.4.0
- **Letztes Update**: Phase 3 abgeschlossen (Security Audit + Runbooks + Prompt-Doku)
- **Tests**: 141 Tests ✅ (siehe `PHASE3_STATUS.md`)
- **Code-Qualität**: CI-Checks aktiv, Test-Suite implementiert

---

**Dokumentationsende** 
Für Updates siehe: `VERSIONING.md` und Git-Commit-History
