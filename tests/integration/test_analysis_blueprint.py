"""
Integration-Tests für Analysis-Blueprint (blueprints/analysis.py)

Testet:
- KI-Analyse-Routes
- Report-Generierung
- PDF-Export
"""

import json
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.integration
class TestAnalysisRoutes:
    """Tests für Analysis-Blueprint-Routes"""

    def test_dashboard_loads(self, client):
        response = client.get('/')
        assert response.status_code == 200

    def test_ai_analysis_select_group_loads(self, client, sample_group):
        response = client.get('/ai_analysis/select_group')
        assert response.status_code == 200
        assert sample_group.name.encode() in response.data

    def test_ai_analysis_select_participants_loads(self, client, sample_group, sample_participant):
        response = client.get(f'/ai_analysis/group/{sample_group.id}')
        assert response.status_code == 200
        assert sample_participant.name.encode() in response.data

    def test_edit_report_route(self, client, sample_participant):
        response = client.get(f'/edit_report/{sample_participant.id}')
        assert response.status_code == 200
        assert sample_participant.name.encode() in response.data

    @patch('blueprints.analysis.generate_report_with_ai')
    def test_run_ki_analysis(self, mock_generate, client, db, sample_participant, sample_observations_payload):
        mock_generate.return_value = json.dumps({
            "sk_ratings": {"flexibility": 5},
            "vk_ratings": {"flexibility": 6},
            "ki_texts": {"summary_text": "Test"}
        })

        # Set observations
        sample_participant.observations = json.dumps(sample_observations_payload)
        db.session.commit()

        response = client.post(
            f'/run_ki_analysis/{sample_participant.id}',
            data={'ki_prompt': 'Test {{name}}', 'ki_model': 'mistral'},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] in ["success", "error"]

    @patch('blueprints.analysis.generate_report_with_ai')
    def test_run_single_analysis_api(self, mock_generate, client, db, sample_participant, sample_observations_payload):
        mock_generate.return_value = json.dumps({
            "sk_ratings": {"flexibility": 5},
            "vk_ratings": {"flexibility": 6},
            "ki_texts": {"summary_text": "Test"}
        })

        sample_participant.observations = json.dumps(sample_observations_payload)
        db.session.commit()

        response = client.post(
            f'/api/run_single_analysis/{sample_participant.id}',
            json={"prompt_template": "{{context}}", "ki_model": "mistral"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] in ["success", "error"]

    @patch('blueprints.analysis.HTML')
    def test_report_pdf_export(self, mock_html, client, sample_participant):
        mock_writer = MagicMock()
        mock_writer.write_pdf.return_value = b"%PDF-1.4"
        mock_html.return_value = mock_writer

        response = client.get(f'/bericht/{sample_participant.id}/pdf')
        assert response.status_code == 200
        assert 'pdf' in response.content_type

    def test_final_report_redirect(self, client, sample_participant):
        response = client.get(f'/final_report/{sample_participant.id}')
        assert response.status_code in [302, 308]

    def test_final_report_pdf_redirect(self, client, sample_participant):
        response = client.post(f'/final_report/{sample_participant.id}/pdf')
        assert response.status_code in [302, 308]
