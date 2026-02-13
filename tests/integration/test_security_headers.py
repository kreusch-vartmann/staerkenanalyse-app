"""Integration tests for security headers and health endpoint."""

import pytest


@pytest.mark.integration
class TestSecurityHeaders:
    def test_security_headers_present_on_dashboard(self, client):
        response = client.get("/")
        assert response.status_code == 200
        headers = response.headers
        assert "Content-Security-Policy" in headers
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

        csp = headers.get("Content-Security-Policy", "")
        assert "default-src 'self'" in csp
        assert "script-src" in csp

    def test_security_headers_present_on_health(self, unauth_client):
        response = unauth_client.get("/health")
        assert response.status_code == 200
        headers = response.headers
        assert "Content-Security-Policy" in headers
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


@pytest.mark.integration
class TestHealthEndpoint:
    def test_health_payload(self, unauth_client):
        response = unauth_client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
