"""Negative archive and controller checks; these tests do not claim coevolution."""
from __future__ import annotations

import importlib.util
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError

_SCRIPT = Path(__file__).parents[1] / 'scripts/rq_full_engine_parallel.py'
_SPEC = importlib.util.spec_from_file_location('rq_parallel_under_test', _SCRIPT)
assert _SPEC and _SPEC.loader
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)


def rows(seed=16001, generations=2):
    return [dict(seed=seed, arm=arm, generation=g, schema=runner.ARCHIVE_SCHEMA,
        config_digest=runner.config_digest(), invariant='ok', reproduction_enabled=True,
        red_queen_proved=False, contact_debit=0.0, contact_credit=0.0, contacts=0)
        for arm in runner.ARMS for g in range(1, generations+1)]


def archive(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row)+'\n' for row in data))


def test_all_expected_rows_pass_without_inventing_a_proof(tmp_path):
    path=tmp_path/'archive.jsonl'
    archive(path, rows())
    runner.validate_archive(path,16001,2,runner.config_digest())


@pytest.mark.parametrize('field,value', [
    ('seed',16002), ('seed',True), ('generation',True), ('schema','old-schema'),
    ('config_digest','different-config'), ('invariant','energy-failure'),
    ('reproduction_enabled',False), ('red_queen_proved',True),
    ('contact_debit',float('nan')), ('contact_credit',-1.0), ('contacts',-1),
])
def test_invalid_persisted_evidence_is_rejected(tmp_path,field,value):
    data=rows();data[0][field]=value;path=tmp_path/'archive.jsonl';archive(path,data)
    with pytest.raises(ConfigurationError):runner.validate_archive(path,16001,2,runner.config_digest())


@pytest.mark.parametrize('kind',['missing','duplicate','malformed'])
def test_missing_duplicate_or_malformed_rows_are_rejected(tmp_path,kind):
    path=tmp_path/'archive.jsonl';data=rows()
    if kind=='missing':data=data[:-1]
    if kind=='duplicate':data[-1]=data[0]
    archive(path,data)
    if kind=='malformed':path.write_text(path.read_text()+'{"broken":\n')
    with pytest.raises(ConfigurationError):runner.validate_archive(path,16001,2,runner.config_digest())


@pytest.mark.parametrize('seeds,generations,workers,seconds', [
    ((16001,),True,1,5), ((16001,),2,True,5), ((True,),2,1,5),
    ((16001,16001),2,1,5), ((16001,),2,1,float('nan')), ((16001,),2,1,True),
])
def test_invalid_budget_is_rejected_before_output_creation(tmp_path,seeds,generations,workers,seconds):
    root=tmp_path/'run'
    with pytest.raises(ConfigurationError):runner.run(root,seeds,generations,workers,seconds)
    assert not root.exists()


def fake_pool(monkeypatch,mutate=None):
    monkeypatch.setattr(runner,'ProcessPoolExecutor',ThreadPoolExecutor)
    def worker(seed,root,generations):
        path=Path(root)/'by_seed'/f'seed{seed}'/'archive.jsonl';data=rows(seed,generations)
        if mutate:mutate(data)
        archive(path,data)
        return dict(seed=seed,failed=None,generations_completed=generations)
    monkeypatch.setattr(runner,'worker',worker)
    monkeypatch.setattr(runner,'replay_phase5_archive',lambda path:dict(matched=True))
    monkeypatch.setattr(runner,'engine_diagnostics',lambda *args:None)
    monkeypatch.setattr(runner,'horizon_diagnostics',lambda *args:None)


def test_controller_records_failure_after_an_apparently_successful_worker(tmp_path,monkeypatch):
    fake_pool(monkeypatch,lambda data:data.pop())
    root=tmp_path/'bad';report=runner.run(root,(16001,),2,1,5)
    assert report['complete'] is False
    assert report['validation_failures']
    assert report['diagnostics_complete'] is False
    assert (root/'STOP').exists()
    assert json.loads((root/'execution.json').read_text())==report
    assert report['red_queen_proved'] is False


def test_diagnostic_exception_is_not_a_success_exit(tmp_path,monkeypatch):
    fake_pool(monkeypatch)
    def bad(*args):raise RuntimeError('diagnostic injection')
    monkeypatch.setattr(runner,'horizon_diagnostics',bad)
    report=runner.run(tmp_path/'diagnostic',(16001,),2,1,5)
    assert report['complete'] is False
    assert report['validation_failures'][0]['stage']=='diagnostics'
    assert report['diagnostics_complete'] is False


def test_cooperative_time_stop_keeps_a_partial_execution_report(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'ProcessPoolExecutor',ThreadPoolExecutor)
    def wait_for_stop(seed,root,generations):
        began=time.monotonic()
        while not (Path(root)/'STOP').exists():
            if time.monotonic()-began>2:raise RuntimeError('watchdog did not stop')
            time.sleep(.005)
        return dict(seed=seed,failed='stopped',generations_completed=0)
    monkeypatch.setattr(runner,'worker',wait_for_stop)
    root=tmp_path/'timed';report=runner.run(root,(16001,),2,1,.02)
    assert report['complete'] is False
    assert (root/'partial_execution.json').is_file()
    assert (root/'health.log').is_file()
