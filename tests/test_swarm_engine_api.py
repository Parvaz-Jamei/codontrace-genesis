from __future__ import annotations

import http.client
import json
import threading

import pytest

from codontrace.console.science_tools import invoke_tool, llm_tool_schemas
from codontrace.console.server import make_server
from codontrace.swarm import SwarmCoordinator, SwarmEngineLink, service
from codontrace.swarm.experiments import hello, reading


@pytest.fixture
def http_swarm(monkeypatch,tmp_path):
    monkeypatch.setenv('CODONTRACE_API_TOKEN','test-token')
    monkeypatch.setenv('CODONTRACE_SWARM_DIR',str(tmp_path))
    service._SWARMS.clear()
    server=make_server('127.0.0.1',0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield server.server_address[1]
    server.shutdown();server.server_close();thread.join(2);service._SWARMS.clear()


def call(port,action,args,token='test-token'):
    c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
    c.request('POST','/api/swarm',json.dumps({'action':action,'args':args}),
              {'Content-Type':'application/json','Authorization':'Bearer '+token})
    r=c.getresponse();data=json.loads(r.read());c.close();return r.status,data


def test_real_http_auth_and_ingest(http_swarm):
    status,_=call(http_swarm,'snapshot',{'swarm_id':'lab'},token='wrong');assert status==403
    status,result=call(http_swarm,'ingest',{'swarm_id':'lab','message':hello('lab','a')});assert status==200 and result['result']['accepted']
    status,result=call(http_swarm,'snapshot',{'swarm_id':'lab'});assert status==200 and 'a' in result['result']['state']['nodes']
    status,_=call(http_swarm,'snapshot',{'swarm_id':'../escape'});assert status==400
    status,_=call(http_swarm,'command',{'swarm_id':'lab','node_id':'a','operation':'exec','params':{}});assert status==400


def test_api_isolates_swarms_and_pause_resume(http_swarm):
    call(http_swarm,'ingest',{'swarm_id':'lab','message':hello('lab','a')})
    status,_=call(http_swarm,'ingest',{'swarm_id':'other','message':hello('lab','a')});assert status==400
    status,r=call(http_swarm,'status',{'swarm_id':'lab','status':'paused'});assert status==200 and r['result']['status']=='paused'
    status,_=call(http_swarm,'command',{'swarm_id':'lab','node_id':'a','operation':'sample','params':{'channel':'s'}});assert status==400
    status,_=call(http_swarm,'status',{'swarm_id':'lab','status':'running'});assert status==200


def test_llm_scope_readonly_while_stopped(http_swarm):
    call(http_swarm,'ingest',{'swarm_id':'lab','message':hello('lab','a')})
    call(http_swarm,'status',{'swarm_id':'lab','status':'stopped'})
    assert any(s['function']['name']=='swarm_inspect' for s in llm_tool_schemas())
    assert invoke_tool('swarm_inspect',{'swarm_id':'lab'},selected_run_id='lab')['ok']
    assert not invoke_tool('swarm_inspect',{'swarm_id':'other'},selected_run_id='lab')['ok']


def test_real_engine_boundary_and_optin_world_mapping():
    from codontrace.genesis.engine import GenesisEngine
    from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
    s=SwarmCoordinator('lab');s.ingest(hello('lab','a'),now_ms=1000);s.ingest(reading('lab','a',1,1000,2),now_ms=1000)
    engine=GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7,tick_count=2,population=2))
    def mapper(world,fusion):world.place_resource((3,3),fusion['value'])
    link=SwarmEngineLink(s,quantity='signal',unit='arb',clock_ms=lambda:1000,environment_mapper=mapper).attach(engine)
    result=link.run_ticks()
    rows=s.snapshot(now_ms=1000)['state']['engine_boundaries']
    assert result.validate_consistency().passed
    assert len(rows)==len(result.ticks)==2
    assert rows[0]['mapped_before_generation'] and rows[0]['world_before'] != rows[0]['world_after']
    assert rows[0]['spec_digest']==engine.spec.digest()
    with pytest.raises(ValueError):link.attach(engine)


def test_device_credentials_are_ingestion_only(http_swarm,monkeypatch):
    monkeypatch.setenv('CODONTRACE_SWARM_NODE_TOKENS',json.dumps({'lab/a':'node-secret'}))
    status,_=call(http_swarm,'ingest',{'swarm_id':'lab','message':hello('lab','a')},token='node-secret')
    assert status==200
    status,_=call(http_swarm,'ingest',{'swarm_id':'lab','message':hello('lab','b')},token='node-secret')
    assert status==403
    status,_=call(http_swarm,'command',{'swarm_id':'lab','node_id':'a','operation':'sample','params':{'channel':'s'}},token='node-secret')
    assert status==403


def test_engine_observation_continues_when_swarm_paused():
    from codontrace.genesis.engine import GenesisEngine
    from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
    swarm = SwarmCoordinator('lab')
    swarm.set_status('paused', now_ms=1000)
    engine = GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7, tick_count=1, population=2))
    link = SwarmEngineLink(swarm, quantity='signal', unit='arb', clock_ms=lambda:1000, request_budget=1).attach(engine)
    result = link.run_ticks()
    assert result.validate_consistency().passed
    row = swarm.snapshot(now_ms=1000)['state']['engine_boundaries'][0]
    assert row['command_ids'] == []


def test_v5_generic_sensor_api_auth_and_configuration(http_swarm,monkeypatch):
    from codontrace.swarm.sensors import fdc_sample
    monkeypatch.setenv('CODONTRACE_SWARM_NODE_TOKENS',json.dumps({'lab/a':'node-secret'}))
    row={'channel':0,'status':'Ok','raw24':0,'capacitancePf':3.125,'capdacCode':1,'capdacEnabled':True,'diagnosticFlags':0}
    args={'swarm_id':'lab','variant':'FDC1004','config_id':'fdc1','reading':row}
    status,_=call(http_swarm,'fdc_decode',args,token='node-secret');assert status==403
    status,r=call(http_swarm,'fdc_decode',args);assert status==200 and not r['result']['device_command_sent']
    channel,payload=fdc_sample(row,variant='FDC1004',config_id='fdc1')
    h=hello('lab','a');h['schema']='genesis_swarm_v2';h['payload']['channels']={'s':channel}
    status,_=call(http_swarm,'ingest',{'swarm_id':'lab','message':h},token='node-secret');assert status==200
    import time
    m=reading('lab','a',1,int(time.time()*1000),0.);m['schema']='genesis_swarm_v2';m['payload'].update(payload)
    status,_=call(http_swarm,'ingest',{'swarm_id':'lab','message':m},token='node-secret');assert status==200
    status,r=call(http_swarm,'snapshot',{'swarm_id':'lab'});assert status==200
    f=r['result']['state']['frames']['a/s'];assert f['value']==3.125e-12 and f['metadata']['raw24']==0
    status,_=call(http_swarm,'configure_channel',{'swarm_id':'lab','key':'a/s','changes':{'range':[0.,1.]}},token='node-secret');assert status==403
    status,r=call(http_swarm,'configure_channel',{'swarm_id':'lab','key':'a/s','changes':{'range':[0.,1.]}});assert status==200
    assert r['result']['host_configuration_applied'] and not r['result']['device_command_sent']
    status,_=call(http_swarm,'journal_recover',{'swarm_id':'lab'},token='node-secret');assert status==403
