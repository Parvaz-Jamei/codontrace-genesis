"""P0.1 separation proof: parasite class frequency is not host pressure.

Directive ``rq-redesign-20260928/DIRECTIVE_FA.md`` P0 item 1 demands two
separately stored quantities:

* ``parasite_class_hist`` — a **parasite class frequency** (counts of
  antagonist match classes), and
* ``host_realised_pressure`` / ``realised_conditional_host_pressure`` — the
  pressure actually realised on a host class by the contact rule (graded
  affinity → ATP debit → survival) under equal exposure.

The discrimination tests below hold one fixed while varying the other.
Nothing here changes a pre-registered threshold or a recorded number: the new
quantity is additive and opt-in.
"""

from __future__ import annotations

from codontrace.genesis.closed_loop_hp_arm01 import ARM_COPASSAGED, ARM_FIXED
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    STRUCT_VIRULENCE,
    StructuralRQArm,
    graded_affinity,
    host_realised_pressure_from_contacts,
    joint_match_class,
)
from codontrace.genesis.measurements.rq_frequency_clocks import (
    CONTACT_MODE_ENGINE_SEATS,
    CONTACT_MODE_FULL_MATRIX,
    affinity_matrix,
    lagged_nfds_score,
    parasite_class_frequency_from_hist,
    realised_conditional_host_pressure,
    reference_graded_affinity,
)

# Recognition windows used by the fixtures (3 sub-loci × 2 bits).
H_A = "000000"  # sub-loci 00|00|00
H_B = "000011"  # sub-loci 00|00|11
H_C = "111000"  # sub-loci 11|10|00
P_STRONG = "110000"  # sub-loci 11|00|00
P_MILD = "100000"  # sub-loci 10|00|00

# Contact-quality matrix used by the discrimination fixture.
# A(000000, 110000) = 4/6   A(000000, 100000) = 5/6
# A(000011, 110000) = 2/6   A(000011, 100000) = 3/6
# A(111000, 110000) = 3/6   A(111000, 100000) = 1/6
A_H_A_STRONG, A_H_A_MILD = 4 / 6, 5 / 6
A_H_B_STRONG, A_H_B_MILD = 2 / 6, 3 / 6
A_H_C_STRONG, A_H_C_MILD = 3 / 6, 1 / 6

EPS = 1e-9
KAPPA = STRUCT_VIRULENCE * 0.15  # 1.2 ATP per unit affinity, pre-registered locks


def _histogram_from_counts(counts: dict[str, int]) -> dict[str, float]:
    """Parasite class frequency histogram (class → share), total sums to 1."""

    return parasite_class_frequency_from_hist({k: float(v) for k, v in counts.items()})


def _sum_pressure(pressure: dict[str, float]) -> float:
    return sum(pressure.values())


# --- Contact-law reference ---------------------------------------------------


def test_reference_affinity_matches_engine_graded_affinity() -> None:
    """The measurement-side mirror must equal the engine contact rule exactly."""

    windows = (
        "000000",
        "000001",
        "000011",
        "001100",
        "100000",
        "110000",
        "101010",
        "010101",
        "111111",
        "111000",
    )
    for h in windows:
        for p in windows:
            assert abs(reference_graded_affinity(h, p) - graded_affinity(h, p)) < EPS, (
                h,
                p,
            )


def test_affinity_matrix_is_full_host_by_parasite_matrix() -> None:
    matrix = affinity_matrix({"a": H_A, "b": H_B}, {"strong": P_STRONG, "mild": P_MILD})
    assert set(matrix) == {"a", "b"}
    assert set(matrix["a"]) == {"strong", "mild"}
    assert abs(matrix["a"]["strong"] - A_H_A_STRONG) < EPS  # 00,00,00 vs 11,00,00
    assert abs(matrix["a"]["mild"] - A_H_A_MILD) < EPS  # 00,00,00 vs 10,00,00
    assert abs(matrix["b"]["strong"] - A_H_B_STRONG) < EPS  # 00,00,11 vs 11,00,00
    assert abs(matrix["b"]["mild"] - A_H_B_MILD) < EPS  # 00,00,11 vs 10,00,00


# --- P0.1(a): histogram constant, realised contact effect differs ------------


def _discrimination_scenario() -> dict[str, object]:
    """Three host worlds with one shared parasite class histogram.

    Contact-quality matrix on these windows (κ = virulence × steal_fraction
    = 1.2; all values verified against ``graded_affinity``):

        A(H1 = 000000, P_STRONG = 110000) = 4/6   A(H1, P_MILD = 100000) = 5/6
        A(H2 = 000011, P_STRONG)          = 2/6   A(H2, P_MILD)          = 3/6
        A(H3 = 111000, P_STRONG)          = 3/6   A(H3, P_MILD)          = 1/6

    World 1 — host class ``H1``, reserve 1.0:

        mean affinity = (4/6 + 5/6)/2 = 9/12
        realised      = (min[1, 0.8] + min[1, 1.0]) / 2 = 0.90

    World 2 — host class ``H2``, same histogram, same exposure, same reserve:

        mean affinity = (2/6 + 3/6)/2 = 5/12
        realised      = (min[1, 0.4] + min[1, 0.6]) / 2 = 0.50

    World 3 — ``H3``: the affinity sits on the lethal contact.

        mean affinity = (3/6 + 1/6)/2 = 4/12
        realised      = (min[1, 0.6] + min[1, 0.2]) / 2 = 0.40

    Every world carries the **same** parasite class histogram
    ``{strong: 0.5, mild: 0.5}``, the same equal exposure (2 contacts, one per
    parasite class), and the same host reserve; only the affinity realised per
    contact differs, and the survival branch flips with it (H1 pays 1.0 = its
    whole reserve on P_MILD, H2 and H3 do not).
    """

    counts = {"strong": 1, "mild": 1}
    hist = _histogram_from_counts(counts)
    common: dict[str, object] = {
        "parasite_class_counts": counts,
        "affinity": {
            "H1": {"strong": A_H_A_STRONG, "mild": A_H_A_MILD},
            "H2": {"strong": A_H_B_STRONG, "mild": A_H_B_MILD},
            "H3": {"strong": A_H_C_STRONG, "mild": A_H_C_MILD},
        },
        "host_capacity_units": 1.0,
    }
    windows = {"H1": H_A, "H2": H_B, "H3": H_C}
    worlds = {
        key: realised_conditional_host_pressure(
            {key: windows[key]},
            {"strong": P_STRONG, "mild": P_MILD},
            contact_mode=CONTACT_MODE_FULL_MATRIX,
            **common,
        )
        for key in ("H1", "H2", "H3")
    }
    return {"hist": hist, **worlds}


def test_histogram_constant_while_realised_contact_effect_differs() -> None:
    """Only the new quantity sees the difference; the histogram series is blind."""

    scenario = _discrimination_scenario()
    hist: dict[str, float] = scenario["hist"]  # type: ignore[assignment]
    world1 = scenario["H1"]  # type: ignore[assignment]
    world2 = scenario["H2"]  # type: ignore[assignment]
    world3 = scenario["H3"]  # type: ignore[assignment]

    # Same parasite class histogram in all worlds.
    assert hist == {"strong": 0.5, "mild": 0.5}
    assert abs(sum(hist.values()) - 1.0) < EPS

    p1, p2, p3 = world1["pressure"], world2["pressure"], world3["pressure"]
    a1, a2, a3 = (
        world1["affinity_sum"],
        world2["affinity_sum"],
        world3["affinity_sum"],
    )

    # New quantity: real, rule-derived ATP number, computed without the histogram.
    assert world1["histogram_used"] is False
    assert world2["histogram_used"] is False
    assert world3["histogram_used"] is False
    assert world1["pressure_units"] == "atp_per_host_per_generation"
    assert abs(a1["H1"] - 9 / 12) < EPS
    assert abs(a2["H2"] - 5 / 12) < EPS
    assert abs(a3["H3"] - 4 / 12) < EPS
    assert abs(p1["H1"] - 0.90) < EPS
    assert abs(p2["H2"] - 0.50) < EPS
    assert abs(p3["H3"] - 0.40) < EPS
    assert abs(p1["H1"] - p2["H2"]) > EPS  # histogram equal, pressure differs
    assert abs(p1["H1"] - p3["H3"]) > EPS
    assert len({p1["H1"], p2["H2"], p3["H3"]}) == 3
    # Decomposition: in all three worlds the per-contact rule stays below the
    # reserve except on H1's P_MILD contact, where min[1.0, κ·5/6] = 1.0 = the
    # whole reserve. The realised pressure is the mean of those per-contact
    # min-terms, i.e. an effect capping, not an affinity or class count.
    assert abs(p1["H1"] - (0.8 + 1.0) / 2) < EPS
    assert abs(p1["H1"] - KAPPA * a1["H1"]) < EPS  # no saturation loss yet (0.9 < 1.2)
    assert abs(p2["H2"] - KAPPA * a2["H2"]) < EPS
    assert abs(p3["H3"] - KAPPA * a3["H3"]) < EPS
    assert abs(world1["affinity_sum"]["H1"] - 0.75) < EPS

    # Survival branch: H1's P_MILD contact consumes its whole reserve (lethal
    # branch), so one of its two contacts kills; H2/H3 pay less than their
    # reserve on every contact and survive the round.
    assert abs(world1["survival_fraction"]["H1"] - 0.5) < EPS
    assert abs(world2["survival_fraction"]["H2"] - 1.0) < EPS
    assert abs(world3["survival_fraction"]["H3"] - 1.0) < EPS

    # The histogram-based statistic is blind: its only dynamic input is the
    # parasite class frequency map, identical in every world.
    scores = []
    for host_class, snap_pressure in (("H1", p1), ("H2", p2), ("H3", p3)):
        dense = {
            g: {
                "joint_freq": {host_class: 1.0},
                "parasite_class_hist": dict(hist),
                "host_realised_pressure": dict(snap_pressure),
            }
            for g in range(25)
        }
        scores.append(
            lagged_nfds_score(
                {g: s["joint_freq"] for g, s in dense.items()},
                {g: s["parasite_class_hist"] for g, s in dense.items()},
                lag=4,
                min_points=20,
            )
        )
    assert scores[0] == scores[1] == scores[2]
    # The class sets never intersect (host class H* vs parasite classes
    # strong/mild), so the paired series is the degenerate x ∈ {1, 0, 0} vs
    # y ∈ {0, 0.5, 0.5} pattern repeated per generation: n = 21 pairs × 3 union
    # classes. Every world produces that identical pattern from its identical
    # histogram, so the statistic is constant across worlds and reports a
    # spurious -1.0 correlation that describes class-key overlap, not pressure.
    assert all(s["n"] == 63 for s in scores)
    assert all(s["corr"] == -1.0 for s in scores)
    assert all(s["pass_prelim"] is True for s in scores)
    assert len({s["corr"] for s in scores}) == 1  # blind to the rule difference
    # … whereas the new quantity is not constant across the same worlds.
    assert len({p1["H1"], p2["H2"], p3["H3"]}) == 3


def test_realised_pressure_equal_exposure_uses_full_matrix() -> None:
    scenario = _discrimination_scenario()
    world1 = scenario["H1"]  # type: ignore[assignment]
    world2 = scenario["H3"]  # type: ignore[assignment]
    assert world1["equal_exposure"]["full_matrix"] is True
    assert world2["equal_exposure"]["full_matrix"] is True
    assert world1["contact_count"] == {"H1": 2.0}
    assert world2["contact_count"] == {"H3": 2.0}
    assert world1["contact_matrix"] == {"H1": {"strong": 1.0, "mild": 1.0}}
    assert world2["contact_matrix"] == {"H3": {"strong": 1.0, "mild": 1.0}}
    assert sorted(world1["parasite_classes"]) == ["mild", "strong"]
    assert world1["parasite_class_windows"] == {"strong": P_STRONG, "mild": P_MILD}


def test_realised_pressure_formula_is_hand_checkable_when_debit_binds() -> None:
    """min[reserve, κ·A] branch: reserve 0.5 caps κ·A = 0.8 exactly."""

    result = realised_conditional_host_pressure(
        {"h": H_A},
        {"p": P_MILD},
        virulence=16.0,
        steal_fraction=0.05,
        host_capacity_units=0.5,
    )
    assert abs(result["kappa"] - 0.8) < EPS
    assert abs(result["pressure"]["h"] - 0.5) < EPS  # capped at reserve
    assert abs(result["survival_fraction"]["h"] - 0.0) < EPS  # capped ⇒ host dies


# --- P0.1(b): realised pressure constant while the histogram varies ---------


def test_realised_pressure_constant_while_histogram_varies() -> None:
    """Uniform affinity ⇒ pressure ignores the parasite class histogram."""

    window_by_class = {"p1": H_A, "p2": H_B}
    assert set(affinity_matrix({"h1": H_A, "h2": H_B}, window_by_class)) == {"h1", "h2"}
    # Flat contact-quality matrix: every class pair is a perfect match, so the
    # parasite class mix cannot change the per-host effect.
    flat = {"h1": {"p1": 1.0, "p2": 1.0}, "h2": {"p1": 1.0, "p2": 1.0}}
    base: dict[str, object] = {
        "affinity": flat,
        "virulence": 8.0,
        "steal_fraction": 0.15,
        "host_capacity_units": 10.0,
        "contact_mode": CONTACT_MODE_FULL_MATRIX,
    }
    thin = realised_conditional_host_pressure(
        {"h1": H_A, "h2": H_B}, {"p1": H_A, "p2": H_B}, **base
    )
    # Rebuild with a different multiset but identical class windows.
    wide = realised_conditional_host_pressure(
        {"h1": H_A, "h2": H_B},
        {"p1": H_A, "p2": H_B},
        parasite_class_counts={"p1": 40, "p2": 60},
        **base,
    )
    doubled = realised_conditional_host_pressure(
        {"h1": H_A, "h2": H_B},
        {"p1": H_A, "p2": H_B},
        parasite_class_counts={"p1": 2, "p2": 2},
        **base,
    )

    hist_thin = _histogram_from_counts({"p1": 1, "p2": 1})
    hist_wide = _histogram_from_counts({"p1": 40, "p2": 60})
    hist_doubled = _histogram_from_counts({"p1": 2, "p2": 2})
    assert hist_thin != hist_wide  # histogram differs …
    assert hist_thin == hist_doubled
    assert hist_wide["p1"] != hist_wide["p2"]

    # … while the new quantity is identical across all three histories.
    assert thin["pressure"] == wide["pressure"] == doubled["pressure"]
    assert thin["pressure"] == {"h1": KAPPA, "h2": KAPPA}
    assert thin["affinity_sum"] == wide["affinity_sum"] == doubled["affinity_sum"]
    assert thin["histogram_used"] is False
    assert wide["histogram_used"] is False
    assert _sum_pressure(hist_wide) == 1.0


def test_contact_matrix_seat_rule_mode_still_rule_derived() -> None:
    """Engine-seats exposure: affinity of the realised seat pairing is used."""

    seats = realised_conditional_host_pressure(
        {"h1": H_A, "h2": H_B},
        {"p1": H_A, "p2": H_B},
        contact_mode=CONTACT_MODE_ENGINE_SEATS,
        host_capacity_units=100.0,
    )
    # tick_index=0 ⇒ order unchanged ⇒ h1↔p1 and h2↔p2.
    assert seats["contact_matrix"] == {"h1": {"p1": 1.0}, "h2": {"p2": 1.0}}
    assert abs(seats["pressure"]["h1"] - KAPPA) < EPS
    assert abs(seats["pressure"]["h2"] - KAPPA) < EPS


def test_host_realised_pressure_from_contacts_uses_survival_cap() -> None:
    """Observed-contact entry point applies the same min[reserve, κ·A] law."""

    capped = host_realised_pressure_from_contacts(
        host_affinity_sums={"c": 0.5},
        host_contact_counts={"c": 1},
        host_min_available={"c": 0.1},
        virulence=8.0,
        steal_fraction=0.15,
    )
    assert abs(capped["c"] - 0.1) < EPS
    uncapped = host_realised_pressure_from_contacts(
        host_affinity_sums={"c": 0.5},
        host_contact_counts={"c": 1},
        host_min_available={"c": 10.0},
        virulence=8.0,
        steal_fraction=0.15,
    )
    assert abs(uncapped["c"] - KAPPA * 0.5) < EPS
    untouched = host_realised_pressure_from_contacts(
        host_affinity_sums={"c": 0.0},
        host_contact_counts={"c": 0},
        virulence=8.0,
        steal_fraction=0.15,
    )
    assert untouched["c"] == 0.0


# --- P0.1(d): additive, opt-in wiring into window_snapshot ------------------


def test_arm_records_realised_pressure_only_when_enabled() -> None:
    plain = StructuralRQArm.boot_structural(arm=ARM_COPASSAGED, seed=42)
    assert plain.collect_realised_host_pressure is False
    plain.run_generations(8)
    assert plain.host_realised_pressure_series == []
    snap = plain.window_snapshot(8)
    assert snap["host_realised_pressure"] == {}
    assert snap["host_realised_pressure_lag"] == []
    # The existing numbers/threshold-free fields are untouched.
    assert isinstance(snap["parasite_class_hist"], dict)
    assert snap["parasite_class_hist_is_class_frequency_not_host_pressure"] is True
    empty_snap = plain.window_snapshot(999)
    assert empty_snap["host_realised_pressure"] == {}
    assert empty_snap["parasite_class_hist"] == {}


def test_arm_records_coevolve_and_frozen_realised_pressure() -> None:
    for arm in (ARM_COPASSAGED, ARM_FIXED):
        boosted = StructuralRQArm.boot_structural(arm=arm, seed=43)
        boosted.collect_realised_host_pressure = True
        boosted.run_generations(6)
        assert len(boosted.host_realised_pressure_series) == 6
        assert len(boosted.host_contact_affinity_series) == 6
        assert len(boosted.host_contact_available_series) == 6
        assert len(boosted.parasite_class_hist_series) == 6
        snap = boosted.window_snapshot(6)
        pressure = snap["host_realised_pressure"]
        assert isinstance(pressure, dict)
        for value in pressure.values():
            assert 0.0 <= float(value) <= KAPPA + EPS
        assert isinstance(snap["host_realised_pressure_lag"], list)
        assert len(snap["host_realised_pressure_lag"]) == 6


def test_recorded_pressure_equals_rule_recomputed_from_recorded_evidence() -> None:
    """Independent recomputation from the arm's own affinity/ATP evidence."""

    arm = StructuralRQArm.boot_structural(arm=ARM_COPASSAGED, seed=44)
    arm.collect_realised_host_pressure = True
    arm.run_generations(5)
    idx = 4
    evidence = {c: (a, n) for c, a, n in arm.host_contact_affinity_series[idx]}
    available = dict(arm.host_contact_available_series[idx])
    assert evidence, "contact evidence must be recorded"
    assert set(evidence) <= set(available)
    recomputed = host_realised_pressure_from_contacts(
        host_affinity_sums={c: a for c, (a, _n) in evidence.items()},
        host_contact_counts={c: n for c, (_a, n) in evidence.items()},
        host_min_available=available,
        virulence=float(arm.virulence),
        steal_fraction=float(arm.hp_env.steal_fraction),
    )
    recorded = {c: v for c, v, _n in arm.host_realised_pressure_series[idx]}
    assert recorded == recomputed
    for cls, (aff_sum, n) in evidence.items():
        assert n >= 1
        mean_affinity = aff_sum / n
        # Realised pressure is at or below the uncapped κ·ā prediction, and it
        # follows the observed availability rather than a class count.
        assert recorded[cls] <= KAPPA * mean_affinity + EPS
        assert recorded[cls] <= max(0.0, available[cls]) + EPS


def test_parasite_histogram_shares_are_not_pressure_shares() -> None:
    """The histogram map and the pressure map are different objects/units."""

    arm = StructuralRQArm.boot_structural(arm=ARM_COPASSAGED, seed=45)
    arm.collect_realised_host_pressure = True
    arm.run_generations(4)
    snap = arm.window_snapshot(4)
    hist = snap["parasite_class_hist"]
    pressure = snap["host_realised_pressure"]
    assert abs(sum(hist.values()) - 1.0) < 1e-9
    expected_classes = {joint_match_class(w) for w in arm.parasite_windows}
    assert set(hist) == expected_classes
    if pressure:
        # Pressures are ATP-per-host, not shares; a total of exactly 1 is a
        # coincidence, not an invariant.
        assert abs(sum(pressure.values()) - 1.0) > EPS
    assert snap["parasite_class_hist_is_class_frequency_not_host_pressure"] is True
