# PROJECT_OVERVIEW.md

**Generiert am**: 2026-02-08 (v0.4.0)

---

## 🎯 Projektziel

Flask-basierte Web-Applikation für **Stärkenanalyse** mit KI-gestützter Berichterstellung:
- Teilnehmermanagement in Gruppen
- Dateneingabe (Beobachtungen, Selbsteinschätzungen)
- KI-Analyse via Mistral/Google Gemini API
- Konfigurierbare PDF-Berichte mit Report-Templates
- Automatisches Backup-System für Datenbank & Prompts

---

## 📊 Projektstatistik

- **Python-Dateien**: 25+
- **Blueprints**: 7 (groups, participants, analysis, data_io, prompts, explanation_blocks, reports)
- **Templates**: 35+
- **Datenbank-Models**: 10 (Group, Participant, Prompt, SelfAssessment, ExplanationBlock, ReportTemplate, ReportConfiguration, CompanyLogo, ClientLogo, SignatureImage)

---

## 🔗 Routing-Übersicht

| Blueprint | Routen-Anzahl | Zweck |
|-----------|---------------|-------|
| groups | 5 | Gruppenverwaltung |
| participants | 9 | Teilnehmerverwaltung & Selbsteinschätzung |
| analysis | 12 | KI-Analyse, Fremdeinschätzung & Abschlussberichte |
| data_io | 9 | Import/Export, Dateneingabe |
| prompts | 4 | Prompt-Management |
| explanation_blocks | 4 | Erklärungstexte für Berichte |
| reports | 10+ | Report-Konfiguration, PDF-Generierung, Vorschau |

---

## 🧩 Modul-Abhängigkeiten

**app.py importiert**:
- extensions (db, migrate)
- models (Group, Participant, Prompt, SelfAssessment)
- blueprints (alle 6)

**Blueprints importieren**:
- models.py (für ORM-Queries)
- extensions.py (für db.session)
- ki_services.py (nur analysis.py)
- utils.py (nur analysis.py)

**Keine zirkulären Abhängigkeiten detected** ✅

---

## 🛠️ Entwicklungsumgebung

**Voraussetzungen**:
- Python 3.12.12
- venv: `/home/timok/kDrive/Dokumente/staerkenanalyse-app/venv`
- System-Dependencies: libcairo, libpango (für WeasyPrint)

**Setup-Schritte**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # API-Keys eintragen
flask db upgrade
python app.py
```

---

## 🆕 Neue Features in v0.4.0

### Backup-System 🔒
- **Automatische Backups**: Beim App-Start (`backup_database.py`)
- **Manuelle Backups**: `flask backup-db` / `python backup_database.py`
- **Retention-Management**: Max. 50 Backups, automatische Bereinigung
- **Prompts-Export**: `flask export-prompts` → JSON-Dateien in `backups/prompts_export/`

### Report-Konfiguration 📄
- **UI-Template**: `templates/reports/configure.html` mit Tailwind CSS Accordions
- **6 Konfigurationsbereiche**: Design, Deckblatt, Selbst-/Fremdeinschätzung, Abschlussblatt, Hinweisblatt
- **Logo-Upload**: Company & Client Logos pro Gruppe
- **Unterschriften-Management**: JPG-Bilder für Leitung FE/SE im Abschlussblatt-Bereich

### Prompt-Management 🧠
- **Unique-Constraint**: Prompt-Namen müssen eindeutig sein (neue Migration)
- **Default-Prompts**: `load_default_prompts.py` lädt Standard-Prompts

---

## 🔐 Security Considerations

1. **API Keys in .env** (nicht in Git!)
2. **SECRET_KEY**: Aktuell `os.urandom(24)` → Für Production: Persistente Key in .env
3. **Debug-Modus**: Für Production deaktivieren
4. **SQLite**: Für Production → PostgreSQL migrieren

---

**Für detaillierte Informationen siehe [CONTEXT.md](CONTEXT.md)**
