"""
Integration-Tests für Reports-Blueprint (blueprints/reports.py)
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from models import ReportConfiguration


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
        mock_instance.render_warnings = []
        mock_generator.return_value = mock_instance

        response = client.get(f'/reports/{sample_group.id}/preview/{sample_participant.id}')
        assert response.status_code == 200
        # Vorschau = das echte PDF (inline) im iframe
        assert f'/reports/{sample_group.id}/generate-pdf/{sample_participant.id}?inline=1'.encode() in response.data
        mock_instance.render_document.assert_called_once_with(mode="combined")

    @patch('blueprints.reports.ReportGenerator')
    def test_preview_shows_layout_warnings(self, mock_generator, client, db, sample_group, sample_participant, sample_report_configuration):
        mock_instance = MagicMock()
        mock_instance.render_warnings = ["Fremdeinschätzung: 4 statt 3 Seiten – der Text ist länger als vorgesehen."]
        mock_generator.return_value = mock_instance

        response = client.get(f'/reports/{sample_group.id}/preview/{sample_participant.id}')
        assert response.status_code == 200
        assert "4 statt 3 Seiten".encode() in response.data

    @patch('blueprints.reports.ReportGenerator')
    def test_generate_pdf_report(self, mock_generator, client, db, sample_group, sample_participant, sample_report_configuration):
        mock_instance = MagicMock()
        mock_instance.to_pdf.return_value = b'%PDF-1.4 test'
        mock_generator.return_value = mock_instance

        response = client.get(f'/reports/{sample_group.id}/generate-pdf/{sample_participant.id}')
        assert response.status_code == 200
        assert 'pdf' in response.content_type
        assert 'attachment' in response.headers['Content-Disposition']
        assert response.headers['X-Frame-Options'] == 'DENY'

    @patch('blueprints.reports.ReportGenerator')
    def test_generate_pdf_report_inline_for_preview(self, mock_generator, client, db, sample_group, sample_participant, sample_report_configuration):
        mock_instance = MagicMock()
        mock_instance.to_pdf.return_value = b'%PDF-1.4 test'
        mock_generator.return_value = mock_instance

        response = client.get(f'/reports/{sample_group.id}/generate-pdf/{sample_participant.id}?inline=1')
        assert response.status_code == 200
        assert 'pdf' in response.content_type
        assert 'attachment' not in response.headers.get('Content-Disposition', '')
        # nur diese Antwort darf same-origin eingebettet werden
        assert response.headers['X-Frame-Options'] == 'SAMEORIGIN'
        assert "frame-ancestors 'self'" in response.headers['Content-Security-Policy']

    def test_preview_report_wrong_group(self, client, db, sample_group, sample_participant, sample_report_configuration):
        response = client.get(f'/reports/{sample_group.id + 1}/preview/{sample_participant.id}')
        assert response.status_code in [403, 404]

    def test_configure_report_invalid_signature_lines_falls_back(self, client, db, sample_group, sample_report_configuration):
        response = client.post(
            f'/reports/{sample_group.id}/configure',
            data={
                "closing_page_signature_lines_count": "abc",
                "template_id": "",
            },
            follow_redirects=False,
        )
        assert response.status_code in [302, 303]

        config = db.session.execute(
            db.select(ReportConfiguration).where(ReportConfiguration.group_id == sample_group.id)
        ).scalar_one()
        modules_config = json.loads(config.modules_config)
        assert modules_config["closing_page"]["signature_lines_count"] == 3

    def test_configure_report_invalid_template_id_ignored(self, client, db, sample_group, sample_report_configuration):
        response = client.post(
            f'/reports/{sample_group.id}/configure',
            data={
                "closing_page_signature_lines_count": "2",
                "template_id": "not-a-number",
            },
            follow_redirects=False,
        )
        assert response.status_code in [302, 303]

        config = db.session.execute(
            db.select(ReportConfiguration).where(ReportConfiguration.group_id == sample_group.id)
        ).scalar_one()
        assert config.template_id is None
