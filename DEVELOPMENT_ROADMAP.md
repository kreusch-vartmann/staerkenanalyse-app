# DEVELOPMENT ROADMAP — Stärkenanalyse-App

> **Erstellt**: 2026-02-09 | **Version**: 0.4.0 → 1.0.0  
> **Ziel**: Produktionsreife, öffentlich zugängliche Web-Applikation  
> **Hosting**: Infomaniak | **Auth**: Eigene Benutzerverwaltung | **Tenant**: Single-Tenant  
> **Zeitrahmen**: So schnell wie möglich  
> **Status**: � Phase 1 COMPLETE - Ready for Phase 2

---

## Phasenübersicht

| Phase | Inhalt | Status | Zielversion |
|-------|--------|--------|-------------|
| **1** | Benutzerverwaltung + Basis-Sicherheit | ✅ COMPLETE | v1.0.0 |
| **2** | Aufgabengenerator | ⬜ Offen | v1.1.0 |
| **3** | Stabilisierung (Sicherheit, Tests, Funktions-Feinschliff) | ⬜ Offen | v1.2.0 |
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

## Phase 2: Aufgabengenerator (v0.6.0)

### B — Aufgabengenerator

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| B1 | Datenmodell: `Task`, `TaskVersion` | ⬜ | Aufgaben-DB mit Versionierung, Beobachtungsbereich (SK/VK), TN-Zahl, Dauer |
| B2 | Import bestehender Aufgaben | ⬜ | .doc-Import der 2 bestehenden Aufgaben (je 1× SK, 1× VK) als Referenz |
| B3 | Aufgaben-Bibliothek UI | ⬜ | Übersicht aller Aufgaben, Filter nach Bereich/Dimension, Vorschau |
| B4 | KI-Generierungslogik | ⬜ | Prompt-Engineering für Aufgabenerstellung, Mistral (default) + Gemini |
| B5 | Web-Recherche-Integration | ⬜ | Recherche zu AC-Best-Practices pro Beobachtungsdimension |
| B6 | Automatische Generierung | ⬜ | Parameter: Beobachtungsbereich, TN-Zahl (1-6), Dauer (25-35 Min) |
| B7 | Bearbeitbare Vorschau | ⬜ | Rich-Text-Editor (Quill.js, bereits im Projekt) unter dem Chat |
| B8 | Chat-Interface | ⬜ | Chat-Fenster über der Vorschau für iterative Änderungswünsche an die KI |
| B9 | Chat-Kontext-Management | ⬜ | Konversationshistorie, Aufgabe + Änderungen als Kontext mitgeben |
| B10 | Aufgabe speichern/versionieren | ⬜ | Speichern als neue Version, Versionshistorie einsehbar |
| B11 | Berechtigungen | ⬜ | Nur Admins dürfen Aufgaben erstellen/bearbeiten |
| B12 | Zusätzliche Daten einpflegen | ⬜ | Anonymisierte Beobachtungsdaten, Berichte, Dimensionen-Infos als Kontext |

**Entscheidungen Phase 2:**
- Kein Prompt-Auswahl-System (anders als Berichterstellung), sondern automatischer Prompt
- Chat-basierte Iteration statt Prompt-Editing
- Bestehende KI-Infrastruktur (`ki_services.py`) erweitern, nicht ersetzen
- TN-Zahl beeinflusst Komplexität und Dauer der generierten Aufgabe

---

## Phase 3: Stabilisierung (v0.7.0)

### C₂ — Erweiterte Sicherheit

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| C6 | Content Security Policy (CSP) | ⬜ | Headers setzen, Inline-Scripts minimieren |
| C7 | Input-Validation-Audit | ⬜ | Alle Eingabefelder auf Sanitization prüfen |
| C8 | Error-Monitoring | ⬜ | Sentry oder vergleichbar, strukturiertes Logging |
| C9 | SQL-Injection-Check | ⬜ | SQLAlchemy-Queries auditieren |

### D — Funktionalitäts-Feinschliff

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| D1 | Edge Cases bestehende Features | ⬜ | Fehlerbehandlung, Validierungen, Ladezeiten |
| D2 | UX-Verbesserungen | ⬜ | Fehlermeldungen, Lädeindikatoren, Bestätigungsdialoge |
| D3 | MistralSozVerb4-Prompt nachbauen | ⬜ | Verlorenen optimierten Prompt rekonstruieren |

### F — Testing

| # | Aufgabe | Status | Details |
|---|---------|--------|---------|
| F1 | Auth-Tests | ⬜ | Login, Logout, Rollen, Berechtigungen, Gruppen-Sichtbarkeit |
| F2 | Aufgabengenerator-Tests | ⬜ | Generierung, Chat, Versionierung |
| F3 | Integrationstests | ⬜ | Komplette Workflows E2E |
| F4 | Security-Tests | ⬜ | OWASP Top 10, Penetration-Basics |

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
