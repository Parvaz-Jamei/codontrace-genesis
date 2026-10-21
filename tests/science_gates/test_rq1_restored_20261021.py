"""Seeds 5706-5708 of the locked RQ-1 pack, rerun at commit 6187ff4.

The restored raw must match its manifest. The control and prefix comparisons
must be recorded as identical. The eight-seed rebuild must not be read as
support.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONF = ROOT / "docs/experiments/2026-09-29/rq1_time_shift/confirmatory"
DIR = CONF / "restored_2026-10-21"


def test_manifest_matches_restored_files() -> None:
    lines = (DIR / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines()
    names = set()
    for line in lines:
        digest, name = line.split()
        names.add(name)
        assert hashlib.sha256((DIR / "raw" / name).read_bytes()).hexdigest() == digest
    for seed in (5706, 5707, 5708):
        assert f"seed_{seed}.json" in names
        with gzip.open(DIR / "raw" / f"summary_seed{seed}.jsonl.gz", "rt") as fh:
            assert sum(1 for _ in fh) == 40


def test_recorded_comparisons_are_identical() -> None:
    for seed in (5701, 5706, 5707, 5708):
        rep = json.loads((DIR / f"verify_{seed}.json").read_text(encoding="utf-8"))
        assert rep["ok"] is True
    ctl = json.loads((DIR / "verify_5701.json").read_text(encoding="utf-8"))["seeds"]["5701"]
    for stream in ("events", "population", "summary"):
        assert ctl[stream]["archived_prefix_identical"] is True
        assert ctl[stream]["archived_records"] == ctl[stream]["reproduced_records"]
    assert ctl["seed_json_fields_differing"] == ["frozen_is_zero"]
    prefix = json.loads((DIR / "verify_5706.json").read_text(encoding="utf-8"))["seeds"]["5706"]
    assert prefix["summary"]["archived_prefix_identical"] is True


def test_frozen_flag_recomputes_true_from_archived_matrix() -> None:
    spec = importlib.util.spec_from_file_location("vp", DIR / "verify_provenance.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for seed in range(5701, 5706):
        rec = json.loads((CONF / "raw" / f"seed_{seed}.json").read_text(encoding="utf-8"))
        assert mod._frozen_is_zero(rec) is True


def test_eight_seed_rebuild_is_not_support() -> None:
    out = json.loads((DIR / "analysis_eight_seeds/analysis_confirmatory.json").read_text(encoding="utf-8"))
    text = json.dumps(out)
    assert '"verdict": "INCONCLUSIVE"' in text
    assert '"hypothesis_supported": true' not in text
    assert '"red_queen_proved": true' not in text


def test_locked_commit_is_in_history() -> None:
    try:
        kind = subprocess.run(
            ["git", "-C", str(ROOT), "cat-file", "-t", "6187ff4"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        pytest.skip("git not available")
    if kind.returncode != 0:
        pytest.skip("history not available (shallow clone or source archive)")
    assert kind.stdout.strip() == "commit"
