"""Integration tests for security controls (CSRF, rate limiting, validation)."""

import pytest


@pytest.mark.integration
class TestCsrfProtection:
    def test_csrf_blocks_logout_when_enabled(self, app, admin_user):
        app.config["WTF_CSRF_ENABLED"] = True
        try:
            client = app.test_client()
            with client.session_transaction() as session:
                session["_user_id"] = str(admin_user.id)
                session["_fresh"] = True
                session["_id"] = "test-session"

            response = client.post("/logout")
            assert response.status_code == 400
        finally:
            app.config["WTF_CSRF_ENABLED"] = False


@pytest.mark.integration
class TestRateLimiting:
    def test_login_rate_limited_after_threshold(self, unauth_client):
        last_response = None
        for _ in range(6):
            last_response = unauth_client.post(
                "/login",
                data={"email": "invalid@test.de", "password": "wrong"},
            )
        assert last_response is not None
        assert last_response.status_code == 429


@pytest.mark.integration
class TestValidationSecurity:
    def test_save_observations_rejects_invalid_payload(self, client, sample_participant):
        response = client.post(
            f"/participant/{sample_participant.id}/save_observations",
            json="invalid",
        )
        assert response.status_code == 400
