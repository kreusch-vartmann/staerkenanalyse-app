"""
Integration-Tests für observation_tasks Blueprint.
"""

import io
import json
from unittest.mock import patch

import pytest

from models import Task, TaskVersion


def _create_task(db, admin_user, **overrides):
    task = Task(
        title=overrides.get("title", "Test Task"),
        description=overrides.get("description"),
        notes=overrides.get("notes"),
        observation_area=overrides.get("observation_area", "Soziale Kompetenzen"),
        participant_count=overrides.get("participant_count", 4),
        duration_minutes=overrides.get("duration_minutes", 30),
        is_active=True,
        is_example=False,
        created_by_id=admin_user.id,
    )
    db.session.add(task)
    db.session.flush()

    context_data = overrides.get(
        "context_data",
        {
            "observation_area": task.observation_area,
            "participant_count": task.participant_count,
            "duration_minutes": task.duration_minutes,
            "target_group": overrides.get("target_group"),
            "use_example": False,
        },
    )

    version = TaskVersion(
        task_id=task.id,
        version_number=1.0,
        content=overrides.get("content", "<h2>Test</h2><p>Initial</p>"),
        context_data=json.dumps(context_data),
        change_notes="Initiale Version",
        created_by_id=admin_user.id,
    )
    db.session.add(version)
    db.session.flush()
    task.current_version_id = version.id
    db.session.commit()
    return task


@pytest.mark.integration
class TestObservationTasksRoutes:
    def test_task_library_loads(self, client):
        response = client.get("/beobachtungsaufgaben/")
        assert response.status_code == 200

    def test_observer_can_view_but_not_manage_tasks(self, observer_client):
        """Beobachter dürfen die Bibliothek sehen, aber nicht verwalten.

        Laut Rollen-Template (`seed_permissions.ROLE_TEMPLATES`) besitzt die
        Beobachter-Rolle `observation_tasks.view`, nicht aber
        `observation_tasks.manage`. Die Bibliothek ist damit lesbar –
        schreibende Routen bleiben gesperrt.
        """
        assert observer_client.get("/beobachtungsaufgaben/").status_code == 200

        response = observer_client.post(
            "/beobachtungsaufgaben/neu",
            data={
                "observation_area": "Soziale Kompetenzen",
                "title": "Unerlaubte Aufgabe",
                "description": "Beschreibung",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers.get("Location", "").endswith("/")

    def test_create_task_post_creates_task(self, client, db, admin_user):
        before_count = db.session.query(Task).count()
        response = client.post(
            "/beobachtungsaufgaben/neu",
            data={
                "observation_area": "Soziale Kompetenzen",
                "participant_count": 4,
                "duration_minutes": 30,
                "target_group": "Auszubildende",
                "use_example": "on",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        after_count = db.session.query(Task).count()
        assert after_count == before_count + 1

        task = db.session.query(Task).order_by(Task.id.desc()).first()
        assert task is not None
        assert task.current_version is not None
        assert task.current_version.version_number == 1.0
        assert task.current_version.content

    def test_create_task_invalid_payload_rejected(self, client, db):
        before_count = db.session.query(Task).count()
        response = client.post(
            "/beobachtungsaufgaben/neu",
            data={
                "observation_area": "Soziale Kompetenzen",
                "participant_count": 99,
                "duration_minutes": 30,
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        after_count = db.session.query(Task).count()
        assert after_count == before_count

    @patch("blueprints.observation_tasks.generate_task")
    def test_generate_task_creates_new_version(self, mock_generate, client, db, admin_user):
        task = _create_task(db, admin_user)
        mock_generate.return_value = {
            "title": "KI Task",
            "content": "<h2>KI</h2><p>Generated</p>",
            "observation_focus": "Focus",
            "facilitator_notes": "Notes",
        }

        response = client.post(
            f"/beobachtungsaufgaben/{task.id}/generieren",
            data={"ki_model": "mistral"},
            follow_redirects=False,
        )
        assert response.status_code == 302

        db.session.refresh(task)
        versions = (
            db.session.query(TaskVersion)
            .filter(TaskVersion.task_id == task.id)
            .order_by(TaskVersion.version_number.asc())
            .all()
        )
        assert len(versions) == 2
        assert task.current_version is not None
        assert task.current_version.content == "<h2>KI</h2><p>Generated</p>"
        assert task.ki_model == "mistral"

    def test_generate_task_invalid_model_rejected(self, client, db, admin_user):
        task = _create_task(db, admin_user)
        response = client.post(
            f"/beobachtungsaufgaben/{task.id}/generieren",
            data={"ki_model": "invalid"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        versions = db.session.query(TaskVersion).filter_by(task_id=task.id).count()
        assert versions == 1

    def test_versions_endpoint_returns_list(self, client, db, admin_user):
        task = _create_task(db, admin_user)
        response = client.get(f"/beobachtungsaufgaben/{task.id}/versions")
        assert response.status_code == 200
        payload = response.get_json()
        assert isinstance(payload, list)
        assert payload

    def test_save_version_creates_new_version(self, client, db, admin_user):
        task = _create_task(db, admin_user)
        response = client.post(
            f"/beobachtungsaufgaben/{task.id}/speichern",
            json={
                "title": "Updated Task",
                "content": "<h2>Neu</h2><p>Content</p>",
                "change_notes": "Update",
            },
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "success"

        versions = db.session.query(TaskVersion).filter_by(task_id=task.id).count()
        db.session.refresh(task)
        assert versions == 2
        assert task.title == "Updated Task"

    @patch("blueprints.observation_tasks.refine_task_content")
    def test_chat_message_returns_updated_content(self, mock_refine, client, db, admin_user):
        task = _create_task(db, admin_user, content="<h2>Alt</h2><p>Content</p>" * 5)
        mock_refine.return_value = {
            "ai_response": "ok",
            "updated_content": "<h2>Neu</h2><p>Updated</p>",
        }

        response = client.post(
            f"/beobachtungsaufgaben/{task.id}/chat",
            json={"message": "Bitte kürzen", "current_content": task.current_version.content},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "success"
        assert payload["updated_content"] == "<h2>Neu</h2><p>Updated</p>"

    def test_view_example_valid(self, client, db, admin_user):
        task = _create_task(db, admin_user)
        response = client.get(f"/beobachtungsaufgaben/{task.id}/beispiel/erbengemeinschaft")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["title"]

    def test_view_example_invalid(self, client, db, admin_user):
        task = _create_task(db, admin_user)
        response = client.get(f"/beobachtungsaufgaben/{task.id}/beispiel/notfound")
        assert response.status_code == 404

    def test_discard_task_deletes_versions(self, client, db, admin_user):
        task = _create_task(db, admin_user)
        response = client.post(
            f"/beobachtungsaufgaben/{task.id}/verwerfen",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert db.session.get(Task, task.id) is None
        assert db.session.query(TaskVersion).filter_by(task_id=task.id).count() == 0

    def test_delete_task_deletes_versions(self, client, db, admin_user):
        task = _create_task(db, admin_user)
        response = client.post(
            f"/beobachtungsaufgaben/{task.id}/löschen",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert db.session.get(Task, task.id) is None
        assert db.session.query(TaskVersion).filter_by(task_id=task.id).count() == 0


@pytest.mark.integration
class TestObservationTasksExport:
    """PDF-/DOCX-Export einzelner Aufgaben (Teilnehmer-Ausdruck)."""

    def test_export_docx_returns_valid_file(self, client, db, admin_user):
        task = _create_task(db, admin_user, title="Exporttest")
        response = client.get(f"/beobachtungsaufgaben/{task.id}/export/docx")
        assert response.status_code == 200
        assert response.content_type == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert response.data[:2] == b"PK"  # DOCX ist ein ZIP-Container
        assert "attachment" in response.headers.get("Content-Disposition", "")

    def test_export_docx_without_content_redirects(self, client, db, admin_user):
        task = Task(
            title="Ohne Inhalt",
            observation_area="Soziale Kompetenzen",
            is_active=True,
            is_example=False,
            created_by_id=admin_user.id,
        )
        db.session.add(task)
        db.session.commit()

        response = client.get(f"/beobachtungsaufgaben/{task.id}/export/docx", follow_redirects=False)
        assert response.status_code == 302

    def test_export_pdf_requires_content(self, client, db, admin_user):
        task = Task(
            title="Ohne Inhalt",
            observation_area="Soziale Kompetenzen",
            is_active=True,
            is_example=False,
            created_by_id=admin_user.id,
        )
        db.session.add(task)
        db.session.commit()

        response = client.get(f"/beobachtungsaufgaben/{task.id}/export/pdf", follow_redirects=False)
        assert response.status_code == 302

    def test_export_pdf_or_graceful_error(self, client, db, admin_user):
        """WeasyPrint braucht System-Bibliotheken - auf Rechnern ohne
        Pango/Cairo wird ein Redirect + Flash statt eines 500ers erwartet."""
        task = _create_task(db, admin_user, title="PDF-Exporttest")
        response = client.get(f"/beobachtungsaufgaben/{task.id}/export/pdf", follow_redirects=False)
        assert response.status_code in (200, 302)
        if response.status_code == 200:
            assert response.content_type == "application/pdf"
            assert response.data[:5] == b"%PDF-"

    def test_export_requires_login(self, unauth_client, db, admin_user):
        task = _create_task(db, admin_user)
        response = unauth_client.get(f"/beobachtungsaufgaben/{task.id}/export/docx", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("Location", "")

    def test_export_observer_with_view_permission_allowed(self, observer_client, db, admin_user):
        """Export erfordert nur 'observation_tasks.view' (Leserecht) - das
        ist laut Rollen-Template Teil der Beobachter-Rolle, im Gegensatz zu
        z. B. der Aufgabenerstellung, die 'observation_tasks.manage' braucht."""
        task = _create_task(db, admin_user)
        response = observer_client.get(f"/beobachtungsaufgaben/{task.id}/export/docx", follow_redirects=False)
        assert response.status_code == 200


@pytest.mark.integration
class TestObservationTasksImport:
    """Einzelimport: 1 Datei (TXT/DOCX) = 1 Aufgabe."""

    def test_import_form_loads(self, client):
        response = client.get("/beobachtungsaufgaben/importieren")
        assert response.status_code == 200

    def test_import_txt_creates_task(self, client, db):
        content = b"Meine Testaufgabe\n\nErster Absatz.\n\nZweiter Absatz."
        response = client.post(
            "/beobachtungsaufgaben/importieren",
            data={
                "observation_area": "Soziale Kompetenzen",
                "title": "TXT Import Test",
                "participant_count": "4",
                "duration_minutes": "30",
                "task_file": (io.BytesIO(content), "aufgabe.txt"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/bearbeiten" in response.headers["Location"]

        task = db.session.query(Task).filter_by(title="TXT Import Test").first()
        assert task is not None
        assert task.observation_area == "Soziale Kompetenzen"
        assert "Erster Absatz" in task.current_version.content

    def test_import_docx_roundtrip_from_export(self, client, db, admin_user):
        """Export einer Aufgabe -> Re-Import muss dieselbe 2-Sektionen-
        Struktur (Aufgabe/Rahmenbedingungen) ergeben."""
        task = _create_task(
            db,
            admin_user,
            title="Round-Trip-Quelle",
            content=(
                "<h2>Round-Trip-Quelle</h2>"
                "<h3>Aufgabe</h3><p>Ausgangssituation.</p><p>Konkreter Auftrag.</p>"
                "<h3>Rahmenbedingungen</h3>"
                "<p><strong>Ablauf:</strong></p><ol><li>Phase 1</li><li>Phase 2</li><li>Phase 3</li></ol>"
                "<p><strong>Materialien:</strong></p><ul><li>Stifte</li><li>Papier</li></ul>"
            ),
        )

        from services.task_export import build_task_docx

        docx_bytes = build_task_docx(task)

        response = client.post(
            "/beobachtungsaufgaben/importieren",
            data={
                "observation_area": "Verbale Kompetenzen",
                "title": "Round-Trip-Ziel",
                "participant_count": "4",
                "duration_minutes": "30",
                "task_file": (io.BytesIO(docx_bytes), "export.docx"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert response.status_code == 302

        imported = db.session.query(Task).filter_by(title="Round-Trip-Ziel").first()
        assert imported is not None
        from services.task_normalization import _extract_sections, _validate_task_content

        sections = _extract_sections(imported.current_version.content)
        assert "Aufgabe" in sections
        assert "Rahmenbedingungen" in sections
        valid, reason = _validate_task_content(imported.current_version.content)
        assert valid, reason

    def test_import_without_file_redirects_with_warning(self, client, db):
        response = client.post(
            "/beobachtungsaufgaben/importieren",
            data={
                "observation_area": "Soziale Kompetenzen",
                "participant_count": "4",
                "duration_minutes": "30",
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_import_unsupported_extension_rejected(self, client, db):
        response = client.post(
            "/beobachtungsaufgaben/importieren",
            data={
                "observation_area": "Soziale Kompetenzen",
                "participant_count": "4",
                "duration_minutes": "30",
                "task_file": (io.BytesIO(b"%PDF-1.4"), "aufgabe.pdf"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert db.session.query(Task).filter_by(observation_area="Soziale Kompetenzen").count() == 0

    def test_import_invalid_observation_area_rejected(self, client, db):
        response = client.post(
            "/beobachtungsaufgaben/importieren",
            data={
                "observation_area": "Unsinn",
                "participant_count": "4",
                "duration_minutes": "30",
                "task_file": (io.BytesIO(b"Titel\n\nText"), "aufgabe.txt"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert db.session.query(Task).count() == 0

    def test_import_requires_manage_permission(self, observer_client, db):
        """Anders als Export (view reicht) braucht Import 'manage', analog
        zur Aufgabenerstellung."""
        response = observer_client.post(
            "/beobachtungsaufgaben/importieren",
            data={
                "observation_area": "Soziale Kompetenzen",
                "participant_count": "4",
                "duration_minutes": "30",
                "task_file": (io.BytesIO(b"Titel\n\nText"), "aufgabe.txt"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert db.session.query(Task).count() == 0

    def test_import_title_falls_back_to_filename(self, client, db):
        response = client.post(
            "/beobachtungsaufgaben/importieren",
            data={
                "observation_area": "Soziale Kompetenzen",
                "participant_count": "4",
                "duration_minutes": "30",
                "task_file": (io.BytesIO(b"Nur Text ohne kurze erste Zeile als moeglichen Titel, dies ist absichtlich sehr lang und ueberschreitet die 80-Zeichen-Grenze klar."), "meine_aufgabe.txt"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert response.status_code == 302
        task = db.session.query(Task).filter(Task.title.like("%meine aufgabe%")).first()
        assert task is not None


@pytest.mark.integration
class TestObservationTasksImportTemplate:
    """Download der leeren Vorlage für den Aufgaben-Import."""

    def test_template_download_returns_valid_docx(self, client):
        response = client.get("/beobachtungsaufgaben/importieren/vorlage.docx")
        assert response.status_code == 200
        assert response.content_type == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert response.data[:2] == b"PK"
        assert "attachment" in response.headers.get("Content-Disposition", "")

    def test_template_requires_login(self, unauth_client):
        response = unauth_client.get("/beobachtungsaufgaben/importieren/vorlage.docx", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("Location", "")

    def test_downloaded_template_can_be_reimported(self, client, db):
        """End-to-End: Vorlage herunterladen -> unverändert hochladen -> muss
        eine valide Aufgabe ergeben."""
        template_response = client.get("/beobachtungsaufgaben/importieren/vorlage.docx")
        assert template_response.status_code == 200

        import io

        response = client.post(
            "/beobachtungsaufgaben/importieren",
            data={
                "observation_area": "Soziale Kompetenzen",
                "title": "Aus Vorlage",
                "participant_count": "4",
                "duration_minutes": "30",
                "task_file": (io.BytesIO(template_response.data), "vorlage.docx"),
            },
            content_type="multipart/form-data",
            follow_redirects=False,
        )
        assert response.status_code == 302

        from models import Task

        task = db.session.query(Task).filter_by(title="Aus Vorlage").first()
        assert task is not None
        from services.task_normalization import _validate_task_content

        valid, reason = _validate_task_content(task.current_version.content)
        assert valid, reason
