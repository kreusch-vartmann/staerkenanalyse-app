# Quality Report

Date: 2026-02-11

## Summary
- Security hardening completed (CSRF, open-redirect, rate limiting, logout POST-only, health endpoint).
- AI services refactored into modular components with compatibility layer.
- Test suite restored and fully green.

## Test Results
- `./venv/bin/python -m pytest tests/ -q --tb=short`
  - Result: **91 passed**, 2 warnings

## Notes
- CSRF token is now injected globally for `fetch()` requests in `templates/base.html`.
- Login is rate-limited to 5 requests per minute (POST only).
- Admin password resets now show a one-time password via session, not in flash messages.
