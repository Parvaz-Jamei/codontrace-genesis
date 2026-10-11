from __future__ import annotations

import copy
import os

import pytest

from codontrace.swarm import SwarmCoordinator, SwarmEngineLink, service
from codontrace.swarm.experiments import hello, reading
from codontrace.swarm.mqtt import MqttSwarmBridge
from codontrace.swarm.protocol import canonical, decode
from codontrace.swarm.sensors import descriptor, fdc_sample, normalize


def config(kind='scalar', **extra):
    return {'value_type': kind, 'measurement_model': 'direct', 'feature_id': 'room',
            'source_unit': 'degC', 'config_id': 'source1', **extra}


def greeting(ch=None):
    m=hello('lab','a');m['schema']='genesis_swarm_v2'
    m['payload']['channels']={'s':ch or {'quantity':'temperature','unit':'degC','descriptor':config()}}
    return m


def observed(value,seq=1,**extras):
    m=reading('lab','a',seq,1000,value);m['schema']='genesis_swarm_v2'
    m['payload'].update(valid=True,status='ok',config_id='source1',**extras)
    return m


def test_v1_replay_unchanged_and_segment_rotation(tmp_path):
    path=tmp_path/'events.jsonl';s=SwarmCoordinator('lab',journal=path,journal_segment_bytes=1024)
    s.ingest(hello('lab','a'),now_ms=1000)
    for seq in range(1,12):s.ingest(reading('lab','a',seq,1000,seq),now_ms=1000)
    original=s.snapshot(now_ms=1000)
    assert original['journal_segment_count']>1
    clone=SwarmCoordinator('lab',journal=path,journal_segment_bytes=1024)
    assert clone.snapshot(now_ms=1000)==original
    # Simulate rotation completed but next active-file creation interrupted.
    target=path.with_name(path.name+f".part.{original['journal_segment_count']+1:08d}");path.rename(target)
    restarted=SwarmCoordinator('lab',journal=path)
    assert restarted.snapshot(now_ms=1000)['state']==original['state']
    restarted.ingest(reading('lab','a',12,1000,12),now_ms=1000)
    assert path.exists()


def test_journal_failure_requires_explicit_recovery_and_adopts_valid_record(tmp_path,monkeypatch):
    s=SwarmCoordinator('lab',journal=tmp_path/'events');real=os.fsync
    monkeypatch.setattr(os,'fsync',lambda fd: (_ for _ in ()).throw(OSError('injected disk fault')))
    with pytest.raises(OSError):s.ingest(hello('lab','a'),now_ms=1000)
    assert s.snapshot(now_ms=1000)['state']['nodes']=={}
    assert s.snapshot(now_ms=1000)['journal_health']=='recovery_required'
    monkeypatch.setattr(os,'fsync',real)
    with pytest.raises(OSError):s.set_status('paused',now_ms=1000)
    result=s.recover();assert result['state_changed'] and result['records_not_truncated']
    assert 'a' in s.snapshot(now_ms=1000)['state']['nodes']
    s.set_status('paused',now_ms=1000)


def test_recovery_never_hides_corrupt_tail(tmp_path):
    p=tmp_path/'events';s=SwarmCoordinator('lab',journal=p);s.ingest(hello('lab','a'),now_ms=1000)
    with p.open('a') as f:f.write('{incomplete')
    before=s.snapshot(now_ms=1000)['state']
    with pytest.raises(ValueError):s.recover()
    assert s.snapshot(now_ms=1000)['state']==before
    assert p.read_text().endswith('{incomplete')


def test_rotation_detects_tamper_in_archive(tmp_path):
    p=tmp_path/'events';s=SwarmCoordinator('lab',journal=p,journal_segment_bytes=1024)
    s.ingest(hello('lab','a'),now_ms=1000)
    for seq in range(1,8):s.ingest(reading('lab','a',seq,1000,seq),now_ms=1000)
    first=sorted(tmp_path.glob('events.part.*'))[0];first.write_text(first.read_text().replace('"now_ms":1000','"now_ms":1001',1))
    with pytest.raises(ValueError):SwarmCoordinator('lab',journal=p)


def test_optional_link_isolates_fault_required_link_stops_before_tick(monkeypatch):
    from codontrace.genesis.engine import GenesisEngine
    from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
    s=SwarmCoordinator('lab');s.ingest(hello('lab','a'),now_ms=1000)
    def fail(*args,**kwargs):raise OSError('journal unavailable')
    e=GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7,tick_count=2,population=2))
    link=SwarmEngineLink(s,quantity='signal',unit='arb',clock_ms=lambda:1000).attach(e)
    monkeypatch.setattr(s,'boundary',fail)
    result=link.run_ticks();assert len(result.ticks)==2 and len(link.errors)==2
    assert link.last_error['phase']=='generation_boundary'
    required_engine=GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7,tick_count=1,population=2))
    strict=SwarmEngineLink(s,quantity='signal',unit='arb',clock_ms=lambda:1000,required=True).attach(required_engine)
    with pytest.raises(RuntimeError):strict.run_ticks()
    assert required_engine.runner.population.generation==0


def test_mqtt_ids_unique_reconnect_stable():
    s=SwarmCoordinator('lab');a=MqttSwarmBridge(s);b=MqttSwarmBridge(s)
    assert a.client_id!=b.client_id
    assert MqttSwarmBridge(s,client_id='configured-client').client_id=='configured-client'


@pytest.mark.parametrize('kind,value,extra',[('scalar',12.,{}),('vector',[1.,2.,3.],{'axes':['x','y','z']}),('waveform',[1.,2.,3.],{'length':3}),('boolean',True,{}),('category','open',{})])
def test_typed_values_store_and_replay_without_scalar_coercion(tmp_path,kind,value,extra):
    s=SwarmCoordinator('lab',journal=tmp_path/'events')
    c={'quantity':'custom','unit':'degC','descriptor':config(kind,**extra)}
    s.ingest(greeting(c),now_ms=1000);s.ingest(observed(value),now_ms=1000)
    snap=s.snapshot(now_ms=1000);f=snap['state']['frames']['a/s']
    assert f['value']==value and f['source_value']==value
    assert SwarmCoordinator('lab',journal=tmp_path/'events').snapshot(now_ms=1000)==snap
    if kind!='scalar':
        assert s.fuse('custom','degC',now_ms=1000)['value'] is None
        with pytest.raises(ValueError):s.command('a','pipeline',{'channel':'s','pipeline':{'alpha':.2,'clip':1.,'event_threshold':1.}},now_ms=1000)


@pytest.mark.parametrize('kind,value,extra',[('scalar',True,{}),('vector',[1.,2.],{'axes':['x','y','z']}),('boolean',1,{}),('category',2.,{}),('waveform',[1.,float('nan')],{'length':2})])
def test_invalid_types_do_not_mutate_state(kind,value,extra):
    s=SwarmCoordinator('lab');s.ingest(greeting({'quantity':'custom','unit':'degC','descriptor':config(kind,**extra)}),now_ms=1000)
    before=s.snapshot(now_ms=1000)
    with pytest.raises(ValueError):s.ingest(observed(value),now_ms=1000)
    assert s.snapshot(now_ms=1000)==before


def test_affine_normalization_preserves_source_and_uncertainty():
    c={'quantity':'temperature','unit':'K','descriptor':config(normalization={'method':'affine','scale':1.,'offset':273.15,'output_unit':'K','evidence_id':'SI-conversion'})}
    s=SwarmCoordinator('lab');s.ingest(greeting(c),now_ms=1000)
    s.ingest(observed(0.,uncertainty={'standard':.2,'unit':'degC','evidence_id':'bench'}),now_ms=1000)
    f=s.snapshot(now_ms=1000)['state']['frames']['a/s']
    assert f['value']==273.15 and f['source_value']==0. and f['uncertainty']['unit']=='K'
    assert f['uncertainty']['standard']==.2


def test_invalid_sample_null_never_enters_fusion():
    s=SwarmCoordinator('lab');s.ingest(greeting(),now_ms=1000)
    m=observed(None);m['payload'].update(valid=False,status='Timeout')
    s.ingest(m,now_ms=1000)
    assert s.snapshot(now_ms=1000)['state']['frames']['a/s']['quality']==0
    assert s.fuse('temperature','degC',now_ms=1000)['value'] is None


def test_host_config_is_journalled_clear_old_frames_and_replay(tmp_path):
    p=tmp_path/'events';s=SwarmCoordinator('lab',journal=p);s.ingest(greeting(),now_ms=1000);s.ingest(observed(1.),now_ms=1000)
    n={'method':'affine','scale':2.,'offset':1.,'output_unit':'degC','evidence_id':'bench'}
    s._transaction('configure_channel',{'key':'a/s','changes':{'normalization':n,'range':[0,10]}},1000)
    assert not s.snapshot(now_ms=1000)['state']['frames']
    s.ingest(observed(2.,seq=2),now_ms=1000)
    assert s.fuse('temperature','degC',now_ms=1000)['value']==5
    assert SwarmCoordinator('lab',journal=p).snapshot(now_ms=1000)==s.snapshot(now_ms=1000)
    with pytest.raises(ValueError):s.ingest(observed(20.,seq=3),now_ms=1000)


def test_table_interpolates_no_extrapolation_or_fake_uncertainty():
    c={'unit':'mm','descriptor':config(normalization={'method':'table','knots':[[0.,0.],[1.,10.],[2.,15.]],'output_unit':'mm','evidence_id':'bench'})}
    p={'value':.5,'valid':True,'status':'ok','config_id':'source1'}
    assert normalize(p,c)['value']==5
    with pytest.raises(ValueError):normalize({**p,'value':-1.},c)
    with pytest.raises(ValueError):normalize({**p,'uncertainty':{'standard':.1,'unit':'degC','evidence_id':'bench'}},c)


def test_measurement_semantics_not_blindly_fused():
    s=SwarmCoordinator('lab');a=greeting();s.ingest(a,now_ms=1000);s.ingest(observed(1.),now_ms=1000)
    b=copy.deepcopy(a);b['node_id']='b';b['payload']['channels']['s']['descriptor']['feature_id']='other-room'
    s.ingest(b,now_ms=1000);m=observed(3.);m['node_id']='b';s.ingest(m,now_ms=1000)
    assert s.fuse('temperature','degC',now_ms=1000)['status']=='incompatible_measurement_semantics'


def test_advertised_rate_and_schema_guard():
    s=SwarmCoordinator('lab');s.ingest(greeting({'quantity':'temperature','unit':'degC','descriptor':config(rate_hz=[1.,10.])}),now_ms=1000)
    with pytest.raises(ValueError):s.command('a','set_rate',{'channel':'s','hz':100.},now_ms=1000)
    with pytest.raises(ValueError):s.ingest(reading('lab','a',1,1000,2.),now_ms=1000)


def test_fdc_direct_no_double_capdac():
    row={'channel':0,'status':'Ok','raw24':0,'capacitancePf':3.125,'capdacCode':1,'capdacEnabled':True,'diagnosticFlags':0}
    c,p=fdc_sample(row,variant='FDC1004',config_id='source1')
    assert normalize(p,c)['value']==3.125e-12
    assert p['metadata']['raw24']==0 and p['metadata']['capdacCode']==1
    c,p=fdc_sample({**row,'status':'Timeout','capacitancePf':0.},variant='FDC1004',config_id='source1')
    assert not p['valid'] and p['value'] is None


def test_fdc_frequency_preserves_clock_and_rejects_unsupported_211():
    row={'channel':0,'status':'Ok','rawCode':1,'frequencyHz':1e6,'frefHz':40e6,'finSelMultiplier':1,'frefDivider':1,'dataReady':True}
    c,p=fdc_sample(row,variant='FDC2214',config_id='source1')
    assert c['quantity']=='frequency' and p['metadata']['frefHz']==40e6
    with pytest.raises(ValueError):fdc_sample(row,variant='FDC2114',config_id='source1')
    with pytest.raises(ValueError):fdc_sample({**row,'frefHz':0},variant='FDC2214',config_id='source1')


def test_service_actions_connected(monkeypatch,tmp_path):
    monkeypatch.setenv('CODONTRACE_SWARM_DIR',str(tmp_path));service._SWARMS.clear()
    service.invoke('ingest',{'swarm_id':'lab','message':greeting()},now_ms=1000)
    assert service.invoke('configure_channel',{'swarm_id':'lab','key':'a/s','changes':{'range':[-10,10]}},now_ms=1000)['result']['host_configuration_applied']
    assert service.invoke('journal_recover',{'swarm_id':'lab'},now_ms=1000)['result']['recovered']
    service._SWARMS.clear()


def test_descriptor_rejects_units_models_and_duplicate_json():
    with pytest.raises(ValueError):descriptor(config(measurement_model='derived'))
    with pytest.raises(ValueError):decode('{"schema":1,"schema":2}')
    s=SwarmCoordinator('lab');g=greeting();g['payload']['channels']['s']['unit']='K'
    with pytest.raises(ValueError):s.ingest(g,now_ms=1000)
    assert canonical(s.snapshot(now_ms=1000))


def test_reboot_clears_host_config_and_reference_unit_is_required():
    s=SwarmCoordinator('lab');s.ingest(greeting(),now_ms=1000)
    s._transaction('configure_channel',{'key':'a/s','changes':{'range':[0,1]}},1000)
    h=greeting();h['boot_id']='boot2';s.ingest(h,now_ms=1000)
    assert not s.snapshot(now_ms=1000)['state']['channel_configs']
    m=observed(2.,reference=2.,reference_id='bench');m['boot_id']='boot2'
    with pytest.raises(ValueError):s.ingest(m,now_ms=1000)
    m['payload']['reference_unit']='degC';s.ingest(m,now_ms=1000)


def test_relative_storage_configuration_is_rejected(monkeypatch):
    monkeypatch.setenv('CODONTRACE_SWARM_DIR','relative-data');service._SWARMS.clear()
    with pytest.raises(ValueError):service.coordinator('relative-test')


def test_recorder_reuses_committed_snapshot_without_changing_frames(tmp_path,monkeypatch):
    from codontrace.genesis.engine import GenesisEngine
    from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
    from codontrace.visualization.recorder import SimulationRecorder
    e=GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=8,tick_count=4,population=4))
    original=e.snapshot
    def forbidden():
        import sys
        if sys._getframe(1).f_code.co_name == 'capture':
            raise AssertionError('duplicate engine snapshot in recorder')
        return original()
    monkeypatch.setattr(e,'snapshot',forbidden)
    recorder=SimulationRecorder(tmp_path/'new').attach(e);result=e.run_ticks()
    assert len(result.ticks)==4 and recorder.finalize()['generation']==4
