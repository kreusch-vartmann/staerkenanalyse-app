# 🔍 Feature-Checkliste: Stärkenanalyse-App

**Datum:** 06.02.2026  
**Branch:** feature/selbsteinschaetzung-abschlussbericht  
**Modus:** Lokale Entwicklung (SQLite)

---

## ✅ Core Features (Basis-Funktionalität)

### 1. Dashboard
- [ ] Zeigt Statistiken (Gruppen, Teilnehmer, abgeschlossene Analysen)
- [ ] Zeigt kürzlich aktualisierte Teilnehmer
- [ ] Navigation funktioniert

### 2. Gruppenverwaltung (`/groups`)
- [ ] Liste aller Gruppen anzeigen (mit Pagination)
- [ ] Neue Gruppe anlegen
- [ ] Gruppe bearbeiten (Name, Beschreibung)
- [ ] Gruppe löschen (mit allen Teilnehmern)
- [ ] Teilnehmer einer Gruppe anzeigen (`/group/<id>/participants`)

### 3. Teilnehmerverwaltung (`/participants`)
- [ ] Liste aller Teilnehmer anzeigen
- [ ] Neuen Teilnehmer zu Gruppe hinzufügen
- [ ] Mehrere Teilnehmer gleichzeitig hinzufügen
- [ ] Teilnehmer bearbeiten (Name, E-Mail)
- [ ] Teilnehmer löschen

### 4. Dateneingabe (Fremdeinschätzung)
- [ ] Dateneingabemaske öffnen (`/participant/<id>/data_entry`)
- [ ] 28 Beobachtungsfelder anzeigen (nach Kategorien gruppiert)
- [ ] Beobachtungen speichern (JSON in DB)
- [ ] Auto-Save funktioniert
- [ ] Gespeicherte Daten laden beim erneuten Öffnen

**Kategorien:**
1. Arbeitstechniken & Selbstorganisation (4 Felder)
2. Sozial- & Selbstkompetenz (4 Felder)
3. Methoden- & Problemlösungskompetenzen (4 Felder)
4. Fremdsprachenkompetenzen (4 Felder)
5. IKT-Kompetenzen (4 Felder)
6. Ökologische Nachhaltigkeit (4 Felder)
7. Stärken & Ressourcen (4 Felder)

### 5. KI-Analyse (Batch & Einzeln)
- [ ] Gruppe für Analyse auswählen (`/ai_analysis/select_group`)
- [ ] Teilnehmer auswählen (`/ai_analysis/group/<id>`)
- [ ] Prompt auswählen
- [ ] KI-Provider auswählen (Mistral, Google Gemini)
- [ ] Batch-Analyse starten
- [ ] Status-Seite anzeigen (`/ai_analysis_status`)
- [ ] Fortschritt in Echtzeit verfolgen
- [ ] Abgebrochene Analysen fortsetzen

### 6. Berichtserstellung
- [ ] Bericht anzeigen (HTML) (`/edit_report/<participant_id>`)
- [ ] Bericht bearbeiten (Inline-Editing mit ContentEditable)
- [ ] Änderungen speichern
- [ ] PDF generieren (`/bericht/<participant_id>/pdf`)
- [ ] PDF-Download
- [ ] Radardiagramme in PDF einbetten (7 Kategorien)

### 7. Prompt-Verwaltung (`/prompts`)
- [ ] Liste aller Prompts anzeigen
- [ ] Neuen Prompt erstellen
- [ ] Prompt bearbeiten
- [ ] Prompt löschen
- [ ] Prompt-Content über API abrufen (`/api/prompt/<id>`)

---

## 🚧 Import/Export Features

### 8. Import (`/import`)
- [ ] Import-Seite anzeigen
- [ ] Namen aus Datei importieren (TXT, CSV, PDF, DOCX)
- [ ] Neue Gruppe beim Import erstellen
- [ ] Teilnehmer automatisch anlegen

### 9. Export (`/export_selection`)
- [ ] Export-Seite anzeigen
- [ ] Gruppen zur Auswahl anzeigen
- [ ] Teilnehmer auswählen
- [ ] Export als Excel (`.xlsx`)
- [ ] Export als CSV (`.csv`)
- [ ] Beobachtungsdaten mit exportieren (flache Struktur)

---

## 🆕 Fehlende Features (Selbsteinschätzung & Abschlussberichte)

### 10. Selbsteinschätzung (FEHLT KOMPLETT)
- [ ] Dateneingabemaske für Selbsteinschätzung
- [ ] 28 Selbsteinschätzungsfelder (parallel zu Fremdeinschätzung)
- [ ] Speichern in `SelfAssessment.self_ratings` (JSON)
- [ ] Model existiert bereits: `models.SelfAssessment`
- [ ] Routes fehlen komplett

**Benötigt:**
- Blueprint-Route: `/participant/<id>/self_assessment`
- Template: `self_assessment_entry.html`
- API-Route: `/save_self_assessment/<id>` (POST)

### 11. Abschlussberichte (FEHLT KOMPLETT)
- [ ] Fremdeinschätzung + Selbsteinschätzung kombinieren
- [ ] Vergleich Fremd- vs. Selbsteinschätzung visualisieren
- [ ] Deckblatt (Participant-Info, Group, Datum)
- [ ] Erläuterungsblatt (Kompetenzübersicht, Legende)
- [ ] PDF-Generierung mit allen 3 Teilen

**Benötigt:**
- Blueprint-Route: `/final_report/<participant_id>`
- Template: `final_report.html`
- PDF-Route: `/final_report/<participant_id>/pdf`

### 12. Dateneingabe Rework (`/data-entry/rework`)
- [ ] Kombinierte Auswahl- und Eingabeseite
- [ ] Gruppe auswählen, Teilnehmer auswählen
- [ ] Direkt Beobachtungen eingeben (ohne Reload)
- [ ] Status: Existiert als Route, aber unklar ob vollständig implementiert

### 13. Dateneingabe Search (`/data-entry/search`)
- [ ] Teilnehmer-Suchfunktion
- [ ] Nach Name suchen
- [ ] Direkt zur Dateneingabe springen
- [ ] Status: Route existiert, muss getestet werden

---

## 🐛 Bekannte Probleme (aus früheren Sessions)

### 14. PDF-Generierung (WeasyPrint)
- [ ] WeasyPrint installiert und funktionsfähig
- [ ] System-Dependencies vorhanden (libcairo, libpango, libgdk-pixbuf)
- [ ] PDF enthält alle Radardiagramme (Base64-Encoding)
- [ ] Unicode-Zeichen werden korrekt dargestellt

### 15. KI-API-Fehlerbehandlung
- [ ] Rate-Limits richtig gehandhabt
- [ ] Timeouts abgefangen
- [ ] API-Key-Validierung
- [ ] Fehler werden benutzerfreundlich angezeigt

### 16. Datenbank-Migrationen
- [ ] Alembic-Migration `ffbd6aad0758` angewendet
- [ ] Alle 4 Models existieren (Group, Participant, Prompt, SelfAssessment)
- [ ] Foreign Keys korrekt
- [ ] JSON-Felder funktionieren (observations, self_ratings, ki_report)

---

## 📊 Testing-Plan

### Phase 1: Basis-Features testen (30 Min)
1. Dashboard öffnen → Statistiken prüfen
2. Gruppe anlegen → "Test-Gruppe 2026"
3. Teilnehmer hinzufügen → 3-5 Teilnehmer
4. Dateneingabe → Beobachtungen für 1 Teilnehmer
5. KI-Analyse → Batch-Analyse für Test-Gruppe
6. Bericht anzeigen → HTML-Report prüfen
7. PDF generieren → Download testen

### Phase 2: Import/Export testen (15 Min)
8. Import → Teilnehmer aus CSV importieren
9. Export → Excel-Export testen
10. Export → CSV-Export testen

### Phase 3: Fehlende Features identifizieren (15 Min)
11. Selbsteinschätzung → Prüfen ob Route/Template existiert
12. Abschlussberichte → Prüfen ob implementiert
13. Dateneingabe Rework → Funktionalität testen
14. Dateneingabe Search → Suchfunktion testen

### Phase 4: Bugfixing & Implementierung
15. Liste der fehlenden Features erstellen
16. Priorität festlegen (HIGH, MEDIUM, LOW)
17. Implementation Plan erstellen
18. Features umsetzen

---

## 🎯 Prioritäten für Implementierung

### HIGH (Muss vor Merge sein)
1. **Selbsteinschätzung komplett** - Dateneingabe + Speicherung
2. **Abschlussberichte** - Fremd + Selbst kombiniert
3. **PDF-Generierung testen** - Muss funktionieren

### MEDIUM (Nice-to-have)
4. **Dateneingabe Rework** - Verbesserte UX
5. **Dateneingabe Search** - Schnellzugriff
6. **CSRF-Protection** - Sicherheit (Flask-WTF bereits installiert)

### LOW (Optional)
7. **Docker PostgreSQL Migration** - Vollständige Umstellung
8. **Performance-Optimierung** - N+1 Queries vermeiden
9. **Error-Handling verbessern** - Bessere Fehlermeldungen

---

## 📝 Nächste Schritte

1. **Systematisch testen** - Jedes Feature durchgehen
2. **Fehler dokumentieren** - Screenshots + Fehlermeldungen
3. **To-Do-Liste erstellen** - Mit manage_todo_list
4. **Features implementieren** - Schritt für Schritt
5. **Testing wiederholen** - Bis alles funktioniert
6. **Commit + Push** - Regelmäßig sichern

---

**Status:** 🔍 Analyse läuft...
