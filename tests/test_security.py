import pytest
import httpx
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from django.test import override_settings
from openai import APITimeoutError, AuthenticationError
from test_pipeline import fixture
from cad_generator.schema import Layout
from cad_generator.services import llm_client


def request():
    return APIClient().post('/api/generate-floorplan/', {'prompt':'two rooms','width':10,'depth':8,'unit':'m'}, format='json')


def test_large_body_is_rejected_before_provider():
    with patch('cad_generator.services.llm_client.request_layout') as provider:
        r=APIClient().post('/api/generate-floorplan/', {'prompt':'a'*270000}, format='json')
    assert r.status_code==413
    provider.assert_not_called()


def test_repairs_are_bounded_and_lot_is_never_silently_changed():
    d=fixture(); d['lot']['width']=11
    with override_settings(GEOMETRY_REPAIR_RETRIES=1), patch('cad_generator.services.llm_client.request_layout',return_value=Layout.model_validate(d)) as provider:
        r=request()
    assert r.status_code==422
    assert provider.call_count==2


@pytest.mark.parametrize('error,status', [(llm_client.ProviderError('Safe failure'),502),(llm_client.ProviderTimeout('Timed out'),504)])
def test_provider_http_errors(error,status):
    with patch('cad_generator.services.llm_client.request_layout',side_effect=error):
        assert request().status_code==status


def test_throttle_before_paid_call():
    from cad_generator.views import GenerateView
    from rest_framework.throttling import AnonRateThrottle
    class OneRequest(AnonRateThrottle):
        rate='1/min'
    with patch.object(GenerateView,'throttle_classes',[OneRequest]), patch('cad_generator.services.llm_client.request_layout',return_value=Layout.model_validate(fixture())) as provider:
        assert request().status_code==200
        assert request().status_code==429
        assert provider.call_count==1


def test_structured_output_uses_layout_schema_and_no_sdk_retries(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','fake-test-token')
    with patch('cad_generator.services.llm_client.ChatOpenAI') as factory:
        llm=factory.return_value
        structured=llm.with_structured_output.return_value
        structured.invoke.return_value=Layout.model_validate(fixture())
        assert llm_client.request_layout({'prompt':'test'}).unit=='m'
        # Structured output is bound to the strict Layout schema.
        assert llm.with_structured_output.call_args.args[0] is Layout
        assert llm.with_structured_output.call_args.kwargs['method']=='json_schema'
        assert llm.with_structured_output.call_args.kwargs['strict'] is True
        # SDK automatic retries are disabled and the timeout is bounded <= 60s.
        assert factory.call_args.kwargs['max_retries']==0
        assert factory.call_args.kwargs['timeout'] <= 60


def test_missing_key_is_not_configured():
    with pytest.raises(llm_client.ProviderError) as exc:
        llm_client.request_layout({})
    assert 'not configured' in str(exc.value)


@pytest.mark.parametrize('kind',['timeout','auth','refusal'])
def test_provider_details_do_not_escape(monkeypatch,kind):
    monkeypatch.setenv('OPENAI_API_KEY','fake-test-token')
    with patch('cad_generator.services.llm_client.ChatOpenAI') as factory:
        llm=factory.return_value
        structured=llm.with_structured_output.return_value
        invoke=structured.invoke
        if kind=='timeout':
            invoke.side_effect=APITimeoutError(request=httpx.Request('POST','https://example.com'))
        elif kind=='auth':
            invoke.side_effect=AuthenticationError('SECRET PROVIDER BODY',response=httpx.Response(401,request=httpx.Request('POST','https://example.com')),body={})
        else:
            invoke.return_value=None
        expected=llm_client.ProviderTimeout if kind=='timeout' else llm_client.ProviderError
        with pytest.raises(llm_client.ProviderError) as exc:
            llm_client.request_layout({})
        assert isinstance(exc.value,expected)
        assert 'SECRET' not in str(exc.value)
