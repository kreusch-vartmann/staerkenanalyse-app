# Changelog

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
