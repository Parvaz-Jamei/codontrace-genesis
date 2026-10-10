"""Cloud wiring uses fake provider responses; never spends API credits."""
from __future__ import annotations
import io
import json
import os
import threading
import urllib.error
import urllib.request

import pytest
from codontrace.console import providers, chat, server

class Response(io.BytesIO):
    def __init__(self, value):super().__init__(json.dumps(value).encode())

@pytest.fixture
def config(tmp_path,monkeypatch):
    monkeypatch.setenv('CODONTRACE_CONFIG_DIR',str(tmp_path))
    monkeypatch.delenv('OPENAI_API_KEY',raising=False);monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    monkeypatch.delenv('CODONTRACE_SETTINGS_TOKEN',raising=False)
    providers._CACHE.clear()
    yield tmp_path
    providers._CACHE.clear()


def test_catalog_dynamic_secret_free_and_disconnect(config,monkeypatch):
    key='fake-key-do-not-expose'
    providers.configure('openai',api_key=key)
    requests=[]
    def fake(req,timeout):
        requests.append(req)
        return Response({'data':[{'id':'gpt-test-new'},{'id':'gpt-test-image'},{'id':'<script>'}]})
    monkeypatch.setattr(providers,'open_request',fake)
    result=providers.refresh('openai')
    assert requests[0].full_url=='https://api.openai.com/v1/models'
    assert requests[0].get_header('Authorization')=='Bearer '+key
    assert key not in json.dumps(result) and 'fingerprint' not in json.dumps(result)
    row=result['providers'][0]
    assert [m['name'] for m in row['models']]==['gpt-test-image','gpt-test-new']
    assert row['models'][0]['chat_candidate'] is False
    assert row['models'][1]['chat_candidate'] is True
    if os.name!='nt':assert (config/'cloud_providers.json').stat().st_mode & 0o777==0o600
    providers.configure('openai',disconnect=True)
    assert not providers.provider_catalog()['providers'][0]['configured']
    assert key not in (config/'cloud_providers.json').read_text()
    with pytest.raises(providers.ProviderError,match='not_configured'):providers.resolve('openai::gpt-test-new')


def test_environment_priority_and_explicit_disable(config,monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY','environment-fake-key')
    providers.configure('deepseek',api_key='saved-fake-key')
    assert providers.resolve('deepseek::new-model')[2]['Authorization']=='Bearer environment-fake-key'
    providers.configure('deepseek',disconnect=True)
    with pytest.raises(providers.ProviderError):providers.resolve('deepseek::new-model')


@pytest.mark.parametrize('kind',['auth','malformed','too_large'])
def test_catalog_errors_are_bounded_and_never_echo_upstream(config,monkeypatch,kind):
    providers.configure('deepseek',api_key='fake-secret-key')
    def fake(req,timeout):
        if kind=='auth':raise urllib.error.HTTPError(req.full_url,401,'raw fake-secret-key',{},io.BytesIO(b'fake-secret-key'))
        return io.BytesIO(b'x'*(512*1024+2)) if kind=='too_large' else Response({'data':'bad'})
    monkeypatch.setattr(providers,'open_request',fake)
    result=providers.refresh('deepseek')
    assert result['providers'][1]['error']
    assert 'fake-secret-key' not in json.dumps(result)


def test_disconnect_during_refresh_cannot_restore_stale_catalog(config,monkeypatch):
    providers.configure('openai',api_key='fake-secret-key')
    def fake(req,timeout):
        providers.configure('openai',disconnect=True)
        return Response({'data':[{'id':'gpt-test'}]})
    monkeypatch.setattr(providers,'open_request',fake)
    result=providers.refresh('openai')
    assert result['providers'][0]['models']==[]
    assert not result['providers'][0]['configured']


def test_cloud_chat_routes_without_a_local_model_and_preserves_auth(config,monkeypatch):
    providers.configure('openai',api_key='fake-openai-key')
    monkeypatch.setattr(chat,'check_llm_status',lambda:{'mounted':False,'model':None})
    captured=[]
    def fake(req,timeout):
        captured.append((req,json.loads(req.data)))
        return Response({'choices':[{'message':{'content':'cloud response'}}]})
    monkeypatch.setattr(providers,'open_request',fake)
    result=chat.chat_turn('hello',model='openai::gpt-new',lang='en')
    assert result['source']=='llm' and result['reply']=='cloud response'
    req,payload=captured[0]
    assert req.full_url=='https://api.openai.com/v1/chat/completions'
    assert payload['model']=='gpt-new' and 'max_completion_tokens' in payload
    assert 'temperature' not in payload and 'max_tokens' not in payload
    assert req.get_header('Authorization')=='Bearer fake-openai-key'
    assert 'fake-openai-key' not in json.dumps(result)


def test_cloud_errors_do_not_masquerade_as_local_analyst(config,monkeypatch):
    providers.configure('deepseek',api_key='fake-deepseek-key')
    monkeypatch.setattr(chat,'check_llm_status',lambda:{'mounted':False,'model':None})
    def fake(req,timeout):raise urllib.error.HTTPError(req.full_url,401,'bad',{},io.BytesIO(b'fake-deepseek-key'))
    monkeypatch.setattr(providers,'open_request',fake)
    result=chat.chat_turn('hello',model='deepseek::new-model',lang='en')
    assert result['source']=='provider_error'
    assert result['error']=='provider_http_401'
    assert result['fallback'] is False
    assert 'fake-deepseek-key' not in json.dumps(result)


def test_provider_settings_http_authorization_and_secret_free_get(config,monkeypatch):
    monkeypatch.setenv('CODONTRACE_SETTINGS_TOKEN','test-settings-token')
    monkeypatch.setattr(providers,'open_request',lambda req,timeout:Response({'data':[{'id':'gpt-new'}]}))
    httpd=server.make_server('127.0.0.1',0)
    threading.Thread(target=httpd.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{httpd.server_port}'
    payload=json.dumps({'provider':'openai','action':'save','api_key':'fake-openai-key'}).encode()
    try:
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(urllib.request.Request(base+'/api/providers',data=payload,headers={'Content-Type':'application/json'}))
        assert err.value.code==403
        result=json.load(urllib.request.urlopen(urllib.request.Request(base+'/api/providers',data=payload,headers={'Content-Type':'application/json','Authorization':'Bearer test-settings-token'})))
        assert result['providers'][0]['models'][0]['id']=='openai::gpt-new'
        public=json.load(urllib.request.urlopen(base+'/api/providers'))
        assert 'fake-openai-key' not in json.dumps(public) and 'test-settings-token' not in json.dumps(public)
    finally:httpd.shutdown();httpd.server_close()


def test_official_provider_credentials_never_follow_redirects(config):
    request=urllib.request.Request('https://api.openai.com/v1/models',headers={'Authorization':'Bearer fake-key'})
    with pytest.raises(providers.ProviderError,match='redirect_refused'):
        providers._NoRedirect().redirect_request(request,None,302,'redirect',{},'https://other.example/steal')
