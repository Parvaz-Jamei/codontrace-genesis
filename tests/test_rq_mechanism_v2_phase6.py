"""Phase-6 gates. The 34/30 rule is computed here, not copied from a claim."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.rq_mechanism_v2_phase4 import (
    BRANCH_ABSENT,
    GENOME_A,
    GENOME_B,
    WINDOW_A,
    WINDOW_B,
    build_phase4_arm,
    equal_host_seats,
    load_conditioned_parasites,
    population_from_parasite_rows,
    run_fitness_branch,
)
from codontrace.genesis.rq_mechanism_v2_phase5 import NO_CONFIRMATORY_SENTENCE, resolve_workers
from codontrace.genesis.rq_mechanism_v2_phase6 import (
    PHASE6_BUDGET,
    PHASE6_PROBE_GENERATIONS,
    absent_baseline_rule,
    choose_phase6_horizon,
    exploratory_direction_scan,
    fitness_kinds,
    fitness_response_delay,
    food_seat_symmetry,
    locked_phase6_seeds,
    phase6_worker_cap,
    pressure_contrast,
    reanalyze_phase5b_reversals,
    registered_oscillation,
    render_phase5b_reanalysis,
    render_phase6_confirm_lock,
    render_phase6_lock,
    replacement_time,
    score_phase6_archive,
    selection_direction,
    shared_paired_estimand,
)


def test_horizon_is_not_three_times_parasite_replacement() -> None:
    chosen = choose_phase6_horizon(parasite_replacement=2.4, host_replacement=9.0, fitness_delay=4.0)
    assert chosen["horizon"] == 9
    assert chosen["horizon"] != math_ceil_three(2.4)
    assert chosen["primary_lag"] == 2
    assert chosen["turnover_multiple_used"] is False
    assert chosen["not_three_times_parasite_replacement"] is True
    missing = choose_phase6_horizon(parasite_replacement=2.4, host_replacement=5.0, fitness_delay=None)
    assert missing["fitness_delay"] is None
    assert missing["fitness_delay_unmeasurable"] is True
    assert missing["horizon"] == 5
    with pytest.raises(ConfigurationError, match="not shortened"):
        choose_phase6_horizon(parasite_replacement=2.0, host_replacement=80.0, fitness_delay=None)
    with pytest.raises(ConfigurationError, match="positive"):
        choose_phase6_horizon(parasite_replacement=0.0, host_replacement=2.0, fitness_delay=None)
    with pytest.raises(ConfigurationError, match="registered budget"):
        choose_phase6_horizon(parasite_replacement=2.0, host_replacement=4.0, fitness_delay=None, budget=16)
    assert PHASE6_BUDGET == 70
    recorded = choose_phase6_horizon(
        parasite_replacement=2.9201520912547525,
        host_replacement=69.54545454545455,
        fitness_delay=9,
    )
    assert recorded["horizon"] == 70
    assert recorded["budget"] == 70
    assert recorded["primary_lag"] == 3
    assert recorded["horizon"] != math_ceil_three(2.9201520912547525)
    assert phase6_worker_cap(7) == 7
    with pytest.raises(ConfigurationError):
        resolve_workers(8)
    seeds = locked_phase6_seeds()
    assert list(seeds) == list(range(9811, 9823))
    assert not (set(seeds) & set(range(9701, 9713)))
    assert not (set(seeds) & set(range(9601, 9613)))


def math_ceil_three(replacement: float) -> int:
    import math

    return math.ceil(3 * replacement)


def test_paired_estimand_separates_host_and_parasite_effects() -> None:
    hosts_now = [{"window": "000000"}, {"window": "000000"}]
    hosts_past = [{"window": "000000"}, {"window": "000000"}]
    parasites_now = [{"window": "000000"}, {"window": "000000"}]
    parasites_past = [{"window": "111111"}, {"window": "111111"}]
    scored = shared_paired_estimand(hosts_now, hosts_past, parasites_now, parasites_past)
    assert scored["paired"] == pytest.approx(scored["host_effect"] + scored["parasite_effect"])
    assert scored["diagnostic_mixed_into_paired"] is False
    assert scored["diagnostic_host_on_contemporary_parasites"] != scored["paired"]


def test_one_sign_change_is_not_a_continuing_cycle() -> None:
    rows = []
    for generation, sign in ((4, 1), (7, -1), (10, -1)):
        rows.append(
            {
                "contact_ok": True,
                "direction": sign,
                "generation": generation,
                "genotypes_present": True,
            }
        )
    scored = registered_oscillation(rows, horizon=10, lag=3)
    assert scored["one_sign_change_is_not_a_cycle"] is True
    assert scored["continuing_cycle"] is False
    assert scored["exploratory"] is False
    rows[2]["direction"] = 1
    cycle = registered_oscillation(rows, horizon=10, lag=3)
    assert cycle["continuing_cycle"] is True
    assert cycle["direction_changes"] == [7, 10]
    infectivity_only = selection_direction(
        ancestry_fitness_a=None,
        ancestry_fitness_b=None,
        contact=1.0,
        genotype_a_present=True,
        genotype_b_present=True,
        infectivity_gap=0.2,
    )
    assert infectivity_only["direction"] is None
    assert infectivity_only["infectivity_used_as_selection"] is False
    no_contact = selection_direction(
        ancestry_fitness_a=1.2,
        ancestry_fitness_b=0.4,
        contact=0.0,
        genotype_a_present=True,
        genotype_b_present=True,
    )
    assert no_contact["direction"] is None
    scan = exploratory_direction_scan([1, -1, 1, -1])
    assert scan["exploratory"] is True
    assert scan["confirmatory"] is False
    early = registered_oscillation(
        [{"generation": 2, "direction": 1, "contact_ok": True, "genotypes_present": True}],
        horizon=4,
        lag=3,
    )
    assert early["unmeasurable"] is True
    assert early["continuing_cycle"] is False


def test_absent_baseline_rule_is_id_order_not_food_headcount() -> None:
    ids = [f"host-A-{index:03d}" for index in range(1, 31)] + [f"host-B-{index:03d}" for index in range(1, 31)]
    ruled = absent_baseline_rule(ids)
    assert ruled["alive_A"] == 34
    assert ruled["alive_B"] == 30
    assert ruled["births_A"] == 4
    assert ruled["births_B"] == 0
    swapped = [f"host-B-{index:03d}" for index in range(1, 31)] + [f"host-A-{index:03d}" for index in range(1, 31)]
    # Same multiset of ids. The rule follows the sorted name, which is still A first.
    assert absent_baseline_rule(swapped)["births_A"] == 4
    renamed = []
    a_count = 0
    for item in ids:
        if "-A-" in item:
            a_count += 1
            renamed.append(f"host-M-{a_count:03d}")
        else:
            renamed.append(item.replace("-B-", "-A-"))
    # Former B ids are now host-A and sort first. Former A ids are host-M and are not reached.
    flipped = absent_baseline_rule(renamed)
    assert flipped["births_A"] == 4
    assert flipped["births_B"] == 0
    assert sorted(renamed)[0].startswith("host-A-")
    food = food_seat_symmetry()
    assert food["headcount_equal"] is True
    assert food["class_counts"] == {"A": 30, "B": 30}
    assert food["even_patches_are_only_A"] is True
    assert food["odd_patches_are_only_B"] is True
    kinds = fitness_kinds(ancestry_a=1.5, ancestry_b=0.5, current_a=0.5, current_b=1.5)
    assert kinds["ancestry_gap"] == pytest.approx(1.0)
    assert kinds["current_genotype_gap"] == pytest.approx(-1.0)
    assert kinds["current_substituted_for_ancestry"] is False
    pressure = pressure_contrast(
        absent_contacts=0,
        absent_births={"A": 4, "B": 0},
        absent_deaths={"A": 0, "B": 0},
        pressured_contacts=540,
        pressured_births={"A": 4, "B": 0},
        pressured_deaths={"A": 21, "B": 1},
    )
    assert pressure["baseline_is_pressure"] is False
    assert pressure["deaths_differ"] is True
    delay = fitness_response_delay([1, 1, 1], [1, -1, -1])
    assert delay["delay"] == 2
    none = fitness_response_delay([1, 1], [1, 1])
    assert none["measurable"] is False
    assert none["delay"] is None
    blocked = replacement_time([0, 0], [60, 60])
    assert blocked["measurable"] is False
    assert blocked["replacement"] is None
    opened = replacement_time([4, 4], [64, 64])
    assert opened["replacement"] == pytest.approx(16.0)


def test_phase5b_reanalysis_keeps_the_boundary_and_does_not_rerun() -> None:
    result = reanalyze_phase5b_reversals()
    assert result["analysis"] == "REANALYSIS"
    assert result["fresh_confirmation"] is False
    assert result["seeds_rerun"] is False
    assert result["seeds"] == list(range(9701, 9713))
    assert result["reversal_true_n"] == 0
    assert result["n_used"] == 12
    assert result["red_queen_proved"] is False
    assert result["claim_a_mean_archived"] == pytest.approx(0.002210517787016947)
    interval = result["reversal_interval"]
    assert interval["lower"] == 0.0
    assert interval["upper"] < 0.5
    assert interval["p_two_sided"] == pytest.approx(2.0 / 4096.0)
    assert interval["p_one_sided"] != 0.0
    assert interval["wald_se_zero"] is True
    assert result["wald_p_was_null"] is True
    text = render_phase5b_reanalysis(result)
    assert "REANALYSIS" in text
    assert "9701" in text or "Seeds 9701" in text
    assert "red_queen_proved" in text
    design = choose_phase6_horizon(parasite_replacement=2.2, host_replacement=8.0, fitness_delay=None)
    design["seeds"] = list(locked_phase6_seeds())
    lock = render_phase6_lock(design, code_commit="abc123")
    assert lock.splitlines()[2] == NO_CONFIRMATORY_SENTENCE
    assert lock.strip().splitlines()[-1] == NO_CONFIRMATORY_SENTENCE
    assert "not three times" in lock
    assert "9811" in lock and "9822" in lock
    assert "workers" in lock and "7" in lock
    assert PHASE6_PROBE_GENERATIONS == 12


def test_live_absent_generation_follows_the_id_order_rule(tmp_path: Path) -> None:
    source = Path("runs/rq-mechanism-v2/phase3-frequency/by_seed/seed9501/common_a/archive.jsonl")
    rows, _digest, generation = load_conditioned_parasites(source)
    assert generation == 7
    parasites = population_from_parasite_rows(rows)
    seats = equal_host_seats()
    ids = [seat["host_id"] for seat in seats]
    predicted = absent_baseline_rule(ids)
    archive = tmp_path / "absent" / "archive.jsonl"
    summary = run_fitness_branch(
        seed=9491,
        branch=BRANCH_ABSENT,
        seats=seats,
        parasites=parasites,
        generations=1,
        archive_path=archive,
        source_sha256="0" * 64,
    )
    assert summary["failed"] is None
    row = json.loads(archive.read_text(encoding="utf-8").splitlines()[0])
    assert row["contacts"] == 0
    assert row["alive_end_A"] == predicted["alive_A"] == 34
    assert row["alive_end_B"] == predicted["alive_B"] == 30
    assert row["births_A"] == 4
    assert row["births_B"] == 0
    assert row["deaths_A"] == 0 and row["deaths_B"] == 0
    parents = {item["id"]: item["parent_id"] for item in row["parents"]}
    children = [item_id for item_id, parent in parents.items() if parent]
    assert len(children) == 4
    assert [parents[item] for item in children] == ["host-A-001", "host-A-002", "host-A-003", "host-A-004"]
    # Name swap. Window B is named host-A so it sorts first. The extra births follow the name.
    swapped = []
    counts = {"A": 0, "B": 0}
    for seat in seats:
        letter = str(seat["role_letter"])
        other = "B" if letter == "A" else "A"
        counts[other] += 1
        swapped.append(
            {
                "genome": GENOME_B if letter == "A" else GENOME_A,
                "host_id": f"host-{other}-{counts[other]:03d}",
                "role_letter": letter,
                "window": WINDOW_B if letter == "A" else WINDOW_A,
            }
        )
    # role_letter stays with the original class. The name and the window move together above,
    # which would confound name with window. Rebuild so the window stays and only the name moves.
    named = []
    counts = {"A": 0, "B": 0}
    for seat in seats:
        letter = str(seat["role_letter"])
        other = "B" if letter == "A" else "A"
        counts[other] += 1
        named.append(
            {
                "genome": seat["genome"],
                "host_id": f"host-{other}-{counts[other]:03d}",
                "role_letter": letter,
                "window": seat["window"],
            }
        )
    arm = build_phase4_arm(9491, BRANCH_ABSENT, named, parasites)
    assert [org.id for org in arm._hosts()[:2]] == ["host-B-001", "host-A-001"]
    archive_b = tmp_path / "swapped" / "archive.jsonl"
    swapped_summary = run_fitness_branch(
        seed=9491,
        branch=BRANCH_ABSENT,
        seats=named,
        parasites=parasites,
        generations=1,
        archive_path=archive_b,
        source_sha256="0" * 64,
    )
    assert swapped_summary["failed"] is None
    swapped_row = json.loads(archive_b.read_text(encoding="utf-8").splitlines()[0])
    # Founder class A still has window A, but its ids are host-B and sort later.
    assert swapped_row["births_A"] == 0
    assert swapped_row["births_B"] == 4
    assert swapped_row["alive_end_A"] == 30
    assert swapped_row["alive_end_B"] == 34
    del swapped


def test_confirm_lock_opens_with_the_sentence_and_scores_prelim_without_a_new_probe() -> None:
    recorded = choose_phase6_horizon(
        parasite_replacement=2.9201520912547525,
        host_replacement=69.54545454545455,
        fitness_delay=9,
    )
    recorded["seeds"] = list(locked_phase6_seeds())
    text = render_phase6_confirm_lock(recorded, code_commit="066fa3da1e64c2d7f77319052fc3d93fb7c1131a")
    assert text.startswith("No confirmatory number has been computed.")
    assert "Papkou et al. 2019" in text
    assert "10.1073/pnas.1810402116" in text
    assert "PMC2867683" in text
    assert "not a parameter tune" in text
    assert "9811" in text and "9822" in text
    assert '"horizon": 70' in text
    assert '"budget": 70' in text
    assert '"workers": 7' in text
    rows = []
    archive = Path("runs/rq-mechanism-v2/phase6-prelim-3/by_seed/seed9807/archive.jsonl")
    for line in archive.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    scored = score_phase6_archive(rows, lag=3, horizon=12)
    assert scored["accounting_error"] is None
    assert scored["red_queen_proved"] is False
    assert scored["oscillation"]["exploratory"] is False
    assert scored["exploratory_scan"]["confirmatory"] is False
