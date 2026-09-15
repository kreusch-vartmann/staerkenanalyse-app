# CONTEXT.md - KI-optimierter Projektkontext

**Aktualisiert am**: 2026-09-15 (Version 1.6.0)

**Ziel**: Diese Datei liefert KI‑Agenten einen schnellen, präzisen Überblick über Architektur, Datenflüsse, Regeln und kritische Stellen. 
**Für vollständige Dateilisten** siehe `FILE_STRUCTURE.md`.

---

## 📌 Projektzweck (Kurzfassung)

Die Stärkenanalyse‑App unterstützt Assessment‑Center‑Workflows: Teilnehmende erfassen Beobachtungen (sozial/verbal), KI generiert Fremdeinschätzungen, und Abschlussberichte (Fremd + Selbst) werden als PDF erstellt.

---

## 🧱 Architektur & Kernmodule

**Backend**: Flask (Python 3.11+), SQLAlchemy, SQLite/PostgreSQL via `DATABASE_URL`  
**KI**: Mistral + Google Gemini (Fallback), JSON‑Antworten werden normalisiert

**Wichtige Dateien**:
- `blueprints/analysis.py`: KI‑Analyse (Batch/Single), Report‑Editing, Status‑UI
- `blueprints/admin.py`: Benutzer-/Rollenverwaltung + KI-Einstellungen (`/admin/settings`)
- `services/ai_client.py`: KI‑Provider‑Adapter, Fehler‑Handling, JSON‑Response
  - `get_mistral_client()` / `ensure_gemini_configured()`: lösen Provider-Clients
    zur Laufzeit auf (DB-Key via `services/settings.py` **hat Vorrang** vor
    ENV-Variablen). NIE die alten Modul-Konstanten `MISTRAL_CLIENT`/`genai_client`
    direkt für die Live-Prüfung nutzen – die spiegeln nur den ENV-Zustand beim
    Prozessstart und ignorieren über die Admin-UI gespeicherte Keys.
  - `describe_ai_error()`: übersetzt Provider-Exceptions (v. a. Google
    Rate-/Tages-Limits, `429 ResourceExhausted`) in verständliche Meldungen.
- `services/settings.py` + `services/crypto.py`: Verschlüsselte App-Settings
  (API-Keys) in der DB, Fernet-Key aus `SECRET_KEY` abgeleitet.
- `services/import_service.py`: Teilnehmer-Namenslisten-Import (TXT/CSV/XLSX/ODS/DOCX).
- `services/report_generator.py`: HTML/CSS für Reports, PDF‑Export (WeasyPrint;
  braucht System-Libs Pango/Cairo – siehe `WEASYPRINT_SETUP.md`).
- `models.py`: Kern‑Modelle (Participant, Group, Task, SelfAssessment, AppSetting)
- `utils.py`: File‑Parsing, HTML‑Sanitizing, Helper (z. B. `html_to_plaintext`)

---

## 🔁 Haupt‑Flows (für KI‑Agenten)

### 1) Batch‑KI‑Analyse
`ai_analysis_select_group` → `ai_analysis_select_participants` → `execute_batch_ai_analysis` → UI Status in `ai_analysis_status.html` → API `run_single_analysis_api`

### 2) Einzel‑KI‑Analyse (z. B. „KI neu“ im Report)
`run_ki_analysis` → `generate_report_with_ai` → `_normalize_ki_data` → Speicherung `participant.ki_texts`

### 3) Report‑Bearbeitung
`edit_report` (Template `staerkenanalyse_bericht_vorlage3.html`) → Autosave via `save_report` → optional PDF

### 4) Abschlussbericht
`final_report` → `reports.preview_report_html` (kombiniert FE + SE) → PDF über `reports.generate_pdf_report`

### 5) Teilnehmer-Import
`data_io.import_page` → `data_io.import_names` (POST) → `extract_names_from_file()`
(erkennt Format an Extension, siehe `ALLOWED_IMPORT_EXTENSIONS` in `utils.py`)

### 6) API-Key-Verwaltung
`admin.settings` (GET/POST) → `services/settings.set_setting()` (Fernet-verschlüsselt) →
Provider-Clients lösen den Key beim NÄCHSTEN Request lazy auf (kein Neustart nötig,
sofern der Prozess bereits die neuen Python-Module geladen hat).

---

## 🧬 Domänenlogik (kritisch)

- **Selbsteinschätzung** = reiner Text (keine Riemannkreuze)
- **Fremdeinschätzung** = 2 Seiten (Sozial + Verbal, inkl. Radar‑Charts)
- **Kompetenzbereiche**: „Soziale Kompetenzen“ und „Verbale Kompetenzen“
- **Referenzaufgaben**: Tasks mit `is_example=True` sind funktional identisch zu normalen Aufgaben

---

## 🧪 Typische Fehlerquellen

- **KI‑Antwort enthält Listen** → `_normalize_ki_data()` muss Listen/Dictionaries in Strings umwandeln (fixiert)
- **`participant.ki_texts`** ist JSON‑String; immer `json.loads` verwenden
- **Berichte**: CSS ausschließlich in `services/report_generator.py` ändern (HTML‑Struktur stabil halten)
- **Python-Code-Änderungen brauchen einen vollständigen Server-Neustart**
  (`flask run` lädt `.py`-Änderungen NICHT automatisch nach, anders als Jinja-Templates).
- **KI-Provider-Clients**: Niemals `MISTRAL_CLIENT`/`genai_client` (Modul-Konstanten)
  für Verfügbarkeits-Checks verwenden – siehe oben unter `services/ai_client.py`.
- **JS-Funktionen nicht doppelt in `base.html` UND einem Kind-Template definieren**:
  Die zuletzt im DOM geparste Definition gewinnt und überschreibt die andere
  lautlos (führte einmal dazu, dass eine Prompt-Auswahl nie erkannt wurde).
- **Test-Isolation**: `tests/conftest.py`s `db`-Fixture nutzt SAVEPOINTs
  (`join_transaction_mode="create_savepoint"` + deaktiviertes pysqlite-Autocommit).
  Fixtures, die feste Berechtigungen brauchen, müssen explizit `admin_permissions`/
  `observer_permissions` anfordern – die Basis-Rollen haben bewusst keine Rechte.

---

## 🗃️ Datenmodell (Essentials)

- `Participant`: `observations`, `sk_ratings`, `vk_ratings`, `ki_texts`, `ki_raw_response`
- `Task`: `observation_area`, `is_example`, `current_version`
- `SelfAssessment`: Text für SE
- `AppSetting`: `key`, `value_encrypted` (Fernet), `updated_by` – verwaltet über `/admin/settings`

---

## 🔐 Umgebung & Betrieb

**Env Vars**:
- `DATABASE_URL` (SQLite/PostgreSQL)
- `MISTRAL_API_KEY`, `GOOGLE_API_KEY` (Fallback; DB-Keys über Admin-UI haben Vorrang)
- `SECRET_KEY` (auch Basis für Verschlüsselung der DB-gespeicherten API-Keys!)

**Start lokal**:
- Üblich: `flask run --port 5001`  # Lokal: 5001, Container: 5000

**Google Gemini Free-Tier**: harte Limits (z. B. 5 Anfragen/Minute, 20/Tag je Modell).
`429 ResourceExhausted` ist KEIN Bug, sondern das erwartete Verhalten des Gratis-Kontingents.

**Testdaten**:
- Beispiel-Teilnehmer vorhanden: Gruppe 1 (Trainingsgruppe Herbst 2024) mit 2 Teilnehmern (Laura Becker, Marie Koch), beide mit Selbsteinschätzungen

---

## 📚 Weiterführend

- Struktur & Dateien: `FILE_STRUCTURE.md`
- Workflows: `PROJECT_OVERVIEW.md`
- Prompts: `PROMPT_DOCUMENTATION.md`

---

**Letzte Aktualisierung**: 2026-09-15
