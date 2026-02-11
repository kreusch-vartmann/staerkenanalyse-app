# Feature-Checkliste: Stärkenanalyse-App

**Datum:** 11.02.2026 (v1.3.1)
**Branch:** main
**Modus:** Lokale Entwicklung (SQLite)

---

## Core Features (Basis-Funktionalität)

### 1. Dashboard
- [x] Zeigt Statistiken (Gruppen, Teilnehmer, abgeschlossene Analysen)
- [x] Zeigt kürzlich aktualisierte Teilnehmer
- [x] Navigation funktioniert (Sidebar + Dashboard-Kacheln)
- [x] Workflow-Kacheln: Gruppen, Teilnehmer, Selbsteinschätzung, Beobachtungsdaten, KI-Analyse, Fremdeinschätzung, Abschlussberichte
- [x] Verwaltungs-Kacheln: Prompts, Text, Import, Export

### 2. Gruppenverwaltung (`/groups`)
- [x] Liste aller Gruppen anzeigen (Accordion-Ansicht mit Suche)
- [x] Neue Gruppe anlegen
- [x] Gruppe bearbeiten (Name)
- [x] Gruppe löschen (mit allen Teilnehmern)
- [x] Teilnehmer einer Gruppe anzeigen (Accordion aufklappen)
- [x] Teilnehmer direkt aus Gruppenansicht hinzufügen

### 3. Teilnehmerverwaltung (`/participants`)
- [x] Alle Teilnehmer gruppiert anzeigen (Accordion mit Suche)
- [x] Status-Indikatoren pro Teilnehmer: SE, BD, KI, AB
- [x] Teilnehmer bearbeiten (umbenennen)
- [x] Teilnehmer löschen
- [x] Schnellzugriff auf alle Funktionen pro Teilnehmer (Selbsteinschätzung, Beobachtungsdaten, KI-Analyse, Fremdeinschätzung, Abschlussbericht)
- [x] Abschlussbericht-Button immer sichtbar (ausgegraut wenn Voraussetzungen fehlen)

### 4. Beobachtungsdaten (`/participant/<id>/data_entry`)
- [x] Dateneingabemaske mit 28 Beobachtungsfeldern (7 Kategorien)
- [x] Beobachtungen speichern (JSON in DB)
- [x] Auto-Save funktioniert
- [x] Gespeicherte Daten laden beim erneuten Öffnen
- [x] Übersichtsseite mit Accordion und Suche (`/data-entry/rework`)

### 5. Selbsteinschätzung (`/participant/<id>/self_assessment`)
- [x] Texteingabe für Selbsteinschätzung
- [x] Rich-Text-Editor (Quill.js)
- [x] Speichern in `SelfAssessment.content`
- [x] Übersichtsseite mit Accordion und Suche (`/self-assessments`)

### 6. KI-Analyse (Batch & Einzeln)
- [x] Gruppe für Analyse auswählen (`/ai_analysis/select_group`)
- [x] Teilnehmer auswählen (`/ai_analysis/group/<id>`)
- [x] Prompt auswählen
- [x] KI-Provider auswählen (Mistral, Google Gemini)
- [x] Batch-Analyse starten
- [x] Status-Seite anzeigen
- [x] Fortschritt in Echtzeit verfolgen

### 7. Fremdeinschätzung (`/foreign-assessments`)
- [x] Übersichtsseite mit Accordion und Suche
- [x] Status pro Teilnehmer (vorhanden/fehlend)
- [x] Fremdeinschätzung bearbeiten (Rich-Text-Editor mit Quill.js)
- [x] PDF-Export der Fremdeinschätzung
- [x] Radardiagramme in PDF einbetten (7 Kategorien)

### 8. Abschlussberichte (`/final-reports`)
- [x] Übersichtsseite mit Accordion und Suche
- [x] Status-Anzeige: Fremdeinschätzung + Selbsteinschätzung vorhanden?
- [x] Abschlussbericht erstellen (Fremd + Selbst kombiniert)
- [x] Deckblatt mit Teilnehmer-Info
- [x] Erklärungsblöcke (konfigurierbar)
- [x] PDF-Generierung

### 9. Prompt-Verwaltung (`/prompts`)
- [x] Liste aller Prompts anzeigen
- [x] Neuen Prompt erstellen
- [x] Prompt bearbeiten
- [x] Prompt löschen

### 10. Erklärungsblöcke (`/explanation-blocks`)
- [x] Liste aller Erklärungsblöcke anzeigen
- [x] Neuen Block erstellen (Rich-Text-Editor)
- [x] Block bearbeiten
- [x] Block löschen
- [x] Reihenfolge und Sichtbarkeit konfigurierbar

---

## Import/Export Features

### 11. Import (`/import`)
- [x] Import-Seite anzeigen
- [x] Namen aus Datei importieren (TXT, CSV, PDF, DOCX)
- [x] Neue Gruppe beim Import erstellen
- [x] Teilnehmer automatisch anlegen

### 12. Export (`/export_selection`)
- [x] Export-Seite anzeigen
- [x] Gruppen und Teilnehmer zur Auswahl anzeigen
- [x] Export als Excel (`.xlsx`)
- [x] Export als CSV (`.csv`)
- [x] Beobachtungsdaten mit exportieren

---

## Sicherheit & Infrastruktur

### 13. CSRF-Protection
- [x] Flask-WTF integriert
- [x] CSRF-Token in allen Formularen
- [x] CSRF-Header für AJAX/Fetch-Endpunkte integriert

### 14. PDF-Generierung (WeasyPrint)
- [x] WeasyPrint installiert und funktionsfähig
- [x] System-Dependencies vorhanden (libcairo, libpango)
- [x] PDF enthält Radardiagramme (Base64-Encoding)

### 15. Datenbank
- [x] SQLAlchemy ORM mit Flask-SQLAlchemy
- [x] Flask-Migrate (Alembic) für Migrationen
- [x] 10 Models: Group, Participant, Prompt, SelfAssessment, ExplanationBlock, ReportTemplate, ReportConfiguration, CompanyLogo, ClientLogo, SignatureImage

### 16. Report-Konfiguration (NEU in v0.4.0) 📄
- [x] Report-Konfiguration UI (`/reports/<group_id>/configure`)
- [x] Tailwind CSS Accordions (6 Bereiche)
- [x] Template-Auswahl (ReportTemplate Model)
- [x] Logo-Upload (Company & Client)
- [x] Unterschriften-Verwaltung (FE/SE im Abschlussblatt-Bereich)
- [x] Modul-Aktivierung (Cover, SE, FE, Closing, Info, TOC)
- [x] Form-Validierung mit CSRF-Token
- [x] Nested-Form-Fix (keine verschachtelten `<form>` Tags mehr)
- [x] HTML-Vorschau (`/reports/<group_id>/preview/<pid>`)
- [x] PDF-Download (`/reports/<group_id>/generate-pdf/<pid>`)

### 17. Backup-System (NEU in v0.4.0) 🔒
- [x] Automatische Backups beim App-Start (`backup_database.py`)
- [x] Manuelle Backups: `flask backup-db` / `python backup_database.py`
- [x] Retention-Management (max. 50 Backups)
- [x] Backup-Verzeichnis: `backups/`
- [x] Timestamped Backups mit Grund (startup, manual, before_migration)
- [x] Größenverifizierung nach Backup
- [x] Prompts-Export: `flask export-prompts`
- [x] JSON-Export aller Prompts mit Metadaten (`backups/prompts_export/`)

### 18. Prompt-Management-Improvements (NEU in v0.4.0) 🧠
- [x] Unique-Constraint für Prompt-Namen (Migration: `65898bde1230`)
- [x] Default-Prompts-Loader (`load_default_prompts.py`)
- [x] Prompt-Bearbeitungs-UI verbessert
- [x] Error-Handling bei Duplikaten

---

## UI/UX Features

- [x] Sidebar-Navigation mit allen Workflow-Schritten
- [x] Einheitliches Accordion-Pattern auf allen Übersichtsseiten
- [x] Suche mit Autocomplete auf allen Übersichtsseiten
- [x] Status-Indikatoren (SE, BD, KI, AB) auf Teilnehmerseite
- [x] Breadcrumb-Navigation
- [x] Responsive Design (Tailwind CSS)

---

**Status:** Implementierung abgeschlossen (inkl. Aufgabengenerator + Chat-Refinement Stabilisierung)

---

## Beobachtungsaufgaben (Assessment-Center Tasks)

### 19. Aufgabenbibliothek & Generierung
- [x] Aufgabenbibliothek (`/beobachtungsaufgaben`) mit Filter & Suche
- [x] Neue Aufgabe erstellen (Beobachtungsbereich, Dauer, TN-Zahl)
- [x] Zielgruppen-Auswahl (Schüler, Azubis, Trainees, Experten, Führungskräfte, Bestandsmitarbeiter)
- [x] Knowledge-Base-gestützte Generierung (12 Aufgabentypen + Kompetenzdimensionen)
- [x] HTML-Ausgabe auf 4 Standard-Sektionen normalisiert

### 20. Chat-Refinement
- [x] Chat-Seitenleiste im Editor
- [x] KI-Refinement der Aufgaben
- [x] Auto-Save + Reload nach Chat-Änderungen
- [x] Keine leeren Sektionen nach Refinement
- [x] Markdown-Artefakte entfernt
