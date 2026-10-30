import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'core.settings'
os.environ['DJANGO_LOAD_DOTENV'] = 'false'
os.environ['DJANGO_SECRET_KEY'] = 'test-only-not-for-deployment'
os.environ['OPENAI_API_KEY'] = ''
import django
django.setup()
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from unittest.mock import patch
from test_pipeline import fixture
from cad_generator.schema import Layout

@pytest.fixture(autouse=True)
def clear_throttles():
    cache.clear()


def test_generate_api():
    with patch('cad_generator.services.llm_client.request_layout', return_value=Layout.model_validate(fixture())):
        r = APIClient().post('/api/generate-floorplan/', {'prompt':'two rooms','width':10,'depth':8,'unit':'m'}, format='json')
    assert r.status_code == 200, r.data
    assert r.data['layout'] == fixture()
    assert r.data['dxf_content'].endswith('EOF\n')
    assert r.data['render_geometry']['doors']


def test_modify_api_preserves_dimensions_with_bounded_repair():
    bad = fixture(); bad['unit']='ft'
    with patch('cad_generator.services.llm_client.request_layout', side_effect=[Layout.model_validate(bad), Layout.model_validate(fixture())]) as provider:
        r=APIClient().post('/api/modify-floorplan/', {'current_layout':fixture(),'instruction':'improve furniture'}, format='json')
    assert r.status_code==200, r.data
    assert provider.call_count == 2
    assert r.data['layout']['unit']=='m'


def test_invalid_input_never_calls_provider():
    with patch('cad_generator.services.llm_client.request_layout') as provider:
        r=APIClient().post('/api/generate-floorplan/', {'prompt':'x','width':float('inf'),'depth':8,'unit':'m'}, content_type='application/json')
    assert r.status_code==400
    provider.assert_not_called()
