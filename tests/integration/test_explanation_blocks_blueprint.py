"""
Integration-Tests für Explanation-Blocks-Blueprint (blueprints/explanation_blocks.py)
"""

import pytest
from models import ExplanationBlock


@pytest.mark.integration
class TestExplanationBlocksRoutes:
    def test_manage_explanation_blocks_loads(self, client):
        response = client.get('/explanation-blocks')
        assert response.status_code == 200

    def test_add_explanation_block(self, client, db):
        response = client.post(
            '/explanation-block/add',
            data={'title': 'Block 1', 'content': 'Inhalt', 'order': 1},
            follow_redirects=True,
        )
        assert response.status_code == 200
        block = db.session.query(ExplanationBlock).filter_by(title='Block 1').first()
        assert block is not None

    def test_edit_explanation_block(self, client, db, sample_explanation_block):
        response = client.post(
            f'/explanation-block/edit/{sample_explanation_block.id}',
            data={'title': 'Block Update', 'content': 'Neu', 'order': 2},
            follow_redirects=True,
        )
        assert response.status_code == 200
        db.session.refresh(sample_explanation_block)
        assert sample_explanation_block.title == 'Block Update'

    def test_delete_explanation_block(self, client, db, sample_explanation_block):
        block_id = sample_explanation_block.id
        response = client.post(
            f'/explanation-block/delete/{block_id}',
            follow_redirects=True,
        )
        assert response.status_code == 200
        deleted = db.session.get(ExplanationBlock, block_id)
        assert deleted is None
