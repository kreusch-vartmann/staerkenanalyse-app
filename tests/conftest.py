"""
Pytest-Fixtures für Test-Suite

Dieses Modul stellt gemeinsame Fixtures für alle Tests bereit:
- app: Flask-App-Instanz
- client: Test-Client für HTTP-Requests
- db: Datenbank-Session mit automatischem Rollback
- sample_data: Vorgenerierte Testdaten
"""

import os
import pytest
import tempfile
from datetime import date
from uuid import uuid4

# Import der App und Extensions
from app import app as flask_app
from extensions import db as _db
from models import (
    Group,
    Participant,
    SelfAssessment,
    ExplanationBlock,
    Prompt,
    ReportTemplate,
    ReportConfiguration,
    CompanyLogo,
    ClientLogo,
    SignatureImage,
)


@pytest.fixture(scope="session")
def app():
    """
    Flask-App-Instanz für Test-Session.
    Nutzt separate Test-Datenbank (SQLite in-memory).
    """
    # Erstelle temporäre Datenbankdatei
    db_fd, db_path = tempfile.mkstemp()
    
    # Test-Konfiguration
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,  # CSRF für Tests deaktivieren
    }
    
    # Nutze existierende Flask-App mit Test-Config
    flask_app.config.update(test_config)
    app = flask_app
    
    # Setup App-Context
    with app.app_context():
        _db.create_all()  # Erstelle alle Tabellen
        yield app
        _db.drop_all()  # Cleanup nach Tests
    
    # Schließe und lösche temporäre DB
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def client(app):
    """
    Test-Client für HTTP-Requests.
    Jeder Test bekommt einen frischen Client.
    """
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """
    Datenbank-Session mit automatischem Rollback.
    Jeder Test bekommt eine saubere DB-Session.
    """
    with app.app_context():
        # Begin nested transaction
        _db.session.begin_nested()
        
        yield _db
        
        # Rollback after test
        _db.session.rollback()
        _db.session.remove()


@pytest.fixture
def sample_group(db):
    """Erstellt eine Test-Gruppe."""
    group = Group(
        name="Testgruppe A",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 6, 30),
        location="Test-Ort",
        leitung_fremdeinschatzung="Leitung FE",
        leitung_selbsteinschatzung="Leitung SE",
        beobachter1="Beobachter 1",
        beobachter2="Beobachter 2",
    )
    db.session.add(group)
    db.session.commit()
    return group


@pytest.fixture
def sample_participant(db, sample_group):
    """Erstellt einen Test-Teilnehmer."""
    participant = Participant(
        name="Max Mustermann",
        group_id=sample_group.id,
        observations="{}",
        sk_ratings="{}",
        vk_ratings="{}",
        ki_texts="{}",
        footer_data="{}",
    )
    db.session.add(participant)
    db.session.commit()
    return participant


@pytest.fixture
def sample_self_assessment(db, sample_participant):
    """Erstellt eine Selbsteinschätzung."""
    assessment = SelfAssessment(
        participant_id=sample_participant.id,
        content="Ich bin teamfähig und kommunikativ.",
    )
    db.session.add(assessment)
    db.session.commit()
    return assessment


@pytest.fixture
def sample_observations_payload():
    """Beobachtungs-JSON für Tests (kein eigenes Model)."""
    return {
        "social": "Zeigt exzellente Teamfähigkeit",
        "verbal": "Kommuniziert klar und präzise",
    }


@pytest.fixture
def sample_prompt(db):
    """Erstellt einen Test-Prompt."""
    prompt = Prompt(
        name="Test-Analyse-Prompt",
        description="Prompt für Unit-Tests",
        content="Analysiere folgende Beobachtungen: {observations}"
    )
    db.session.add(prompt)
    db.session.commit()
    return prompt


@pytest.fixture
def sample_explanation_block(db):
    """Erstellt einen Erklärungs-Textbaustein."""
    block = ExplanationBlock(
        title="Test-Erklärung",
        content="Dies ist ein Test-Textbaustein für Reports.",
        order=1,
    )
    db.session.add(block)
    db.session.commit()
    return block


@pytest.fixture
def sample_report_template(db):
    """Erstellt ein Report-Template."""
    template = ReportTemplate(
        name=f"Test-Report-Template-{uuid4().hex}",
        description="Template für Unit-Tests",
        design_config='{"primary_color": "#000000", "layout_style": "classic"}',
        is_active=True
    )
    db.session.add(template)
    db.session.commit()
    return template


@pytest.fixture
def sample_company_logo(db):
    """Erstellt ein Company-Logo."""
    logo = CompanyLogo(
        logo_path="uploads/logos/company_logo.png",
        filename="company_logo.png",
        is_active=True,
    )
    db.session.add(logo)
    db.session.commit()
    return logo


@pytest.fixture
def sample_client_logo(db, sample_group):
    """Erstellt ein Client-Logo."""
    logo = ClientLogo(
        group_id=sample_group.id,
        logo_path="uploads/logos/client_logo.png",
        filename="client_logo.png",
    )
    db.session.add(logo)
    db.session.commit()
    return logo


@pytest.fixture
def sample_report_configuration(db, sample_group, sample_report_template, sample_company_logo):
    """Erstellt eine Report-Konfiguration."""
    config = ReportConfiguration(
        group_id=sample_group.id,
        template_id=sample_report_template.id,
        company_logo_id=sample_company_logo.id,
        modules_config='{"cover_page": {"enabled": true}}',
    )
    db.session.add(config)
    db.session.commit()
    return config


@pytest.fixture
def mock_mistral_response():
    """Mock-Antwort für Mistral-API-Calls."""
    return {
        "content": '{"strengths": ["Teamfähigkeit", "Kommunikation"], "areas_for_development": ["Zeitmanagement"], "summary": "Sehr guter Teilnehmer"}',
        "provider": "mistral"
    }


@pytest.fixture
def mock_gemini_response():
    """Mock-Antwort für Google-Gemini-API-Calls."""
    return {
        "content": '{"strengths": ["Analytisches Denken"], "areas_for_development": ["Präsentationsfähigkeiten"], "summary": "Solide Leistung"}',
        "provider": "google_gemini"
    }
