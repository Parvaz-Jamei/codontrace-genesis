"""Phase 1 lock: HE02 runner must call contrasts_from_seed_dicts."""

from pathlib import Path


def test_he02_runner_source_uses_delta_helper() -> None:
    src = (
        Path(__file__).resolve().parents[1]
        / "src/codontrace/genesis/hard_experiment_02.py"
    ).read_text(encoding="utf-8")
    assert "contrasts_from_seed_dicts" in src
    assert "paired_effect_size(lefts, rights)" not in src
