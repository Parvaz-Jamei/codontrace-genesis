"""The golden helper fails on drift and on missing fixtures, and refuses updates on CI."""
from __future__ import annotations

import pytest

from . import _golden


@pytest.fixture
def golden_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(_golden, 'GOLDEN_DIR', tmp_path)
    monkeypatch.delenv(_golden.UPDATE_ENV, raising=False)
    monkeypatch.delenv('CI', raising=False)
    return tmp_path


def test_drift_and_missing_fail_by_default(golden_dir):
    (golden_dir / 'x.json').write_bytes(_golden.golden_json_bytes({'a': 1.5}))
    _golden.check_json('x.json', {'a': 1.5})
    with pytest.raises(pytest.fail.Exception, match='drifted'):
        _golden.check_json('x.json', {'a': 1.5000000000000002})
    with pytest.raises(pytest.fail.Exception, match='missing'):
        _golden.check_json('absent.json', {})
    assert not (golden_dir / 'absent.json').exists()


def test_tree_layout_drift_fails(golden_dir, tmp_path_factory):
    produced = tmp_path_factory.mktemp('produced')
    (produced / 'a').write_bytes(b'1')
    (golden_dir / 'tree').mkdir(); (golden_dir / 'tree' / 'a').write_bytes(b'1')
    _golden.check_tree('tree', produced)
    (produced / 'b').write_bytes(b'2')
    with pytest.raises(AssertionError, match='layout'):
        _golden.check_tree('tree', produced)


def test_update_writes_locally_but_is_refused_on_ci(golden_dir, monkeypatch):
    monkeypatch.setenv(_golden.UPDATE_ENV, '1')
    _golden.check_json('new.json', [1])
    assert (golden_dir / 'new.json').read_bytes() == b'[\n 1\n]\n'
    monkeypatch.setenv('CI', 'true')
    with pytest.raises(pytest.fail.Exception, match='CI'):
        _golden.check_json('new.json', [2])
