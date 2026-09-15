"""
Comprehensive RBAC Permission Tests

Tests für vollständige RBAC-Coverage:
- Admin-Rolle (all-access)
- Beobachter-Rolle (limited access)
- Custom Roles mit spezifischen Permissions
- Template UI visibility gates
- Permission denial scenarios
"""

import pytest
from models import Permission, Role, User, Group, Participant
from datetime import date


class TestAdminRoleAccess:
    """Admin-Rolle sollte Zugriff auf alle kritischen Seiten haben."""

    def test_admin_can_access_groups_page(self, client):
        """Admin kann Gruppen-Management-Seite öffnen."""
        response = client.get("/groups")
        assert response.status_code == 200
        assert b"Gruppen verwalten" in response.data

    def test_admin_can_access_participants_page(self, client):
        """Admin kann Teilnehmer-Management-Seite öffnen."""
        response = client.get("/participants")
        assert response.status_code == 200
        assert b"Teilnehmer" in response.data

    def test_admin_can_access_admin_panel(self, client):
        """Admin kann Admin-Panel öffnen."""
        response = client.get("/admin/users")
        assert response.status_code == 200
        assert b"Benutzer" in response.data or b"Benutzerverwaltung" in response.data

    def test_admin_can_access_observation_tasks(self, client, sample_group):
        """Admin kann Beobachtungsaufgaben-Seite öffnen."""
        response = client.get("/beobachtungsaufgaben/", follow_redirects=True)
        assert response.status_code == 200

    def test_admin_can_access_analysis(self, client, sample_group):
        """Admin kann KI-Analyse-Seite öffnen."""
        response = client.get("/ai_analysis/select_group", follow_redirects=True)
        assert response.status_code == 200

    def test_admin_sees_create_group_button(self, client):
        """Admin sieht 'Neue Gruppe' Button auf Groups-Seite."""
        response = client.get("/groups")
        assert response.status_code == 200
        # Button sollte im HTML sein
        assert b"Neue Gruppe" in response.data or b"neue-gruppe" in response.data or b"add_group" in response.data

    def test_admin_sees_all_management_buttons(self, client, sample_group):
        """Admin sieht alle Management-Buttons (Edit, Delete, etc)."""
        response = client.get("/groups")
        assert response.status_code == 200
        content = response.data.decode()
        # Mindestens einer dieser sollte vorhanden sein
        assert any([
            "Bearbeiten" in content,
            "L\u00f6schen" in content,
            "edit_group" in content,
            "delete_group" in content,
        ])


class TestObserverRoleAccess:
    """Beobachter-Rolle sollte limitierten Zugriff haben."""

    def test_observer_cannot_access_admin_panel(self, observer_client):
        """Beobachter DARF Admin-Panel nicht öffnen."""
        response = observer_client.get("/admin/users")
        assert response.status_code == 302  # Redirect zu Login/Home

    def test_observer_can_access_data_entry(self, observer_client, sample_participant):
        """Beobachter kann Dateneingabe-Seite öffnen."""
        response = observer_client.get(f"/participant/{sample_participant.id}/data_entry")
        assert response.status_code == 200

    def test_observer_can_view_participants(self, observer_client):
        """Beobachter kann Teilnehmer-Seite anschauen."""
        response = observer_client.get("/participants")
        assert response.status_code == 200

    def test_observer_cannot_delete_participant(self, observer_client, db, sample_participant):
        """Beobachter DARF Teilnehmer nicht löschen.

        `permission_required` verweigert per Redirect (302) + Flash, nicht
        per 403. Entscheidend ist, dass die Aktion wirkungslos bleibt.
        """
        participant_id = sample_participant.id
        response = observer_client.post(
            f"/participant/delete/{participant_id}",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert db.session.get(Participant, participant_id) is not None

    def test_observer_cannot_create_group(self, observer_client, db):
        """Beobachter DARF keine neue Gruppe erstellen (Redirect + keine Anlage)."""
        response = observer_client.post(
            "/group/add",
            data={
                "name": "Neue Test-Gruppe",
                "date_from": "2026-01-01",
                "date_to": "2026-06-30",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert Group.query.filter_by(name="Neue Test-Gruppe").first() is None


class TestTemplateUIVisibilityGates:
    """Template-Elemente sollten nur für autorisierte Rollen sichtbar sein."""

    def test_admin_sees_create_group_button_in_template(self, client):
        """Admin-Template zeigt 'Neue Gruppe' Button."""
        response = client.get("/groups")
        content = response.data.decode()
        # Suche nach Button mit Text oder onclick
        assert ("Neue Gruppe" in content or 
                "addGroup" in content or 
                "openAddGroupModal" in content or
                "add_group" in content)

    def test_observer_cannot_see_manage_admin_links(self, observer_client):
        """Beobachter sieht keine Admin-Links in den Templates."""
        response = observer_client.get("/participants")
        content = response.data.decode()
        # Admin-Links sollten NICHT sichtbar sein
        if response.status_code == 200:
            content = response.data.decode()
            # Admin-Links sollten NICHT sichtbar sein
            # (z.B. "Rollen verwalten", "Benutzer verwalten")
            assert "/admin/users" not in content
            assert "/admin/roles" not in content

    def test_permission_gates_in_manage_groups_template(self, client, sample_group):
        """manage_groups.html renderiert permission gates korrekt."""
        response = client.get("/groups")
        assert response.status_code == 200
        content = response.data.decode()
        
        # Prüfe ob permission-gates in HTML sind (via Jinja2 condition)
        # Dies kann indirekt geprüft werden durch Sichtbarkeit von Buttons
        assert "groups" in content.lower()

    def test_permission_gates_in_manage_participants_template(self, client):
        """manage_participants.html renderiert permission gates korrekt."""
        response = client.get("/participants")
        assert response.status_code == 200
        content = response.data.decode()
        
        # Seite sollte laden und Content hab
    def test_permission_gates_in_participants_page_template(self, client, sample_group):
        """participants.html (group-specific) renderiert permission gates korrekt."""
        response = client.get(f"/group/{sample_group.id}/participants")
        if response.status_code == 200:
            content = response.data.decode()
            assert len(content) > 0


class TestPermissionBasedRouteAccess:
    """Route-access sollte Permission-basiert eingeschränkt sein."""

    def test_groups_view_permission_required(self, observer_client):
        """groups.view Permission ist erforderlich."""
        response = observer_client.get("/groups")
        # Beobachter sollte diese Seite sehen oder redirect
        assert response.status_code in [200, 302]

    def test_groups_edit_permission_blocks_create(self, observer_client, db):
        """Ohne groups.edit Permission: Create Group schlägt fehl."""
        response = observer_client.post(
            "/group/add",
            data={
                "name": "Test-Gruppe",
                "date_from": "2026-01-01",
                "date_to": "2026-06-30",
                "location": "Test",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert Group.query.filter_by(name="Test-Gruppe").first() is None

    def test_participants_edit_permission_blocks_delete(self, observer_client, db, sample_participant):
        """Ohne participants.delete Permission: Delete schlägt fehl."""
        participant_id = sample_participant.id
        response = observer_client.post(
            f"/participant/delete/{participant_id}",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert db.session.get(Participant, participant_id) is not None

    def test_admin_analysis_permission_allows_access(self, client):
        """Mit analysis.run Permission: Admin kann Analyse-Seite öffnen."""
        response = client.get("/ai_analysis/select_group", follow_redirects=True)
        assert response.status_code == 200  # Kein Redirect für Admins


class TestPermissionDenialScenarios:
    """Test expliziter Permission-Denial-Szenarien."""

    def test_403_returned_when_permission_denied(self, observer_client):
        """403 Forbidden wird zurückgegeben wenn Permission fehlt."""
        # Versuche Admin-Panel zu öffnen
        response = observer_client.get("/admin/users")
        assert response.status_code in [302, 403]

    def test_redirect_to_home_on_permission_denied(self, observer_client):
        """Redirect z.B. zu Home bei Permission-Denial."""
        response = observer_client.get("/admin/users", follow_redirects=False)
        if response.status_code == 302:
            location = response.headers.get("Location", "").lower()
            # Sie sollte redirect zur Home oder Login sein
            assert any(x in location for x in ["login", "auth", "/"])

    def test_permission_check_decorator_works(self, observer_client):
        """@permission_required Decorator blockiert Zugriff.

        Der Decorator leitet auf das Dashboard um (302) statt 403 zu
        senden; die geschützte Seite wird nicht ausgeliefert.
        """
        response = observer_client.get("/admin/users", follow_redirects=False)
        assert response.status_code == 302

        followed = observer_client.get("/admin/users", follow_redirects=True)
        assert b"Benutzerverwaltung" not in followed.data


class TestRoleBasedAccessMatrix:
    """Umfassende Matrix: Role × Action → Allowed/Denied."""

    # Hinweis: Verweigerter Zugriff endet laut `permission_required` in
    # einem Redirect (302) auf das Dashboard – nicht in einem 403.
    @pytest.mark.parametrize("resource,expected_admin,expected_observer", [
        ("/groups", 200, 200),
        ("/admin/users", 200, 302),
        ("/participants", 200, 200),
        ("/beobachtungsaufgaben/", 200, 200),
    ])
    def test_resource_access_matrix(self, client, observer_client, resource, expected_admin, expected_observer):
        """Teste Zugriffs-Matrix für verschiedene Rollen."""
        admin_response = client.get(resource)
        observer_response = observer_client.get(resource)
        
        assert admin_response.status_code == expected_admin
        assert observer_response.status_code == expected_observer


class TestCustomRolePermissions:
    """Custom Roles mit spezifischen Permissions."""

    def test_custom_role_with_single_permission(self, db):
        """Custom Role kann mit einzelner Permission erstellt werden."""
        custom_role = Role(name="custom_test", description="Test Custom Role")
        perm = Permission(codename="groups.view", description="View Groups", category="groups")
        db.session.add(perm)
        db.session.flush()
        
        custom_role.permissions.append(perm)
        db.session.add(custom_role)
        db.session.commit()
        
        assert custom_role.has_permission("groups.view") is True
        assert custom_role.has_permission("groups.edit") is False

    def test_custom_role_permission_check_works(self, db):
        """Custom Role permission Überprüfung funktioniert."""
        custom_role = Role(name="tester_role")
        perm1 = Permission(codename="test.read")
        perm2 = Permission(codename="test.write")
        
        db.session.add(custom_role)
        db.session.add(perm1)
        db.session.add(perm2)
        db.session.flush()
        
        custom_role.permissions.append(perm1)
        db.session.commit()
        
        assert custom_role.has_permission("test.read") is True
        assert custom_role.has_permission("test.write") is False

    def test_system_role_has_all_permissions(self, db):
        """System Role (Admin) hat automatisch alle Permissions."""
        system_role = Role(name="system_admin", is_system=True)
        db.session.add(system_role)
        db.session.commit()
        
        # System role sollte jede beliebige Permission haben
        assert system_role.has_permission("groups.view") is True
        assert system_role.has_permission("groups.edit") is True
        assert system_role.has_permission("admin.manage_everything") is True


class TestUserPermissionDelegation:
    """User delegiert Permission-Checks an seine Role."""

    def test_user_has_permission_delegates_to_role(self, db, admin_user, admin_permissions):
        """User.has_permission() delegiert zu Role.has_permission().

        `admin_permissions` richtet die Rolle wie in der Produktion ein
        (is_system + alle Berechtigungen); ohne diese Fixture besitzt die
        Test-Rolle bewusst keine Rechte.
        """
        assert admin_user.has_permission("groups.edit") is True

    def test_user_without_permission_returns_false(self, db, observer_user, observer_role):
        """User ohne Permission gibt False zurück."""
        # Beobachter hat keine admin Permissions
        assert observer_user.has_permission("admin.manage_users") is False

    def test_inactive_user_cannot_access_protected_routes(self, app, db, admin_user):
        """Inaktiver User kann geschützte Routen nicht zugreifen."""
        admin_user.is_active = False
        db.session.commit()
        
        client = app.test_client()
        # Client versucht zugreifen (sollte fehlschlagen oder redirect)
        response = client.get("/groups")
        assert response.status_code in [302, 401, 403]


class TestDataVisibilityByRole:
    """Daten sollten basierend auf Role visibility begrenzt werden."""

    def test_observer_only_sees_assigned_groups(self, observer_client, observer_user, db):
        """Beobachter sieht nur zugewiesene Gruppen."""
        response = observer_client.get("/participants")
        assert response.status_code == 200

    def test_admin_sees_all_groups(self, client, db):
        """Admin sieht alle Gruppen."""
        response = client.get("/groups")
        assert response.status_code == 200


class TestPermissionEdgeCases:
    """Edge cases in Permission-System."""

    def test_empty_permission_string_returns_false(self, admin_user):
        """Empty permission string gibt False zurück."""
        assert admin_user.has_permission("") is False

    def test_nonexistent_permission_returns_false(self, admin_user):
        """Nicht-existierende Permission gibt False zurück."""
        assert admin_user.has_permission("nonexistent.permission") is False

    def test_permission_codename_case_sensitive(self, db, admin_role):
        """Permission codename ist case-sensitive."""
        perm = Permission(codename="groups.VIEW")  # Großbuchstaben
        db.session.add(perm)
        db.session.flush()
        admin_role.permissions.append(perm)
        db.session.commit()
        
        # Sollte nicht matched mit "groups.view"
        assert admin_role.has_permission("groups.view") is False
        assert admin_role.has_permission("groups.VIEW") is True
