"""Integration tests for auth and RBAC flows."""

import models


def test_login_success_redirects_dashboard(unauth_client, admin_user):
    response = unauth_client.post(
        "/login",
        data={"email": admin_user.email, "password": "testpassword123"},
    )
    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith("/")


def test_login_force_password_change_redirects(unauth_client, admin_user, db):
    admin_user.force_password_change = True
    db.session.commit()

    response = unauth_client.post(
        "/login",
        data={"email": admin_user.email, "password": "testpassword123"},
    )
    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith("/change-password")


def test_login_inactive_user_rejected(unauth_client, admin_user, db):
    admin_user.is_active = False
    db.session.commit()

    response = unauth_client.post(
        "/login",
        data={"email": admin_user.email, "password": "testpassword123"},
    )
    assert response.status_code == 302
    assert "/login" in response.headers.get("Location", "")


def test_login_disallows_external_next(unauth_client, admin_user, db):
    admin_user.force_password_change = False
    admin_user.is_active = True
    db.session.commit()
    response = unauth_client.post(
        "/login?next=//evil.example.com",
        data={"email": admin_user.email, "password": "testpassword123"},
    )
    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith("/")


def test_logout_redirects_to_login(client):
    response = client.post("/logout")
    assert response.status_code == 302
    assert "/login" in response.headers.get("Location", "")


def test_change_password_success(client, admin_user, db):
    response = client.post(
        "/change-password",
        data={
            "old_password": "testpassword123",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        },
    )
    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith("/")

    updated_user = db.session.get(models.User, admin_user.id)
    assert updated_user.check_password("newpassword123")
    assert updated_user.force_password_change is False


def test_change_password_invalid_old(client, admin_user, db):
    admin_user.set_password("testpassword123")
    admin_user.force_password_change = False
    db.session.commit()
    response = client.post(
        "/change-password",
        data={
            "old_password": "wrongpassword",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        },
    )
    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith("/change-password")

    refreshed_user = db.session.get(models.User, admin_user.id)
    assert refreshed_user.check_password("testpassword123")


def test_admin_required_blocks_observer(observer_client):
    response = observer_client.get("/admin/users")
    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith("/")


def test_participant_access_allows_assigned_observer(observer_client, sample_participant):
    response = observer_client.get(f"/participant/{sample_participant.id}/data_entry")
    assert response.status_code == 200


def test_participant_access_blocks_unassigned_observer(observer_client, other_participant):
    response = observer_client.get(f"/participant/{other_participant.id}/data_entry")
    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith("/")


def test_admin_can_access_any_participant(client, other_participant):
    response = client.get(f"/participant/{other_participant.id}/data_entry")
    assert response.status_code == 200


def test_group_access_blocks_unassigned_observer(observer_client, other_group):
    response = observer_client.get(f"/api/group/{other_group.id}/participants")
    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith("/")


def test_group_access_missing_group_returns_404(client):
    response = client.get("/api/group/999999/participants")
    assert response.status_code == 404


def test_participant_access_missing_returns_404(client):
    response = client.get("/api/participant/999999/observations")
    assert response.status_code == 404


def test_observer_without_groups_redirects(app, db, observer_role, sample_group):
    user = models.User(
        email="nogroups@test.de",
        role_id=observer_role.id,
        force_password_change=False,
        is_active=True,
    )
    user.set_password("testpassword123")
    db.session.add(user)
    db.session.commit()

    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
        session["_id"] = "test-session"

    response = client.get(f"/api/group/{sample_group.id}/participants")
    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith("/")
