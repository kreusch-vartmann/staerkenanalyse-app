"""
Integration-Tests für komplette Workflows

Testet End-to-End-User-Journeys:
- Kompletter Analyse-Workflow (Gruppe → TN → Beobachtungen → KI → Report → PDF)
- Batch-Analyse-Flow
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from models import Group, Participant


@pytest.mark.integration
class TestCompleteAnalysisWorkflow:
    @patch('blueprints.analysis.generate_report_with_ai')
    def test_full_single_participant_workflow(self, mock_generate_ki, client, db):
        mock_generate_ki.return_value = json.dumps({
            "sk_ratings": {"flexibility": 5},
            "vk_ratings": {"flexibility": 6},
            "ki_texts": {"summary_text": "Test"}
        })

        # 1. Gruppe erstellen
        response = client.post('/group/add', data={
            'name': 'Workflow-Testgruppe',
            'date_from': date(2026, 1, 1).isoformat(),
            'date_to': date(2026, 6, 30).isoformat(),
        }, follow_redirects=True)
        assert response.status_code == 200

        group = db.session.query(Group).filter_by(name='Workflow-Testgruppe').first()
        assert group is not None

        # 2. Teilnehmer erstellen (über add_participant Route)
        response = client.post(
            f'/group/{group.id}/participant/add',
            data={'participant_names': 'Workflow-Teilnehmer'},
            follow_redirects=True,
        )
        assert response.status_code == 200

        participant = db.session.query(Participant).filter_by(name='Workflow-Teilnehmer').first()
        assert participant is not None

        # 3. Beobachtungen speichern
        response = client.post(
            f'/participant/{participant.id}/save_observations',
            json={'social': 'Teamfähig', 'verbal': 'Kommunikativ'},
        )
        assert response.status_code == 200

        # 4. Selbsteinschätzung speichern
        response = client.post(
            f'/save_self_assessment/{participant.id}',
            json={'content': 'Ich bin zuverlässig.'},
        )
        assert response.status_code == 200

        # 5. KI-Analyse durchführen
        response = client.post(
            f'/run_ki_analysis/{participant.id}',
            data={'ki_prompt': 'Test {{name}}', 'ki_model': 'mistral'},
        )
        assert response.status_code == 200

        # 6. Report-Editor laden
        response = client.get(f'/edit_report/{participant.id}')
        assert response.status_code == 200

    @patch('blueprints.analysis.generate_report_with_ai')
    def test_batch_analysis_workflow(self, mock_generate_ki, client, db, sample_group):
        mock_generate_ki.return_value = json.dumps({
            "sk_ratings": {},
            "vk_ratings": {},
            "ki_texts": {"summary_text": "Test"}
        })

        # Mehrere Teilnehmer erstellen
        for i in range(3):
            p = Participant(name=f"Batch-TN-{i}", group_id=sample_group.id)
            db.session.add(p)
        db.session.commit()

        participant_ids = [p.id for p in db.session.query(Participant).filter_by(group_id=sample_group.id).all()]

        # Batch-Analyse konfigurieren
        response = client.post(
            '/ai_analysis/execute',
            data={'participant_ids': participant_ids, 'ki_prompt': '{{context}}', 'ki_model': 'mistral'},
        )
        assert response.status_code == 200
