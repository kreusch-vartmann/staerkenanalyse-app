# Changelog

## Unreleased

### PDF-Berichte (Fremdeinschätzung, Selbsteinschätzung, Gesamtbericht)
- Fix: Leerseite und abgeschnittener Text bei längeren Fremdeinschätzungen. Die Sidebar ist jetzt Teil der Seitengestaltung (`@page`, running elements) statt einer Flex-Spalte im Seiteninhalt; Text fließt auf beliebig viele Seiten, Sidebar und „Seite X von Y“ wiederholen sich automatisch.
- Fremdeinschätzung: je ein Abschnitt pro Seite (Sozial, Verbal, Zusammenfassung); Zusammenfassung als hervorgehobener Kasten; größere Radar-Diagramme; Silbentrennung.
- Alle PDF-Wege (Gesamt, SE, FE, alte URL `/bericht/<id>/pdf`) nutzen denselben `ReportGenerator`; das alte Template `bericht_pdf_vorlage.html` entfällt.
- Vorschau zeigt das echte PDF (iframe) statt eines HTML-Nachbaus; Warnung, wenn ein Text mehr Seiten braucht als vorgesehen.
- Berichtstexte werden bereinigt (HTML) bzw. escaped (Klartext); Klartext-Zeilenumbrüche werden zu Absätzen.
- Schrift Inter liegt lokal in `static/fonts/`.
- Editor: Wortzähler je Textfeld; Standard-Prompt `ReubelRiemannV1` mit Wortbudget (`flask sync-prompt reubelriemannv1.txt` für Produktion).
- Neue Layout-Regressionstests (`tests/integration/test_report_pdf_layout.py`).

## 1.4.0 — 2026-02-13

### Phase 3 Complete
- Added default prompt support (UI + DB) and prompt documentation.
- Added security audit report and incident runbooks.
- Reconstructed MistralSozVerb4 prompt template for analysis.

### Tests & Migrations
- Added prompt default integration tests.
- Stabilized Alembic migrations (SQLite batch operations + merged heads).

## 1.3.1 — 2026-02-11

### Stabilization & Tests
- Added Auth/RBAC integration tests (login/logout/password change, access control).
- Added admin user management flow tests (create/edit/toggle/reset/delete).
- Added RBAC edge-case coverage for groups and missing resources.

### Fixes
- Fixed group clearing in admin edit flow for dynamic relationships.

## 1.3.0 — 2026-02-11

### Security
- Validated `next` redirects on login to prevent open-redirects.
- Restored CSRF protection on JSON POST endpoints and added a global CSRF header for `fetch()`.
- Added login rate limiting (5/min) with Flask-Limiter.
- Enforced POST-only logout and updated UI accordingly.
- Hardened health endpoint to avoid leaking exception details.
- Strengthened cookie settings and development secret handling.
- Removed password exposure in admin flash messages (one-time display only).

### Quality & Stability
- Fixed test client authentication fixtures and uniqueness conflicts in tests.
- Modularized AI services into dedicated modules while keeping compatibility layer.
- Replaced `print()` with structured logging in AI services.
- Added curated `requirements.in` for direct dependencies.

### CI
- Added tests workflow badge to README.
