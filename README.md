# Stärkenanalyse-App

**Version:** 0.1.0 (Pre-Release)  
**Status:** In Entwicklung 🚧

Eine lokale Flask-Webanwendung zur Verwaltung von Gruppen und Teilnehmenden und zur Durchführung von KI-gestützten Stärkenanalysen.

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

- `database.py` enthält helper-Funktionen zum Zugriff und zur Paginierung. Falls Sie Probleme mit Such- oder Pagination-Features haben, beginnen Sie hier.

## Entwickeln & Tests

- Verwenden Sie `python -m venv .venv` und `pip install -r requirements.txt` wie oben beschrieben.
- Linter/Formatters: `black`, `flake8`, `pylint` sind in `requirements.txt` gelistet. Sie können `pre-commit`-Hooks hinzufügen, falls gewünscht.

## Nächste Schritte / Empfehlungen

1. Entfernen oder optionalisieren Sie große KI-Abhängigkeiten in `requirements.txt`, wenn Sie die App lokal mit eingeschränkten Features betreiben möchten.
2. Falls Sie PDF-Generierung benötigen, installieren Sie die Systempakete für `weasyprint` (distribution-spezifisch).
3. Fügen Sie ein CLI-Kommando `flask init-db` (oder ein kleines `manage.py`) hinzu, das `schema.sql` benutzt, damit die DB-Initialisierung benutzerfreundlicher wird.

## GitHub Actions & CI/CD

Dieses Projekt nutzt GitHub Actions für automatische Code-Qualitätsprüfungen und Dokumentations-Updates:

### Workflows

1. **CI - Code Quality** (`.github/workflows/ci-quality.yml`)
   - Läuft bei jedem Push auf `main` oder `feature/*` Branches
   - Prüft Code-Formatierung mit `black`, `isort`, `flake8`, `pylint`
   - Security-Checks mit `bandit` und `pip-audit`
   - Code-Komplexitäts-Analyse mit `radon`

2. **Context Generator** (`.github/workflows/context-generator.yml`)
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

### App-Version (aktuell: `0.1.0`)

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

**0.1.0** (2026-02-07) - Initial Pre-Release
- ✅ Export/Import-Funktion mit Schema-Versionierung
- ✅ CSRF-Schutz für alle Formulare
- ✅ Modernisiertes UI (Tailwind CSS)
- ✅ Robuste Datenbank-Migrationen

## Kontakt

Bei Fragen oder wenn ich die `README.md` weiter anpassen soll (z. B. Beispiele für API-Nutzung, Screenshots, oder CI/CD-Integration), sag kurz Bescheid — ich kann die Datei erweitern.
