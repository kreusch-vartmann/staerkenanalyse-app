"""
Integration-Tests für observation_tasks Blueprint.
"""

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

    def test_observer_blocked_from_task_library(self, observer_client):
        response = observer_client.get("/beobachtungsaufgaben/")
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
