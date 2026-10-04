"""Phase-1 gates. Two repeated histories are not twelve, and a label is not a witness."""

from __future__ import annotations

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.rq_mechanism_v2_phase5 import VERDICT_BLOCKED, VERDICT_NOT_DECLARED, VERDICT_SUPPORTED
from codontrace.genesis.rq_reciprocal_validity import assess_independent_histories

WINDOW_A = "000000"
WINDOW_B = "111111"


def _generation(generation: int, *, gap: float, births_a: int = 2, births_b: int = 1) -> dict[str, object]:
    births = [{"parent_window": WINDOW_A} for _ in range(births_a)]
    births += [{"parent_window": WINDOW_B} for _ in range(births_b)]
    return {
        "generation": generation,
        "host_births": births,
        "host_deaths": [],
        "selection_gap": gap,
        "start_windows": [WINDOW_A, WINDOW_A, WINDOW_B, WINDOW_B],
    }


def _history(seed: int, *, gap_start: float = 0.2, gap_end: float = -0.2) -> dict[str, object]:
    # The gap carries the seed so twelve histories are not one body repeated.
    return {
        "generations": [
            _generation(1, gap=gap_start + seed / 100000.0),
            _generation(2, gap=gap_end - seed / 100000.0),
        ],
        "history_id": f"hist-{seed}",
        "reversal": True,
        "fitness_measured": False,
        "seed": seed,
    }


def test_boolean_label_cannot_declare_and_repeated_histories_cannot_fill_n() -> None:
    seeds = list(range(9911, 9923))
    one = _history(9911)
    other = _history(9912, gap_start=-0.4, gap_end=0.4)
    other["history_id"] = "hist-9912"
    with pytest.raises(ConfigurationError, match="duplicate history"):
        assess_independent_histories([one, dict(one)], seeds, importance_bound=0.2)
    cloned = dict(one)
    cloned["seed"] = 9912
    cloned["history_id"] = "hist-copy"
    with pytest.raises(ConfigurationError, match="duplicate history"):
        assess_independent_histories([one, cloned], seeds, importance_bound=0.2)
    relabeled = dict(one)
    with pytest.raises(ConfigurationError, match="duplicate history_id"):
        assess_independent_histories([one, relabeled], seeds, importance_bound=None)
    doubled = list(seeds) + [9911]
    with pytest.raises(ConfigurationError, match="duplicate seeds"):
        assess_independent_histories([_history(seed) for seed in seeds], doubled, importance_bound=None)
    broken = _history(9911)
    broken["generations"] = list(broken["generations"]) + [dict(broken["generations"][0])]
    with pytest.raises(ConfigurationError, match="duplicate generations"):
        assess_independent_histories([broken], seeds, importance_bound=None)


def test_label_only_history_is_not_a_valid_sample_and_cannot_prove_red_queen() -> None:
    seeds = list(range(9911, 9923))
    labeled = []
    for seed in seeds:
        labeled.append(
            {
                "fitness_measured": True,
                "generations": [{"generation": 1, "selection_gap": float(seed)}],
                "history_id": f"label-{seed}",
                "reversal": True,
                "seed": seed,
            }
        )
    report = assess_independent_histories(labeled, seeds, importance_bound=0.2)
    assert report["n_independent"] == 0
    assert report["n_independent"] != 12
    assert report["verdict"] == VERDICT_BLOCKED
    assert report["interval"] is None
    assert report["red_queen_proved"] is False
    assert report["used_boolean_label"] is False
    full = [_history(seed) for seed in seeds]
    scored = assess_independent_histories(full, seeds, importance_bound=None)
    assert scored["n_independent"] == 12
    assert scored["measurement_floor"] == 12
    assert scored["verdict"] != VERDICT_SUPPORTED
    assert scored["supported_forbidden"] is True
    assert scored["red_queen_proved"] is False
    # Every archived gap changes sign, so the rate is 12/12. Importance is still required.
    declared = assess_independent_histories(full, seeds, importance_bound=0.5)
    assert declared["reversal_true_n"] == 12
    assert declared["interval"]["lower"] > 0.5
    assert declared["interval"]["upper"] == 1.0
    assert declared["verdict"] == VERDICT_SUPPORTED
    assert declared["red_queen_proved"] is False
    assert declared["verdict"] != VERDICT_NOT_DECLARED


def test_adaptation_cut_hold_keeps_state_and_balances_energy() -> None:
    from dataclasses import replace as dc_replace

    from codontrace.genesis.organism import GenesisOrganism
    from codontrace.genesis.rq_mechanism_v2_phase4 import GENOME_B, WINDOW_B
    from codontrace.genesis.rq_mechanism_v2_phase5 import ARM_ADAPTATION_CUT, build_phase5_arm
    from codontrace.genesis.rq_reciprocal_validity import TARGET_QUANTITY

    arm = build_phase5_arm(ARM_ADAPTATION_CUT, 9592)
    host = arm._hosts()[0]
    host.atp_state.debit_runtime(
        1.25,
        tick=0,
        organism_id=host.id,
        codon="000",
        action="HOLD_CHECK",
        reason="state preservation",
    )
    host._step_index = 7
    host._cursor = 3
    host.position = arm.food_patches[-1]
    digest_before = host.atp_state.ledger_digest()
    atp_before = float(host.atp_state.runtime_available)
    assert arm.host_composition_hold is not None
    scratch = GenesisOrganism.from_bits(host.id + ":scratch", GENOME_B, initial_runtime_atp=0.0, position=host.position)
    assert scratch  # genome B decodes
    from codontrace.genesis.closed_loop_hp_arm01 import _window

    host.genome = scratch.genome
    host.ribosome = scratch.ribosome
    host.compiled_brain = scratch.compiled_brain
    assert _window(host) == WINDOW_B
    arm.host_composition_hold(arm)
    again = next(org for org in arm._hosts() if org.id == host.id)
    assert again is host
    assert float(again.atp_state.runtime_available) == pytest.approx(atp_before)
    assert again.atp_state.ledger_digest() == digest_before
    assert again._step_index == 7
    assert again._cursor == 3
    assert again.position == arm.food_patches[-1]
    assert arm.energy_account["kind"] == "hold_founder_genotypes"
    assert arm.energy_account["target_quantity"] == TARGET_QUANTITY
    assert arm.energy_account["exits"] == 0.0
    kinds = [item["kind"] for item in arm.intervention_ledger]
    assert "genotype_restore" in kinds
    assert "energy_resupply" not in kinds
    extra = GenesisOrganism.from_bits(
        "host-extra-001",
        GENOME_B,
        initial_runtime_atp=2.5,
        position=arm.food_patches[0],
    )
    extra.atp_state.debit_runtime(
        0.5,
        tick=1,
        organism_id=extra.id,
        codon="000",
        action="EXIT_CHECK",
        reason="exit energy",
    )
    arm.runner.population = dc_replace(
        arm.runner.population,
        organisms=tuple(arm.runner.population.organisms) + (extra,),
    )
    arm.host_composition_hold(arm)
    exit_lines = [item for item in arm.intervention_ledger if item["kind"] == "population_exit"]
    assert [item["host_id"] for item in exit_lines] == ["host-extra-001"]
    assert exit_lines[0]["energy_out"] == pytest.approx(2.0)
    assert arm.energy_account["exits"] == pytest.approx(2.0)
    balance = arm.energy_account["sum_before"] - arm.energy_account["exits"] + arm.energy_account["entries"]
    assert arm.energy_account["sum_after"] == pytest.approx(balance)
    assert all(org.id != extra.id for org in arm._hosts())


def test_only_an_id_swap_is_classified_as_moving_births() -> None:
    from codontrace.genesis.rq_mechanism_v2_phase4 import equal_host_seats
    from codontrace.genesis.rq_reciprocal_validity import swapped_seats, which_swap_moves

    seats = equal_host_seats()
    renamed = swapped_seats("ids", seats)
    assert renamed[0]["host_id"].startswith("host-B-")
    assert renamed[0]["window"] == seats[0]["window"]
    genomes = swapped_seats("genome_background", seats)
    assert genomes[0]["host_id"] == seats[0]["host_id"]
    assert genomes[0]["window"] != seats[0]["window"]
    food = swapped_seats("food_access", seats)
    assert food[0]["role_letter"] == "B"
    assert food[0]["host_id"].startswith("host-B-")
    moved = which_swap_moves(
        {"births_A": 4, "births_B": 0},
        {
            "processing_order": {"births_A": 4, "births_B": 0},
            "ids": {"births_A": 0, "births_B": 4},
            "position": {"births_A": 4, "births_B": 0},
        },
    )
    assert moved["moved"] == ["ids"]
