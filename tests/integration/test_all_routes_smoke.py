"""
Smoke-Test für alle GET-Routen der App.

Zweck: Regressionen finden, die sich als 500 (Server-Fehler) zeigen –
z. B. kaputte Queries, fehlende Template-Variablen, NameErrors.

Wichtig: Der Test nutzt die `client`-Fixture aus conftest.py, die als
Admin eingeloggt ist. Zusätzlich wird verifiziert, dass die Session
tatsächlich authentifiziert ist – sonst wäre der Test wertlos, weil
alle Routen nur auf den Login umleiten würden (302 statt 500).
"""

import re

import pytest

# Routen, die im Smoke-Test bewusst nicht per GET geprüft werden
EXCLUDED_ENDPOINTS = {
    "auth.logout",  # beendet die Session und verfälscht Folge-Requests
    "static",
}


def _weasyprint_available() -> bool:
    """Prüft, ob WeasyPrint inkl. System-Bibliotheken (Pango/Cairo) nutzbar ist."""
    try:
        import weasyprint  # noqa: F401

        return True
    except Exception:
        return False


WEASYPRINT_AVAILABLE = _weasyprint_available()


def _resolve_url(rule_str: str, group_id: int, participant_id: int) -> str:
    """Ersetzt URL-Parameter durch existierende IDs bzw. Platzhalter."""
    url = rule_str
    url = url.replace("<int:group_id>", str(group_id))
    url = url.replace("<int:participant_id>", str(participant_id))
    # Restliche Konverter (z. B. <int:user_id>, <response_type>) mit 1 füllen
    return re.sub(r"<[^>]+>", "1", url)


@pytest.fixture
def full_admin(monkeypatch):
    """Simuliert die Produktions-Admin-Rolle (alle Berechtigungen).

    Die conftest-Fixture `admin_role` legt die Rolle ohne `is_system` an.
    `permission_required` würde dadurch greifen und Routen auf das
    Dashboard umleiten – in der echten Datenbank ist die Admin-Rolle
    hingegen `is_system=1` und besitzt alle Berechtigungen.

    Bewusst als In-Memory-Patch (kein DB-Schreibzugriff): Die
    `db`-Fixture dieses Projekts committet in Teil-Fixtures, weshalb
    DB-Mutationen über Testgrenzen hinweg bestehen bleiben würden.
    """
    import models

    monkeypatch.setattr(
        models.Role, "has_permission", lambda self, codename: True, raising=True
    )
    yield


def test_admin_session_is_authenticated(client):
    """Vorbedingung: Der Test-Client ist wirklich eingeloggt."""
    response = client.get("/")
    assert response.status_code == 200, (
        "Dashboard nicht erreichbar – Session ist nicht authentifiziert, "
        "der Smoke-Test wäre dadurch aussagelos."
    )


def test_all_get_routes_no_server_error(client, full_admin, sample_group, sample_participant):
    """Keine GET-Route darf einen 500er liefern."""
    app = client.application

    routes = [
        (rule.endpoint, str(rule))
        for rule in app.url_map.iter_rules()
        if "GET" in rule.methods
        and rule.endpoint not in EXCLUDED_ENDPOINTS
        and "static" not in rule.endpoint
    ]
    assert routes, "Keine GET-Routen gefunden – url_map leer?"

    failures = []
    login_redirects = []
    skipped_pdf = []

    for endpoint, rule_str in routes:
        # PDF-Routen benötigen Pango/Cairo. Fehlen die System-Bibliotheken
        # (z. B. lokaler Host ohne `pango`), ist ein 500 kein Code-Fehler.
        # Im Container/CI mit installierten Libs werden sie mitgeprüft.
        if not WEASYPRINT_AVAILABLE and "pdf" in endpoint.lower():
            skipped_pdf.append(endpoint)
            continue

        url = _resolve_url(rule_str, sample_group.id, sample_participant.id)
        response = client.get(url)

        if response.status_code == 500:
            failures.append(f"{endpoint} ({url}) -> 500")
        elif response.status_code in (301, 302) and "/login" in (
            response.headers.get("Location") or ""
        ):
            login_redirects.append(f"{endpoint} ({url})")

    if skipped_pdf:
        print(
            "\nHinweis: PDF-Routen übersprungen (WeasyPrint-Systembibliotheken "
            f"fehlen): {', '.join(skipped_pdf)}"
        )

    assert not failures, "Routen mit Server-Fehler:\n" + "\n".join(failures)
    # Umleitungen auf den Login deuten auf einen Session-Verlust hin
    assert not login_redirects, (
        "Routen leiten auf den Login um (Session verloren?):\n"
        + "\n".join(login_redirects)
    )


@pytest.mark.parametrize(
    "url",
    [
        "/admin/users",
        "/admin/settings",
        "/admin/roles",
        "/import",
    ],
)
def test_key_admin_pages_render(client, full_admin, url):
    """Zentrale Admin-Seiten müssen mit 200 rendern."""
    response = client.get(url)
    assert response.status_code == 200, f"{url} -> {response.status_code}"
