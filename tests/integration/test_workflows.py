"""
Integration-Tests für komplette Workflows

Testet End-to-End-User-Journeys:
- Kompletter Analyse-Workflow (Gruppe → TN → Beobachtungen → KI → Report → PDF)
- Batch-Analyse-Flow
"""

import json
from datetime import date
from io import BytesIO
from unittest.mock import patch, MagicMock

import pytest

from models import Group, Participant, ReportConfiguration, ReportTemplate


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


@pytest.mark.integration
class TestImportExportWorkflow:
    def test_import_names_creates_group_and_participants(self, client, db):
        response = client.post(
            '/import/names',
            data={
                'group_name': 'Import-Workflow Gruppe',
                'name_file': (BytesIO(b'Anna Schmidt\nMax Muster\n'), 'names.txt'),
            },
            content_type='multipart/form-data',
            follow_redirects=False,
        )
        assert response.status_code == 302

        group = db.session.query(Group).filter_by(name='Import-Workflow Gruppe').first()
        assert group is not None
        participants = db.session.query(Participant).filter_by(group_id=group.id).all()
        assert len(participants) == 2

    def test_export_all_participants_csv(self, client, db, sample_participant):
        response = client.post(
            '/export_data',
            data={
                'select_all_data': 'true',
                'format': 'csv',
            },
        )
        assert response.status_code == 200
        assert 'text/csv' in response.content_type
        assert response.data


@pytest.mark.integration
class TestEndToEndImportAnalysisReportFlow:
    @patch('blueprints.reports.ReportGenerator')
    @patch('blueprints.analysis.generate_report_with_ai')
    def test_import_to_report_pdf_flow(
        self,
        mock_generate_ki,
        mock_report_generator,
        client,
        db,
    ):
        mock_generate_ki.return_value = json.dumps({
            "sk_ratings": {"flexibility": 5},
            "vk_ratings": {"flexibility": 6},
            "ki_texts": {"summary_text": "Test"},
        })

        # Import names creates group + participant
        response = client.post(
            '/import/names',
            data={
                'group_name': 'E2E-Workflow Gruppe',
                'name_file': (BytesIO(b'E2E Teilnehmer\n'), 'names.txt'),
            },
            content_type='multipart/form-data',
            follow_redirects=False,
        )
        assert response.status_code == 302

        group = db.session.query(Group).filter_by(name='E2E-Workflow Gruppe').first()
        assert group is not None
        participant = db.session.query(Participant).filter_by(group_id=group.id).first()
        assert participant is not None

        # Save observations + self assessment
        response = client.post(
            f'/participant/{participant.id}/save_observations',
            json={'social': 'Teamfähig', 'verbal': 'Kommunikativ'},
        )
        assert response.status_code == 200

        response = client.post(
            f'/save_self_assessment/{participant.id}',
            json={'content': 'Ich bin zuverlässig.'},
        )
        assert response.status_code == 200

        # Run analysis (mocked)
        response = client.post(
            f'/run_ki_analysis/{participant.id}',
            data={'ki_prompt': '{{context}}', 'ki_model': 'mistral'},
        )
        assert response.status_code == 200

        # Create report config
        template = ReportTemplate(
            name='E2E Template',
            description='E2E Template',
            design_config='{"primary_color": "#000000", "layout_style": "classic"}',
            is_active=True,
        )
        db.session.add(template)
        db.session.flush()

        config = ReportConfiguration(
            group_id=group.id,
            template_id=template.id,
            modules_config='{"cover_page": {"enabled": true}}',
        )
        db.session.add(config)
        db.session.commit()

        mock_instance = MagicMock()
        mock_instance.build_html.return_value = '<html>Preview</html>'
        mock_instance.to_pdf.return_value = b'%PDF-1.4 test'
        mock_report_generator.return_value = mock_instance

        # Report preview
        response = client.get(f'/reports/{group.id}/preview/{participant.id}')
        assert response.status_code == 200
        assert b'Preview' in response.data

        # Report PDF
        response = client.get(f'/reports/{group.id}/generate-pdf/{participant.id}')
        assert response.status_code == 200
        assert 'application/pdf' in response.content_type


@pytest.mark.integration
class TestTaskAssignmentAnalysisReportFlow:
    @patch('blueprints.reports.ReportGenerator')
    @patch('blueprints.analysis.generate_report_with_ai')
    def test_task_assignment_to_report_pdf_flow(
        self,
        mock_generate_ki,
        mock_report_generator,
        client,
        db,
    ):
        mock_generate_ki.return_value = json.dumps({
            "sk_ratings": {"flexibility": 5},
            "vk_ratings": {"flexibility": 6},
            "ki_texts": {"summary_text": "Test"},
        })

        response = client.post(
            '/import/names',
            data={
                'group_name': 'Task-Flow Gruppe',
                'name_file': (BytesIO(b'Task Teilnehmer\n'), 'names.txt'),
            },
            content_type='multipart/form-data',
            follow_redirects=False,
        )
        assert response.status_code == 302

        group = db.session.query(Group).filter_by(name='Task-Flow Gruppe').first()
        assert group is not None
        participant = db.session.query(Participant).filter_by(group_id=group.id).first()
        assert participant is not None

        # Create and assign a task with content
        from models import Task, TaskVersion

        task = Task(
            title='Task Flow',
            observation_area='Soziale Kompetenzen',
            participant_count=4,
            duration_minutes=30,
            is_active=True,
            is_example=False,
            created_by_id=1,
        )
        db.session.add(task)
        db.session.flush()

        version = TaskVersion(
            task_id=task.id,
            version_number=1.0,
            content='<h2>Aufgabe</h2><p>Inhalt</p>',
            context_data='{}',
            change_notes='Initial',
            created_by_id=1,
        )
        db.session.add(version)
        db.session.flush()
        task.current_version_id = version.id
        group.tasks.append(task)
        db.session.commit()

        response = client.post(
            f'/participant/{participant.id}/save_observations',
            json={'social': 'Teamfähig', 'verbal': 'Kommunikativ'},
        )
        assert response.status_code == 200

        response = client.post(
            f'/save_self_assessment/{participant.id}',
            json={'content': 'Ich bin zuverlässig.'},
        )
        assert response.status_code == 200

        response = client.post(
            f'/run_ki_analysis/{participant.id}',
            data={'ki_prompt': '{{context}}', 'ki_model': 'mistral'},
        )
        assert response.status_code == 200

        template = ReportTemplate(
            name='Task Flow Template',
            description='Task Flow Template',
            design_config='{"primary_color": "#000000", "layout_style": "classic"}',
            is_active=True,
        )
        db.session.add(template)
        db.session.flush()

        config = ReportConfiguration(
            group_id=group.id,
            template_id=template.id,
            modules_config='{"cover_page": {"enabled": true}}',
        )
        db.session.add(config)
        db.session.commit()

        mock_instance = MagicMock()
        mock_instance.build_html.return_value = '<html>Preview</html>'
        mock_instance.to_pdf.return_value = b'%PDF-1.4 test'
        mock_report_generator.return_value = mock_instance

        response = client.get(f'/reports/{group.id}/preview/{participant.id}')
        assert response.status_code == 200

        response = client.get(f'/reports/{group.id}/generate-pdf/{participant.id}')
        assert response.status_code == 200
        assert 'application/pdf' in response.content_type
