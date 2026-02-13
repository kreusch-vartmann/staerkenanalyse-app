# DEVELOPMENT ROADMAP — Stärkenanalyse-App

> **Erstellt**: 2026-02-09 | **Aktualisiert**: 2026-02-13 | **Version**: 1.0.0 → 1.4.0  
> **Ziel**: Produktionsreife, öffentlich zugängliche Web-Applikation  
> **Hosting**: Infomaniak | **Auth**: Eigene Benutzerverwaltung | **Tenant**: Single-Tenant  
> **Zeitrahmen**: So schnell wie möglich  
> **Status**: ✅ Phase 1 COMPLETE | ✅ Phase 2 COMPLETE | ✅ Phase 3 COMPLETE

---

## Phasenübersicht

| Phase | Inhalt | Status | Zielversion |
|-------|--------|--------|-------------|
| **1** | Benutzerverwaltung + Basis-Sicherheit | ✅ COMPLETE | v1.0.0 |
| **2** | Aufgabengenerator + KI-Gym Learning System | ✅ COMPLETE | v1.1.0 → v1.2.1 |
| **3** | Stabilisierung (Sicherheit, Tests, Funktions-Feinschliff) | ✅ COMPLETE | v1.4.0 |
| **4** | Design-Feinschliff | ⬜ Offen | v1.3.0 |
| **5** | Dokumentation + Produktions-Deployment | ⬜ Offen | v2.0.0 |

---

## Phase 1: Benutzerverwaltung & Basis-Sicherheit (v1.0.0) ✅ COMPLETE

### A — Benutzerverwaltung

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| A1 | `User`-Modell erstellen | ✅ | E-Mail, Passwort-Hash (PBKDF2-SHA256), Rolle, aktiv-Flag, erstellt/geändert-Timestamps |
| A2 | Rollen-System (RBAC) | ✅ | `Role`-Modell, rollen-basiert, flexibel auf Decorators extensible |
| A3 | Standard-Rollen anlegen | ✅ | **Admin**: Vollzugriff; **Beobachter**: nur zugewiesene Gruppen |
| A4 | Gruppen-Zuordnung | ✅ | Many-to-Many: User ↔ Group (via `user_groups` Tabelle) |
| A5 | Login / Logout | ✅ | Flask-Login, Session-basiert (8h lifetime), Login-Seite, Redirect-Logik |
| A6 | Passwort vergessen | ✅ | Admin-basierter Reset-Flow (MVP), generiert 16-Zeichen-PW |
| A7 | `@login_required` überall | ✅ | 60/60 Routes geschützt mit `@login_required` und Rollen-Decorators |
| A8 | `@role_required` Decorator | ✅ | `@admin_required`, `@group_access_required`, `@participant_access_required` |
| A9 | Gruppen-basierte Sichtbarkeit | ✅ | Filter-Helper in decorators.py: `filter_groups_by_access()`, `filter_participants_by_group()` |
| A10 | Admin-UI: Nutzerverwaltung | ✅ | CRUD für User, Rollen zuweisen, Gruppen zuordnen in `/admin/users` |
| A11 | Initialer Admin-Seed | ✅ | CLI-Command `flask create-admin` mit interaktiver Eingabe |
| A12 | Datenmigration | ✅ | Alembic-Migration mit Seed-Rollen (admin, beobachter)

### C₁ — Basis-Sicherheit (parallel zu A)

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| C1 | SECRET_KEY-Management | ✅ | Env-basierte Konfiguration über config.py |
| C2 | Passwort-Hashing | ✅ | PBKDF2-SHA256 via `werkzeug.security` (600k iterations) |
| C3 | Session-Sicherheit | ✅ | `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SECURE=auto`, `SESSION_COOKIE_SAMESITE='Lax'` |
| C4 | Login-Rate-Limiting | 🟡 | `flask-limiter` installiert, 5/min limit in auth.py konfiguriert (nicht global) |
| C5 | CSRF-Schutz prüfen | ✅ | Flask-WTF vorhanden, alle Forms CSRF-geschützt |

**Entscheidungen Phase 1:**
- Rollen zunächst Admin + Beobachter, Framework erlaubt spätere Erweiterung
- Passwort-Vergessen: Für MVP reicht Admin-Reset, E-Mail-Flow optional
- Flask-Login als Auth-Library (bewährt, gut dokumentiert)

---

## Phase 2: Aufgabengenerator + KI-Gym System (v1.1.0) 🟡 PARTIAL

### B — Aufgabengenerator (Beobachtungsaufgaben)

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| B1 | Datenmodell: `Task`, `TaskVersion` | ✅ | Vollständig implementiert mit circular dependency handling |
| B2 | Import bestehender Aufgaben | ✅ | Als hardcoded EXAMPLE_TASKS (Erbengemeinschaft, Plakat) |
| B3 | Aufgaben-Bibliothek UI | ✅ | `/beobachtungsaufgaben` Library mit Beispiel- und eigenen Aufgaben |
| B4 | KI-Generierungslogik | ✅ | Best-Practice Prompt-Engineering für AC-Tasks (ki_services.py) |
| B5 | Knowledge-Base Integration | ✅ | v1.2.0: 12 AC-Aufgabentypen, 10 Kompetenzdimensionen, 6 Zielgruppen, 2 Phasenmodelle |
| B6 | Automatische Generierung | ✅ | Parameter: Beobachtungsbereich (SK/VK), TN-Zahl (1-10), Dauer (5-120 Min) |
| B7 | Bearbeitbare Vorschau | ✅ | Quill.js Rich-Text-Editor mit HTML-Unterstützung |
| B8 | Chat-Interface | ✅ | Chat-Seitenleiste mit KI-Iteration für Aufgaben-Verfeinerung |
| B9 | Chat-Kontext-Management | ✅ | `refine_task_content()` mit conversation_history Parameter |
| B10 | Aufgabe speichern/versionieren | ✅ | Vollständiges Versions-Management mit change_notes |
| B11 | Berechtigungen | ✅ | `@admin_required` auf allen Task-Routes |
| B12 | Zusätzliche Daten einpflegen | 🟡 | Beispiel-Tasks als Context, AIRawResponse-Tracking via KI-Gym |
| **B13** | **KI-Modell-Auswahl** | ✅ | **NEU**: Reusable Modal für Mistral vs. Gemini (visual branding) |
| **B14** | **Group-Tasks Integration** | ✅ | **NEU**: Aufgaben können Gruppen zugeordnet werden (many-to-many) |
| **B15** | **Chat-Refinement Stabilisierung** | ✅ | **NEU v1.2.1**: Sektionen normalisiert, Auto-Save + Reload, konsistente Darstellung |

### B* — KI-Gym Learning System (BONUS Feature) 🧠

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| X1 | Datenmodell: `AIRawResponse`, `ContentEdit` | ✅ | Tracking von KI-Outputs und manuellen Edits |
| X2 | Datenmodell: `LearnedPromptRule` | ✅ | Speicherung generierter Prompt-Verbesserungsregeln |
| X3 | Pattern-Extraktion Service | ✅ | `ai_gym.py` mit length/magnitude/similarity Analyse |
| X4 | Rule-Generierung | ✅ | Automatische Analyse und Regel-Vorschlags-Erstellung |
| X5 | Admin Dashboard | ✅ | `/admin/ki-gym` UI für Training und Rule-Management |
| X6 | Auto-Integration (Tasks) | ✅ | Task-Rules werden automatisch in Prompts eingebunden |
| X7 | Manuelle Integration (Reports) | ✅ | Report-Rules als Vorschläge mit Bestätigung |
| X8 | Confidence-Scoring | ✅ | Bewertung von Rules basierend auf Sample-Anzahl |
| X9 | Content-Edit Auto-Tracking | ✅ | Automatisches Diff-Tracking bei Task-Speicherung |
| X10 | Training-Status-Dashboard | ✅ | Anzeige pro Typ/Bereich mit min. Samples-Anforderung |

### B** — Wissensdatenbank für Aufgabengenerator (v1.2.0) ✅ COMPLETE

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| Y1 | `services/task_knowledge_base.py` erstellen | ✅ | 12 AC-Aufgabentypen (Selbstpräsentation bis Strukturiertes Interview) |
| Y2 | Kompetenzdimensionen mit Ankern | ✅ | 10 Dimensionen (Kommunikation, Teamfähigkeit, Führung, etc.) mit je 5 pos./neg. Indikatoren |
| Y3 | Zielgruppen-Kategorien | ✅ | 6 Zielgruppen (Schüler, Azubis, Trainees, Experten, Führungskräfte, Bestandsmitarbeiter) |
| Y4 | Phasenmodelle | ✅ | 2 Templates (Einfach: 4 Phasen; Komplex: 6 Phasen) mit prozentual Zeitverteilung |
| Y5 | `get_knowledge_for_prompt()` Funktion | ✅ | Intelligentes Selection von geeigneten Aufgaben/Kompetenzen/Phasen basierend auf Parametern |
| Y6 | KI-Prompt-Injection | ✅ | AC-Fachwissen wird in `system_prompt` von `generate_task()` injiziert |
| Y7 | Zielgruppen-Dropdown in UI | ✅ | Neues Form-Feld in `create.html`, speichert in `context_data` |
| Y8 | Target-Group-Durchleitung | ✅ | `target_group` wird von create → generate → `generate_task()` durchgereicht |
| Y9 | `get_target_group_options()` Rendering | ✅ | Hilfsfunktion für Template-Rendering mit Label + Value |
| Y10 | Services-Module erweitern | ✅ | Import in `services/__init__.py` für öffentliche API |

**Entscheidungen Phase 2:**
- ✅ Chat-basierte Iteration statt Prompt-Editing (umgesetzt)
- ✅ Bestehende KI-Infrastruktur erweitert (nicht ersetzt)
- ✅ TN-Zahl beeinflusst Komplexität (in Prompts berücksichtigt)
- ✅ **BONUS**: KI-Gym Learning System für kontinuierliche Verbesserung
- ✅ **BONUS**: Modell-Auswahl-Modal für bessere UX
- ✅ **v1.2.0**: Knowledge-Base statt Web-Recherche (wartbar, versionierbar, offline-ready)

**Neu implementiert in v1.1.0:**
- 🎓 **KI-Gym Learning System**: Automatisches Pattern-Learning aus User-Edits
- 📋 **Beobachtungsaufgaben-Verwaltung**: Vollständige Task-Library mit KI-Generierung
- 🤖 **KI-Modell-Auswahl**: Reusable Modal für Mistral/Gemini Auswahl
- 📊 **Content-Edit-Tracking**: Diff-Metriken für alle manuellen Änderungen
- 🔧 **API-Fixes**: Group-Tasks JSON Response, Batch-Analysis Stabilität

**Neu implementiert in v1.2.0:**
- 🧠 **Assessment-Center Knowledge Base**: 12 Aufgabentypen + 10 Dimensionen + 6 Zielgruppen
- 🎯 **Zielgruppen-Differenzierung**: Target-Group-Dropdown mit KI-Prompt-Anpassung
- 📚 **AC-Fachwissen in Prompts**: Automatische Injection von Best-Practice-Standards in KI-Generierungen
- 🔗 **Intelligente Aufgaben-Selektion**: `get_knowledge_for_prompt()` wählt geeignete Aufgabentypen basierend auf Kontext

**Neu implementiert in v1.2.1:**
- ✅ **Chat-Refinement Stabilisierung**: Fixierte 4-Sektionen-Struktur inkl. Fallbacks
- ✅ **HTML-Cleanup**: Entfernt Markdown-Artefakte und leere Abschnitte
- ✅ **Auto-Save + Reload**: Chat-Ergebnisse werden direkt gespeichert und korrekt geladen

**Noch offen für Phase 2 Completion:**
- ⬜ Beobachtungsbögen-Generierung basierend auf Indikatoren-Matrix (v1.3.0+)
- ⬜ PDF-Export für Observer-Sheets mit Beurteilungsskalen (v1.3.0+)
- ⬜ Multi-Tenant-Support für Aufgaben (optional)

---

## Phase 3: Stabilisierung (v1.4.0)

### C₂ — Erweiterte Sicherheit

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| C6 | Content Security Policy (CSP) | ✅ | Headers gesetzt, Inline-Scripts geprüft |
| C7 | Input-Validation-Audit | ✅ | Pydantic-Validierung eingeführt |
| C8 | Error-Monitoring | ✅ | Bugfender SDK + Global Error Handler |
| C9 | SQL-Injection-Check | ✅ | ORM-Queries auditieren, No-raw-SQL |

### D — Funktionalitäts-Feinschliff

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| D1 | Edge Cases bestehende Features | ✅ | Fehlerbehandlung + Validierungen erweitert, stabile APIs |
| D2 | UX-Verbesserungen | ✅ | Default‑Prompt UX, Prompt‑Badges, Stabilitäts‑Fixes |
| D3 | MistralSozVerb4-Prompt nachbauen | ✅ | Rekonstruiertes Prompt-Template hinzugefügt |

### F — Testing

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| F1 | Auth-Tests | ✅ | Login, Logout, Rollen, Berechtigungen, Gruppen-Sichtbarkeit |
| F2 | Aufgabengenerator-Tests | ✅ | Generierung, Chat, Versionierung |
| F3 | Integrationstests | ✅ | Komplette Workflows E2E |
| F4 | Security-Tests | ✅ | OWASP Top 10, Penetration-Basics |

---

## Phase 4: Design-Feinschliff (v0.8.0)

### E — Design

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| E1 | Design-Entscheidung treffen | ⬜ | Tailwind aufräumen vs. komplettes Redesign (Aufwand/Nutzen bewerten) |
| E2 | Responsive Design | ⬜ | Tablet- und Mobile-Optimierung |
| E3 | Einheitliche Komponenten | ⬜ | Buttons, Cards, Forms, Modals konsistent gestalten |
| E4 | Login- und Admin-Seiten | ⬜ | Professionelles Styling der neuen Auth-Seiten |
| E5 | Barrierefreiheit | ⬜ | WCAG 2.1 AA Basics (Kontraste, Labels, Keyboard-Navigation) |

---

## Phase 5: Go-Live (v1.0.0)

### G — Dokumentation

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| G1 | Benutzer-Handbuch | ⬜ | Anleitung für Beobachter und Admins |
| G2 | Admin-Anleitung | ⬜ | Nutzerverwaltung, Rollensystem, Backup |
| G3 | DEPLOYMENT.md aktualisieren | ⬜ | Neue Auth-Konfiguration, Umgebungsvariablen |

### H — Produktions-Deployment

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| H1 | Domain & SSL (Infomaniak) | ⬜ | HTTPS einrichten, Domain konfigurieren |
| H2 | PostgreSQL Produktion | ⬜ | Infomaniak-DB, Verbindungspool, Tuning |
| H3 | Backup-Strategie | ⬜ | Automatische DB-Backups, Retention-Policy |
| H4 | Monitoring & Alerting | ⬜ | Uptime-Check, Error-Alerts |
| H5 | Go-Live-Checklist | ⬜ | Finale Prüfung aller Punkte vor Launch |

---

## Technische Entscheidungen (Protokoll)

| Datum | Entscheidung | Begründung |
|-------|-------------|-----------|
| 2026-02-09 | Single-Tenant-Architektur | Zunächst eine Instanz pro Organisation |
| 2026-02-09 | Eigene Benutzerverwaltung (kein OAuth) | Einfacher, unabhängig von Drittanbietern |
| 2026-02-09 | Rollen: Admin + Beobachter (erweiterbar) | RBAC-Framework, zunächst 2 Rollen |
| 2026-02-09 | Hosting: Infomaniak | Bestehendes Setup, DSGVO-konform |
| 2026-02-09 | Aufgabengenerator: Chat-basiert, kein Prompt-System | Nutzerfreundlicher, iterativer Workflow |

---

## Offene Fragen (für spätere Klärung)

- [ ] E-Mail-Service für Passwort-Reset: Infomaniak SMTP oder Drittanbieter?
- [ ] Web-Recherche für Aufgabengenerator: Welche API? (Tavily, Serper, SearXNG?)
- [ ] Design-Entscheidung: Tailwind aufräumen vs. Redesign?
- [ ] Zusätzliche Daten für Aufgabengenerator: Wann/wie bereitstellen?
- [ ] DSGVO: Datenschutzerklärung, Impressum, Cookie-Banner nötig?

---

*Diese Datei dient als zentrale Referenz für alle Entwicklungssessions. Status-Updates direkt in den Tabellen pflegen.*
