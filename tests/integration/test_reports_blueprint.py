"""
Integration-Tests für Reports-Blueprint (blueprints/reports.py)
"""

import json
import pytest
from unittest.mock import MagicMock, patch


@pytest.mark.integration
class TestReportsRoutes:
    def test_list_templates(self, client, sample_report_template):
        response = client.get('/reports/templates')
        assert response.status_code == 200
        assert sample_report_template.name.encode() in response.data

    def test_view_template(self, client, sample_report_template):
        response = client.get(f'/reports/templates/{sample_report_template.id}')
        assert response.status_code == 200

    def test_configure_report_get(self, client, sample_group, sample_report_template):
        response = client.get(f'/reports/{sample_group.id}/configure')
        assert response.status_code == 200

    @patch('blueprints.reports.ReportGenerator')
    def test_preview_report_html(self, mock_generator, client, db, sample_group, sample_participant, sample_report_configuration):
        mock_instance = MagicMock()
        mock_instance.build_html.return_value = '<html>Preview</html>'
        mock_generator.return_value = mock_instance

        response = client.get(f'/reports/{sample_group.id}/preview/{sample_participant.id}')
        assert response.status_code == 200
        assert b'Preview' in response.data

    @patch('blueprints.reports.ReportGenerator')
    def test_generate_pdf_report(self, mock_generator, client, db, sample_group, sample_participant, sample_report_configuration):
        mock_instance = MagicMock()
        mock_instance.to_pdf.return_value = b'%PDF-1.4 test'
        mock_generator.return_value = mock_instance

        response = client.get(f'/reports/{sample_group.id}/generate-pdf/{sample_participant.id}')
        assert response.status_code == 200
        assert 'pdf' in response.content_type

    def test_preview_report_wrong_group(self, client, db, sample_group, sample_participant, sample_report_configuration):
        response = client.get(f'/reports/{sample_group.id + 1}/preview/{sample_participant.id}')
        assert response.status_code in [403, 404]
