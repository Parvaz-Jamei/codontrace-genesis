"""Phase-4 fitness link. Expectations are computed here, not copied from a run.

Seeds 9501-9504 are not booted as measurement histories.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import replace
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import SexualRecombinationConfig
from codontrace.genesis.host_parasite_life_plugin import ROLE_PRIMARY, ROLE_SECONDARY, silence_outcross_locus
from codontrace.genesis.measurements.antagonist_population import AntagonistPopulation
from codontrace.genesis.organism import GenesisOrganism
from codontrace.genesis.population import PopulationState
from codontrace.genesis.rq_bidirectional_timeshift import ARM_A, build_arm
from codontrace.genesis.rq_bidirectional_timeshift_confirm import MEASUREMENT_FLOOR, VERDICT_BLOCKED
from codontrace.genesis.rq_mechanism_v2_phase2 import MAX_WORKERS as PHASE2_MAX_WORKERS
from codontrace.genesis.rq_mechanism_v2_phase3 import MAX_WORKERS as PHASE3_MAX_WORKERS
from codontrace.genesis.rq_mechanism_v2_phase4 import (
    BRANCH_ABSENT,
    BRANCH_COMMON_A,
    BRANCHES,
    GENOME_A,
    GENOME_B,
    NO_FITNESS_SENTENCE,
    PHASE4_HORIZON,
    PHASE4_SEEDS,
    PHASE4B_HORIZON,
    TEST_SEED,
    VERDICT_NOT_DECLARED,
    assert_phase4_seeds,
    assess_phase4,
    branch_archive_hash,
    build_phase4_arm,
    contact_without_demography,
    equal_host_seats,
    fitness_contrast,
    fitness_from_lineage,
    lineage_share,
    load_conditioned_parasites,
    locked_genomes,
    population_from_parasite_rows,
    render_phase4_lock,
    render_phase4b_lock,
    resolve_workers,
    run_fitness_branch,
)

PHASE3_ROOT = Path("runs/rq-mechanism-v2/phase3-frequency")


def _hand_founders() -> dict[str, str]:
    return {"a": "A", "b": "B"}


def _hand_parents() -> dict[str, str | None]:
    # a and b are founders. c and d are children of a. e is a child of b.
    return {"a": None, "b": None, "c": "a", "d": "a", "e": "b"}


def test_atp_drop_is_not_the_fitness_share() -> None:
    founders = _hand_founders()
    parents = _hand_parents()
    living = ["a", "b", "c", "d", "e"]
    # Three of five living ids walk to A (a, c, d). Two walk to B (b, e).
    hand_share_a = 3 / 5
    hand_share_b = 2 / 5
    heavy_loss = {"a": 1000.0, "b": 0.0, "c": 1000.0, "d": 1000.0, "e": 0.0}
    light_loss = {"a": 0.0, "b": 50.0, "c": 0.0, "d": 0.0, "e": 50.0}
    heavy = fitness_from_lineage(living, parents, founders, atp_loss=heavy_loss)
    light = fitness_from_lineage(living, parents, founders, atp_loss=light_loss)
    assert heavy == light
    assert heavy["share_A"] == pytest.approx(hand_share_a)
    assert heavy["share_B"] == pytest.approx(hand_share_b)
    assert heavy["n_A"] == 3
    assert heavy["n_B"] == 2
    atp_ratio = (1000.0 + 1000.0 + 1000.0) / (1000.0 * 3 + 0.0 + 0.0)
    assert heavy["share_A"] != pytest.approx(atp_ratio)
    assert heavy["share_A"] != pytest.approx(1.0)
    # A real one-class census is a measured zero, not a missing value.
    only_a = lineage_share(["a", "c"], parents, founders)
    assert only_a["share_A"] == pytest.approx(1.0)
    assert only_a["share_B"] == pytest.approx(0.0)
    assert only_a["share_B"] is not None
    # Nobody alive is missing, not zero.
    empty = lineage_share([], parents, founders)
    assert empty["share_A"] is None
    assert empty["share_A"] != 0.0
    # One unresolved id voids the share. It is not the share of the rest.
    unresolved = lineage_share(["a", "b", "z"], parents, founders)
    assert unresolved["share_A"] is None
    assert unresolved["share_A"] != pytest.approx(0.5)
    assert unresolved["n_unresolved"] == 1


def test_hand_contrast_does_not_use_the_absent_branch() -> None:
    # R(common A) = 0.25 - 0.75 = -0.5. R(common B) = 0.75 - 0.25 = 0.5.
    # F = -0.5 - 0.5 = -1. The absent advantage 0 is not an input.
    left = 0.25 - 0.75
    right = 0.75 - 0.25
    measured = fitness_contrast(0.25, 0.75, 0.75, 0.25)
    assert measured == pytest.approx(left - right)
    assert measured == pytest.approx(-1.0)
    assert fitness_contrast(None, 0.75, 0.75, 0.25) is None
    assert fitness_contrast(None, 0.75, 0.75, 0.25) != 0.0
    report = contact_without_demography(
        contacts_a=10,
        contacts_b=0,
        paid_a=4.0,
        paid_b=0.0,
        births_a={"A": 2, "B": 2},
        births_b={"A": 2, "B": 2},
        deaths_a={"A": 1, "B": 1},
        deaths_b={"A": 1, "B": 1},
    )
    assert report["contact_changed"] is True
    assert report["reproduction_changed"] is False
    assert report["survival_changed"] is False
    assert report["contact_without_demographic_change"] is True
    moved = contact_without_demography(
        contacts_a=10,
        contacts_b=0,
        paid_a=4.0,
        paid_b=0.0,
        births_a={"A": 3, "B": 1},
        births_b={"A": 1, "B": 3},
        deaths_a={"A": 1, "B": 1},
        deaths_b={"A": 1, "B": 1},
    )
    assert moved["contact_without_demographic_change"] is False
    assert moved["reproduction_changed"] is True


def test_recognition_mutation_off_and_reproduction_stays_on(tmp_path: Path) -> None:
    source = Path("runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9501/common_a/archive.jsonl")
    rows, _digest, generation = load_conditioned_parasites(source)
    assert generation == 7
    parasites = population_from_parasite_rows(rows)
    seats = equal_host_seats()
    assert sum(1 for seat in seats if seat["role_letter"] == "A") == 30
    assert sum(1 for seat in seats if seat["role_letter"] == "B") == 30
    assert seats[0]["host_id"] == "host-A-001"
    assert seats[0]["genome"] == GENOME_A
    assert seats[1]["genome"] == GENOME_B
    adapted = build_phase4_arm(TEST_SEED, BRANCH_COMMON_A, seats, parasites)
    assert adapted.runner.configs.reproduction.enabled is True
    assert adapted.runner.configs.reproduction.parent_atp_cost > 0.0
    assert adapted.runner.configs.mutation.bit_flip_rate == 0.0
    assert adapted.antagonist_pop.mutation_rate == 0.0
    assert adapted.passage == "coevolve"
    assert adapted.passage != "frozen"
    assert adapted.passage != "shuffled_labels"
    assert adapted.host_inheritance == "transmit"
    assert adapted.host_composition_hold is None
    absent = build_phase4_arm(TEST_SEED, BRANCH_ABSENT, seats, parasites)
    assert absent.passage == "absent"
    assert absent.runner.configs.reproduction.enabled is True
    assert absent.runner.configs.reproduction.parent_atp_cost > 0.0
    assert absent.host_inheritance == "transmit"
    archive = tmp_path / "common_a" / "archive.jsonl"
    summary = run_fitness_branch(
        seed=TEST_SEED,
        branch=BRANCH_COMMON_A,
        seats=seats,
        parasites=parasites,
        generations=1,
        archive_path=archive,
        source_sha256="0" * 64,
    )
    assert summary["failed"] is None
    assert summary["reproduction_enabled"] is True
    absent_archive = tmp_path / "absent" / "archive.jsonl"
    absent_summary = run_fitness_branch(
        seed=TEST_SEED,
        branch=BRANCH_ABSENT,
        seats=seats,
        parasites=parasites,
        generations=1,
        archive_path=absent_archive,
        source_sha256="0" * 64,
    )
    assert absent_summary["failed"] is None
    assert absent_summary["passage"] == "absent"
    absent_row = json.loads(absent_archive.read_text(encoding="utf-8").splitlines()[0])
    adapted_row = json.loads(archive.read_text(encoding="utf-8").splitlines()[0])
    assert absent_row["contacts"] == 0
    assert absent_row["host_atp_paid"] == 0.0
    assert absent_row["reproduction_enabled"] is True
    assert absent_row["parent_atp_cost"] > 0.0
    assert absent_row["host_bit_flip_rate"] == 0.0
    assert absent_row["parasite_mutation_events"] == 0
    assert adapted_row["parasite_mutation_events"] == 0
    assert adapted_row["host_bit_flip_rate"] == 0.0
    assert adapted_row["reproduction_enabled"] is True
    assert adapted_row["passage"] == "coevolve"
    assert adapted_row["red_queen_proved"] is False
    # Pairing is min(hosts, parasites). Both censuses are 60, and contact
    # counts a seat even when affinity is 0. Absent skips that loop.
    assert adapted_row["contacts"] == 60
    assert adapted_row["contacts"] != absent_row["contacts"]


def test_phase3_archive_bytes_are_unchanged_after_the_assay(tmp_path: Path) -> None:
    paths = [
        PHASE3_ROOT / "by_seed" / f"seed{seed}" / branch / "archive.jsonl"
        for seed in PHASE4_SEEDS
        for branch in ("common_a", "common_b")
    ]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    source = paths[0]
    rows, digest, generation = load_conditioned_parasites(source)
    assert generation == 7
    parasites = population_from_parasite_rows(rows)
    summary = run_fitness_branch(
        seed=TEST_SEED,
        branch=BRANCH_COMMON_A,
        seats=equal_host_seats(),
        parasites=parasites,
        generations=1,
        archive_path=tmp_path / "assay" / "archive.jsonl",
        source_sha256=digest,
    )
    assert summary["failed"] is None
    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    assert after == before


def test_incomplete_seed_list_is_blocked_measurement() -> None:
    assert MEASUREMENT_FLOOR == 12
    # Three contrasts and one missing seed. Their mean is -0.4.
    # Filling the hole with zero would move that mean to -0.3. Neither is a verdict.
    present_mean = (-0.2 + -0.5 + -0.5) / 3.0
    assert present_mean == pytest.approx(-0.4)
    imputed = (-0.2 + -0.5 + -0.5 + 0.0) / 4.0
    assert imputed == pytest.approx(-0.3)
    report = assess_phase4(
        {
            9501: {"F": -0.2},
            9502: {"F": -0.5},
            9503: {"F": -0.5},
        }
    )
    assert report["verdict"] == VERDICT_BLOCKED
    assert report["verdict"] == "BLOCKED_MEASUREMENT"
    assert report["verdict"] != "NEGATIVE_IN_MODEL"
    assert report["verdict"] != "SUPPORTED_IN_MODEL"
    assert report["n_locked"] == 4
    assert report["n_used"] == 3
    assert report["dropped_seeds"] == [9504]
    assert report["F_mean"] is None
    assert report["F_mean"] != present_mean
    assert report["F_mean"] != imputed
    assert report["importance_bound"] is None
    assert report["supported_forbidden"] is True
    assert report["mde_is_importance_bound"] is False
    assert report["measurement_floor"] == 12
    assert report["red_queen_proved"] is False
    missing = next(row for row in report["per_seed_status"] if row["seed"] == 9504)
    assert missing["F"] is None
    assert missing["F"] != 0.0


def test_complete_sample_is_not_declared_and_horizon_is_the_recorded_multiple() -> None:
    report = assess_phase4({seed: {"F": -1.0} for seed in PHASE4_SEEDS})
    assert report["n_locked"] == 4
    assert report["n_used"] == 4
    assert report["dropped_seeds"] == []
    assert report["F_mean"] == pytest.approx(-1.0)
    assert report["verdict"] == VERDICT_NOT_DECLARED
    assert report["verdict"] != "SUPPORTED_IN_MODEL"
    assert report["red_queen_proved"] is False
    # Ceiling of 3 * 60/26. Computed here, not read back from a fitness sign.
    assert math.ceil(3 * (60 / 26)) == 7
    assert PHASE4_HORIZON == 7
    assert PHASE4_HORIZON > 1
    assert resolve_workers(7) == 7
    with pytest.raises(ConfigurationError, match="workers"):
        resolve_workers(8)
    assert PHASE2_MAX_WORKERS == 4
    assert PHASE3_MAX_WORKERS == 7
    genomes = locked_genomes()
    assert genomes["genome_a"] == GENOME_A
    assert genomes["genome_b"] == GENOME_B
    text = render_phase4_lock(code_commit="a" * 40)
    assert NO_FITNESS_SENTENCE in text
    assert "9501, 9502, 9503, 9504" in text
    assert GENOME_A in text
    assert GENOME_B in text
    assert "undeclared" in text
    assert "SUPPORTED is forbidden" in text
    assert "at most 7" in text
    assert "not a pure evolution control" in text
    assert "shuffled_labels` is not a frozen genotype" in text
    assert re.search(r"F\s*=\s*-?\d", text) is None
    with pytest.raises(ConfigurationError, match="exactly"):
        assert_phase4_seeds([9501, 9502, 9503])
    lock = Path("runs/rq-mechanism-v2/PHASE3_LOCK.md").read_text(encoding="utf-8")
    assert "CPU workers at most 4." in lock


def test_one_child_is_accepted_on_the_engine_path(tmp_path: Path) -> None:
    source = PHASE3_ROOT / "by_seed" / "seed9501" / "common_a" / "archive.jsonl"
    rows, digest, _generation = load_conditioned_parasites(source)
    parasites = population_from_parasite_rows(rows)
    seats = equal_host_seats()
    arm = build_phase4_arm(TEST_SEED, BRANCH_ABSENT, seats, parasites)
    assert arm.runner.configs.sexual_recombination.uses_birth_chamber is True
    assert arm.runner.configs.reproduction.enabled is True
    assert arm.runner.configs.reproduction.parent_atp_cost > 0.0
    assert arm.runner.configs.mutation.bit_flip_rate == 0.0
    founders = {str(org.id) for org in arm.runner.population.organisms}
    arm.run_generations(1)
    living = list(arm.runner.population.organisms)
    children = [org for org in living if org.id not in founders]
    assert children, "a flag is not a child"
    child = children[0]
    assert child.id
    assert any(org.id == child.id for org in living)
    # Control: reproduction.enabled without the chamber still refuses.
    refused = build_phase4_arm(TEST_SEED, BRANCH_ABSENT, seats, parasites)
    refused.runner.configs = replace(
        refused.runner.configs,
        sexual_recombination=SexualRecombinationConfig(enabled=False),
    )
    assert refused.runner.configs.reproduction.enabled is True
    assert refused.runner.configs.sexual_recombination.uses_birth_chamber is False
    before = {str(org.id) for org in refused.runner.population.organisms}
    result = refused.runner.step_generation(seed=TEST_SEED)
    after = {str(org.id) for org in result.population.organisms}
    assert after == before
    assert result.births == 0
    reasons = []
    for trace in result.traces:
        for event in trace.events:
            if getattr(event, "action", None) != "COPY_SELF":
                continue
            delta = event.world_delta or {}
            if delta.get("reproduction_blocked_reason"):
                reasons.append(delta["reproduction_blocked_reason"])
    assert reasons
    assert set(reasons) == {"outcross_chamber_required"}
    archive = tmp_path / "birth" / "archive.jsonl"
    summary = run_fitness_branch(
        seed=TEST_SEED,
        branch=BRANCH_ABSENT,
        seats=seats,
        parasites=parasites,
        generations=1,
        archive_path=archive,
        source_sha256=digest,
    )
    assert summary["failed"] is None
    row = json.loads(archive.read_text(encoding="utf-8").splitlines()[0])
    born_ids = [item["id"] for item in row["parents"] if item["parent_id"]]
    assert born_ids
    assert row["births_A"] + row["births_B"] == len(born_ids)
    assert row["births_A"] + row["births_B"] > 0


def test_death_generation_comes_from_the_atp_ledger_not_from_a_helper() -> None:
    """No-food maximum debit. The expected generation is the ledger sum."""

    arm = build_arm(ARM_A, TEST_SEED)
    arm.resource_bolus_amount = 0.0
    arm.runner.world.resources.clear()
    configs = arm.runner.configs
    arm.runner.configs = replace(configs, mutation=replace(configs.mutation, bit_flip_rate=0.0))
    assert arm.runner.configs.sexual_recombination.uses_birth_chamber is False
    org = GenesisOrganism.from_bits(
        "host-A-001",
        GENOME_A,
        initial_runtime_atp=48.0,
        position=arm.food_patches[0],
    )
    silence_outcross_locus(org, arm.runner.configs.closed_loop_hp_life)
    arm.runner.population = PopulationState(
        generation=0,
        tick=0,
        organisms=(org,),
        lineage=(),
        fitness=(),
    )
    arm.roles = {"host-A-001": ROLE_PRIMARY, "parasite_stock": ROLE_SECONDARY}
    arm.antagonist_pop = AntagonistPopulation.founders(
        ["000000"],
        keep_fraction=0.5,
        mutation_rate=0.0,
    )
    arm.parasite_windows = ["000000"]
    arm.passage = "coevolve"
    opening = 48.0
    assert org.atp_state.runtime_available == opening
    death_at = None
    hand = opening
    credits = 0.0
    max_contact = 0.0
    for generation in range(1, 16):
        arm.runner.world.resources.clear()
        # Same order as run_generations: refill, life-loop, then contact debit.
        arm._apply_passage_refill()
        arm.runner.step_generation(seed=TEST_SEED + generation)
        watched = next(item for item in arm.runner.population.organisms if item.id == "host-A-001")
        arm._apply_hp_env_contact()
        hand = opening
        credits = 0.0
        max_contact = 0.0
        for entry in watched.atp_state.runtime.ledger:
            amount = float(entry.amount)
            if entry.kind == "credit":
                hand += amount
                credits += amount
            else:
                hand -= amount
                if entry.action == "HP_ENV_MATCH":
                    max_contact = max(max_contact, amount)
        assert abs(hand - float(watched.atp_state.runtime_available)) < 1e-9
        alive = any(item.id == "host-A-001" for item in arm._hosts())
        if hand <= 1e-12:
            death_at = generation
            assert alive is False
            break
        assert alive is True
        assert hand > 0.0
    assert credits == 0.0
    assert max_contact == pytest.approx(1.2)
    assert death_at is not None
    assert death_at > 7
    # Generation 7 of this account is still above zero. 60/26 is not the horizon.
    assert math.ceil(3 * (60 / 26)) == 7
    assert death_at != 7
    assert PHASE4B_HORIZON == death_at
    assert PHASE4_HORIZON == 7
    assert PHASE4_HORIZON != PHASE4B_HORIZON


def test_branch_archive_hashes_are_not_aliased() -> None:
    blobs = {
        BRANCH_COMMON_A: b"common-a-bytes",
        "common_b": b"common-b-bytes-differ",
        BRANCH_ABSENT: b"common-a-bytes",
    }
    file_sha = {key: hashlib.sha256(raw).hexdigest() for key, raw in blobs.items()}
    labels = {
        key: branch_archive_hash(key, file_sha[key], blobs[key])
        for key in BRANCHES
    }
    assert labels[BRANCH_COMMON_A] == file_sha[BRANCH_COMMON_A]
    assert labels["common_b"] == file_sha["common_b"]
    assert labels[BRANCH_COMMON_A] != labels["common_b"]
    assert labels[BRANCH_ABSENT] != labels[BRANCH_COMMON_A]
    assert len(set(labels.values())) == 3
    aliased = {key: labels[BRANCH_COMMON_A] for key in BRANCHES}
    assert len(set(aliased.values())) == 1
    assert labels != aliased
    # Real phase-3 files differ, so their labels must differ.
    paths = {
        branch: PHASE3_ROOT / "by_seed" / "seed9501" / branch / "archive.jsonl"
        for branch in ("common_a", "common_b")
    }
    raw = {branch: path.read_bytes() for branch, path in paths.items()}
    assert raw["common_a"] != raw["common_b"]
    real = {
        "common_a": branch_archive_hash("common_a", hashlib.sha256(raw["common_a"]).hexdigest(), raw["common_a"]),
        "common_b": branch_archive_hash("common_b", hashlib.sha256(raw["common_b"]).hexdigest(), raw["common_b"]),
        BRANCH_ABSENT: branch_archive_hash(
            BRANCH_ABSENT,
            hashlib.sha256(raw["common_a"]).hexdigest(),
            raw["common_a"],
        ),
    }
    assert len(set(real.values())) == 3
    text = render_phase4b_lock(code_commit="b" * 40)
    assert NO_FITNESS_SENTENCE in text
    assert "Fitness generations: 9" in text
    assert "per-generation debit cap is 1.2" in text
    assert "Opening runtime ATP is the structural birth ATP, 48." in text
    assert GENOME_A in text
    assert GENOME_B in text
    assert "at most 7" in text
    assert "phase4b-fitness" in text
    assert "not a pure evolution control" in text
    assert re.search(r"F\s*=\s*-?\d", text) is None
    with pytest.raises(ConfigurationError, match="inside"):
        from codontrace.genesis.rq_mechanism_v2_phase4 import assert_output_dir

        assert_output_dir(Path("runs/rq-mechanism-v2/phase4-fitness"), forbid_rejected_archive=True)
