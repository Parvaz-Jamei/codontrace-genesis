from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from codontrace.rng import RNGManager
from codontrace.swarm import Pipeline, PolicyArchive, SwarmCoordinator, transfer_decision
from codontrace.swarm.coevolution import coevolve
from codontrace.swarm.experiments import hello, packet, reading, run_seed
from codontrace.swarm.mqtt import MqttSwarmBridge
from codontrace.swarm.protocol import decode
from codontrace.swarm.research import SensorTwin, perturb, processing_contrast


def make():
    s = SwarmCoordinator('lab')
    s.ingest(hello('lab', 'a'), now_ms=1000)
    return s


@pytest.mark.parametrize('value', [float('nan'), float('inf'), True, '3', None, {}, []])
def test_invalid_values_rejected_without_mutation(value):
    s = make(); before = s.snapshot(now_ms=1000)
    m = reading('lab', 'a', 1, 1000, value)
    with pytest.raises((ValueError, TypeError)):
        s.ingest(m, now_ms=1000)
    assert s.snapshot(now_ms=1000) == before


@pytest.mark.parametrize('key,value', [('node_id','../escape'), ('swarm_id','other'), ('boot_id','old'), ('seq',True)])
def test_identity_isolation(key, value):
    s=make(); m=reading('lab','a',1,1000,3); m[key]=value
    with pytest.raises(ValueError): s.ingest(m,now_ms=1000)


def test_unknown_keys_and_duplicate_json():
    m=hello('lab','a');m['extra']=1
    with pytest.raises(ValueError): decode(m)
    with pytest.raises(ValueError): decode('{"schema":1,"schema":2}')


def test_wifi_and_capability_validation():
    m=hello('lab','a');m['payload']['wifi']=False
    with pytest.raises(ValueError):decode(m)
    m=hello('lab','a');m['payload']['operations']=['exec']
    with pytest.raises(ValueError):decode(m)


def test_duplicate_reorder_and_reboot():
    s=make();m=reading('lab','a',1,1000,3)
    assert s.ingest(m,now_ms=1000)['accepted']
    assert not s.ingest(m,now_ms=1000)['accepted']
    s.calibrate('a/s',3,'ref',now_ms=1000)
    h=hello('lab','a');h['boot_id']='boot2';s.ingest(h,now_ms=1001)
    assert s.snapshot(now_ms=1001)['state']['frames']=={}
    assert s.snapshot(now_ms=1001)['state']['trust']=={}
    with pytest.raises(ValueError):s.ingest(m,now_ms=1001)


@pytest.mark.parametrize('sample', [0,20000])
def test_stale_and_future_samples(sample):
    s=make()
    with pytest.raises(ValueError):s.ingest(reading('lab','a',1,sample,3),now_ms=12000)


def test_fusion_units_alignment_quality_and_empty():
    s=make();s.ingest(reading('lab','a',1,1000,2),now_ms=1000)
    s.ingest(hello('lab','b'),now_ms=2500);s.ingest(reading('lab','b',1,2500,4),now_ms=2500)
    assert s.fuse('signal','arb',now_ms=2500)['count']==1
    assert s.fuse('signal','C',now_ms=2500)['value'] is None
    assert s.fuse('signal','arb',now_ms=20000)['value'] is None
    m=reading('lab','b',2,2501,100);m['payload']['quality']=0;s.ingest(m,now_ms=2501)
    assert s.fuse('signal','arb',now_ms=2501)['value']==2


def test_processing_version_invalidates_trust():
    s=make();s.ingest(reading('lab','a',1,1000,2),now_ms=1000);s.calibrate('a/s',2,'ref',now_ms=1000)
    m=reading('lab','a',2,1001,2);m['payload']['processing_version']='new';s.ingest(m,now_ms=1001)
    assert not s.snapshot(now_ms=1001)['state']['trust']


def test_commands_ack_identity_expiry_and_pause():
    s=make();c=s.command('a','sample',{'channel':'s'},now_ms=1000,timeout_ms=5)
    assert c['status']=='pending'
    s.ingest(packet('lab','a',1,'reply',{'command_id':c['command_id'],'ok':True}),now_ms=1001)
    assert s.snapshot(now_ms=1001)['state']['commands'][c['command_id']]['status']=='acknowledged'
    c=s.command('a','sample',{'channel':'s'},now_ms=1001,timeout_ms=5)
    assert s.snapshot(now_ms=1006)['state']['commands'][c['command_id']]['status']=='expired'
    with pytest.raises(ValueError):s.ingest(packet('lab','a',2,'reply',{'command_id':c['command_id'],'ok':True}),now_ms=1006)
    s.set_status('paused',now_ms=1007)
    with pytest.raises(ValueError):s.ingest(reading('lab','a',2,1007,2),now_ms=1007)
    with pytest.raises(ValueError):s.command('a','sample',{'channel':'s'},now_ms=1007)
    s.set_status('running',now_ms=1008)
    assert s.ingest(reading('lab','a',2,1008,2),now_ms=1008)['accepted']


def test_unsupported_operation_and_arbitrary_code_rejected():
    s=make()
    with pytest.raises(ValueError):s.command('a','exec',{'code':'print(1)'},now_ms=1000)
    with pytest.raises(ValueError):s.command('a','pipeline',{'channel':'s','pipeline':{'code':'print(1)'}},now_ms=1000)


def test_journal_recovery_tamper_and_truncation(tmp_path):
    path=tmp_path/'journal';s=SwarmCoordinator('lab',journal=path)
    s.ingest(hello('lab','a'),now_ms=1000);s.ingest(reading('lab','a',1,1000,3),now_ms=1000)
    clone=SwarmCoordinator('lab',journal=path)
    assert clone.snapshot(now_ms=1000)==s.snapshot(now_ms=1000)
    saved=path.read_text();row=json.loads(saved.splitlines()[0]);row['now_ms']=999
    path.write_text(json.dumps(row)+'\n')
    with pytest.raises(ValueError):SwarmCoordinator('lab',journal=path)
    path.write_text(saved[:-1])
    with pytest.raises(ValueError):SwarmCoordinator('lab',journal=path)


def test_snapshot_and_message_do_not_alias():
    s=make();m=reading('lab','a',1,1000,3);m['payload']['raw']=[3,4,5]
    s.ingest(m,now_ms=1000);m['payload']['raw'][0]=99
    x=s.snapshot(now_ms=1000);x['state']['frames']['a/s']['raw'][0]=88
    assert s.snapshot(now_ms=1000)['state']['frames']['a/s']['raw'][0]==3


def test_swarm_does_not_identify_shared_fault_from_consensus():
    s=make();s.ingest(reading('lab','a',1,1000,10),now_ms=1000)
    assert s.diagnose('signal','arb',now_ms=1000)['causal_proof'] is False
    assert s.diagnose('signal','arb',now_ms=1000,reference=0)['suspects']==['a/s']


def test_plan_budget_and_reallocation():
    s=make();s.ingest(hello('lab','b'),now_ms=1000)
    commands=s.plan('signal','arb',now_ms=1000,budget=1)
    assert len(commands)==1
    assert len(s.plan('signal','arb',now_ms=1000,budget=1))==1
    assert not s.plan('signal','arb',now_ms=1000,budget=2)
    s.ingest(packet('lab','b',1,'heartbeat',{}),now_ms=12000)
    assert [c['node_id'] for c in s.plan('signal','arb',now_ms=12000,budget=2)]==['b']


def test_concurrent_node_ingest():
    s=SwarmCoordinator('lab')
    def send(i):return s.ingest(hello('lab','n'+str(i)),now_ms=1000)
    with ThreadPoolExecutor(max_workers=8) as ex:
        assert all(v['accepted'] for v in ex.map(send,range(32)))
    assert len(s.snapshot(now_ms=1000)['state']['nodes'])==32


def test_mqtt_scope_and_retained():
    bridge=MqttSwarmBridge(SwarmCoordinator('lab'));raw=json.dumps(hello('lab','a')).encode()
    assert bridge.handle('genesis/swarm/lab/a/up',raw,now_ms=1000)['accepted']
    with pytest.raises(ValueError):bridge.handle('genesis/swarm/lab/b/up',raw,now_ms=1000)
    with pytest.raises(ValueError):bridge.handle('genesis/swarm/lab/a/up',raw,now_ms=1000,retained=True)


def test_pipeline_negative_transfer_and_raw_events():
    x=[0,10,0,10,0];r=list(x)
    result=transfer_decision(Pipeline(alpha=.01),Pipeline(),x,r)
    assert result['accepted'] is False
    assert Pipeline(alpha=.01).process(x)[1]==[1,2,3,4]


def test_policy_search_replays_and_handles_no_effect():
    a=PolicyArchive(7);b=PolicyArchive(7);x=[0.,1.,0.,1.];r=x.copy()
    assert a.fit(x,r)==b.fit(x,r)==Pipeline()
    assert a.rng.snapshot()==b.rng.snapshot()
    assert not transfer_decision(Pipeline(),Pipeline(),x,r)['accepted']


def test_twin_identifiability_and_processing_contrast():
    with pytest.raises(ValueError):SensorTwin.fit([1,1,1],[2,3,4])
    twin=SensorTwin.fit([0,1,2],[3,5,7]);assert twin.predict(4)==11
    assert processing_contrast({'raw':[1,1,1],'value':5},reference=1)['status']=='processing_disagreement_candidate'


def test_disturbance_limits_and_coevolution_replay():
    with pytest.raises(ValueError):perturb([1],rng=RNGManager(1),dropout=2)
    a=coevolve([0,1]*8,seed=3,rounds=2);b=coevolve([0,1]*8,seed=3,rounds=2)
    assert a==b
    assert len(a['history'])==2
    for row in a['history']:
        n=row['disturbance'];assert n['amplitude']+abs(n['bias'])<=1.00000001


def test_all_ten_probes_have_measured_finite_outputs():
    a=run_seed(7,samples=32);b=run_seed(7,samples=32)
    assert a==b and len(a)==10
    assert all(row['synthetic'] and row['claim']=='engineering_probe_only' for row in a)
    assert a[6]['estimate'] is None
    assert a[8]['heldout_mse'] < 1e-20
    assert a[9]['training']['history']


def test_journal_write_error_does_not_commit_memory(tmp_path,monkeypatch):
    s=SwarmCoordinator('lab',journal=tmp_path/'journal')
    before=s.snapshot(now_ms=1000)
    monkeypatch.setattr('codontrace.swarm.runtime.os.fsync',lambda fd: (_ for _ in ()).throw(OSError('disk failure')))
    with pytest.raises(OSError):s.ingest(hello('lab','a'),now_ms=1000)
    assert s.snapshot(now_ms=1000)['state']==before['state']
    assert s.snapshot(now_ms=1000)['journal_digest']==before['journal_digest']
    assert s.snapshot(now_ms=1000)['journal_health']=='recovery_required'
    with pytest.raises(OSError):s.ingest(hello('lab','b'),now_ms=1000)


def test_reply_wrong_node_and_reboot_cancel():
    s=make();s.ingest(hello('lab','b'),now_ms=1000)
    c=s.command('a','sample',{'channel':'s'},now_ms=1000)
    with pytest.raises(ValueError):s.ingest(packet('lab','b',1,'reply',{'command_id':c['command_id'],'ok':True}),now_ms=1000)
    h=hello('lab','a');h['boot_id']='boot2';s.ingest(h,now_ms=1000)
    assert s.snapshot(now_ms=1000)['state']['commands'][c['command_id']]['status']=='boot_replaced'


def test_mqtt_sdk_builds_v5_tls_and_dispatch(monkeypatch):
    import time
    from types import SimpleNamespace

    mqtt = pytest.importorskip('paho.mqtt.client')
    calls=[]
    class Client:
        def __init__(self,*args,**kwargs):calls.append(('client',kwargs))
        def reconnect_delay_set(self,**kwargs):calls.append(('backoff',kwargs))
        def username_pw_set(self,*args):pass
        def tls_set(self,**kwargs):calls.append(('tls',kwargs))
        def connect(self,*args,**kwargs):pass
        def subscribe(self,*args,**kwargs):calls.append(('subscribe',args))
        def publish(self,*args,**kwargs):calls.append(('publish',args,kwargs));return SimpleNamespace(rc=0)
    monkeypatch.setattr(mqtt,'Client',Client)
    now=int(time.time()*1000);s=SwarmCoordinator('lab');s.ingest(hello('lab','a'),now_ms=now)
    bridge=MqttSwarmBridge(s);client=bridge.connect('broker.invalid',username='u',password='p')
    client.on_connect(client,None,None,SimpleNamespace(is_failure=False),None)
    s.command('a','sample',{'channel':'s'},now_ms=now)
    assert bridge.drain(client,now_ms=now)==1
    assert bridge.drain(client,now_ms=now)==0
    assert calls[0][1]['protocol']==mqtt.MQTTv5
    assert any(c[0]=='tls' for c in calls)
    publish=next(c for c in calls if c[0]=='publish');assert publish[2]=={'qos':1,'retain':False}


@pytest.mark.parametrize('n',[16,32,64])
def test_all_probe_sizes_are_deterministic(n):
    assert run_seed(2,samples=n)==run_seed(2,samples=n)


def test_stale_cross_process_writer_cannot_fork_journal(tmp_path):
    path = tmp_path / 'events.jsonl'
    first = SwarmCoordinator('lab', journal=path)
    second = SwarmCoordinator('lab', journal=path)
    first.ingest(hello('lab', 'a'), now_ms=1000)
    before = path.read_bytes()
    with pytest.raises(OSError, match='changed externally'):
        second.ingest(hello('lab', 'b'), now_ms=1000)
    assert path.read_bytes() == before
    recovered = SwarmCoordinator('lab', journal=path)
    recovered.ingest(hello('lab', 'b'), now_ms=1001)
    assert len(recovered.snapshot(now_ms=1001)['state']['nodes']) == 2


def test_information_selection_requires_feasible_validated_payload():
    from codontrace.swarm.research import information_level
    options = {'raw': {'payload': [1.0]*20, 'validation_mse': 0, 'validation_id': 'day2'},
               'result': {'payload': 1.0, 'validation_mse': 2, 'validation_id': 'day2'}}
    assert information_level(options, byte_budget=100, maximum_mse=0)['selected'] == 'raw'
    assert information_level(options, byte_budget=10, maximum_mse=0)['selected'] is None
    assert information_level(options, byte_budget=10, maximum_mse=3)['selected'] == 'result'


def test_enormous_numeric_input_is_validation_error_not_overflow():
    from codontrace.swarm.protocol import number
    with pytest.raises(ValueError):number(10**1000)


def test_common_mode_fault_requires_independent_reference():
    from codontrace.swarm.policies import diagnose
    shifted={'a':5.,'b':5.,'c':5.}
    assert diagnose(shifted)['suspects']==[]
    assert diagnose(shifted,reference=0.)['suspects']==['a','b','c']
    assert not diagnose(shifted,reference=0.)['causal_proof']


def test_repeated_training_preserves_bounded_archive():
    from codontrace.swarm.policies import PolicyArchive
    archive=PolicyArchive(7)
    archive.entries={f'old-{i}':{'training_mse':1.} for i in range(4096)}
    archive.fit([0.,1.,0.],[0.,1.,0.],rounds=1)
    assert len(archive.entries)<=4096
