# CONTEXT.md - KI-optimierter Projektkontext

**Aktualisiert am**: 2026-02-14 (Version 1.5.0)

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
- `services/ai_client.py`: KI‑Provider‑Adapter, Fehler‑Handling, JSON‑Response
- `services/report_generator.py`: HTML/CSS für Reports, PDF‑Export
- `models.py`: Kern‑Modelle (Participant, Group, Task, SelfAssessment)
- `utils.py`: File‑Parsing, HTML‑Sanitizing, Helper (z. B. `html_to_plaintext`)

---

## 🔁 Haupt‑Flows (für KI‑Agenten)

### 1) Batch‑KI‑Analyse
`ai_analysis_select_group` → `ai_analysis_select_participants` → `execute_batch_ai_analysis` → UI Status in `ai_analysis_status.html` → API `run_single_analysis_api`

### 2) Einzel‑KI‑Analyse (z. B. „KI neu“ im Report)
`run_ki_analysis` → `generate_report_with_ai` → `_normalize_ki_data` → Speicherung `participant.ki_texts`

### 3) Report‑Bearbeitung
`edit_report` (Template `staerkenanalyse_bericht_vorlage3.html`) → Autosave via `save_report` → optional PDF

### 4) Abschlussbericht
`final_report` → `reports.preview_report_html` (kombiniert FE + SE) → PDF über `reports.generate_pdf_report`

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

---

## 🗃️ Datenmodell (Essentials)

- `Participant`: `observations`, `sk_ratings`, `vk_ratings`, `ki_texts`, `ki_raw_response`
- `Task`: `observation_area`, `is_example`, `current_version`
- `SelfAssessment`: Text für SE

---

## 🔐 Umgebung & Betrieb

**Env Vars**:
- `DATABASE_URL` (SQLite/PostgreSQL)
- `MISTRAL_API_KEY`, `GOOGLE_API_KEY`

**Start lokal**:
- Üblich: `flask run --port 5002`

**Testdaten**:
- Beispiel‑Teilnehmer vorhanden: Gruppe 1, Participant 1 (komplett mit SE+FE)

---

## 📚 Weiterführend

- Struktur & Dateien: `FILE_STRUCTURE.md`
- Workflows: `PROJECT_OVERVIEW.md`
- Prompts: `PROMPT_DOCUMENTATION.md`

---

**Letzte Aktualisierung**: 2026-02-14
