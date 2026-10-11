from __future__ import annotations

import json
from urllib.request import Request, urlopen

import pytest

from codontrace.console.simulation import read_simulation
from codontrace.visualization import SimulationRecorder
from codontrace.visualization.__main__ import export
from codontrace.visualization.frames import frame_from_population


def engine(seed=7, ticks=4):
    from codontrace.genesis.engine import GenesisEngine
    from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
    return GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=seed, tick_count=ticks, population=4))


def test_real_engine_frames_preserve_outcomes_and_seed_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path))
    root=tmp_path/'run_atlas';plain=engine();observed=engine()
    rec=SimulationRecorder(root).attach(observed)
    result=observed.run_ticks();control=plain.run_ticks()
    assert result.validate_consistency().passed
    assert [x.digest() for x in result.ticks]==[x.digest() for x in control.ticks]
    assert observed.runner.population.digest()==plain.runner.population.digest()
    second=engine(seed=8,ticks=2);SimulationRecorder(root).attach(second);second.run_ticks()
    page=read_simulation('run_atlas',seed=7,cursor=0,limit=10)
    assert page['seeds']==[7,8] and page['total_frames']==5
    assert page['frames'][0]['metrics']['births'] is None
    for f,t in zip(page['frames'][1:],result.ticks,strict=True):
        assert f['metrics']['population']==t.generation_result.after_count
        assert f['metrics']['births']==t.generation_result.births
        assert f['metrics']['deaths']==t.generation_result.deaths
        assert f['seed']==7
    assert read_simulation('run_atlas',seed=8)['total_frames']==3
    with pytest.raises(ValueError):rec.attach(second)
    with pytest.raises(FileExistsError):SimulationRecorder(root).attach(engine())


def test_every_interval_counts_are_aggregated(tmp_path, monkeypatch):
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path))
    e=engine();SimulationRecorder(tmp_path/'run',every=2).attach(e);r=e.run_ticks()
    frames=read_simulation('run')['frames'];assert [f['generation'] for f in frames]==[0,2,4]
    assert frames[1]['metrics']['births']==sum(x.generation_result.births for x in r.ticks[:2])
    assert frames[1]['metrics']['deaths']==sum(x.generation_result.deaths for x in r.ticks[:2])


def test_absent_positions_not_invented_and_disappearance_not_death(tmp_path,monkeypatch):
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path));(tmp_path/'run').mkdir()
    assert not read_simulation('run')['available']
    world={'width':4,'height':4};old={'tick':0,'agents':[{'id':'A','position':[1,1]}]}
    frame=frame_from_population({'generation':1,'tick':1,'agents':[]},world,run_id='run',seed=7,previous=old)
    assert frame['deaths']==[] and frame['metrics']['deaths'] is None
    assert not frame['lineage_recorded']


def test_explicit_two_parent_birth_and_death_positions():
    old={'tick':0,'agents':[{'id':'A','position':[1,1]},{'id':'B','position':[2,1]}]}
    pop={'generation':1,'tick':1,'agents':[{'organism_id':'C','position':[1,2],'runtime_atp':2}],
         'lineage':[{'organism_id':'C','parent_id':'A','second_parent_id':'B','birth_tick':1,'death_tick':None},
                    {'organism_id':'A','parent_id':None,'birth_tick':0,'death_tick':1}]}
    f=frame_from_population(pop,{'width':4,'height':4},run_id='run',seed=7,previous=old,summary={'births':1,'deaths':1,'after_count':1})
    assert f['born_ids']==['C'];assert f['deaths'][0]['position']==[1,1]
    assert [link['kind'] for link in f['links']]==['parentage','parentage','two_parent_birth']
    assert f['metrics']['two_parent_births']==1


@pytest.mark.parametrize('seed,cursor,limit',[(True,0,8),(1,-1,8),(1,0,0),(1,0,33)])
def test_paging_validation(tmp_path,monkeypatch,seed,cursor,limit):
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path))
    with pytest.raises(ValueError):read_simulation('run',seed=seed,cursor=cursor,limit=limit)


def test_path_escape_and_corruption_rejected(tmp_path,monkeypatch):
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path))
    outside=tmp_path/'outside';outside.mkdir();root=tmp_path/'run';root.mkdir()
    (root/'simulation').symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError):read_simulation('run')
    with pytest.raises(FileNotFoundError):read_simulation('../outside')
    (root/'simulation').unlink();(root/'simulation/seed_7').mkdir(parents=True)
    path=root/'simulation/seed_7/frame_000000000000.json';path.write_text('{bad')
    with pytest.raises(ValueError):read_simulation('run',seed=7)


def test_export_actual_core_result_no_summary_reconstruction(tmp_path,monkeypatch):
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path));r=engine(ticks=2).run_ticks()
    source=tmp_path/'core.json';source.write_text(json.dumps(r._core_payload()))
    assert export(source,tmp_path/'run_export')==2
    assert read_simulation('run_export')['total_frames']==2
    with pytest.raises(FileExistsError):export(source,tmp_path/'run_export')


def test_real_http_simulation_auth_and_paused_archives(tmp_path,monkeypatch):
    import threading

    from codontrace.console.server import make_server
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path));monkeypatch.setenv('CODONTRACE_API_TOKEN','test-secret')
    e=engine(ticks=1);SimulationRecorder(tmp_path/'run').attach(e);e.run_ticks()
    server=make_server('127.0.0.1',0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        url=f'http://127.0.0.1:{server.server_address[1]}/api/runs/run/simulation?seed=7'
        from urllib.error import HTTPError
        with pytest.raises(HTTPError) as err:urlopen(url)
        assert err.value.code==403
        with urlopen(Request(url,headers={'Authorization':'Bearer test-secret'})) as response:
            data=json.load(response);assert data['total_frames']==2
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)


def test_recorder_finalizes_tail_and_return_value_is_detached(tmp_path,monkeypatch):
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path))
    e=engine(ticks=3);rec=SimulationRecorder(tmp_path/'run',every=2).attach(e);result=e.run_ticks()
    tail=rec.finalize();assert tail['generation']==3
    assert tail['metrics']['births']==result.ticks[-1].generation_result.births
    tail['agents'].clear()
    assert len(rec.finalize()['agents'])==result.ticks[-1].generation_result.after_count
    assert read_simulation('run')['total_frames']==3


def test_mixed_run_is_rejected_across_pages(tmp_path,monkeypatch):
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path))
    e=engine(ticks=2);SimulationRecorder(tmp_path/'run').attach(e);e.run_ticks()
    path=tmp_path/'run/simulation/seed_7/frame_000000000002.json'
    row=json.loads(path.read_text());row['run_id']='another-engine';path.write_text(json.dumps(row))
    with pytest.raises(ValueError,match='mixed engine'):
        read_simulation('run',seed=7,cursor=2,limit=1)


def test_failed_attachment_can_be_retried_without_adding_observer(tmp_path):
    e=engine();root=tmp_path/'run'
    SimulationRecorder(root).attach(e)
    recorder=SimulationRecorder(root)
    before=len(e.generation_boundary_observers)
    with pytest.raises(FileExistsError):recorder.attach(e)
    assert recorder.engine is None and len(e.generation_boundary_observers)==before
    recorder.directory=tmp_path/'retry';recorder.attach(e)
    assert len(e.generation_boundary_observers)==before+1


def test_initial_snapshot_has_no_historical_birth_links_and_rejects_time_reversal():
    pop={'generation':2,'tick':2,'agents':[{'id':'A','position':[1,1]},{'id':'B','position':[2,1]}],
         'lineage':[{'organism_id':'B','parent_id':'A','birth_tick':1,'death_tick':None}]}
    f=frame_from_population(pop,{'width':4,'height':4},run_id='run',seed=7)
    assert f['links']==[] and f['born_ids']==[] and f['metrics']['two_parent_births'] is None
    with pytest.raises(ValueError,match='increase'):
        frame_from_population(pop,{'width':4,'height':4},run_id='run',seed=7,previous=f)
    pop['lineage']={}
    with pytest.raises(ValueError,match='lineage'):
        frame_from_population(pop,{'width':4,'height':4},run_id='run',seed=7)


@pytest.mark.parametrize('corruption',['duplicate_birth','living_death','fractional_position','bad_flag','excess_birth_count'])
def test_frame_event_semantics_are_validated(tmp_path,monkeypatch,corruption):
    from codontrace.console.simulation import validate_frame
    e=engine(ticks=1);rec=SimulationRecorder(tmp_path/'run').attach(e)
    f=rec.previous;assert f is not None
    f=json.loads(json.dumps(f));aid=f['agents'][0]['id']
    if corruption=='duplicate_birth':f['born_ids']=[aid,aid]
    elif corruption=='living_death':f['deaths']=[{'id':aid,'position':[0,0]}]
    elif corruption=='fractional_position':f['agents'][0]['position']=[0.5,0]
    elif corruption=='bad_flag':f['lineage_recorded']='true'
    else:f['metrics'].update(births=0,two_parent_births=1)
    with pytest.raises(ValueError):validate_frame(f,7)


def test_noncanonical_seed_and_bad_anchor_are_rejected_even_on_later_page(tmp_path,monkeypatch):
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path))
    e=engine(ticks=1);SimulationRecorder(tmp_path/'run').attach(e);e.run_ticks()
    directory=tmp_path/'run/simulation/seed_7'
    (tmp_path/'run/simulation/seed_007').mkdir()
    with pytest.raises(ValueError,match='noncanonical'):read_simulation('run')
    (tmp_path/'run/simulation/seed_007').rmdir()
    anchor=directory/'frame_000000000000.json';row=json.loads(anchor.read_text());row['generation']=4;anchor.write_text(json.dumps(row))
    with pytest.raises(ValueError,match='anchor'):read_simulation('run',cursor=1,limit=1)


def test_extinction_keeps_recording_generation_boundaries_without_inventing_ticks(tmp_path,monkeypatch):
    from codontrace.genesis.engine import GenesisEngine
    from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path))
    e=GenesisEngine.from_spec(GenesisRuntimeProfile.life_loop_world(seed=7,tick_count=24,population=16))
    plain=GenesisEngine.from_spec(e.spec)
    SimulationRecorder(tmp_path/'run').attach(e);r=e.run_ticks();control=plain.run_ticks()
    assert [t.digest() for t in r.ticks]==[t.digest() for t in control.ticks]
    frames=read_simulation('run',limit=32)['frames']
    assert len(frames)==25 and frames[-1]['metrics']['population']==0
    assert frames[-1]['generation']==24 and frames[-1]['tick']==frames[-2]['tick']


def test_missing_population_records_cannot_be_misreported_as_extinction():
    with pytest.raises(ValueError,match='explicit spatial'):
        frame_from_population({'generation':1,'tick':1},{'width':4,'height':4},run_id='run',seed=7)


def test_llm_simulation_inspection_has_real_counts_and_readonly_selected_scope(tmp_path,monkeypatch):
    from codontrace.console.science_tools import invoke_tool, llm_tool_schemas
    monkeypatch.setenv('CODONTRACE_RUNS_DIR',str(tmp_path))
    e=engine(ticks=2);SimulationRecorder(tmp_path/'run').attach(e);e.run_ticks()
    assert any(s['function']['name']=='simulation_inspect' for s in llm_tool_schemas())
    result=invoke_tool('simulation_inspect',{'seed':7,'cursor':1,'limit':2},selected_run_id='run')
    assert result['ok'] and result['next_cursor']==3
    assert result['artifacts'][0]['rows'][0][0]==1
    assert result['artifacts'][0]['provenance']['engine_run_id']==e.run.run_id
    assert not invoke_tool('simulation_inspect',{'run_id':'other'},selected_run_id='run')['ok']
    assert not invoke_tool('simulation_inspect',{'limit':33},selected_run_id='run')['ok']
