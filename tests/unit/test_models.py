"""
Unit-Tests für Datenbank-Models (models.py)

Testet:
- Model-Erstellung und Validierung
- Relationships zwischen Models
- Constraints und Defaults
"""

import json
import pytest
from datetime import date

from models import (
    Group,
    Participant,
    Prompt,
    SelfAssessment,
    ExplanationBlock,
    ReportTemplate,
    ReportConfiguration,
    CompanyLogo,
    ClientLogo,
    SignatureImage,
)


# ==================== GROUP MODEL TESTS ====================

@pytest.mark.unit
@pytest.mark.database
class TestGroupModel:
    """Tests für Group-Model"""

    def test_group_creation(self, db):
        """Test: Gruppe kann erstellt werden"""
        group = Group(
            name="Test-Gruppe",
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
            location="Test-Ort",
            leitung_fremdeinschatzung="Leitung FE",
            leitung_selbsteinschatzung="Leitung SE",
            beobachter1="Beobachter 1",
            beobachter2="Beobachter 2",
        )
        db.session.add(group)
        db.session.commit()

        assert group.id is not None
        assert group.name == "Test-Gruppe"
        assert group.date_from == date(2026, 1, 1)
        assert group.date_to == date(2026, 12, 31)

    def test_group_without_name_fails(self, db):
        """Test: Gruppe ohne Name schlägt fehl"""
        group = Group(date_from=date(2026, 1, 1))
        db.session.add(group)

        with pytest.raises(Exception):
            db.session.commit()

    def test_group_has_participants_relationship(self, db, sample_group):
        """Test: Group-Participant-Relationship funktioniert"""
        participant = Participant(name="Test TN", group_id=sample_group.id)
        db.session.add(participant)
        db.session.commit()

        # lazy='dynamic' liefert Query
        assert sample_group.participants.count() == 1
        assert sample_group.participants.first().name == "Test TN"


# ==================== PARTICIPANT MODEL TESTS ====================

@pytest.mark.unit
@pytest.mark.database
class TestParticipantModel:
    """Tests für Participant-Model"""

    def test_participant_creation(self, db, sample_group):
        """Test: Teilnehmer kann erstellt werden"""
        participant = Participant(
            name="Anna Schmidt",
            group_id=sample_group.id,
            observations=json.dumps({"social": "Test"}),
        )
        db.session.add(participant)
        db.session.commit()

        assert participant.id is not None
        assert participant.name == "Anna Schmidt"
        assert participant.group_id == sample_group.id

    def test_participant_without_name_fails(self, db, sample_group):
        """Test: Teilnehmer ohne Name schlägt fehl"""
        participant = Participant(group_id=sample_group.id)
        db.session.add(participant)

        with pytest.raises(Exception):
            db.session.commit()

    def test_participant_group_relationship(self, db, sample_participant):
        """Test: Participant → Group Relationship"""
        assert sample_participant.group is not None
        assert sample_participant.group.name == "Testgruppe A"

    def test_participant_has_self_assessment_relationship(self, db, sample_participant):
        """Test: Participant-SelfAssessment-Relationship"""
        assessment = SelfAssessment(
            participant_id=sample_participant.id,
            content="Selbsteinschätzung Test",
        )
        db.session.add(assessment)
        db.session.commit()

        assert sample_participant.self_assessment is not None
        assert sample_participant.self_assessment.content == "Selbsteinschätzung Test"


# ==================== SELF-ASSESSMENT MODEL TESTS ====================

@pytest.mark.unit
@pytest.mark.database
class TestSelfAssessmentModel:
    """Tests für SelfAssessment-Model"""

    def test_self_assessment_creation(self, db, sample_participant):
        """Test: Selbsteinschätzung kann erstellt werden"""
        assessment = SelfAssessment(
            participant_id=sample_participant.id,
            content="Ich bin teamfähig und zuverlässig.",
        )
        db.session.add(assessment)
        db.session.commit()

        assert assessment.id is not None
        assert "teamfähig" in assessment.content

    def test_self_assessment_unique_per_participant(self, db, sample_participant):
        """Test: Ein Teilnehmer sollte nur eine Selbsteinschätzung haben"""
        assessment1 = SelfAssessment(
            participant_id=sample_participant.id,
            content="Erste Einschätzung",
        )
        db.session.add(assessment1)
        db.session.commit()

        assessment2 = SelfAssessment(
            participant_id=sample_participant.id,
            content="Zweite Einschätzung",
        )
        db.session.add(assessment2)

        with pytest.raises(Exception):
            db.session.commit()


# ==================== PROMPT MODEL TESTS ====================

@pytest.mark.unit
@pytest.mark.database
class TestPromptModel:
    """Tests für Prompt-Model"""

    def test_prompt_creation(self, db):
        """Test: Prompt kann erstellt werden"""
        prompt = Prompt(
            name="Analyse-Prompt v2",
            description="Optimierter Prompt",
            content="Analysiere: {observations}",
        )
        db.session.add(prompt)
        db.session.commit()

        assert prompt.id is not None
        assert "{observations}" in prompt.content


# ==================== EXPLANATION BLOCK MODEL TESTS ====================

@pytest.mark.unit
@pytest.mark.database
class TestExplanationBlockModel:
    """Tests für ExplanationBlock-Model"""

    def test_explanation_block_creation(self, db):
        """Test: Erklärungsblock kann erstellt werden"""
        block = ExplanationBlock(
            title="Einleitung",
            content="Dies ist ein Test-Textbaustein.",
            order=1,
        )
        db.session.add(block)
        db.session.commit()

        assert block.id is not None
        assert block.title == "Einleitung"
        assert block.order == 1


# ==================== REPORT TEMPLATE MODEL TESTS ====================

@pytest.mark.unit
@pytest.mark.database
class TestReportTemplateModel:
    """Tests für ReportTemplate-Model"""

    def test_report_template_creation(self, db):
        """Test: Report-Template kann erstellt werden"""
        template = ReportTemplate(
            name="Standard-Report",
            description="Default-Template",
            design_config='{"primary_color": "#007bff"}',
            is_active=True,
        )
        db.session.add(template)
        db.session.commit()

        assert template.id is not None
        assert template.is_active is True

    def test_report_template_unique_name(self, db):
        """Test: Template-Name ist unique"""
        template1 = ReportTemplate(
            name="Unique-Template",
            design_config='{"layout_style": "classic"}',
        )
        template2 = ReportTemplate(
            name="Unique-Template",
            design_config='{"layout_style": "modern"}',
        )
        db.session.add(template1)
        db.session.commit()

        db.session.add(template2)
        with pytest.raises(Exception):
            db.session.commit()


# ==================== REPORT CONFIGURATION MODEL TESTS ====================

@pytest.mark.unit
@pytest.mark.database
class TestReportConfigurationModel:
    """Tests für ReportConfiguration-Model"""

    def test_report_configuration_creation(self, db, sample_group, sample_report_template, sample_company_logo):
        """Test: Report-Konfiguration kann erstellt werden"""
        config = ReportConfiguration(
            group_id=sample_group.id,
            template_id=sample_report_template.id,
            company_logo_id=sample_company_logo.id,
            modules_config='{"cover_page": {"enabled": true}}',
        )
        db.session.add(config)
        db.session.commit()

        assert config.id is not None
        assert config.group_id == sample_group.id


# ==================== LOGO MODEL TESTS ====================

@pytest.mark.unit
@pytest.mark.database
class TestLogoModels:
    """Tests für CompanyLogo und ClientLogo"""

    def test_company_logo_creation(self, db):
        logo = CompanyLogo(
            logo_path="uploads/logos/company_logo.png",
            filename="company_logo.png",
            is_active=True,
        )
        db.session.add(logo)
        db.session.commit()

        assert logo.id is not None
        assert logo.is_active is True

    def test_client_logo_creation(self, db, sample_group):
        logo = ClientLogo(
            group_id=sample_group.id,
            logo_path="uploads/logos/client_logo.png",
            filename="client_logo.png",
        )
        db.session.add(logo)
        db.session.commit()

        assert logo.id is not None
        assert logo.group_id == sample_group.id


# ==================== SIGNATURE IMAGE MODEL TESTS ====================

@pytest.mark.unit
@pytest.mark.database
class TestSignatureImageModel:
    """Tests für SignatureImage-Model"""

    def test_signature_image_creation(self, db):
        signature = SignatureImage(
            role="leitung_fe",
            image_path="uploads/signatures/sig_fe.png",
            filename="sig_fe.png",
            is_active=True,
        )
        db.session.add(signature)
        db.session.commit()

        assert signature.id is not None
        assert signature.role == "leitung_fe"
        assert signature.image_path.endswith(".png")
