"""Integration tests for admin user management flows."""

import models


def test_admin_users_page_loads(client):
    response = client.get("/admin/users")
    assert response.status_code == 200


def test_admin_users_page_blocked_for_observer(observer_client):
    response = observer_client.get("/admin/users")
    assert response.status_code == 302
    assert response.headers.get("Location", "").endswith("/")


def test_admin_add_user_creates_observer_with_group(client, db, observer_role, sample_group):
    response = client.post(
        "/admin/user/add",
        data={
            "email": "new_observer@test.de",
            "first_name": "Bea",
            "last_name": "Beobachter",
            "role": "beobachter",
            "groups": [str(sample_group.id)],
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    user = db.session.scalar(
        db.select(models.User).where(models.User.email == "new_observer@test.de")
    )
    assert user is not None
    assert user.role_id == observer_role.id
    assert user.groups.filter_by(id=sample_group.id).first() is not None
    assert user.force_password_change is True


def test_admin_edit_user_updates_role_and_clears_groups(client, db, observer_role, admin_role, sample_group):
    user = models.User(
        email="edit_user@test.de",
        role_id=observer_role.id,
        force_password_change=False,
        is_active=True,
    )
    user.set_password("initialpass123")
    user.groups.append(sample_group)
    db.session.add(user)
    db.session.commit()

    response = client.post(
        f"/admin/user/{user.id}/edit",
        data={
            "email": user.email,
            "first_name": "Edit",
            "last_name": "User",
            "role": "admin",
            "new_password": "",
            "groups": [str(sample_group.id)],
        },
        follow_redirects=True,
    )
    assert response.status_code == 200

    updated = db.session.get(models.User, user.id)
    assert updated.role_id == admin_role.id
    assert updated.groups.count() == 0


def test_admin_toggle_active(client, db, observer_role):
    user = models.User(
        email="toggle_active@test.de",
        role_id=observer_role.id,
        force_password_change=False,
        is_active=True,
    )
    user.set_password("initialpass123")
    db.session.add(user)
    db.session.commit()

    response = client.post(
        f"/admin/user/{user.id}/toggle-active",
        follow_redirects=True,
    )
    assert response.status_code == 200

    updated = db.session.get(models.User, user.id)
    assert updated.is_active is False


def test_admin_reset_password_sets_force_change(client, db, observer_role):
    user = models.User(
        email="reset_password@test.de",
        role_id=observer_role.id,
        force_password_change=False,
        is_active=True,
    )
    user.set_password("initialpass123")
    db.session.add(user)
    db.session.commit()

    response = client.post(
        f"/admin/user/{user.id}/reset-password",
        follow_redirects=True,
    )
    assert response.status_code == 200

    updated = db.session.get(models.User, user.id)
    assert updated.force_password_change is True


def test_admin_delete_user_removes_record(client, db, observer_role):
    user = models.User(
        email="delete_user@test.de",
        role_id=observer_role.id,
        force_password_change=False,
        is_active=True,
    )
    user.set_password("initialpass123")
    db.session.add(user)
    db.session.commit()

    response = client.post(
        f"/admin/user/{user.id}/delete",
        follow_redirects=True,
    )
    assert response.status_code == 200

    deleted = db.session.get(models.User, user.id)
    assert deleted is None
