"""
Integration-Tests für Groups-Blueprint (blueprints/groups.py)
"""

import pytest
from datetime import date
from models import Group


@pytest.mark.integration
class TestGroupsRoutes:
    def test_groups_list_loads(self, client):
        response = client.get('/groups')
        assert response.status_code == 200

    def test_manage_groups_shows_all_groups(self, client, sample_group):
        response = client.get('/groups')
        assert response.status_code == 200
        assert sample_group.name.encode() in response.data

    def test_create_group_submit(self, client, db):
        response = client.post(
            '/group/add',
            data={
                'name': 'Neue Testgruppe',
                'date_from': date(2026, 1, 1).isoformat(),
                'date_to': date(2026, 6, 30).isoformat(),
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        group = db.session.query(Group).filter_by(name='Neue Testgruppe').first()
        assert group is not None

    def test_edit_group_submit(self, client, db, sample_group):
        response = client.post(
            f'/group/edit/{sample_group.id}',
            data={
                'group_name': 'Testgruppe A - Aktualisiert',
                'group_date_from': sample_group.date_from.isoformat(),
                'group_date_to': sample_group.date_to.isoformat(),
                'group_location': 'Ort',
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        db.session.refresh(sample_group)
        assert sample_group.name == 'Testgruppe A - Aktualisiert'

    def test_delete_group(self, client, db):
        group = Group(name='Leere Gruppe')
        db.session.add(group)
        db.session.commit()

        response = client.post(
            f'/group/delete/{group.id}',
            follow_redirects=True,
        )
        assert response.status_code == 200
        deleted = db.session.get(Group, group.id)
        assert deleted is None


@pytest.mark.integration
class TestGroupParticipants:
    def test_show_group_participants(self, client, sample_group, sample_participant):
        response = client.get(f'/group/{sample_group.id}/participants')
        assert response.status_code == 200
        assert sample_participant.name.encode() in response.data


@pytest.mark.integration
class TestGroupsErrorHandling:
    def test_edit_nonexistent_group(self, client):
        response = client.post('/group/edit/99999', data={'group_name': 'X'})
        assert response.status_code == 404

    def test_delete_nonexistent_group(self, client):
        response = client.post('/group/delete/99999')
        assert response.status_code == 404
