"""Mechanism test for the frequency-swap signal (campaign ``rq_redesign_20260928``).

Why this file exists
--------------------
The stopping rule of ``STATS_AND_NULL_DESIGN.md`` section 7 (stop condition 3 /
``PREREG_V2.md`` S3) forbids the confirmatory campaign while the anti-phase
counter-sample N1 is not rejected by the primary statistic, and while the
positive synthetic case P1 does not pass. ``SCIENTIFIC_QUESTION_AND_DAG.md``
section 6 is the acceptance contract for the instrument; this module executes it.

The statistic
-------------
    S = pi_A(swap) - pi_A(swap^-1)

with ``pi_A`` the realised conditional pressure on the designated class ``A``
(:func:`realised_conditional_host_pressure`), ``swap`` the counterfactual that
exchanges the host frequencies of the designated common and designated rare
class in place while census, resource state, host genotype multiset, contact
count and random stream are held fixed, and ``swap^-1`` the matched inverse
(unswapped) counterfactual. The exchange is an involution, so the inverse of the
swapped assignment is the baseline. Accepted iff ``S <= -0.20`` ATP per host per
contact opportunity (T9) with a run-level cluster-bootstrap interval excluding
zero; every counter-sample must give ``S = 0``.

One structural fact is used throughout and is checked by hand here. Under equal
exposure the per-opportunity pressure of a class does **not** depend on that
class' own share: ``pi_i = kappa * sum_j F_j A(i, j)``. The swap can therefore
only move ``pi_A`` through the *delayed adaptation channel* (the antagonist pool
is replenished from the contact set, whose composition is proportional to the
host shares, with a one-generation lag: DAG L5-L8). Hence:

* the lag-0 (same-generation) component of ``S`` is exactly zero, and
* a frozen antagonist gives ``S = 0`` even though the host frequencies are
  swapped -- the DAG lists this frozen twin as a required outcome of P1.

The synthetic worlds below are minimal closed loops built from the same contact
law as the measurement kernel: equal exposure, the model's graded affinity, a
per-contact debit of ``virulence x steal_fraction x affinity``, and an
antagonist pool replenished from the contact set with a one-generation lag.
Nothing in this file changes a recorded number, a pre-registered threshold or a
decision branch of ``classify_rq_earn_confirm_outcome``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Any

from codontrace.genesis.measurements.rq_frequency_clocks import (
    DEFAULT_CLUSTER_BOOTSTRAP_RESAMPLES,
    DEFAULT_CLUSTER_BOOTSTRAP_SEED,
    exchange_class_shares,
    frequency_swap_signal,
    lagged_nfds_score,
    realised_conditional_host_pressure,
    reference_graded_affinity,
    run_level_cluster_bootstrap_interval,
)

# --- Locked constants of the calibration design ------------------------------

#: Designated classes are the pre-registered founder windows (``PREREG_V2.md`` 3.3):
#: the numerically lowest distinct window is ``A``, the highest is ``B``.
WINDOW_A = "000000"
WINDOW_B = "111111"

#: Standing locks of the structural design (``PREREG_V2.md`` 3.1).
VIRULENCE = 8.0
STEAL_FRACTION = 0.15
KAPPA = VIRULENCE * STEAL_FRACTION  # 1.2 ATP per unit affinity

#: Pre-registered mechanism floor on the swap-signal (``PREREG_V2.md`` T9).
T9_MECHANISM_FLOOR_ATP = 0.20

#: Mechanism-calibration seed block (``PREREG_V2.md`` section 2, 20 runs).
CALIBRATION_SEEDS = tuple(range(9101, 9121))

#: Generation at which the swap snapshot is taken. The exchange applies to the
#: host shares from the next generation, and the antagonist pool used by
#: generation ``g`` is set at the boundary of ``g - 1``, so the first pressure a
#: swap can reach is generation ``SWAP_SNAPSHOT_GENERATION + 2``.
SWAP_SNAPSHOT_GENERATION = 40
EXCHANGE_FROM_GENERATION = SWAP_SNAPSHOT_GENERATION + 1
FIRST_AFFECTED_GENERATION = SWAP_SNAPSHOT_GENERATION + 2
HORIZON = 61
POST_SWAP_WINDOW = tuple(range(FIRST_AFFECTED_GENERATION, HORIZON + 1))

CENSUS = 50
POOL_SIZE = 20
COMMON_SHARE = 0.6

EPS = 1e-12


# --- Minimal closed-loop synthetic worlds ------------------------------------


@dataclass(frozen=True)
class _WorldSpec:
    """One calibration world. The contact law is fixed; the switch differs."""

    name: str
    #: share of the designated common class before the swap snapshot
    common_share: float = COMMON_SHARE
    #: prescribed host oscillation (the matched forcing / anti-phase driver)
    oscillating_host: bool = False
    #: antagonist pool replenished from the contact set with a one-generation lag
    adaptive_pool: bool = True
    #: antagonist pool held at the ancestral multiset (N3)
    frozen_pool: bool = False
    #: antagonist proportions prescribed anti-phase to the host, no adaptation (N1)
    prescribed_anti_phase: bool = False
    #: class-blind affinity A(h, p) = 0.5 for every pair (N1)
    flat_affinity: bool = False
    #: explicit (A-A, A-B, B-A, B-B) affinity quadruple; None = model rule
    affinity_quadruple: tuple[float, float, float, float] | None = None
    #: fraction of the new pool copied from the contact set (1.0 = pure copy)
    keep_fraction: float = 1.0
    #: uniform mixing of the new pool (the locked campaign value is 0.25)
    mutation_rate: float = 0.0
    #: ancestral antagonist share of the class matching A
    ancestral_share_a: float = 0.5
    #: exchange the host genotype labels A <-> B throughout the world
    label_permuted: bool = False


def _driver_share(spec: _WorldSpec, generation: int) -> float:
    """Host share of the designated class before any intervention."""

    if spec.oscillating_host:
        return 0.2 if generation % 2 == 0 else 0.8
    return float(spec.common_share)


def _branch_share(spec: _WorldSpec, generation: int, swapped: bool) -> float:
    """Host share of the designated class in one branch of the counterfactual."""

    base = _driver_share(spec, generation)
    if swapped and generation >= EXCHANGE_FROM_GENERATION:
        return 1.0 - base  # exchange the shares of the two classes
    return base


def _affinity_quadruple(spec: _WorldSpec) -> tuple[float, float, float, float]:
    if spec.affinity_quadruple is not None:
        return spec.affinity_quadruple
    if spec.flat_affinity:
        return (0.5, 0.5, 0.5, 0.5)
    host_a, host_b = (WINDOW_B, WINDOW_A) if spec.label_permuted else (WINDOW_A, WINDOW_B)
    rule = reference_graded_affinity
    return (
        rule(host_a, host_a),
        rule(host_a, host_b),
        rule(host_b, host_a),
        rule(host_b, host_b),
    )


def _run_branch(spec: _WorldSpec, seed: int, *, swapped: bool) -> list[dict[str, float]]:
    """Run one counterfactual branch and return its per-generation record.

    Equal exposure: the designated class holds ``round(CENSUS * h)`` hosts, each
    with exactly one contact opportunity per generation, and the contact-set
    composition equals the host composition. The realised pressure is
    ``pi_i = kappa * sum_j F_j A(i, j)`` with ``F`` the antagonist pool
    composition. Both branches consume the same random stream in the same order.
    """

    a_aa, a_ab, a_ba, a_bb = _affinity_quadruple(spec)
    rng = random.Random(int(seed))
    pool_a = _pool_count(spec.ancestral_share_a)
    ancestral_a = pool_a
    rows: list[dict[str, float]] = []
    for generation in range(HORIZON + 1):
        h_a = _branch_share(spec, generation, swapped)
        h_b = 1.0 - h_a
        if spec.prescribed_anti_phase:
            f_a = h_b  # anti-phase by construction, never adapts
        else:
            f_a = pool_a / float(POOL_SIZE)
        f_b = 1.0 - f_a
        pi_a = KAPPA * (f_a * a_aa + f_b * a_ab)
        pi_b = KAPPA * (f_a * a_ba + f_b * a_bb)
        census_a = int(round(CENSUS * h_a))
        rows.append(
            {
                "generation": float(generation),
                "h_a": h_a,
                "h_b": h_b,
                "f_a": f_a,
                "f_b": f_b,
                "pi_a": pi_a,
                "pi_b": pi_b,
                "census_a": float(census_a),
                "census_b": float(CENSUS - census_a),
            }
        )
        # Antagonist update at the generation boundary, driven by this
        # generation's realised contact set (one-generation lag: DAG L5).
        if spec.frozen_pool:
            pool_a = ancestral_a
        elif spec.prescribed_anti_phase:
            pool_a = pool_a
        elif spec.adaptive_pool:
            p = spec.keep_fraction * h_a + (1.0 - spec.keep_fraction) * f_a
            p = (1.0 - spec.mutation_rate) * p + spec.mutation_rate * 0.5
            pool_a = sum(1 for _ in range(POOL_SIZE) if rng.random() < p)
        else:
            raise ValueError(f"{spec.name}: no antagonist update rule selected")
    return rows


def _pool_count(share: float) -> int:
    return int(round(POOL_SIZE * share))


def _series(rows: list[dict[str, float]], key: str) -> dict[int, float]:
    return {int(row["generation"]): float(row[key]) for row in rows}


def _world_statistic(spec: _WorldSpec, seeds: tuple[int, ...] = CALIBRATION_SEEDS) -> dict[str, Any]:
    """Paired swap-signal over independent runs, with the cluster bootstrap."""

    run_values: list[float] = []
    run_values_label_b: list[float] = []
    instantaneous: list[float] = []
    swap_rows: list[list[dict[str, float]]] = []
    base_rows: list[list[dict[str, float]]] = []
    for seed in seeds:
        base = _run_branch(spec, seed, swapped=False)
        swap = _run_branch(spec, seed, swapped=True)
        base_rows.append(base)
        swap_rows.append(swap)
        signal = frequency_swap_signal(
            _series(swap, "pi_a"),
            _series(base, "pi_a"),
            window=POST_SWAP_WINDOW,
            instantaneous_generation=SWAP_SNAPSHOT_GENERATION,
        )
        run_values.append(float(signal["s"]))
        instantaneous.append(float(signal["instantaneous_component"]))
        signal_b = frequency_swap_signal(
            _series(swap, "pi_b"),
            _series(base, "pi_b"),
            window=POST_SWAP_WINDOW,
        )
        run_values_label_b.append(float(signal_b["s"]))
    interval = run_level_cluster_bootstrap_interval(
        run_values,
        n_resamples=DEFAULT_CLUSTER_BOOTSTRAP_RESAMPLES,
        seed=DEFAULT_CLUSTER_BOOTSTRAP_SEED,
    )
    return {
        "spec": spec,
        "run_values": run_values,
        "run_values_label_b": run_values_label_b,
        "instantaneous": instantaneous,
        "interval": interval,
        "point": float(interval["point"]),
        "lo": float(interval["lo"]),
        "hi": float(interval["hi"]),
        "swap_rows": swap_rows,
        "base_rows": base_rows,
    }


def _p1_world() -> _WorldSpec:
    return _WorldSpec(name="P1-delayed-adaptation")


def _n1_world() -> _WorldSpec:
    return _WorldSpec(
        name="N1-anti-phase-no-adaptation-flat-affinity",
        oscillating_host=True,
        adaptive_pool=False,
        prescribed_anti_phase=True,
        flat_affinity=True,
    )


def _n2_world() -> _WorldSpec:
    return _WorldSpec(name="N2-sham-equal-shares-and-permuted-labels", common_share=0.5)


def _n3_world() -> _WorldSpec:
    return _WorldSpec(
        name="N3-frozen-antagonist-matched-forcing",
        oscillating_host=True,
        adaptive_pool=False,
        frozen_pool=True,
        ancestral_share_a=0.6,
    )


# --- Hand-checkable arithmetic ----------------------------------------------


def test_swap_signal_arithmetic_on_hand_written_contact_matrix() -> None:
    """Hand-written contact matrices, hand-computed pressures and sign.

    Affinity (the model's own rule: perfect match 1.0, complete mismatch 0.0):

        A(A, P_A) = 1.0   A(A, P_B) = 0.0
        A(B, P_A) = 0.0   A(B, P_B) = 1.0

    ``kappa = 8.0 x 0.15 = 1.2`` ATP per unit affinity. Four contacts on class
    ``A``, hand-written multiplicities:

    * world "A was common", antagonist pool adapted to A: ``C(A, P_A) = 3``,
      ``C(A, P_B) = 1`` ->
      ``pi_A = 1.2 x (3 x 1.0 + 1 x 0.0) / 4 = 0.900`` ATP per opportunity;
    * world "A was rare", antagonist pool adapted to B: ``C(A, P_A) = 1``,
      ``C(A, P_B) = 3`` ->
      ``pi_A = 1.2 x (1 x 1.0 + 3 x 0.0) / 4 = 0.300`` ATP per opportunity.

    Hence ``S = 0.300 - 0.900 = -0.600 < 0`` and ``|S| = 0.600 >= 0.200`` (T9):
    the sign follows from the exchange alone. With the contact matrix held fixed
    the same swap gives exactly zero, which is the frozen-antagonist property.
    """

    host_windows = {"A": WINDOW_A}
    parasite_windows = {"P_A": WINDOW_A, "P_B": WINDOW_B}
    affinity = {"A": {"P_A": 1.0, "P_B": 0.0}}

    # The hand-written affinity is the model's own rule, written out.
    assert reference_graded_affinity(WINDOW_A, WINDOW_A) == 1.0
    assert reference_graded_affinity(WINDOW_A, WINDOW_B) == 0.0

    common = realised_conditional_host_pressure(
        host_windows,
        parasite_windows,
        affinity=affinity,
        contact_matrix={"A": {"P_A": 3.0, "P_B": 1.0}},
    )
    rare = realised_conditional_host_pressure(
        host_windows,
        parasite_windows,
        affinity=affinity,
        contact_matrix={"A": {"P_A": 1.0, "P_B": 3.0}},
    )
    pi_common = float(common["pressure"]["A"])
    pi_rare = float(rare["pressure"]["A"])
    assert abs(pi_common - 0.900) < EPS
    assert abs(pi_rare - 0.300) < EPS
    assert abs(pi_common - KAPPA * 3.0 / 4.0) < EPS

    signal = frequency_swap_signal({0: pi_rare}, {0: pi_common}, window=[0], instantaneous_generation=0)
    assert abs(float(signal["s"]) - (-0.600)) < EPS
    assert float(signal["s"]) < 0.0
    assert abs(float(signal["s"])) >= T9_MECHANISM_FLOOR_ATP

    # The exchange intervention on the share vector is an involution and keeps
    # the population size and the other classes untouched.
    shares = {"A": 0.75, "B": 0.20, "C": 0.05}
    exchanged = exchange_class_shares(shares, "A", "B")
    assert exchanged == {"A": 0.20, "B": 0.75, "C": 0.05}
    assert abs(sum(exchanged.values()) - sum(shares.values())) < EPS
    assert exchange_class_shares(exchanged, "A", "B") == shares

    # Frozen contact matrix: the swap moves the frequencies, not the pairing, so
    # the realised per-opportunity pressure is untouched and S is exactly zero.
    frozen_common = realised_conditional_host_pressure(
        host_windows,
        parasite_windows,
        affinity=affinity,
        contact_matrix={"A": {"P_A": 3.0, "P_B": 1.0}},
    )
    frozen_swap = realised_conditional_host_pressure(
        host_windows,
        parasite_windows,
        affinity=affinity,
        contact_matrix={"A": {"P_A": 3.0, "P_B": 1.0}},
    )
    assert frozen_common["pressure"] == frozen_swap["pressure"] == {"A": 0.9}
    frozen_signal = frequency_swap_signal(
        {0: float(frozen_swap["pressure"]["A"])},
        {0: float(frozen_common["pressure"]["A"])},
        window=[0],
    )
    assert abs(float(frozen_signal["s"])) < EPS


def test_run_level_cluster_bootstrap_is_over_runs_not_generations() -> None:
    """The interval resamples runs; generation-level dependence is not laundered."""

    degenerate = run_level_cluster_bootstrap_interval([0.5, 0.5, 0.5, 0.5], n_resamples=200, seed=7)
    assert degenerate["n_runs"] == 4
    assert degenerate["n_resamples"] == 200
    assert degenerate["point"] == 0.5
    assert degenerate["interval_defined"] is False
    assert degenerate["excludes_zero"] is False
    assert degenerate["inferential_eligible"] is False
    assert degenerate["status"] == "degenerate_variance"
    assert degenerate["unit_of_replication"] == "run"

    spread = run_level_cluster_bootstrap_interval([-0.30, -0.20, -0.10, 0.05], n_resamples=4000, seed=7)
    assert spread["lo"] < float(spread["point"]) < spread["hi"]
    assert spread["inferential_eligible"] is False
    assert spread["status"] == "below_auditor_floor"
    assert spread["excludes_zero"] is False
    again = run_level_cluster_bootstrap_interval([-0.30, -0.20, -0.10, 0.05], n_resamples=4000, seed=7)
    assert (spread["lo"], spread["hi"]) == (again["lo"], again["hi"])

    straddling = run_level_cluster_bootstrap_interval([-0.4, -0.1, 0.1, 0.4], n_resamples=4000, seed=7)
    assert straddling["excludes_zero"] is False

    defaults = run_level_cluster_bootstrap_interval([-0.30, -0.20, -0.10, 0.05], n_resamples=50)
    assert defaults["seed"] == DEFAULT_CLUSTER_BOOTSTRAP_SEED
    assert DEFAULT_CLUSTER_BOOTSTRAP_RESAMPLES == 10_000


def test_instantaneous_swap_component_is_zero_under_equal_exposure() -> None:
    """The same-generation component vanishes: pressure is share-independent.

    ``pi_i = kappa * sum_j F_j A(i, j)`` contains no host share, so both branches
    evaluate the same contact round at the snapshot generation. This is why the
    mechanism can only appear through the delayed adaptation channel.
    """

    result = _world_statistic(_p1_world())
    assert all(value == 0.0 for value in result["instantaneous"]), (
        "the lag-0 swap component must be exactly zero under equal exposure; "
        f"observed {result['instantaneous'][:3]}"
    )
    base = result["base_rows"][0]
    swap = result["swap_rows"][0]
    snapshot = SWAP_SNAPSHOT_GENERATION
    assert base[snapshot] == swap[snapshot]


# --- P1: the positive case the mechanism test must accept --------------------


def test_p1_delayed_adaptation_passes_the_mechanism_floor() -> None:
    """P1 must give ``S <= -0.20`` with the run-level interval excluding zero.

    Hand-checked expectation. The pool at generation ``g + 1`` is a copy of the
    contact set of generation ``g`` (DAG L5, lag 1). The mean host share of the
    designated class is 0.6 before the snapshot and 0.4 after the exchange, and
    ``pi_A = kappa * F_A`` because the two windows are perfect matches and
    complete mismatches, so

        E[S] = kappa x (0.4 - 0.6) = 1.2 x (-0.2) = -0.24 ATP per opportunity.
    """

    result = _world_statistic(_p1_world())
    point, lo, hi = result["point"], result["lo"], result["hi"]

    assert all(value <= 0.0 for value in result["run_values"])
    assert point <= -T9_MECHANISM_FLOOR_ATP, (
        f"P1 must reach the pre-registered mechanism floor: S={point:.6f}, floor={T9_MECHANISM_FLOOR_ATP}"
    )
    assert hi < 0.0, f"P1's run-level cluster-bootstrap interval must exclude zero: [{lo:.6f}, {hi:.6f}]"
    assert abs(point - (-0.24)) < 0.03, f"P1 does not reproduce the hand-computed -0.24: {point:.6f}"

    # The frozen-passage twin of the same seeds is a required outcome of P1:
    # with the pool held fixed the exchange cannot reach the pressure.
    frozen_twin = _world_statistic(replace(_p1_world(), name="P1-frozen-twin", frozen_pool=True))
    assert all(value == 0.0 for value in frozen_twin["run_values"])
    assert abs(frozen_twin["point"]) < EPS
    assert frozen_twin["interval"]["excludes_zero"] is False

    # Direction rule (DAG 6.1): the swap is applied in both directions and the
    # two directions must agree in magnitude and oppose in sign, which is what
    # rules out an effect of the label rather than of frequency.
    for forward, reverse in zip(result["run_values"], result["run_values_label_b"], strict=True):
        assert abs(forward + reverse) < 1e-9, (forward, reverse)


def test_p1_signal_shrinks_with_campaign_pool_retention_and_mutation() -> None:
    """Sensitivity, not a threshold change: mutation/retention attenuate the signal.

    The locked campaign values are keep fraction 0.5 and antagonist mutation rate
    0.25 (``PREREG_V2.md`` 3.1). With a blended pool the tracked contrast is
    diluted, so this calibration world's signal is smaller in magnitude. The test
    records that direction only; it does not move T9 and it does not certify the
    campaign.
    """

    pure_copy = _world_statistic(_p1_world())
    locked = _world_statistic(replace(_p1_world(), name="P1-locked-pool", keep_fraction=0.5, mutation_rate=0.25))
    assert locked["point"] < 0.0
    assert abs(locked["point"]) < abs(pure_copy["point"])


# --- N1: the load-bearing counter-sample -------------------------------------


def test_n1_anti_phase_counter_sample_is_not_rejected() -> None:
    """N1 must NOT reject. If it does, the statistic measures oscillation.

    N1 is hostile by construction: the host shares oscillate 0.2/0.8, the
    antagonist proportions move exactly anti-phase (``F_A = 1 - h_A``), and the
    affinity matrix is flat (``A(h, p) = 0.5``), so every class pays the same
    debit and there is no frequency-dependent loss anywhere.

    The retired composition statistic fails on this counter-sample -- it reports
    ``corr = -1`` at the campaign lag with ``pass_prelim = True`` -- while a
    confounded total-damage statistic also moves, because the exchange moves the
    class census. The swap-signal must stay at exactly zero: any rejection here
    is an instrument failure and the campaign must not run.
    """

    spec = _n1_world()
    result = _world_statistic(spec)
    point, lo, hi = result["point"], result["lo"], result["hi"]

    assert all(value == 0.0 for value in result["run_values"]), (
        "N1 COUNTER-SAMPLE VIOLATION: the swap-signal moves on the anti-phase, "
        "adaptation-free, frequency-independent-loss-free world "
        f"(run values {result['run_values'][:4]}). The statistic is measuring "
        "oscillation, not the delayed-adaptation mechanism."
    )
    assert abs(point) < EPS, f"N1 must give S = 0 within tolerance, observed {point:.12f}"
    assert abs(point) < T9_MECHANISM_FLOOR_ATP
    assert result["interval"]["excludes_zero"] is False, (
        "N1 COUNTER-SAMPLE VIOLATION: the swap-signal interval excludes zero on "
        f"the anti-phase counter-sample (S={point:.6f}, 95% CI [{lo:.6f}, {hi:.6f}]). "
        "The statistic is measuring oscillation; the campaign must not run and "
        "the statistic must not be tuned until this is fixed."
    )

    # The counter-sample really oscillates, and the retired composition score
    # accepts it: that is precisely the failure mode the design documents.
    base = result["base_rows"][0]
    host_freq = {int(row["generation"]): {WINDOW_A: row["h_a"], WINDOW_B: row["h_b"]} for row in base}
    para_freq = {int(row["generation"]): {WINDOW_A: row["f_a"], WINDOW_B: row["f_b"]} for row in base}
    retired = lagged_nfds_score(host_freq, para_freq, lag=4, min_points=20)
    assert abs(float(retired["corr"]) + 1.0) < 1e-9
    assert retired["pass_prelim"] is True
    assert int(retired["n"]) >= 20
    for row in base:
        assert row["f_a"] == row["h_b"]  # exact anti-phase, by construction

    # A confounded total-damage statistic does move here, so N1 is not a
    # degenerate zero-variance surface: the per-opportunity normalisation is what
    # protects the swap-signal from oscillation.
    swap_by_gen = {int(row["generation"]): row for row in result["swap_rows"][0]}
    base_by_gen = {int(row["generation"]): row for row in base}
    confounded = [
        abs(swap_by_gen[g]["pi_a"] * swap_by_gen[g]["census_a"] - base_by_gen[g]["pi_a"] * base_by_gen[g]["census_a"])
        for g in POST_SWAP_WINDOW
    ]
    assert max(confounded) > 1.0


# --- N2: sham intervention and permuted genotype labels ----------------------


def test_n2_sham_intervention_and_permuted_labels_have_no_effect() -> None:
    """N2 must give zero: the intervention is a no-op at equal shares.

    With ``h_A = h_B = 0.5`` the exchange maps the frequency assignment onto
    itself, so the swapped branch is the baseline branch event for event while
    the pressures are the same mechanism pressures as P1's (the pool still
    fluctuates and ``pi_A`` is not constant). Permuting the genotype labels
    A <-> B leaves every frequency, every pressure and the statistic unchanged.
    """

    spec = _n2_world()
    result = _world_statistic(spec)

    base = result["base_rows"][0]
    swap = result["swap_rows"][0]
    assert base == swap  # the intervention is a true no-op
    assert len({row["pi_a"] for row in base}) > 1, "N2 must carry real pressure variation, not a flat world"

    assert all(value == 0.0 for value in result["run_values"])
    assert abs(result["point"]) < EPS
    assert result["interval"]["excludes_zero"] is False
    assert abs(result["point"]) < T9_MECHANISM_FLOOR_ATP

    # Permuted genotype labels: same frequencies, same pressures, same zero.
    permuted = _world_statistic(replace(spec, name="N2-label-permuted", label_permuted=True))
    assert permuted["base_rows"][0] == base
    assert all(value == 0.0 for value in permuted["run_values"])
    assert permuted["interval"]["excludes_zero"] is False


# --- N3: frozen antagonist under matched forcing -----------------------------


def test_n3_frozen_antagonist_matched_forcing_has_no_effect() -> None:
    """N3 must give zero: a frozen pool cannot transmit the swapped frequencies.

    The resource/census schedule is identical in both branches (same total census
    and same contact count at every generation), the affinity is the
    discriminating model rule, and the ancestral multiset is 12/8 so the frozen
    pressure is a real, class-specific 0.72 ATP per opportunity -- yet it is the
    same constant in both branches, so ``S = 0`` exactly.
    """

    spec = _n3_world()
    result = _world_statistic(spec)
    point = result["point"]

    assert all(value == 0.0 for value in result["run_values"])
    assert abs(point) < EPS, f"N3 must give S = 0 exactly, observed {point:.12f}"
    assert result["interval"]["excludes_zero"] is False

    base = result["base_rows"][0]
    swap = result["swap_rows"][0]
    for row_base, row_swap in zip(base, swap, strict=True):
        # matched demography and contact count
        assert row_base["census_a"] + row_base["census_b"] == CENSUS
        assert row_swap["census_a"] + row_swap["census_b"] == CENSUS
        assert row_base["f_a"] == row_swap["f_a"] == 0.6
        assert abs(row_base["pi_a"] - 0.72) < EPS
        assert row_swap["pi_a"] == row_base["pi_a"]
    # The host trajectory oscillates, so the world is not static.
    assert len({row["h_a"] for row in base}) > 1
    assert base[0]["h_a"] != base[1]["h_a"]
