"""
Integration-Tests für Data-IO-Blueprint (blueprints/data_io.py)
"""

import json
import pytest
from io import BytesIO
from models import Participant


@pytest.mark.integration
class TestDataIORoutes:
    def test_data_entry_rework_loads(self, client):
        response = client.get('/data-entry/rework')
        assert response.status_code == 200

    def test_data_entry_search_no_query(self, client):
        response = client.get('/data-entry/search')
        assert response.status_code == 200

    def test_data_entry_search_query(self, client, sample_participant):
        response = client.get('/data-entry/search', query_string={'query': 'Max'})
        assert response.status_code == 200
        assert sample_participant.name.encode() in response.data

    def test_api_get_participants_by_group(self, client, sample_group, sample_participant):
        response = client.get(f'/api/group/{sample_group.id}/participants')
        assert response.status_code == 200
        data = response.get_json()
        assert any(p['name'] == sample_participant.name for p in data)

    def test_api_get_observations(self, client, db, sample_participant):
        sample_participant.observations = json.dumps({'social': 'A', 'verbal': 'B'})
        db.session.commit()
        response = client.get(f'/api/participant/{sample_participant.id}/observations')
        assert response.status_code == 200
        data = response.get_json()
        assert data['social'] == 'A'

    def test_save_observations_api(self, client, db, sample_participant):
        payload = {'social': 'Test', 'verbal': 'Test2'}
        response = client.post(
            f'/save_observations/{sample_participant.id}',
            json=payload,
        )
        assert response.status_code == 200
        db.session.refresh(sample_participant)
        saved = json.loads(sample_participant.observations)
        assert saved['social'] == 'Test'

    def test_import_page_loads(self, client):
        response = client.get('/import')
        assert response.status_code == 200

    def test_export_selection_loads(self, client):
        response = client.get('/export_selection')
        assert response.status_code == 200

    def test_export_data_csv(self, client, db, sample_participant):
        response = client.post(
            '/export_data',
            data={'select_all_data': 'true', 'format': 'csv'},
        )
        assert response.status_code == 200
        assert 'csv' in response.content_type
        assert sample_participant.name.encode() in response.data
