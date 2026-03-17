# CONTEXT.md - Stärkenanalyse-App

**Automatisch generiert am**: 2026-03-17 03:52:09

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

### Blueprints (12 total)

#### _tasks_deprecated.py (0 Routes)

#### admin.py (0 Routes)

#### analysis.py (0 Routes)

#### auth.py (0 Routes)

#### data_import.py (0 Routes)

#### data_io.py (0 Routes)

#### explanation_blocks.py (0 Routes)

#### groups.py (0 Routes)

#### observation_tasks.py (0 Routes)

#### participants.py (0 Routes)

#### prompts.py (0 Routes)

#### reports.py (0 Routes)

### Templates (30 HTML-Dateien)
- ai_analysis_select_group.html
- ai_analysis_select_participants.html
- ai_analysis_status.html
- base.html
- bericht_pdf_vorlage.html
- change_password.html
- dashboard.html
- data_entry.html
- data_entry_rework.html
- data_entry_search.html
- explanation_block_form.html
- export_selection.html
- final_report.html
- final_report_pdf.html
- import_page.html
- info.html
- login.html
- login_base.html
- manage_explanation_blocks.html
- manage_final_reports.html
- manage_foreign_assessments.html
- manage_groups.html
- manage_participants.html
- manage_prompts.html
- manage_self_assessments.html
- participants.html
- prompt_form.html
- run_batch_ai.html
- self_assessment_entry.html
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
