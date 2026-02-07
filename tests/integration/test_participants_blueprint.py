"""
Integration-Tests für Participants-Blueprint (blueprints/participants.py)

Testet:
- Teilnehmer-CRUD-Operationen
- Beobachtungs-Speicherung (JSON)
- Selbsteinschätzung
"""

import json
import pytest
from models import Participant, SelfAssessment


@pytest.mark.integration
class TestParticipantsRoutes:
    def test_manage_participants_loads(self, client):
        response = client.get('/participants')
        assert response.status_code == 200

    def test_add_participant_to_group(self, client, db, sample_group):
        response = client.post(
            f'/group/{sample_group.id}/participant/add',
            data={'participant_names': 'Lisa Müller\nPeter Schmidt'},
            follow_redirects=True,
        )
        assert response.status_code == 200

        participants = db.session.query(Participant).filter_by(group_id=sample_group.id).all()
        names = [p.name for p in participants]
        assert "Lisa Müller" in names
        assert "Peter Schmidt" in names

    def test_edit_participant(self, client, db, sample_participant):
        response = client.post(
            f'/participant/edit/{sample_participant.id}',
            data={'participant_name': 'Max Mustermann Neu'},
            follow_redirects=True,
        )
        assert response.status_code == 200

        db.session.refresh(sample_participant)
        assert sample_participant.name == 'Max Mustermann Neu'

    def test_delete_participant(self, client, db, sample_participant):
        participant_id = sample_participant.id
        response = client.post(
            f'/participant/delete/{participant_id}',
            follow_redirects=True,
        )
        assert response.status_code == 200

        deleted = db.session.get(Participant, participant_id)
        assert deleted is None


@pytest.mark.integration
class TestObservations:
    def test_data_entry_page_loads(self, client, sample_participant):
        response = client.get(f'/participant/{sample_participant.id}/data_entry')
        assert response.status_code == 200

    def test_save_observations_api(self, client, db, sample_participant):
        payload = {"social": "Test", "verbal": "Test"}
        response = client.post(
            f'/participant/{sample_participant.id}/save_observations',
            json=payload,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"

        db.session.refresh(sample_participant)
        saved = json.loads(sample_participant.observations)
        assert saved["social"] == "Test"


@pytest.mark.integration
class TestSelfAssessment:
    def test_manage_self_assessments_loads(self, client):
        response = client.get('/self-assessments')
        assert response.status_code == 200

    def test_show_self_assessment(self, client, sample_participant):
        response = client.get(f'/participant/{sample_participant.id}/self_assessment')
        assert response.status_code == 200

    def test_save_self_assessment(self, client, db, sample_participant):
        response = client.post(
            f'/save_self_assessment/{sample_participant.id}',
            json={'content': 'Ich bin zuverlässig.'},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"

        assessment = db.session.query(SelfAssessment).filter_by(
            participant_id=sample_participant.id
        ).first()
        assert assessment is not None
        assert 'zuverlässig' in assessment.content


@pytest.mark.integration
class TestParticipantsErrorHandling:
    def test_edit_nonexistent_participant(self, client):
        response = client.post('/participant/edit/99999', data={'participant_name': 'X'})
        assert response.status_code == 404

    def test_delete_nonexistent_participant(self, client):
        response = client.post('/participant/delete/99999')
        assert response.status_code == 404
