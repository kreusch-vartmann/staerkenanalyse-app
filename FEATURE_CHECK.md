# Feature-Checkliste: Stärkenanalyse-App

**Datum:** 06.02.2026
**Branch:** feature/selbsteinschaetzung-abschlussbericht
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
- [x] CSRF-Exempt für AJAX-Endpunkte (explizit konfiguriert)

### 14. PDF-Generierung (WeasyPrint)
- [x] WeasyPrint installiert und funktionsfähig
- [x] System-Dependencies vorhanden (libcairo, libpango)
- [x] PDF enthält Radardiagramme (Base64-Encoding)

### 15. Datenbank
- [x] SQLAlchemy ORM mit Flask-SQLAlchemy
- [x] Flask-Migrate (Alembic) für Migrationen
- [x] 4 Models: Group, Participant, Prompt, SelfAssessment

---

## UI/UX Features

- [x] Sidebar-Navigation mit allen Workflow-Schritten
- [x] Einheitliches Accordion-Pattern auf allen Übersichtsseiten
- [x] Suche mit Autocomplete auf allen Übersichtsseiten
- [x] Status-Indikatoren (SE, BD, KI, AB) auf Teilnehmerseite
- [x] Breadcrumb-Navigation
- [x] Responsive Design (Tailwind CSS)

---

**Status:** Implementierung abgeschlossen
