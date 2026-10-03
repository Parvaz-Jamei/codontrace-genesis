"""Phase-2 arm wiring. Expectations come from the locked cuts, not from a saved output."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.closed_loop_hp_arm01 import ARM_COPASSAGED
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import StructuralRQArm
from codontrace.genesis.closed_loop_pearl_spc import PASSAGE_COEVOLVE, PASSAGE_FROZEN
from codontrace.genesis.measurements.antagonist_population import (
    ANTAGONIST_ECOLOGY_POPULATION,
    ANTAGONIST_PASSAGE_SHUFFLED_LABELS,
)
from codontrace.genesis.rq_bidirectional_timeshift import (
    ARM_A,
    ARM_B,
    ARM_C,
    ARM_D,
    ARMS,
    EXPERIMENT_ID,
    build_arm,
    build_phase2_arm,
    control_statement,
    invariant_status,
    replay_archived_contact,
)
from codontrace.genesis.rq_mechanism_v2_phase2 import (
    PHASE2_SEEDS,
    _Append,
    _run_logged_arm,
    _run_pool,
    archive_field_status,
    assert_phase2_seeds,
    founder_identity,
    replay_phase2_archive,
    scientific_body,
)
from codontrace.genesis.rq_stream import derive_stream_seed, open_stream

# Not a phase-2 history and not a forbidden seed. Outcomes here are not the short run.
_TEST_SEED = 9401


def _required_archive_record() -> dict[str, object]:
    """The fields the lock requires, written out here rather than read back from the checker."""

    host = {"id": "h0", "parent_id": None, "runtime_atp": 1.0, "window": "000000"}
    parasite = {"energy": 1.0, "parent_id": None, "unit_id": "a0-0", "window": "000000"}
    return {
        "arm": "A",
        "contact_credit": 0.0,
        "contact_debit": 0.0,
        "contact_hosts": [dict(host)],
        "contact_parasites": [dict(parasite)],
        "contact_tick": 0,
        "contacts": [{"atp": 0.0, "host_id": "h0", "unit_id": "a0-0"}],
        "generation": 1,
        "host_births": [],
        "host_deaths": [],
        "host_energy": 1.0,
        "hosts": [dict(host)],
        "invariant": "ok",
        "parasite_births": [],
        "parasite_deaths": [],
        "parasite_energy": 1.0,
        "parasites": [dict(parasite)],
        "passage": "frozen",
        "seed": _TEST_SEED,
    }


def test_phase2_frozen_passage_is_not_shuffled_labels() -> None:
    frozen = build_phase2_arm(ARM_B, _TEST_SEED)
    both = build_phase2_arm(ARM_D, _TEST_SEED)
    assert PASSAGE_FROZEN == "frozen"
    assert frozen.passage == PASSAGE_FROZEN
    assert both.passage == PASSAGE_FROZEN
    assert frozen.passage != ANTAGONIST_PASSAGE_SHUFFLED_LABELS
    assert both.passage != ANTAGONIST_PASSAGE_SHUFFLED_LABELS
    # Phase-1 confirmatory arms stay on the old cut.
    assert build_arm(ARM_B, _TEST_SEED).passage == ANTAGONIST_PASSAGE_SHUFFLED_LABELS
    assert build_arm(ARM_D, _TEST_SEED).passage == ANTAGONIST_PASSAGE_SHUFFLED_LABELS
    statement = control_statement(ARM_B, phase=2)
    assert "frozen genotype" in statement
    assert "shuffled_labels is not a frozen genotype" in statement
    assert "PASSAGE_FROZEN" in statement
    phase1 = control_statement(ARM_B)
    assert "shuffled_labels" in phase1
    assert phase1 != statement


def test_host_freeze_does_not_empty_the_population_or_claim_a_pure_control() -> None:
    evolving = build_phase2_arm(ARM_A, _TEST_SEED)
    frozen = build_phase2_arm(ARM_C, _TEST_SEED)
    assert evolving.antagonist_pop is not None
    assert frozen.antagonist_pop is not None
    assert len(frozen._hosts()) == len(evolving._hosts()) > 0
    assert len(frozen.antagonist_pop.units) == len(evolving.antagonist_pop.units) > 0
    assert frozen.runner.configs.reproduction.enabled is False
    assert float(frozen.runner.configs.mutation.bit_flip_rate) == 0.0
    assert evolving.runner.configs.reproduction.enabled is True
    assert frozen.passage == PASSAGE_COEVOLVE
    assert float(frozen.antagonist_pop.mutation_rate) > 0.0
    text = control_statement(ARM_C, phase=2)
    assert "not a pure evolution control" in text
    assert text.count("pure evolution control") == 1
    both = control_statement(ARM_D, phase=2)
    assert "not a pure evolution control" in both
    assert "shuffled_labels is not a frozen genotype" in both
    assert "not a pure evolution control" in control_statement(ARM_C)


def test_four_arms_share_founders_and_do_not_share_a_rng_object() -> None:
    direct = StructuralRQArm.boot_structural(
        arm=ARM_COPASSAGED,
        seed=_TEST_SEED,
        antagonist_ecology=ANTAGONIST_ECOLOGY_POPULATION,
    )
    expected = founder_identity(direct)
    arms = {name: build_phase2_arm(name, _TEST_SEED) for name in ARMS}
    assert len(expected["hosts"]) > 0
    assert len(expected["parasites"]) > 0
    for arm in arms.values():
        assert founder_identity(arm) == expected
    assert arms[ARM_A].passage == PASSAGE_COEVOLVE
    assert arms[ARM_B].passage == PASSAGE_FROZEN
    assert arms[ARM_A].host_inheritance == "transmit"
    assert arms[ARM_C].host_inheritance == "frozen"
    assert "arm" not in inspect.signature(derive_stream_seed).parameters
    left = open_stream(EXPERIMENT_ID, str(_TEST_SEED), "host-step", 1)
    right = open_stream(EXPERIMENT_ID, str(_TEST_SEED), "host-step", 1)
    assert left is not right
    assert left.random() == right.random()
    arms[ARM_A].run_generations(1)
    arms[ARM_B].run_generations(1)
    assert arms[ARM_A].last_host_rng is not arms[ARM_B].last_host_rng


def test_missing_archive_field_and_contact_series_are_bugs() -> None:
    complete = _required_archive_record()
    assert archive_field_status(complete) == "ok"
    del complete["contacts"]
    assert archive_field_status(complete) == "archive-missing:contacts"
    arm = build_phase2_arm(ARM_A, _TEST_SEED)
    founders = {org.id for org in arm._hosts()}
    arm.run_generations(1)
    assert invariant_status(arm, generation=1, founder_ids=founders) == "ok"
    arm.graded_contact_count.pop()
    assert invariant_status(arm, generation=1, founder_ids=founders) == "contact-length"


def test_replay_matches_engine_debit_and_one_shot_matches_resume(tmp_path: Path) -> None:
    root = tmp_path / "short"
    root.mkdir()
    live = _Append(root / "live.log")
    dataset = _Append(root / "trajectory.jsonl")
    archive_path = root / "archive.jsonl"
    arm = build_phase2_arm(ARM_B, _TEST_SEED)
    try:
        with archive_path.open("w", encoding="utf-8") as handle:
            outcome = _run_logged_arm(
                arm,
                seed=_TEST_SEED,
                arm_name=ARM_B,
                generations=2,
                archive=handle,
                live=live,
                dataset=dataset,
                stop=root / "STOP",
            )
    finally:
        live.close()
        dataset.close()
    assert outcome["failed"] is None
    report = replay_phase2_archive(archive_path)
    assert report["matched"] is True
    assert int(report["compared_generations"]) == 2
    row = json.loads(archive_path.read_text(encoding="utf-8").splitlines()[0])
    assert row["passage"] == "frozen"
    paid = sum(float(item["atp"]) for item in row["contacts"])
    scored = replay_archived_contact(
        json.loads(json.dumps(row["contact_hosts"])),
        json.loads(json.dumps(row["contact_parasites"])),
        tick_index=int(row["contact_tick"]),
        seed=0,
    )
    assert scored["evolution"] is False
    assert scored["reproduction"] is False
    assert scored["mutation"] is False
    assert abs(float(scored["total_debit"]) - paid) < 1e-6
    assert abs(float(scored["credit"]) - float(row["contact_credit"])) < 1e-6
    resumed = build_phase2_arm(ARM_B, _TEST_SEED)
    one_shot = build_phase2_arm(ARM_B, _TEST_SEED)
    resumed.run_generations(1)
    resumed.run_generations(1)
    one_shot.run_generations(2)
    assert scientific_body(resumed) == scientific_body(one_shot)


def test_phase2_seed_lock_rejects_forbidden_histories(tmp_path: Path) -> None:
    assert_phase2_seeds(PHASE2_SEEDS)
    with pytest.raises(ConfigurationError, match="forbidden"):
        assert_phase2_seeds((9099,))
    with pytest.raises(ConfigurationError, match="forbidden"):
        assert_phase2_seeds((601, 602, 603))
    with pytest.raises(ConfigurationError, match="forbidden"):
        assert_phase2_seeds(tuple(range(9201, 9225)))
    with pytest.raises(ConfigurationError, match="locked"):
        assert_phase2_seeds((9301, 9302, 9303, 9305))
    with pytest.raises(ConfigurationError, match="workers"):
        _run_pool(tmp_path / "unused", workers=5)
