"""
Integration-Tests für Prompts-Blueprint (blueprints/prompts.py)
"""

import pytest
from models import Prompt


@pytest.mark.integration
class TestPromptsRoutes:
    def test_manage_prompts_loads(self, client):
        response = client.get('/prompts')
        assert response.status_code == 200

    def test_add_prompt(self, client, db):
        response = client.post(
            '/prompt/add',
            data={'name': 'Test-Prompt', 'description': 'Desc', 'content': 'Analyse: {x}'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        prompt = db.session.query(Prompt).filter_by(name='Test-Prompt').first()
        assert prompt is not None

    def test_edit_prompt(self, client, db, sample_prompt):
        response = client.post(
            f'/prompt/edit/{sample_prompt.id}',
            data={'name': 'Prompt-Update', 'description': 'Neu', 'content': 'Neu Inhalt'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        db.session.refresh(sample_prompt)
        assert sample_prompt.name == 'Prompt-Update'

    def test_delete_prompt(self, client, db, sample_prompt):
        prompt_id = sample_prompt.id
        response = client.post(
            f'/prompt/delete/{prompt_id}',
            follow_redirects=True,
        )
        assert response.status_code == 200
        deleted = db.session.get(Prompt, prompt_id)
        assert deleted is None

    def test_get_prompt_content_api(self, client, sample_prompt):
        response = client.get(f'/api/prompt/{sample_prompt.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert 'content' in data

    def test_get_prompt_content_api_not_found(self, client):
        response = client.get('/api/prompt/99999')
        assert response.status_code == 404

    def test_add_prompt_can_set_default(self, client, db):
        response = client.post(
            '/prompt/add',
            data={
                'name': 'Default-Prompt',
                'description': 'Default desc',
                'content': 'Analyse: {x}',
                'is_default': '1',
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        prompt = db.session.query(Prompt).filter_by(name='Default-Prompt').first()
        assert prompt is not None
        assert prompt.is_default is True

    def test_default_prompt_is_exclusive(self, client, db):
        first = Prompt(name='Default A', description='A', content='A', is_default=True)
        second = Prompt(name='Default B', description='B', content='B', is_default=False)
        db.session.add_all([first, second])
        db.session.commit()

        response = client.post(
            f'/prompt/edit/{second.id}',
            data={
                'name': 'Default B',
                'description': 'B',
                'content': 'B',
                'is_default': '1',
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        db.session.refresh(first)
        db.session.refresh(second)
        assert second.is_default is True
        assert first.is_default is False
