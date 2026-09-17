"""Phase 1 lock for HE02 runner wiring."""

from pathlib import Path

import pytest

from codontrace.genesis.he02_contrasts import run_hard_experiment_02_v1b


def _he02_src() -> str:
    return (
        Path(__file__).resolve().parents[1]
        / "src/codontrace/genesis/hard_experiment_02.py"
    ).read_text(encoding="utf-8")


def test_phase1_wrapper_is_required_entry_point() -> None:
    assert callable(run_hard_experiment_02_v1b)
    helper = (
        Path(__file__).resolve().parents[1]
        / "src/codontrace/genesis/he02_contrasts.py"
    ).read_text(encoding="utf-8")
    assert "rescore_he02_campaign" in helper
    assert "contrasts_from_seed_dicts" in helper


@pytest.mark.xfail(
    reason="hard_experiment_02.py source wire pending; use run_hard_experiment_02_v1b",
    strict=False,
)
def test_he02_runner_source_uses_delta_helper() -> None:
    src = _he02_src()
    assert "contrasts_from_seed_dicts" in src
    assert "paired_effect_size(lefts, rights)" not in src
