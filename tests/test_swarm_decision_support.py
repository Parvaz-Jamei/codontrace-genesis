from __future__ import annotations

import json

import pytest

from codontrace.swarm.decision_support import capsule_shadow, residual_interval, schedule_measurements
from codontrace.swarm.experiments import hello, reading
from codontrace.swarm.policies import Pipeline
from codontrace.swarm.runtime import SwarmCoordinator
from codontrace.swarm.service import invoke


def candidate(key='a',group='target',age=1000,cost=100,q=.01):
    return dict(key=key,group=group,sample_ms=1000-age,noise_variance=.1,process_variance_per_ms=q,
                latency_ms=10,success_probability=1.,payload_bytes=cost,evidence_id='calibration-1')


def test_conformal_order_statistic_and_small_data_are_not_clamped():
    f=residual_interval([float(i) for i in range(10)],[0.]*10,estimate=5.,training_id='train',calibration_id='cal',model_id='model',alpha=.1)
    assert f['quantile_rank']==10 and f['radius']==9 and f['lower']==-4 and f['upper']==14
    g=residual_interval([1.,2.,3.],[0.]*3,estimate=5.,training_id='train',calibration_id='cal',model_id='model',alpha=.01)
    assert g['radius'] is None and g['lower'] is None and not g['coverage_verified']
    with pytest.raises(ValueError):residual_interval([1.]*10,[0.]*10,estimate=0,training_id='same',calibration_id='same',model_id='m')


@pytest.mark.parametrize('bad',[True,float('nan'),float('inf'),10**500])
def test_bad_calibration_data_is_rejected(bad):
    with pytest.raises(ValueError):residual_interval([bad,0,0],[0,0,0],estimate=0,training_id='train',calibration_id='cal',model_id='model')


def test_budget_selection_discounts_redundancy_and_is_order_independent():
    rows=[candidate('a','same'),candidate('b','same'),candidate('c','other')]
    a=schedule_measurements(rows,now_ms=1000,byte_budget=200)
    b=schedule_measurements(rows[::-1],now_ms=1000,byte_budget=200)
    assert [r['key'] for r in a['selected']]==['a','c']
    assert a==b or a['selected']==b['selected']
    assert a['estimated_payload_bytes']==200 and not a['command_sent']
    assert schedule_measurements(rows,now_ms=1000,byte_budget=99)['selected']==[]


def test_latency_and_stationary_signal_can_make_refresh_useless():
    a=candidate(age=5);b=candidate('b',q=0)
    result=schedule_measurements([a,b],now_ms=1000,byte_budget=1000)
    assert result['selected']==[]
    assert result['expected_group_gain_proxy']==0


@pytest.mark.parametrize('change',[{'payload_bytes':0},{'sample_ms':1001},{'success_probability':1.1},{'process_variance_per_ms':-1}])
def test_invalid_schedule_models_are_rejected(change):
    a=candidate();a.update(change)
    with pytest.raises(ValueError):schedule_measurements([a],now_ms=1000,byte_budget=1000)


def test_shadow_comparison_accepts_good_rejects_bad_and_advises_rollback():
    baseline=Pipeline();good=Pipeline(alpha=.01);bad=Pipeline(alpha=.01)
    values=[0.,1.,-1.,1.,-1.,1.,-1.,0.];refs=[0.]*8
    qualified=capsule_shadow(good,baseline,values,refs,training_id='train',evaluation_id='holdout')
    assert qualified['qualification_passed'] and qualified['gain_mse']>0
    exact=[0.,1.,2.,3.,4.,5.]
    rejected=capsule_shadow(bad,baseline,exact,exact,training_id='train',evaluation_id='holdout2')
    assert not rejected['qualification_passed'] and rejected['recommended_pipeline']['alpha']==1.
    monitor=capsule_shadow(bad,baseline,exact,exact,training_id='train',evaluation_id='post',phase='monitoring')
    assert monitor['rollback_advised'] and not monitor['command_sent'] and not monitor['statistical_safety_guarantee']
    with pytest.raises(ValueError):capsule_shadow(good,baseline,values,refs,training_id='same',evaluation_id='same')


def test_snapshot_scheduler_uses_real_node_times_unit_scope_and_pending_commands():
    s=SwarmCoordinator('lab');s.ingest(hello('lab','a'),now_ms=1000);s.ingest(reading('lab','a',1,1000,2.),now_ms=1000)
    model=candidate();model.pop('key');model.pop('sample_ms')
    before=s.snapshot(now_ms=2000)
    result=s.freshness_plan({'a/s':model},'signal','arb',now_ms=2000,byte_budget=1000)
    assert result['selected'][0]['sample_ms']==1000 and result['selected'][0]['key']=='a/s'
    assert s.snapshot(now_ms=2000)==before
    assert not s.freshness_plan({'a/s':model},'signal','C',now_ms=2000,byte_budget=1000)['selected']
    s.command('a','sample',{'channel':'s'},now_ms=2000)
    assert not s.freshness_plan({'a/s':model},'signal','arb',now_ms=2000,byte_budget=1000)['selected']
    with pytest.raises(ValueError):s.freshness_plan({'other/s':model},'signal','arb',now_ms=2000,byte_budget=1000)


def test_service_actions_are_connected_and_json_finite(tmp_path,monkeypatch):
    from codontrace.swarm import service
    monkeypatch.setenv('CODONTRACE_SWARM_DIR',str(tmp_path));service._SWARMS.clear()
    result=invoke('uncertainty_interval',dict(swarm_id='lab',predictions=[0.]*10,references=[1.]*10,
                  estimate=1.,training_id='train',calibration_id='cal',model_id='m'),now_ms=1000)
    assert result['result']['radius']==1.
    schedule=invoke('freshness_schedule',dict(swarm_id='lab',candidates=[candidate()],byte_budget=100),now_ms=1000)
    assert schedule['result']['selected'][0]['key']=='a'
    shadow=invoke('capsule_shadow',dict(swarm_id='lab',candidate={'alpha':.1},baseline={},values=[0.,1.,-1.],
                  references=[0.]*3,training_id='train',evaluation_id='test'),now_ms=1000)
    json.dumps([result,schedule,shadow],allow_nan=False)
    service._SWARMS.clear()


def test_readonly_llm_report_keeps_seed_scope_and_synthetic_label(tmp_path,monkeypatch):
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    from codontrace.console.science_tools import invoke_tool
    spec=spec_from_file_location('probe',Path(__file__).parents[1]/'examples/swarm_decision_support.py')
    module=module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path));root=tmp_path/'run';root.mkdir()
    (root/'swarm_decision_support.json').write_text(json.dumps({'schema':'genesis_swarm_decision_report_v1','synthetic':True,'reports':[module.run_probe(7),module.run_probe(8)]}))
    result=invoke_tool('swarm_decision_report',{'seed':8},selected_run_id='run')
    assert result['ok'] and len(result['artifacts'][0]['rows'])==1
    assert result['artifacts'][0]['rows'][0][:2]==[8,True]
    assert result['artifacts'][0]['provenance']['synthetic']
    assert not invoke_tool('swarm_decision_report',{'run_id':'other'},selected_run_id='run')['ok']
    (root/'swarm_decision_support.json').unlink();(root/'swarm_decision_support.json').symlink_to(tmp_path/'outside')
    assert not invoke_tool('swarm_decision_report',{},selected_run_id='run')['ok']


def test_live_planner_excludes_future_sample_without_blocking_other_nodes():
    s=SwarmCoordinator('lab')
    for node in ('a','b'):
        s.ingest(hello('lab',node),now_ms=1000)
        s.ingest(reading('lab',node,1,1100 if node=='a' else 900,2.),now_ms=1000)
    model=candidate();model.pop('key');model.pop('sample_ms')
    report=s.freshness_plan({'a/s':model,'b/s':model},'signal','arb',now_ms=1000,byte_budget=1000)
    assert report['excluded_channels']==['a/s']
    assert [r['key'] for r in report['selected']]==['b/s']


@pytest.mark.parametrize('report',[[],{'schema':'wrong','synthetic':True,'reports':[]},
                                  {'schema':'genesis_swarm_decision_report_v1','synthetic':True,'reports':[[]]}])
def test_malformed_saved_report_returns_error_not_uncaught_exception(tmp_path,monkeypatch,report):
    from codontrace.console.science_tools import invoke_tool
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path));root=tmp_path/'run';root.mkdir()
    (root/'swarm_decision_support.json').write_text(json.dumps(report))
    assert not invoke_tool('swarm_decision_report',{},selected_run_id='run')['ok']
