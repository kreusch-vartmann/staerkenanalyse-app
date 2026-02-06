# CONTEXT.md - Stärkenanalyse-App

**Automatisch generiert am**: 2026-02-06 11:00:24

---

## 📋 Projektübersicht

**Technologie-Stack**:
- **Backend**: Python 3.12.12, Flask 3.1.2
- **ORM**: SQLAlchemy 2.0.28 + Flask-SQLAlchemy 3.0.4
- **Database**: SQLite (via DATABASE_URL env var)
- **KI-Integration**: Mistral API (mistralai==0.4.2), Google Generative AI
- **Frontend**: Vanilla JavaScript, Chart.js, Tailwind CSS, Bootstrap 4
- **PDF-Generation**: WeasyPrint
- **Migrations**: Flask-Migrate 4.0.4 (Alembic)

---

## 🗂️ Dateistruktur

### Core Application Files
- **app.py**: Flask-App-Initialisierung, Blueprint-Registrierung, Dashboard-Route
- **models.py**: SQLAlchemy-Modelle (0 Models: )
- **extensions.py**: db, migrate Objekte (verhindert circular imports)
- **ki_services.py**: KI-API-Integration (Mistral, Google Gemini)
- **utils.py**: File-Processing (PDF, DOCX Extraktion)

### Blueprints (5 total)

#### analysis.py (8 Routes)
- `GET /edit_report/<int:participant_id>` → `edit_report()`
- `GET /bericht/<int:participant_id>/pdf` → `bericht_pdf()`
- `GET /ai_analysis/select_group` → `ai_analysis_select_group()`
- `GET /ai_analysis/group/<int:group_id>` → `ai_analysis_select_participants()`
- `POST /ai_analysis/configure` → `configure_batch_ai_analysis()`
- `POST /ai_analysis/execute` → `execute_batch_ai_analysis()`
- `POST /run_ki_analysis/<int:participant_id>` → `run_ki_analysis()`
- `POST /api/run_single_analysis/<int:participant_id>` → `run_single_analysis_api()`

#### data_io.py (9 Routes)
- `GET /data-entry/rework` → `data_entry_rework()`
- `GET /data-entry/search` → `data_entry_search()`
- `GET /api/group/<int:group_id>/participants` → `api_get_participants_by_group()`
- `GET /api/participant/<int:participant_id>/observations` → `api_get_observations()`
- `POST /save_observations/<int:participant_id>` → `save_observations_api()`
- `GET /import` → `import_page()`
- `POST /import/names` → `import_names()`
- `GET /export_selection` → `export_selection()`
- `POST /export_data` → `export_data()`

#### groups.py (5 Routes)
- `GET /groups` → `manage_groups()`
- `GET /group/<int:group_id>/participants` → `show_group_participants()`
- `POST /group/add` → `add_group()`
- `POST /group/edit/<int:group_id>` → `edit_group()`
- `POST /group/delete/<int:group_id>` → `delete_group()`

#### participants.py (6 Routes)
- `GET /participants` → `manage_participants()`
- `POST /group/<int:group_id>/participant/add` → `add_participant()`
- `POST /participant/edit/<int:participant_id>` → `edit_participant()`
- `POST /participant/delete/<int:participant_id>` → `delete_participant()`
- `GET /participant/<int:participant_id>/data_entry` → `show_data_entry()`
- `POST /participant/<int:participant_id>/save_observations` → `save_observations()`

#### prompts.py (5 Routes)
- `GET /prompts` → `manage_prompts()`
- `GET, POST /prompt/add` → `add_prompt()`
- `GET, POST /prompt/edit/<int:prompt_id>` → `edit_prompt()`
- `POST /prompt/delete/<int:prompt_id>` → `delete_prompt()`
- `GET /api/prompt/<int:prompt_id>` → `get_prompt_content_api()`

### Templates (19 HTML-Dateien)
- ai_analysis_select_group.html
- ai_analysis_select_participants.html
- ai_analysis_status.html
- base.html
- bericht_pdf_vorlage.html
- dashboard.html
- data_entry.html
- data_entry_rework.html
- data_entry_search.html
- export_selection.html
- import_page.html
- info.html
- manage_groups.html
- manage_participants.html
- manage_prompts.html
- participants.html
- prompt_form.html
- run_batch_ai.html
- staerkenanalyse_bericht_vorlage3.html

---

## 🗄️ Datenbank-Schema (SQLAlchemy Models)

---

## 🔐 Environment Variables

**Erforderlich**:
- `DATABASE_URL`: SQLAlchemy Database URI (z.B. `sqlite:///instance/database.db`)
- `MISTRAL_API_KEY`: Mistral AI API Key (optional, für KI-Analysen)
- `GOOGLE_API_KEY`: Google Generative AI Key (optional, Fallback)

**Flask-Konfiguration**:
- `SECRET_KEY`: Automatisch generiert via `os.urandom(24)` (⚠️ regeneriert bei Restart!)
- Port: 5001 (hardcoded in app.py)
- Debug: Aktiviert (⚠️ für Production deaktivieren!)

---

## 📦 Wichtige Abhängigkeiten

**Kritische Libraries**:
- Flask 3.1.2, SQLAlchemy 2.0.28
- mistralai==0.4.2 (⚠️ Version fixed wegen Kompatibilität)
- WeasyPrint (benötigt System-Dependencies: libcairo, libpango)
- pandas 2.3.2, numpy 2.3.3 (für Excel-Export)
- protobuf==5.29.5 (⚠️ Bekannter Konflikt mit älteren Packages)

---

## 🚀 Typische Workflows

### 1. Neuen Teilnehmer hinzufügen
1. Dashboard → "Gruppen verwalten" → Gruppe auswählen
2. "Teilnehmer hinzufügen" → Name eingeben
3. → `participants.add_participant()` → Participant-Model erstellt

### 2. KI-Analyse durchführen
1. Dashboard → "KI-Analyse" → Gruppe auswählen
2. Teilnehmer auswählen → "Starten"
3. → `analysis.run_ki_analysis_api()` → Mistral API Call
4. Weiterleitung → `analysis.edit_report()` → staerkenanalyse_bericht_vorlage3.html

### 3. Bericht bearbeiten/exportieren
1. Dashboard → "Berichte bearbeiten" (manage_participants.html)
2. "Bericht ansehen" Button (nur wenn `ki_texts` vorhanden)
3. → `analysis.edit_report()` → HTML-Bericht editieren
4. PDF-Export → `analysis.bericht_pdf()` → WeasyPrint → PDF

---

## ⚠️ Bekannte Issues & TODOs

1. **SECRET_KEY regeneriert bei Restart** → Sessions werden ungültig
2. **3x TODOs in blueprints/data_io.py** → Export-Funktion Field-Mapping
3. **schema.sql veraltet** → Nur `leitung`, models.py hat `leitung_fremdeinschatzung` + `leitung_selbsteinschatzung`
4. **database.py (338 Zeilen)** → Legacy Code, vermutlich unused
5. **Debug-Modus in Production** → `app.run(debug=True)` hardcoded

---

**Letzte Aktualisierung**: {self._get_timestamp()}
