"""
Pytest-Fixtures für Test-Suite

Dieses Modul stellt gemeinsame Fixtures für alle Tests bereit:
- app: Flask-App-Instanz
- client: Test-Client für HTTP-Requests
- db: Datenbank-Session mit automatischem Rollback
- sample_data: Vorgenerierte Testdaten

🛡️ SAFETY: Alle Tests laufen ISOLIERT mit temporärer Datenbank!
   Produktions-DB wird NIEMALS von Tests berührt.
"""

import os
import sys
import pytest
import tempfile
from datetime import date
from uuid import uuid4

# 🛡️ SAFETY LAYER 1: Pre-Test Database Isolation Check
# Diese Prüfung läuft VOR dem Import der Flask-App
def _validate_test_safety():
    """
    Validiert dass Tests in einer sicheren Umgebung laufen.
    Verhindert dass die Production-DB von Tests beschädigt wird.
    """
    env_db_url = os.getenv("DATABASE_URL", "").lower()
    
    # Prüfung 1: DATABASE_URL darf nicht auf Production-DB zeigen
    forbidden_patterns = [
        "database.db",  # Production-DB im Root
        "/prod",
        "/production", 
        "remote",
        ".sqlite",
    ]
    
    for pattern in forbidden_patterns:
        if pattern in env_db_url:
            raise RuntimeError(
                f"🚨 PYTEST SAFETY VIOLATION 🚨\n"
                f"DATABASE_URL zeigt auf Production-DB: {env_db_url}\n"
                f"Tests MÜSSEN mit isolierter Datenbank laufen!\n"
                f"Verwende: pytest (nutzt conftest.py Isolation)\n"
                f"ABBRUCH: Tests können nicht ausgeführt werden."
            )
    
    # Prüfung 2: Mindestens pytest im Prozess vorhanden
    if "pytest" not in sys.modules and __name__ == "__main__":
        # Optional: Warnung wenn nicht über pytest gestartet (für lokale Runs)
        pass

# Führe Safety-Check VOR App-Import durch
_validate_test_safety()

# 🛡️ SET DEFAULT TEST DATABASE CONFIG BEFORE APP IMPORT
# This prevents errors when app.py tries to initialize SQLAlchemy
os.environ.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:')
os.environ.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', 'False')

# Import der App und Extensions
from app import app as flask_app
from extensions import db as _db
from models import (
    Group,
    Participant,
    SelfAssessment,
    ExplanationBlock,
    Prompt,
    User,
    Role,
    ReportTemplate,
    ReportConfiguration,
    CompanyLogo,
    ClientLogo,
    SignatureImage,
)


def pytest_configure(config):
    """
    🛡️ SAFETY LAYER 2: Root-Level pytest Hook
    Läuft am ANFANG jeder Pytest-Session.
    Validiert dass Isolation aktiv ist.
    """
    # Assertion: DATABASE_URL darf nicht Production-DB sein
    prod_db_path = "instance/database.db"
    if os.path.exists(prod_db_path):
        # Production-DB existiert - prüfe dass Tests NICHT dagegen laufen
        prod_db_abs = os.path.abspath(prod_db_path)
        db_url = os.getenv("DATABASE_URL", "").lower()
        if prod_db_abs.lower() in db_url or "instance/database.db" in db_url:
            pytest.exit(
                f"🛡️ PYTEST ISOLATION GUARD 🛡️\n"
                f"Tests sollen NICHT gegen Production-DB laufen!\n"
                f"Erkannte Production-DB: {prod_db_abs}\n"
                f"DATABASE_URL: {db_url}\n\n"
                f"conftest.py erstellt automatisch temporäre Test-DB.\n"
                f"Diese Assertion sollte nicht erreicht werden!\n"
                f"Bei Fehler: Überprüfe pytest.ini und .env",
                1
            )


@pytest.fixture(scope="session")
def app():
    """
    Flask-App-Instanz für Test-Session.
    Nutzt IMMER separate Test-Datenbank (SQLite temporär).
    
    🛡️ SAFETY LAYER 3: Fixture-Level Isolation
    """
    # Erstelle temporäre Datenbankdatei (wird automatisch gelöscht)
    db_fd, db_path = tempfile.mkstemp(suffix=".db", prefix="pytest_")
    
    print(f"\n🛡️  Test-DB erstellt: {db_path}")
    
    # 🛡️ Assertion: Test-DB darf NICHT Production-DB sein
    prod_db = os.path.abspath("instance/database.db")
    test_db = os.path.abspath(db_path)
    assert prod_db != test_db, (
        f"SAFETY VIOLATION: Test-DB = Production-DB!\n"
        f"Test-DB: {test_db}\n"
        f"Prod-DB: {prod_db}"
    )
    
    # Test-Konfiguration mit isolierter DB
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key-only-for-tests',
        'WTF_CSRF_ENABLED': False,  # CSRF für Tests deaktivieren
    }
    
    # Nutze existierende Flask-App mit Test-Config
    flask_app.config.update(test_config)
    app = flask_app
    
    # Setup App-Context
    with app.app_context():
        _db.create_all()  # Erstelle alle Tabellen in temporärer DB
        yield app
        _db.drop_all()  # Cleanup nach Tests
    
    # Cleanup: Schließe und lösche temporäre DB
    try:
        os.close(db_fd)
        os.unlink(db_path)
        print(f"🛡️  Test-DB gelöscht: {db_path}\n")
    except Exception as e:
        print(f"⚠️  Fehler beim DB-Cleanup: {e}")


@pytest.fixture(scope="function")
def client(app, db, admin_user):
    """
    Test-Client für HTTP-Requests.
    Jeder Test bekommt einen frischen Client.
    """
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(admin_user.id)
        session["_fresh"] = True
        session["_id"] = "test-session"
    return client


@pytest.fixture(scope="function")
def unauth_client(app):
    """Test-Client ohne eingeloggten User."""
    return app.test_client()


@pytest.fixture(scope="function")
def observer_client(app, db, observer_user):
    """Test-Client mit eingeloggtem Beobachter."""
    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(observer_user.id)
        session["_fresh"] = True
        session["_id"] = "test-session"
    return client


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
def admin_role(db):
    """Erstellt eine Admin-Rolle."""
    role = Role.query.filter_by(name="admin").first()
    if role:
        return role
    role = Role(name="admin", description="Administrator")
    db.session.add(role)
    db.session.commit()
    return role


@pytest.fixture
def observer_role(db):
    """Erstellt eine Beobachter-Rolle."""
    role = Role.query.filter_by(name="beobachter").first()
    if role:
        return role
    role = Role(name="beobachter", description="Beobachter")
    db.session.add(role)
    db.session.commit()
    return role


@pytest.fixture
def admin_user(db, admin_role):
    """Erstellt einen Admin-User für Tests."""
    user = User.query.filter_by(email="admin@test.de").first()
    if user:
        if user.role_id != admin_role.id:
            user.role_id = admin_role.id
            db.session.commit()
        return user
    user = User(
        email="admin@test.de",
        role_id=admin_role.id,
        force_password_change=False,
    )
    user.set_password("testpassword123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def observer_user(db, observer_role, sample_group):
    """Erstellt einen Beobachter-User mit Gruppenzuordnung."""
    user = User.query.filter_by(email="observer@test.de").first()
    if user:
        if user.role_id != observer_role.id:
            user.role_id = observer_role.id
        user.is_active = True
        user.force_password_change = False
        if not user.groups.filter_by(id=sample_group.id).first():
            user.groups.append(sample_group)
        db.session.commit()
        return user
    user = User(
        email="observer@test.de",
        role_id=observer_role.id,
        force_password_change=False,
        is_active=True,
    )
    user.set_password("testpassword123")
    user.groups.append(sample_group)
    db.session.add(user)
    db.session.commit()
    return user


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
def other_group(db):
    """Erstellt eine zweite, nicht zugewiesene Gruppe."""
    group = Group(
        name="Testgruppe B",
        date_from=date(2026, 2, 1),
        date_to=date(2026, 7, 31),
        location="Test-Ort B",
        leitung_fremdeinschatzung="Leitung FE B",
        leitung_selbsteinschatzung="Leitung SE B",
        beobachter1="Beobachter B1",
        beobachter2="Beobachter B2",
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
def other_participant(db, other_group):
    """Erstellt einen Teilnehmer in einer nicht zugewiesenen Gruppe."""
    participant = Participant(
        name="Erika Muster",
        group_id=other_group.id,
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
        name=f"Test-Analyse-Prompt-{uuid4().hex}",
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
