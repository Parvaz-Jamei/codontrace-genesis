"""Regressions for confirmatory stop and failed-arm scoring. No 600-generation run."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.rq_bidirectional_timeshift import (
    ARCHIVE_SCHEMA,
    EXPERIMENT_ID,
    SNAPSHOT_SCHEMA,
    write_snapshot,
)
from codontrace.genesis.rq_bidirectional_timeshift_confirm import (
    ARMS,
    VERDICT_BLOCKED,
    VERDICT_SUPPORTED,
    analyze,
    main,
    mark_started,
    required_snapshot_generations,
    restart_clean,
)

_RUN = "run-hunt"
_CODE = "code"
_CFG = "cfg"
_DESIGN = "design"
# One center carries the contrast. Later snapshots match each other, so the
# other centers are zero and are not imputed. Even and odd seeds differ so
# the sample standard error is not zero.
_SPEC = {
    "A": {
        0: ("000000", "000111", "111000", "000000"),
        1: ("000000", "111100", "000111", "000000"),
    },
    "B": {
        0: ("000000", "000000", "000000", "111111"),
        1: ("000000", "111000", "000000", "111111"),
    },
    "C": {
        0: ("000000", "111000", "000000", "111111"),
        1: ("000000", "111100", "000000", "111111"),
    },
    "D": {
        0: ("000000", "000000", "000000", "000000"),
        1: ("111111", "111111", "111111", "111111"),
    },
}


def _stop_lock(*, started: bool) -> dict[str, object]:
    return {
        "confirmatory": {
            "confirmatory_started": started,
            "delta": 40,
            "dispersion": {"resolvable": False},
            "generations": 600,
            "locked": True,
            "practical_effect": 0.9,
            "revised_design": {
                "n_histories": 40,
                "practical_effect": 0.2,
                "reason": "cannot resolve",
                "started": False,
            },
            "run_id": "must-not-run",
            "seeds": [9201],
        },
        "confirmatory_started": started,
    }


def test_prereg_stop_blocks_start_even_if_the_flag_is_already_set(tmp_path: Path) -> None:
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    (fresh / "prereg_lock.json").write_text(json.dumps(_stop_lock(started=False)), encoding="utf-8")
    assert main(["--root", str(fresh)]) == 2
    body = json.loads((fresh / "prereg_lock.json").read_text(encoding="utf-8"))
    assert body["confirmatory"]["confirmatory_started"] is False
    assert body["confirmatory_started"] is False
    assert not (fresh / "live.log").exists()

    started = tmp_path / "started"
    started.mkdir()
    (started / "prereg_lock.json").write_text(json.dumps(_stop_lock(started=True)), encoding="utf-8")
    (started / "live.log").write_text("phase=2 keep\n", encoding="utf-8")
    assert main(["--root", str(started)]) == 2
    assert main(["--root", str(started), "--analyze-only"]) == 2
    log = (started / "live.log").read_text(encoding="utf-8")
    assert "confirmatory-start" not in log
    assert not (started / "confirmatory" / "verdict.json").exists()
    with pytest.raises(ConfigurationError, match="must not be started"):
        mark_started(started, "new-run")
    after = json.loads((started / "prereg_lock.json").read_text(encoding="utf-8"))
    assert after["confirmatory"]["confirmatory_started"] is True
    assert after["confirmatory"]["run_id"] == "must-not-run"


def test_restart_clean_does_not_start_a_revised_design(tmp_path: Path) -> None:
    (tmp_path / "prereg_lock.json").write_text(json.dumps(_stop_lock(started=False)), encoding="utf-8")
    (tmp_path / "confirmatory").mkdir()
    (tmp_path / "confirmatory" / "evidence.txt").write_text("keep-me", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="must not be started"):
        restart_clean(tmp_path)
    body = json.loads((tmp_path / "prereg_lock.json").read_text(encoding="utf-8"))
    assert body["confirmatory"]["confirmatory_started"] is False
    assert (tmp_path / "confirmatory" / "evidence.txt").read_text(encoding="utf-8") == "keep-me"
    assert not (tmp_path / "retained").exists()


def _write_supporting_root(root: Path) -> list[int]:
    seeds = list(range(1, 13))
    generations = list(required_snapshot_generations())
    snapshots = root / "confirmatory" / "snapshots"

    def host(seed: int, window: str) -> dict[str, object]:
        return {"id": f"h{seed}", "window": window, "runtime_atp": 48.0, "parent_id": None}

    def parasite(seed: int, window: str) -> dict[str, object]:
        return {
            "born_generation": 0,
            "energy": 1.0,
            "parent_id": None,
            "unit_id": f"p{seed}",
            "window": window,
        }

    for seed in seeds:
        seed_dir = root / "confirmatory" / "by_seed" / f"seed{seed}"
        seed_dir.mkdir(parents=True)
        lines: list[str] = []
        for arm in ARMS:
            lines.append(
                json.dumps(
                    {
                        "arm": arm,
                        "code_version": _CODE,
                        "config_digest": _CFG,
                        "design_version": _DESIGN,
                        "experiment": EXPERIMENT_ID,
                        "generation": 1,
                        "history_id": str(seed),
                        "run_id": _RUN,
                        "schema": ARCHIVE_SCHEMA,
                        "seed": seed,
                    },
                    sort_keys=True,
                )
            )
            past_h, past_p, now_h, now_p = _SPEC[arm][seed % 2]
            for generation in generations:
                host_window, parasite_window = (past_h, past_p) if generation == 160 else (now_h, now_p)
                write_snapshot(
                    snapshots / f"seed{seed}_{arm}_g{generation:04d}.json",
                    {
                        "arm": arm,
                        "code_version": _CODE,
                        "config_digest": _CFG,
                        "design_version": _DESIGN,
                        "experiment": EXPERIMENT_ID,
                        "generation": generation,
                        "history_id": str(seed),
                        "hosts": [host(seed, host_window)],
                        "parasites": [parasite(seed, parasite_window)],
                        "phase": 2,
                        "red_queen_proved": False,
                        "run_id": _RUN,
                        "schema": SNAPSHOT_SCHEMA,
                        "seed": seed,
                    },
                )
        (seed_dir / "archive.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (seed_dir / "initial.json").write_text(
            json.dumps({"run_id": _RUN, "seed": seed}),
            encoding="utf-8",
        )
        (seed_dir / "COMPLETE").write_text(
            json.dumps(
                {
                    "arms": {
                        name: {"failed": None, "generations_completed": 1, "red_queen_proved": False}
                        for name in ARMS
                    },
                    "failed": None,
                    "red_queen_proved": False,
                    "run_id": _RUN,
                    "seed": seed,
                }
            ),
            encoding="utf-8",
        )
    block = {
        "code_commit": "abc",
        "code_version": _CODE,
        "config_digest": _CFG,
        "confirmatory_started": True,
        "delta": 40,
        "design_version": _DESIGN,
        "dispersion": {"resolvable": True},
        "generations": 1,
        "importance_bound": 0.01,
        "locked": True,
        "minimum_detectable_effect": 1.0,
        "practical_effect": 0.9,
        "run_id": _RUN,
        "seeds": seeds,
    }
    (root / "prereg_lock.json").write_text(
        json.dumps({"confirmatory": block, "confirmatory_started": True}),
        encoding="utf-8",
    )
    return seeds


def test_failed_arm_and_locked_stop_are_not_support(tmp_path: Path) -> None:
    seeds = _write_supporting_root(tmp_path)
    supported = analyze(tmp_path)
    assert supported["verdict"] == VERDICT_SUPPORTED
    assert supported["red_queen_proved"] is False
    assert supported["biological_red_queen_proved"] is False

    prereg_path = tmp_path / "prereg_lock.json"
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    prereg["confirmatory"]["revised_design"] = {
        "n_histories": 80,
        "reason": "cannot resolve",
        "started": False,
    }
    prereg_path.write_text(json.dumps(prereg), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="must stop"):
        analyze(tmp_path)

    del prereg["confirmatory"]["revised_design"]
    prereg_path.write_text(json.dumps(prereg), encoding="utf-8")
    for seed in seeds:
        path = tmp_path / "confirmatory" / "by_seed" / f"seed{seed}" / "COMPLETE"
        body = json.loads(path.read_text(encoding="utf-8"))
        body["arms"]["B"]["failed"] = "energy-residual"
        path.write_text(json.dumps(body), encoding="utf-8")
    failed = analyze(tmp_path)
    assert failed["verdict"] == VERDICT_BLOCKED
    assert failed["verdict"] != VERDICT_SUPPORTED
    assert failed["archive_ok"] is False
    assert failed["red_queen_proved"] is False
    assert failed["biological_red_queen_proved"] is False
