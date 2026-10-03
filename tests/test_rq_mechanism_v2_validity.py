"""Phase-1 validity controls. Expectations are derived, not copied from outputs.

Each important path has a positive control and an independent negative control.
No confirmatory campaign is started. Seeds, horizon, lag and maintenance cost
are not retuned.
"""

from __future__ import annotations

import json
import math
import statistics
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    STRUCT_STEAL_FRACTION,
    STRUCT_VIRULENCE,
)
from codontrace.genesis.measurements.antagonist_population import (
    EARNED_YIELD,
    PAIRING_COST,
    AntagonistPopulation,
)
from codontrace.genesis.rq_bidirectional_timeshift import (
    ARCHIVE_SCHEMA,
    ARM_A,
    ARM_B,
    ARM_C,
    ARM_D,
    EXPERIMENT_ID,
    RQ_CODE_VERSION,
    RQ_DESIGN_VERSION,
    SNAPSHOT_SCHEMA,
    build_arm,
    control_statement,
    read_bound_snapshot,
    read_snapshot,
    replay_archived_contact,
    write_snapshot,
)
from codontrace.genesis.rq_bidirectional_timeshift_confirm import (
    ALPHA,
    VERDICT_BLOCKED,
    VERDICT_INCONCLUSIVE,
    VERDICT_SUPPORTED,
    assert_artifacts_one_run,
    assess_locked_histories,
    decide_verdict,
    infectivity,
    one_sample_t,
    require_complete_times,
    require_same_histories,
    restart_clean,
    run_one_history,
    student_t_ppf,
    validate_archive,
)
from codontrace.genesis.rq_stream import ARM_STREAM_POLICY, derive_stream_seed, open_stream

# Documented instrument. A change here is a retune, not a silent follow.
SCALE = 8.0 * 0.15
CREDIT_NET = 0.75 - 0.25
LOCKED_T_DF23 = 2.3978750646571103


def _bits(host: str, parasite: str) -> tuple[int, float, float]:
    matches = sum(1 for left, right in zip(host, parasite, strict=True) if left == right)
    affinity = matches / 6.0
    debit = SCALE * affinity
    return matches, affinity, debit


def _pair(host: str, parasite: str, *, atp: float, host_id: str = "h", parasite_id: str = "p") -> dict[str, object]:
    hosts = [{"id": host_id, "window": host, "runtime_atp": atp, "parent_id": None}]
    parasites = [
        {
            "unit_id": parasite_id,
            "window": parasite,
            "energy": 1.0,
            "parent_id": None,
            "born_generation": 0,
        }
    ]
    return replay_archived_contact(hosts, parasites, atp_override=atp, tick_index=0)


def test_stream_derivation_does_not_collide_and_arms_do_not_share_an_object() -> None:
    assert STRUCT_VIRULENCE == 8.0
    assert STRUCT_STEAL_FRACTION == 0.15
    left = derive_stream_seed(EXPERIMENT_ID, "9201", "host-step", 2)
    right = derive_stream_seed(EXPERIMENT_ID, "9202", "host-step", 1)
    # Negative control: the old numeric sum collides. The new stream must not.
    assert (9201 + 2) == (9202 + 1)
    assert left != right
    assert left != 9201 + 2
    assert right != 9202 + 1
    again = derive_stream_seed(EXPERIMENT_ID, "9201", "host-step", 2)
    assert again == left
    other_history = derive_stream_seed(EXPERIMENT_ID, "9300", "host-step", 2)
    assert other_history != left
    assert ARM_STREAM_POLICY["policy_id"] == "shared-derivation-separate-objects"
    first = open_stream(EXPERIMENT_ID, "9201", "host-step", 2)
    second = open_stream(EXPERIMENT_ID, "9201", "host-step", 2)
    assert first is not second
    drawn = first.random()
    # If the two arms shared one mutable RNG, this draw would be the second, not the first.
    assert second.random() == drawn


def test_one_shot_matches_resume_and_capture_restores_rng_and_births() -> None:
    one_shot = build_arm(ARM_A, 9201)
    resumed = build_arm(ARM_A, 9201)
    one_shot.run_generations(3)
    resumed.run_generations(1)
    resumed.run_generations(2)
    assert one_shot.parasite_windows == resumed.parasite_windows
    assert [org.id for org in one_shot._hosts()] == [org.id for org in resumed._hosts()]
    assert one_shot.tick_index == resumed.tick_index == 3
    captured = resumed.capture_rng_and_births()
    assert resumed.last_host_rng is not None
    assert resumed.antagonist_pop is not None
    expected_draw = resumed.last_host_rng.random()
    resumed.last_host_rng.random()
    resumed.antagonist_pop.child_serial = int(resumed.antagonist_pop.child_serial) + 5
    resumed.antagonist_pop.known_unit_ids.add("not-a-birth")
    resumed.restore_rng_and_births(captured)
    assert resumed.last_host_rng is not None
    assert resumed.last_host_rng.random() == expected_draw
    assert resumed.antagonist_pop.child_serial == captured["child_serial"]
    assert "not-a-birth" not in resumed.antagonist_pop.known_unit_ids


def test_seed_order_and_four_workers_do_not_change_the_archive(tmp_path: Path) -> None:
    serial = tmp_path / "serial"
    reverse = tmp_path / "reverse"
    pooled = tmp_path / "pooled"
    for root in (serial, reverse, pooled):
        root.mkdir(parents=True, exist_ok=True)
        (root / "live.log").write_text("", encoding="utf-8")
    for seed in (9201, 9202):
        outcome = run_one_history(seed, str(serial), 1, "validity", 0)
        assert outcome["red_queen_proved"] is False
    for seed in (9202, 9201):
        run_one_history(seed, str(reverse), 1, "validity", 0)
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = [
            pool.submit(run_one_history, seed, str(pooled), 1, "validity", 0)
            for seed in (9201, 9202)
        ]
        assert [future.result()["red_queen_proved"] for future in futures] == [False, False]
    for seed in (9201, 9202):
        serial_bytes = (serial / "confirmatory" / "by_seed" / f"seed{seed}" / "archive.jsonl").read_bytes()
        reverse_bytes = (reverse / "confirmatory" / "by_seed" / f"seed{seed}" / "archive.jsonl").read_bytes()
        pooled_bytes = (pooled / "confirmatory" / "by_seed" / f"seed{seed}" / "archive.jsonl").read_bytes()
        assert serial_bytes == reverse_bytes == pooled_bytes
        rows = [json.loads(line) for line in serial_bytes.decode().splitlines()]
        assert rows
        assert all(row["host_step_seed"] != seed + row["generation"] for row in rows)
        assert all(row["schema"] == ARCHIVE_SCHEMA for row in rows)
        births = [birth for row in rows for birth in row["host_births"]]
        assert all(birth["parent_id"] and int(birth["generation"]) != 0 for birth in births)


def test_controls_are_named_as_what_they_cut_and_founders_are_not_births() -> None:
    assert "not a pure evolution control" in control_statement(ARM_C)
    assert "not a frozen genotype" in control_statement(ARM_B)
    assert "not a frozen genotype" in control_statement(ARM_D)
    assert "not a pure evolution control" in control_statement(ARM_D)
    arm = build_arm(ARM_A, 7)
    assert arm.antagonist_pop is not None
    assert all(unit.parent_id is None and unit.born_generation == 0 for unit in arm.antagonist_pop.units)
    assert AntagonistPopulation.__dataclass_fields__["maintenance_cost"].default == 0.15
    # Negative control: a generation-0 record with no parent is a founder, not a birth.
    founder_like = [unit for unit in arm.antagonist_pop.units if unit.parent_id is None]
    assert founder_like
    assert all(unit.born_generation == 0 for unit in founder_like)


def test_assay_follows_the_engine_seat_not_the_cartesian_mean() -> None:
    full = _pair("000000", "000000", atp=48.0)
    _matches, affinity, intended = _bits("000000", "000000")
    assert affinity == 1.0
    assert intended == SCALE
    assert full["debit"] == pytest.approx(min(48.0, intended))
    assert full["loss"] == pytest.approx(full["debit"])
    assert EARNED_YIELD - PAIRING_COST == CREDIT_NET
    assert full["credit"] == pytest.approx(CREDIT_NET * float(full["debit"]))
    assert full["infectivity"] == pytest.approx(float(full["debit"]) / SCALE)
    assert full["archive_mutated"] is False

    mid = _pair("000000", "000111", atp=48.0)
    _matches, affinity, intended = _bits("000000", "000111")
    assert affinity == 0.5
    assert mid["debit"] == pytest.approx(intended)
    assert mid["infectivity"] == pytest.approx(0.5)

    zero = _pair("000000", "111111", atp=48.0)
    assert _bits("000000", "111111")[1] == 0.0
    assert zero["debit"] == 0.0
    assert zero["credit"] == 0.0
    assert zero["loss"] == 0.0
    assert zero["infectivity"] == 0.0

    clipped = _pair("000000", "000000", atp=0.3)
    assert clipped["debit"] == pytest.approx(0.3)
    assert clipped["loss"] == pytest.approx(0.3)
    assert clipped["credit"] == pytest.approx(CREDIT_NET * 0.3)
    assert clipped["infectivity"] == pytest.approx(0.3 / SCALE)

    hosts = [
        {"id": "h0", "window": "000000", "runtime_atp": 48.0},
        {"id": "h1", "window": "000000", "runtime_atp": 48.0},
        {"id": "h2", "window": "111111", "runtime_atp": 48.0},
    ]
    parasites = [{"unit_id": "p0", "window": "111111", "energy": 1.0, "born_generation": 0}]
    token = json.dumps({"hosts": hosts, "parasites": parasites}, sort_keys=True)
    uneven = replay_archived_contact(hosts, parasites, atp_override=48.0, tick_index=0)
    # Seat 0 at tick 0 is the first host. Cartesian mean would be 1/3.
    assert uneven["contacts"] == 1
    assert uneven["infectivity"] == 0.0
    assert uneven["infectivity"] != pytest.approx(1.0 / 3.0)
    assert json.dumps({"hosts": hosts, "parasites": parasites}, sort_keys=True) == token

    swapped_hosts = [hosts[2], hosts[0], hosts[1]]
    swapped = replay_archived_contact(swapped_hosts, parasites, atp_override=48.0, tick_index=0)
    assert swapped["infectivity"] == pytest.approx(1.0)
    assert swapped["infectivity"] != uneven["infectivity"]

    assert infectivity([], parasites) is None
    assert infectivity(hosts, []) is None
    assert infectivity([], parasites) != 0.0


def test_snapshot_identity_rejects_a_healthy_digest_with_the_wrong_name(tmp_path: Path) -> None:
    body = {
        "arm": ARM_A,
        "code_version": RQ_CODE_VERSION,
        "config_digest": "cfg-1",
        "design_version": RQ_DESIGN_VERSION,
        "experiment": EXPERIMENT_ID,
        "generation": 2,
        "history_id": "9201",
        "hosts": [{"id": "h", "window": "000000"}],
        "parasites": [{"unit_id": "p", "window": "111111"}],
        "red_queen_proved": False,
        "run_id": "prov",
        "schema": SNAPSHOT_SCHEMA,
        "seed": 9201,
    }
    path = tmp_path / "ok.json"
    write_snapshot(path, body)
    expected = {
        "arm": ARM_A,
        "code_version": RQ_CODE_VERSION,
        "config_digest": "cfg-1",
        "design_version": RQ_DESIGN_VERSION,
        "experiment": EXPERIMENT_ID,
        "generation": 2,
        "history_id": "9201",
        "run_id": "prov",
        "schema": SNAPSHOT_SCHEMA,
        "seed": 9201,
    }
    loaded = read_bound_snapshot(path, expected=expected)
    assert loaded["red_queen_proved"] is False

    def rejected(**changes: object) -> None:
        other = dict(body)
        other.update(changes)
        target = tmp_path / f"bad-{changes.keys()}.json"
        write_snapshot(target, other)
        with pytest.raises(ConfigurationError):
            read_bound_snapshot(target, expected=expected)

    rejected(seed=9202, history_id="9202")
    rejected(arm=ARM_D)
    rejected(generation=3)
    rejected(run_id="other-run")
    rejected(config_digest="cfg-2")
    rejected(schema="rq-timeshift-snapshot/0")
    rejected(code_version="other")
    rejected(design_version="other")
    rejected(experiment="OTHER")

    missing = dict(body)
    del missing["schema"]
    missing_path = tmp_path / "missing.json"
    write_snapshot(missing_path, missing)
    with pytest.raises(ConfigurationError):
        read_bound_snapshot(missing_path, expected=expected)

    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["hosts"] = [{"id": "h", "window": "111111"}]
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ConfigurationError):
        read_snapshot(tampered)


def _archive_row(arm: str, generation: int) -> dict[str, object]:
    return {
        "arm": arm,
        "code_version": "code",
        "config_digest": "cfg",
        "design_version": "design",
        "experiment": EXPERIMENT_ID,
        "generation": generation,
        "history_id": "7",
        "run_id": "run-7",
        "schema": ARCHIVE_SCHEMA,
        "seed": 7,
    }


def test_archive_line_count_is_not_enough_and_artifacts_share_one_run(tmp_path: Path) -> None:
    good = tmp_path / "good.jsonl"
    good.write_text(
        "\n".join(json.dumps(_archive_row(arm, 1)) for arm in (ARM_A, ARM_D)) + "\n",
        encoding="utf-8",
    )
    assert validate_archive(
        good,
        seed=7,
        generations=1,
        arms=(ARM_A, ARM_D),
        run_id="run-7",
        config_digest_value="cfg",
        code_version="code",
        design_version="design",
    )["ok"] is True
    duplicate = tmp_path / "duplicate.jsonl"
    duplicate.write_text(
        json.dumps(_archive_row(ARM_A, 1)) + "\n" + json.dumps(_archive_row(ARM_A, 1)) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="duplicated or missing"):
        validate_archive(
            duplicate,
            seed=7,
            generations=1,
            arms=(ARM_A, ARM_D),
            run_id="run-7",
            config_digest_value="cfg",
            code_version="code",
            design_version="design",
        )
    seed_dir = tmp_path / "confirmatory" / "by_seed" / "seed7"
    seed_dir.mkdir(parents=True)
    (seed_dir / "initial.json").write_text(json.dumps({"run_id": "run-7", "seed": 7}), encoding="utf-8")
    (seed_dir / "COMPLETE").write_text(json.dumps({"run_id": "run-7", "seed": 7}), encoding="utf-8")
    assert_artifacts_one_run(tmp_path, run_id="run-7", seeds=(7,))
    (seed_dir / "COMPLETE").write_text(json.dumps({"run_id": "other", "seed": 7}), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="not bound"):
        assert_artifacts_one_run(tmp_path, run_id="run-7", seeds=(7,))


def test_restart_retains_evidence_and_does_not_strip_the_log(tmp_path: Path) -> None:
    lock = {
        "confirmatory": {
            "delta": 40,
            "generations": 600,
            "locked": True,
            "restart_clean_count": 0,
            "run_id": "old",
            "seeds": [9201],
        }
    }
    (tmp_path / "prereg_lock.json").write_text(json.dumps(lock), encoding="utf-8")
    evidence = tmp_path / "confirmatory" / "by_seed"
    evidence.mkdir(parents=True)
    (tmp_path / "confirmatory" / "evidence.txt").write_text("keep-me", encoding="utf-8")
    (tmp_path / "live.log").write_text("phase=2 event=confirmatory keep\n", encoding="utf-8")
    restart_clean(tmp_path)
    retained = tmp_path / "retained" / "restart-1"
    assert (retained / "confirmatory" / "evidence.txt").read_text(encoding="utf-8") == "keep-me"
    assert "phase=2" in (tmp_path / "live.log").read_text(encoding="utf-8")
    assert "phase=2" in (retained / "live.log").read_text(encoding="utf-8")
    assert not (tmp_path / "confirmatory").exists()


def test_stats_refuse_zero_se_bad_samples_and_accept_a_real_positive() -> None:
    importance = 0.05
    constant = one_sample_t([0.2] * 24, importance, mde=0.2)
    assert constant["se_zero"] is True
    assert constant["p_one_sided"] is None
    assert constant["reject"] is False
    assert constant["practical_support"] is False
    names = ("CH_A", "CP_A", "S_A_minus_S_B", "S_A_minus_S_C")
    assert (
        decide_verdict(
            {name: constant for name in names},
            verification_ok=True,
            archive_ok=True,
            practical_effect=importance,
        )
        == VERDICT_INCONCLUSIVE
    )
    short = one_sample_t([0.2] * 11, importance)
    assert (
        decide_verdict(
            {name: short for name in names},
            verification_ok=True,
            archive_ok=True,
            practical_effect=importance,
        )
        == VERDICT_BLOCKED
    )
    with pytest.raises(ConfigurationError):
        one_sample_t([0.1, math.nan], importance)
    with pytest.raises(ConfigurationError):
        one_sample_t([0.1, math.inf], importance)

    alias = assess_locked_histories(
        ({"seed": 1, "value": 0.2}, {"seed": 1, "value": 0.3}),
        (1,),
    )
    assert alias["ok"] is False
    assert alias["reason"] == "duplicate-history-alias"
    assert alias["support_allowed"] is False
    omitted = assess_locked_histories(({"seed": 1, "value": None},), (1,))
    assert omitted["estimand_changed"] is True
    assert omitted["n_used"] == 0
    assert "not imputed as 0" in str(omitted["estimand"])
    with pytest.raises(ConfigurationError):
        require_complete_times((1, 3), (1, 2, 3))
    with pytest.raises(ConfigurationError):
        require_same_histories((9201, 9202), (9201, 9203))
    require_same_histories((9201, 9202), (9201, 9202))

    values = [0.30] * 12 + [0.50] * 12
    mean = statistics.fmean(values)
    se = statistics.stdev(values) / math.sqrt(len(values))
    lower = mean - LOCKED_T_DF23 * se
    assert abs(student_t_ppf(1.0 - ALPHA, 23) - LOCKED_T_DF23) < 1e-8
    assert lower > importance
    assert lower < mean
    scored = one_sample_t(values, importance, mde=1.0)
    assert scored["mean"] == pytest.approx(mean)
    assert scored["lower_decision"] == pytest.approx(lower)
    assert scored["p_one_sided"] not in (None, 0.0)
    assert scored["practical_support"] is True
    assert scored["mde"] == 1.0
    assert scored["importance_bound"] == importance
    between = one_sample_t(values, (lower + mean) / 2.0, mde=1.0)
    # The point estimate clears this bound. The one-sided lower bound does not.
    assert mean > float(between["importance_bound"]) > lower
    assert between["meets_practical_effect"] is False
    assert between["reject"] is True
    assert (
        decide_verdict(
            {name: scored for name in names},
            verification_ok=True,
            archive_ok=True,
            practical_effect=importance,
        )
        == VERDICT_SUPPORTED
    )
