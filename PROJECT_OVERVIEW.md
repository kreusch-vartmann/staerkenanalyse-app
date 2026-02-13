# PROJECT_OVERVIEW.md

**Generiert am**: 2026-02-13 (v1.4.0)

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
- **Blueprints**: 10 (auth, admin, groups, participants, analysis, data_io, prompts, explanation_blocks, reports, observation_tasks)
- **Templates**: 35+
- **Datenbank-Models**: 15+ (inkl. Task/TaskVersion, KI-Gym Modelle, Report-Modelle)

---

## 🔗 Routing-Übersicht

| Blueprint | Routen-Anzahl | Zweck |
|-----------|---------------|-------|
| auth | 3 | Login, Logout, Passwortwechsel |
| admin | 10+ | Nutzerverwaltung, Rollen, KI-Gym |
| groups | 5 | Gruppenverwaltung |
| participants | 9 | Teilnehmerverwaltung & Selbsteinschätzung |
| analysis | 12 | KI-Analyse, Fremdeinschätzung & Abschlussberichte |
| data_io | 9 | Import/Export, Dateneingabe |
| prompts | 4 | Prompt-Management |
| explanation_blocks | 4 | Erklärungstexte für Berichte |
| reports | 10+ | Report-Konfiguration, PDF-Generierung, Vorschau |
| observation_tasks | 10+ | Aufgaben-Generierung, Chat-Refinement, Versionierung |

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
- Python 3.11+
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

## 🆕 Neue Features in v1.4.0

### Phase 3 Abschluss
- Prompt‑Dokumentation + Default‑Prompt (UI/DB)
- Security Audit Report + Incident Runbooks
- Rekonstruiertes MistralSozVerb4‑Prompt (Basis‑Template)

## 🆕 Neue Features in v1.3.1

### Stabilisierung & Tests
- Auth/RBAC Tests für Login, Rollen, Gruppen-/Teilnehmerzugriff
- Admin-Flow Tests für User-CRUD und Passwort-Reset
- RBAC Edge-Cases für unzugewiesene Gruppen und fehlende Ressourcen

## 🆕 Neue Features in v1.2.1

### Chat-Refinement Stabilisierung
- **Sektionen normalisiert**: Ausgabe wird auf 4 Standard-Sektionen vereinheitlicht
- **Auto-Save + Reload**: Chat-Änderungen werden gespeichert und korrekt geladen
- **HTML-Cleanup**: Entfernt Markdown-Artefakte und leere Bereiche

## 🆕 Neue Features in v1.2.0

### Assessment-Center Knowledge Base
- **12 AC-Aufgabentypen** + 10 Kompetenzdimensionen
- **Zielgruppen-Differenzierung**: Prompts passen sich Zielgruppe an
- **Prompt-Injection**: Fachwissen wird automatisch in KI-Prompts integriert

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
