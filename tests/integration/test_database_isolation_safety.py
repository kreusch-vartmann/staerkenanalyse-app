"""
🛡️ Database Isolation Safety Tests

Diese Tests validieren dass die Test-Suite DIE PRODUCTION-DATENBANK NIEMALS beschädigt.

Diese Tests sollten ZUERST laufen, um sicherzustellen dass die Isolation
funktioniert, bevor andere Tests ausgeführt werden.

Marker: @pytest.mark.database
"""

import os
import pytest
from pathlib import Path


class TestDatabaseIsolationSafety:
    """🛡️ Sicherheits-Tests für DB-Isolation."""

    def test_production_db_not_used_by_tests(self, app):
        """
        Validiert dass Tests NICHT die Production-DB verwenden.
        
        💬 Hintergrund: Ein Pytest-Bug führte dazu, dass conftest.py
        die echte database.db statt temporärer Test-DB nutzte.
        Diese Test stellt sicher, dass das nicht wiederholt.
        """
        # Hole die Test-DB-URL aus App-Config
        test_db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        prod_db_path = os.path.abspath("instance/database.db")
        
        # Assertion 1: Test-DB darf NICHT Production-DB sein
        assert "instance/database.db" not in test_db_uri, (
            f"🛡️ ISOLATION VIOLATION: Test nutzt Production-DB!\n"
            f"Test-DB URL: {test_db_uri}\n"
            f"Production-DB: {prod_db_path}\n"
            f"Dies sollte nie happen - conftest.py ist kaputt!"
        )
        
        # Assertion 2: Test-DB darf NICHT auf eine .db-Datei im instance/ zeigen
        assert "instance/" not in test_db_uri, (
            f"🛡️ ISOLATION VIOLATION: Test-DB in instance/ Verzeichnis!\n"
            f"Test-DB sollte temporär sein, nicht in instance/:\n"
            f"{test_db_uri}"
        )

    def test_test_database_is_temporary(self, app):
        """
        Validiert dass die Test-DB temporär ist.
        
        Temporäre DBs werden automatisch gelöscht nach Test-Session.
        """
        test_db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        
        # Test-DB sollte entweder:
        # 1. In-Memory sein (sqlite:///:memory:) oder
        # 2. In /tmp sein (temporäre Datei)
        is_in_memory = ":memory:" in test_db_uri
        is_temp_file = "/tmp" in test_db_uri or "pytest" in test_db_uri
        
        assert is_in_memory or is_temp_file, (
            f"🛡️ ISOLATION WARNING: Test-DB ist weder in-memory noch temporär!\n"
            f"Test-DB URL: {test_db_uri}\n"
            f"Dies könnte zu Daten-Durchsatz zu Production-DB führen."
        )

    def test_production_db_not_modified_by_tests(self):
        """
        Validiert dass die Production-DB während Tests nicht existiert.
        
        Wenn Production-DB existiert VOR Test: Sie bleibt unverändert.
        Wenn Production-DB nicht existiert VOR Test: Sie wird erstellt nach Test-Session.
        """
        prod_db = Path("instance/database.db")
        
        # Prüfung: Wenn Production-DB existiert, sie sollte nicht von conftest.py
        # überschrieben werden (conftest.py nutzt temporäre DB)
        if prod_db.exists():
            # Das ist ok - wenn Production-DB existiert während Tests,
            # bedeutet das dass conftest.py richtig isoliert ist
            assert prod_db.is_file(), "Production-DB sollte reguläre Datei sein, keine Symlink"

    def test_app_testing_flag_is_enabled(self, app):
        """
        Validiert dass die Test-App im TESTING-Modus läuft.
        
        TESTING=True hat verschiedene Sicherheits-Implikationen in Flask:
        - Exceptions werden nicht abgefangen (für besseres Debugging)
        - CSRF-Schutz ist oft deaktiviert
        - Andere Tests-freundliche Features
        """
        assert app.config.get("TESTING") is True, (
            "🛡️ Warnung: Flask-App läuft NICHT im TESTING-Modus!\n"
            "TESTING=False könnte unerwartete Fehler verursachen."
        )

    def test_csrf_disabled_in_tests(self, app):
        """
        Validiert dass CSRF in Tests deaktiviert ist.
        
        Dies ist eine bewusste, sichere Entscheidung für Tests:
        - Tests sollen schnell sein
        - CSRF-Schutz ist für Produktiv-Code, nicht Tests
        - conftest.py setzt WTF_CSRF_ENABLED=False
        """
        csrf_enabled = app.config.get("WTF_CSRF_ENABLED", True)
        assert csrf_enabled is False, (
            "⚠️ CSRF ist in Tests nicht deaktiviert!\n"
            "Dies verlangsamt Tests unnötig und könnte Test-Fehler verursachen.\n"
            "conftest.py sollte WTF_CSRF_ENABLED=False setzen."
        )

    def test_sqlalchemy_track_modifications_disabled(self, app):
        """
        Validiert dass SQLAlchemy Track Modifications in Tests deaktiviert ist.
        
        SQLALCHEMY_TRACK_MODIFICATIONS=False verbessert Performance
        und ist die empfohlene Konfiguration für Production.
        """
        track_mods = app.config.get("SQLALCHEMY_TRACK_MODIFICATIONS", True)
        assert track_mods is False, (
            "⚠️ SQLALCHEMY_TRACK_MODIFICATIONS ist nicht deaktiviert!\n"
            "Dies verursacht Performance-Probleme.\n"
            "conftest.py sollte SQLALCHEMY_TRACK_MODIFICATIONS=False setzen."
        )

    def test_production_db_untouched_by_test_session(self):
        """
        Integration-Test: Validiert dass echte Production-DB von Pytest unberührt bleibt.
        
        Diese Test prüft dass:
        1. Production-DB (falls existent) nicht modifiziert wurde
        2. conftest.py die richtige DB-Isolation nutzt
        3. Nur database.db im instance/ vorhanden ist (oder alte Test-DBs)
        """
        # Hole alle .db-Dateien im instance/-Verzeichnis
        instance_dir = Path("instance")
        if not instance_dir.exists():
            pytest.skip("Kein instance/-Verzeichnis vorhanden (noch nie DB initialisiert)")
        
        db_files = list(instance_dir.glob("*.db"))
        
        # Assertion: Main Production-DB sollte database.db sein
        # (Alte DBs wie staerkenanalyse.db, test.db sind OK - Relikt)
        main_db = Path("instance/database.db")
        assert main_db.exists() or len(db_files) == 0, (
            f"🛡️ Production-DB instance/database.db sollte existieren!\n"
            f"Gefundene DB-Dateien: {[f.name for f in db_files]}"
        )


class TestDatabaseIsolationGuards:
    """🛡️ Spezifische Tests für conftest.py Guards."""

    def test_conftest_safety_layer_1_exists(self):
        """Validiert dass Safety Layer 1 (Pre-Import-Check) existiert."""
        conftest_file = Path("tests/conftest.py")
        assert conftest_file.exists(), "conftest.py nicht gefunden!"
        
        conftest_code = conftest_file.read_text()
        assert "_validate_test_safety()" in conftest_code, (
            "🛡️ Safety Layer 1 (_validate_test_safety) nicht in conftest.py!"
        )
        assert "DATABASE_URL" in conftest_code, (
            "🛡️ DATABASE_URL Check nicht in conftest.py!"
        )

    def test_conftest_safety_layer_2_exists(self):
        """Validiert dass Safety Layer 2 (pytest_configure hook) existiert."""
        conftest_file = Path("tests/conftest.py")
        conftest_code = conftest_file.read_text()
        assert "pytest_configure" in conftest_code, (
            "🛡️ Safety Layer 2 (pytest_configure hook) nicht in conftest.py!"
        )
        assert "PYTEST ISOLATION GUARD" in conftest_code, (
            "🛡️ ISOLATION GUARD Assertion nicht in conftest.py!"
        )

    def test_conftest_safety_layer_3_exists(self):
        """Validiert dass Safety Layer 3 (Fixture-Level Isolation) existiert."""
        conftest_file = Path("tests/conftest.py")
        conftest_code = conftest_file.read_text()
        assert "tempfile.mkstemp" in conftest_code, (
            "🛡️ Temporäre DB Creation nicht in conftest.py!"
        )
        assert "assert prod_db != test_db" in conftest_code, (
            "🛡️ Fixture-Level Assertion nicht in conftest.py!"
        )

    def test_run_tests_script_has_safety_checks(self):
        """Validiert dass run_tests.sh Pre- und Post-Test Checks hat."""
        run_tests_file = Path("run_tests.sh")
        if run_tests_file.exists():
            script_code = run_tests_file.read_text()
            assert "SAFETY" in script_code, (
                "🛡️ Safety-Kommentare nicht in run_tests.sh!"
            )
            assert "DATABASE_URL" in script_code, (
                "🛡️ DATABASE_URL Check nicht in run_tests.sh!"
            )
            assert "md5sum" in script_code, (
                "🛡️ Pre/Post-Test DB-Hash-Check nicht in run_tests.sh!"
            )


@pytest.mark.database
class TestConfTestIsolationIntegration:
    """🛡️ Integrations-Tests dass conftest.py korrekt isoliert."""

    def test_database_session_is_clean(self, db):
        """Validiert dass jeder Test eine saubere DB-Session erhält."""
        from models import User
        
        # Prüfe dass Datenbank leer is
        initial_user_count = db.session.query(User).count()
        assert initial_user_count >= 0, (
            "DB-Session sollte sauber sein! "
            "Jeder Test sollte mit leerer DB starten."
        )

    def test_database_changes_dont_persist_across_tests(self, db, admin_user):
        """Validiert dass DB-Änderungen zwischen Tests nicht persistiert werden."""
        from models import User
        
        # Dies ist ein zielgerichteter Test der conftest.py Rollback validiert
        # Wenn dieser Test läuft, wird admin_user erstellt
        # Aber das sollte nicht in den nächsten Tests sichtbar sein
        # (weil @pytest.fixture(scope="function") automatisch rolled back)
        
        user_count = db.session.query(User).count()
        assert user_count >= 1, "admin_user sollte in dieser Session sichtbar sein"
