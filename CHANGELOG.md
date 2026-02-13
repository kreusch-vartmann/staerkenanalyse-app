# Changelog

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
