"""HP-ARM01 structural RQ regime pilot — Stages A→D under NEW prereg.

Constants match
``docs/handoff/CLOSED_LOOP_HP_ARM01_STRUCTURAL_RQ_REGIME_PREREG_20260926.md``.

Sealed Slowinski (214df20 / 201–208), persistence (91ab0c6 / 301–308), and
mating ledger (7171d19 / 401–408) are untouched. Mating / Slowinski stay
deferred. ``red_queen_proved`` stays false. HP physics stays out of
``engine.py``. Primary success this wave: ``polymorphism_hold`` only.
``cycle_candidate`` is observation-only / secondary.
"""

from __future__ import annotations

from contextlib import contextmanager

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Mapping, Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.closed_loop_hp_arm01 import (
    ARM_AVIRULENT,
    ARM_COPASSAGED,
    ARM_FIXED,
    ARM_TO_PASSAGE,
    CLAIM_CEILING_CANDIDATE,
    CLAIM_CEILING_OBSERVATION,
    ECOLOGY_ARMS,
    HP_ENV_MATCH_REASON,
    LifeLoopEcologyArm,
    PASSAGE_REFILL_GENERATION_BOUNDARY,
    SUBSTRATE_LIFE_LOOP,
    _mutate_window,
    _window,
    assert_ecology_arm_taxonomy,
)
from codontrace.genesis.host_parasite_life_plugin import (
    MATCH_BIT_WIDTH,
    ROLE_PRIMARY,
    role_of,
)
from codontrace.genesis.birth import ReproductionMode, SexualRecombinationConfig
from codontrace.genesis.population import MutationConfig, PopulationState
from codontrace.genesis.organism import GenesisOrganism
from codontrace.rng import RNGManager

from codontrace.genesis.closed_loop_pearl_spc import (
    PASSAGE_ABSENT,
    PASSAGE_COEVOLVE,
    PASSAGE_FROZEN,
)

PREREG_VERSION = "hp_arm01_structural_rq_regime_prereg_20260926"
PREREG_RELATIVE_PATH = (
    "docs/handoff/CLOSED_LOOP_HP_ARM01_STRUCTURAL_RQ_REGIME_PREREG_20260926.md"
)
HP_ARM01_STRUCTURAL_RQ_REVISION = "hp-arm01-structural-rq-regime-20260926"
SLICE_NAME = "HP-ARM01-STRUCTURAL-RQ-REGIME"
ESTIMAND = "structural_polymorphism_hold_under_large_N_multilocus_mid_turnover"

OUTCOME_SWEEP_FIXATION = "sweep_fixation"
OUTCOME_POLYMORPHISM_HOLD = "polymorphism_hold"
OUTCOME_CYCLE_CANDIDATE = "cycle_candidate"
OUTCOME_HORIZON_INSUFFICIENT = "horizon_insufficient"
OUTCOME_PARASITE_EXTINCT = "parasite_extinct"
OUTCOME_SELFING_NONVIABLE = "selfing_nonviable"
OUTCOME_SLOWINSKI_UNSCORED = "Slowinski_unscored"
OUTCOME_REGIME_HOSTILE_NE = "regime_hostile_ne"
OUTCOME_REGIME_HOSTILE_TURNOVER = "regime_hostile_turnover"

TYPED_OUTCOMES = frozenset(
    {
        OUTCOME_SWEEP_FIXATION,
        OUTCOME_POLYMORPHISM_HOLD,
        OUTCOME_CYCLE_CANDIDATE,
        OUTCOME_HORIZON_INSUFFICIENT,
        OUTCOME_PARASITE_EXTINCT,
        OUTCOME_SELFING_NONVIABLE,
        OUTCOME_SLOWINSKI_UNSCORED,
        OUTCOME_REGIME_HOSTILE_NE,
        OUTCOME_REGIME_HOSTILE_TURNOVER,
    }
)

PILOT_SEEDS: tuple[int, ...] = (601, 602, 603)
SEALED_P7_SEEDS: tuple[int, ...] = (101, 102, 103, 104, 105, 106, 107, 108)
SEALED_SLOWINSKI_SEEDS: tuple[int, ...] = (201, 202, 203, 204, 205, 206, 207, 208)
SEALED_PERSISTENCE_SEEDS: tuple[int, ...] = (301, 302, 303, 304, 305, 306, 307, 308)
SEALED_MATING_SEEDS: tuple[int, ...] = (401, 402, 403, 404, 405, 406, 407, 408)
SEALED_SELFING_HOLD_SEEDS: tuple[int, ...] = (501, 502, 503, 504, 505, 506, 507, 508)

STRUCT_GENERATIONS = 250
STRUCT_MID_WINDOWS: tuple[int, ...] = (50, 125)
STRUCT_TERMINAL_WINDOW = 250
STRUCT_LOCKED_WINDOWS: tuple[int, ...] = (50, 125, 250)

# None = locked-windows-only (pilot backward-compatible API).
STRUCT_SNAP_STRIDE: int | None = None
STRUCT_PARASITE_CLASS_MEMORY_L = 8
STRUCT_R_MIN = 3
STRUCT_EPSILON = 0.15  # single class > 1-ε = 0.85 fails hold
STRUCT_VIRULENCE = 8.0
STRUCT_PARASITE_MUTATION = 0.25
STRUCT_HOST_BIT_FLIP = 0.02
STRUCT_HOST_N = 64
STRUCT_PARASITE_N = 64
STRUCT_SOFT_K = 64
STRUCT_KEEP_FRACTION = 0.5
STRUCT_STEAL_FRACTION = 0.15
STRUCT_BIRTH_ATP = 48.0
STRUCT_BASAL_ATP_COST = 0.05
STRUCT_HANDLING_TIME = 0.0
STRUCT_RESOURCE_BOLUS_AMOUNT = 20.0
STRUCT_PASSAGE_REFILL_MODE = PASSAGE_REFILL_GENERATION_BOUNDARY
STRUCT_WORLD_SIZE = 16
STRUCT_MIN_VIABLE_CENSUS = 12
STRUCT_FOUNDER_SPATIAL_POLICY = "food_patch_interleaved"
STRUCT_FOOD_PATCHES: tuple[tuple[int, int], ...] = tuple(
    (x, y) for x in range(4) for y in range(4)
)
STRUCT_SUB_LOCUS_WIDTH = 2
STRUCT_N_SUB_LOCI = 3
STRUCT_KAPPA_TOLERANCE = 0.15
DEBIT_ACTIVE_ARMS: tuple[str, ...] = (ARM_FIXED, ARM_COPASSAGED)

# 16 distinct match-state founders (prereg §4)
_DISTINCT_WINDOWS: tuple[str, ...] = (
    "000000",
    "000001",
    "000010",
    "000011",
    "000100",
    "000101",
    "000110",
    "000111",
    "111000",
    "111001",
    "111010",
    "111011",
    "111100",
    "111101",
    "111110",
    "111111",
)


def _structural_founders(host_n: int = STRUCT_HOST_N) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for index in range(int(host_n)):
        rows.append(("outcross", _DISTINCT_WINDOWS[index % len(_DISTINCT_WINDOWS)]))
    return tuple(rows)


STRUCT_FOUNDERS: tuple[tuple[str, str], ...] = _structural_founders()


def prereg_document_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / PREREG_RELATIVE_PATH


def locked_design_dict() -> dict[str, object]:
    return {
        "prereg_version": PREREG_VERSION,
        "revision": HP_ARM01_STRUCTURAL_RQ_REVISION,
        "slice": SLICE_NAME,
        "estimand": ESTIMAND,
        "substrate": SUBSTRATE_LIFE_LOOP,
        "seeds": list(PILOT_SEEDS),
        "sealed_p7_seeds_untouched": list(SEALED_P7_SEEDS),
        "sealed_slowinski_seeds_untouched": list(SEALED_SLOWINSKI_SEEDS),
        "sealed_persistence_seeds_untouched": list(SEALED_PERSISTENCE_SEEDS),
        "sealed_mating_seeds_untouched": list(SEALED_MATING_SEEDS),
        "sealed_selfing_hold_seeds_untouched": list(SEALED_SELFING_HOLD_SEEDS),
        "generations": STRUCT_GENERATIONS,
        "locked_windows": list(STRUCT_LOCKED_WINDOWS),
        "snap_stride": STRUCT_SNAP_STRIDE,
        "parasite_class_memory_L": STRUCT_PARASITE_CLASS_MEMORY_L,
        "mid_windows": list(STRUCT_MID_WINDOWS),
        "terminal_window": STRUCT_TERMINAL_WINDOW,
        "r_min": STRUCT_R_MIN,
        "epsilon": STRUCT_EPSILON,
        "virulence": STRUCT_VIRULENCE,
        "parasite_mutation": STRUCT_PARASITE_MUTATION,
        "host_bit_flip_rate": STRUCT_HOST_BIT_FLIP,
        "host_n": STRUCT_HOST_N,
        "parasite_n": STRUCT_PARASITE_N,
        "soft_carrying_capacity": STRUCT_SOFT_K,
        "parasite_keep_fraction_kappa": STRUCT_KEEP_FRACTION,
        "steal_fraction": STRUCT_STEAL_FRACTION,
        "birth_atp": STRUCT_BIRTH_ATP,
        "basal_runtime_atp_cost": STRUCT_BASAL_ATP_COST,
        "handling_time": STRUCT_HANDLING_TIME,
        "passage_refill_mode": STRUCT_PASSAGE_REFILL_MODE,
        "resource_bolus_amount": STRUCT_RESOURCE_BOLUS_AMOUNT,
        "food_patches": [list(p) for p in STRUCT_FOOD_PATCHES],
        "world_size": STRUCT_WORLD_SIZE,
        "founder_spatial_policy": STRUCT_FOUNDER_SPATIAL_POLICY,
        "min_viable_census": STRUCT_MIN_VIABLE_CENSUS,
        "distinct_match_founders": list(_DISTINCT_WINDOWS),
        "n_distinct_match_founders": len(_DISTINCT_WINDOWS),
        "sub_locus_partition": {
            "n_sub_loci": STRUCT_N_SUB_LOCI,
            "sub_locus_width": STRUCT_SUB_LOCUS_WIDTH,
            "ranges": [[0, 2], [2, 4], [4, 6]],
            "affinity_rule": "feature_overlap",
            "and_collapse_forbidden": True,
        },
        "arms": list(ECOLOGY_ARMS),
        "debit_active_arms": list(DEBIT_ACTIVE_ARMS),
        "typed_outcomes": sorted(TYPED_OUTCOMES),
        "primary_success": OUTCOME_POLYMORPHISM_HOLD,
        "cycle_candidate_secondary_observation_only": True,
        "slowinski_scored": False,
        "mating_deferred": True,
        "red_queen_proved_allowed": False,
        "biological_red_queen_proved_allowed": False,
        "spc_owns_accept_path": False,
        "body_census_is_ne_proxy": False,
        "second_population_registry": False,
        "reproduction_mode": "asexual",
        "mating_deferred_asexual_substrate": True,
        "prereg_path": PREREG_RELATIVE_PATH,
    }


def structural_rq_design_digest() -> str:
    return canonical_digest(locked_design_dict(), prefix="hp_arm01_structural_rq_design")


def structural_rq_document_digest() -> str:
    path = prereg_document_path()
    if not path.is_file():
        raise ConfigurationError(f"missing preregistration file: {PREREG_RELATIVE_PATH}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_pilot_seed_policy(seeds: Sequence[int] | None = None) -> None:
    chosen = tuple(int(s) for s in (seeds if seeds is not None else PILOT_SEEDS))
    if not chosen:
        raise ConfigurationError("structural RQ pilot seeds must be non-empty")
    if len(set(chosen)) != len(chosen):
        raise ConfigurationError("structural RQ pilot seeds must be unique")
    for label, sealed in (
        ("P7", SEALED_P7_SEEDS),
        ("Slowinski", SEALED_SLOWINSKI_SEEDS),
        ("persistence", SEALED_PERSISTENCE_SEEDS),
        ("mating", SEALED_MATING_SEEDS),
        ("selfing_hold", SEALED_SELFING_HOLD_SEEDS),
    ):
        overlap = sorted(set(chosen) & set(sealed))
        if overlap:
            raise ConfigurationError(
                f"sealed {label} seeds must not be reused; overlap={overlap}"
            )


def sub_loci(window: str) -> tuple[str, ...]:
    if len(window) != MATCH_BIT_WIDTH:
        raise ConfigurationError("recognition window must be 6 bits")
    w = STRUCT_SUB_LOCUS_WIDTH
    return tuple(window[i : i + w] for i in range(0, MATCH_BIT_WIDTH, w))


def graded_affinity(host_window: str, parasite_window: str) -> float:
    """Mean of independent bit-disjoint sub-locus agreement scores in [0, 1].

    Forbids AND-collapse of the full window to one exact-match bit
    (Engelstädter 2015 multi-locus / feature-overlap spirit).
    """

    host_subs = sub_loci(host_window)
    para_subs = sub_loci(parasite_window)
    if len(host_subs) != STRUCT_N_SUB_LOCI or len(para_subs) != STRUCT_N_SUB_LOCI:
        raise ConfigurationError("sub-locus partition must yield 3×2-bit alleles")
    scores: list[float] = []
    for h, p in zip(host_subs, para_subs, strict=True):
        agree = sum(1 for a, b in zip(h, p, strict=True) if a == b)
        scores.append(agree / float(STRUCT_SUB_LOCUS_WIDTH))
    return float(sum(scores) / len(scores))


def joint_match_class(window: str) -> str:
    return "|".join(sub_loci(window))


def _freq_table(windows: Sequence[str]) -> dict[str, float]:
    if not windows:
        return {}
    counts = Counter(windows)
    total = sum(counts.values())
    return {key: counts[key] / total for key in sorted(counts)}


def _richness_and_max(freq: Mapping[str, float]) -> tuple[int, float]:
    if not freq:
        return 0, 1.0
    return len(freq), max(freq.values())


def _dominant_class(freq: Mapping[str, float]) -> str | None:
    if not freq:
        return None
    best = max(freq.values())
    winners = sorted(k for k, v in freq.items() if v == best)
    return winners[0]



def dense_snap_generations(
    horizon: int, snap_stride: int | None
) -> tuple[int, ...]:
    """Generations for dense lag/phase series; empty when stride is None/<=0.

    Locked windows remain the sole hold-clause inputs. Dense generations feed
    lagged NFDS / phase clocks only and never soften the conjunctive hold.
    """

    if snap_stride is None:
        return ()
    stride = int(snap_stride)
    if stride <= 0:
        return ()
    horizon_i = int(horizon)
    return tuple(range(stride, horizon_i + 1, stride))



def assert_census_series_len(arm: "StructuralRQArm", *, generations: int) -> None:
    """Domain-free tick fidelity: host/parasite hist series length == generations.

    Falsifier for engine/arm off-by-one masking lagged clocks (WAVE8 P3).
    HP vocabulary is not introduced into ``engine.py`` by this assert.
    """

    g = int(generations)
    host_n = len(arm.host_joint_class_series)
    para_n = len(arm.parasite_class_hist_series)
    if host_n != g or para_n != g:
        raise ConfigurationError(
            f"census series length mismatch: host={host_n} parasite={para_n} "
            f"expected_generations={g}"
        )
    if arm.bolus_sync_before_census and len(arm.bolus_sync_before_census) != g:
        raise ConfigurationError(
            "bolus_sync_before_census length must equal generations"
        )



def collect_lag_clock_snaps(
    arm: "StructuralRQArm",
    *,
    horizon: int,
) -> dict[int, dict[str, object]]:
    """Every-generation snaps for lagged NFDS (τ in generations).

    Floquet/phase may subsample with ``snap_stride``; the lag clock requires
    generations ``t`` and ``t+τ`` both present. With stride=25 and τ=4, no
    pairs exist (n=0) even when parasite hist is non-empty — a wiring defect.
    """

    horizon_i = int(horizon)
    if horizon_i < 1:
        return {}
    return {int(g): arm.window_snapshot(int(g)) for g in range(1, horizon_i + 1)}


def collect_dense_snaps(
    arm: "StructuralRQArm",
    *,
    horizon: int,
    snap_stride: int | None,
) -> dict[int, dict[str, object]]:
    """Record window_snapshot every snap_stride generation (measurement only)."""

    return {
        int(g): arm.window_snapshot(int(g))
        for g in dense_snap_generations(horizon, snap_stride)
    }




@contextmanager
def _population_unique_id_guard():
    """Closed-loop guard: asexual twin births can collide on digest-based ids.

    Remap duplicate ids with a numeric suffix before PopulationState validates.
    Does not edit engine.py; HP vocabulary stays out of the engine.
    """

    original = PopulationState.__post_init__

    def _patched(self: PopulationState) -> None:
        organisms = list(self.organisms)
        seen: dict[str, int] = {}
        fixed: list[GenesisOrganism] = []
        changed = False
        for org in organisms:
            oid = org.id
            if oid not in seen:
                seen[oid] = 0
                fixed.append(org)
                continue
            seen[oid] += 1
            new_id = f"{oid}#{seen[oid]}"
            fixed.append(replace(org, id=new_id))
            changed = True
        if changed:
            object.__setattr__(self, "organisms", tuple(fixed))
            # Keep roles map coherent for newly suffixed ids when possible.
        original(self)

    PopulationState.__post_init__ = _patched  # type: ignore[method-assign]
    try:
        yield
    finally:
        PopulationState.__post_init__ = original  # type: ignore[method-assign]


@dataclass
class StructuralRQArm(LifeLoopEcologyArm):
    """Life-loop arm with Stage A–C structural locks (plugin/env only)."""

    host_bit_flip_rate: float = STRUCT_HOST_BIT_FLIP
    parasite_keep_fraction: float = STRUCT_KEEP_FRACTION
    turnover_kept: list[int] = field(default_factory=list)
    turnover_replaced: list[int] = field(default_factory=list)
    turnover_mut_events: list[int] = field(default_factory=list)
    turnover_churn: list[int] = field(default_factory=list)
    host_joint_class_series: list[tuple[tuple[str, int], ...]] = field(
        default_factory=list
    )
    host_sub_locus_series: list[tuple[tuple[tuple[str, int], ...], ...]] = field(
        default_factory=list
    )
    graded_affinity_sum: list[float] = field(default_factory=list)
    graded_contact_count: list[int] = field(default_factory=list)
    parasite_class_memory_L: int = STRUCT_PARASITE_CLASS_MEMORY_L
    parasite_class_hist_series: list[tuple[tuple[str, int], ...]] = field(
        default_factory=list
    )
    # Domain-free diagnostics (WAVE8 P3): no HP args on the observer.
    generation_boundary_observer: Callable[..., None] | None = None
    bolus_sync_before_census: list[bool] = field(default_factory=list)

    @classmethod
    def boot_structural(
        cls,
        *,
        arm: str,
        seed: int,
    ) -> StructuralRQArm:
        base = LifeLoopEcologyArm.boot(
            arm=arm,
            virulence=STRUCT_VIRULENCE,
            seed=int(seed),
            handling_time=STRUCT_HANDLING_TIME,
            birth_atp=STRUCT_BIRTH_ATP,
            parasite_n=STRUCT_PARASITE_N,
            parasite_mutation=STRUCT_PARASITE_MUTATION,
            founders=STRUCT_FOUNDERS,
            world_size=STRUCT_WORLD_SIZE,
            steal_fraction=STRUCT_STEAL_FRACTION,
            soft_carrying_capacity=STRUCT_SOFT_K,
            basal_runtime_atp_cost=STRUCT_BASAL_ATP_COST,
            passage_refill_mode=STRUCT_PASSAGE_REFILL_MODE,
            resource_bolus_amount=STRUCT_RESOURCE_BOLUS_AMOUNT,
            food_patches=STRUCT_FOOD_PATCHES,
            founder_spatial_policy=STRUCT_FOUNDER_SPATIAL_POLICY,
            two_fold_cost_sex=False,
            mating_locus_lock=False,
        )
        # Stage A: non-zero host bit-flip on the SAME PopulationRunner.
        # Mating deferred: asexual reproduction (no sexual chamber ID path).
        configs = base.runner.configs
        base.runner.configs = replace(
            configs,
            mutation=MutationConfig(bit_flip_rate=float(STRUCT_HOST_BIT_FLIP)),
            reproduction=replace(
                configs.reproduction,
                reproduction_mode=ReproductionMode.ASEXUAL,
            ),
            sexual_recombination=SexualRecombinationConfig(enabled=False),
        )
        # Stage A: parasite stock cycles the 16 distinct windows (not modal-only).
        parasite_windows = [
            _DISTINCT_WINDOWS[i % len(_DISTINCT_WINDOWS)]
            for i in range(STRUCT_PARASITE_N)
        ]
        structural = cls(
            arm=base.arm,
            passage=base.passage,
            runner=base.runner,
            roles=dict(base.roles),
            hp_env=base.hp_env,
            parasite_windows=parasite_windows,
            ancestral_window=base.ancestral_window,
            seed=base.seed,
            virulence=base.virulence,
            parasite_mutation=base.parasite_mutation,
            intro_selfing_freq=base.intro_selfing_freq,
            two_fold_cost_sex_applied=base.two_fold_cost_sex_applied,
            birth_atp=base.birth_atp,
            basal_runtime_atp_cost=base.basal_runtime_atp_cost,
            soft_carrying_capacity=base.soft_carrying_capacity,
            passage_refill_mode=base.passage_refill_mode,
            resource_bolus_amount=base.resource_bolus_amount,
            food_patches=base.food_patches,
            cumulative_resource_bolus_placed=base.cumulative_resource_bolus_placed,
            passage_refill_sync=base.passage_refill_sync,
            mating_locus_lock=base.mating_locus_lock,
            selfing_birth_atp_endowment=base.selfing_birth_atp_endowment,
            mate_search_radius=base.mate_search_radius,
            outcross_mates_per_generation_cap=base.outcross_mates_per_generation_cap,
            host_bit_flip_rate=float(STRUCT_HOST_BIT_FLIP),
            parasite_keep_fraction=float(STRUCT_KEEP_FRACTION),
        )
        return structural


    def run_generations(self, generations: int) -> dict[str, object]:
        generations = int(generations)
        if generations < 1:
            raise ConfigurationError("generations must be >= 1")
        rng = RNGManager(seed=self.seed, namespace=f"hp-struct-rq-{self.arm}")
        with _population_unique_id_guard():
            for _ in range(generations):
                # Bolus/refill at generation boundary BEFORE census append (probe).
                self._apply_passage_refill()
                bolus_before = True  # refill precedes census on this path
                result = self.runner.step_generation(seed=self.seed + self.tick_index + 1)
                self._record_births(result)
                for org in self.runner.population.organisms:
                    if org.id not in self.roles:
                        self.roles[org.id] = ROLE_PRIMARY
                debit_count, matched = self._apply_hp_env_contact()
                self.match_debits_by_generation.append(int(debit_count))
                self._passage_update(matched, rng.fork(f"passage/{self.tick_index}"))
                self._census()
                self.bolus_sync_before_census.append(bool(bolus_before))
                self.tick_index += 1
                observer = self.generation_boundary_observer
                if observer is not None:
                    # Domain-free: generation index only (no HP args).
                    observer(generation_index=int(self.tick_index))
        assert_census_series_len(self, generations=generations)
        return self.summary()

    def _apply_hp_env_contact(self) -> tuple[int, list[str]]:
        """Graded feature-overlap debit; forbid AND-exact composite as multi-locus."""

        if self.passage == PASSAGE_ABSENT:
            self.graded_affinity_sum.append(0.0)
            self.graded_contact_count.append(0)
            return 0, []
        hosts = self._hosts()
        if not hosts or not self.parasite_windows:
            self.graded_affinity_sum.append(0.0)
            self.graded_contact_count.append(0)
            return 0, []
        self._reset_env_hosts()
        # Register a shared always-present task so inject seat is available;
        # debit magnitude is driven by graded affinity, not exact-window AND.
        shared_task = "structural_contact"
        for org in hosts:
            self.hp_env.add_host(org.id, [shared_task])

        matched_windows: list[str] = []
        debit_count = 0
        aff_sum = 0.0
        contacts = 0
        # One parasite–host pair per seat per generation (no multi-hit pile-on).
        pair_n = min(len(hosts), len(self.parasite_windows))
        host_order = list(range(len(hosts)))
        # Deterministic rotate by tick so pairing is not always index-0 biased.
        rot = int(self.tick_index) % max(1, len(host_order))
        host_order = host_order[rot:] + host_order[:rot]
        for p_index in range(pair_n):
            host = hosts[host_order[p_index]]
            p_window = self.parasite_windows[p_index]
            host_window = _window(host)
            affinity = graded_affinity(host_window, p_window)
            contacts += 1
            aff_sum += affinity
            if affinity <= 0.0:
                continue
            self.hp_env.try_horizontal_inject(
                host_id=host.id,
                parasite_id=f"p{self.tick_index}-{p_index}",
                parasite_tasks=[shared_task],
                payload=(1,),
            )
            # Graded debit: f(independent bit-disjoint sub-scores) × virulence × steal.
            debit = float(self.virulence) * float(self.hp_env.steal_fraction) * float(
                affinity
            )
            if debit > 0.0:
                payable = min(host.atp_state.runtime_available, debit)
                if payable > 0.0:
                    host.atp_state.debit_runtime(
                        payable,
                        tick=self.tick_index,
                        organism_id=host.id,
                        codon="000",
                        action="HP_ENV_MATCH",
                        reason=HP_ENV_MATCH_REASON,
                    )
                    debit_count += 1
                    matched_windows.append(host_window)
        survivors = [
            org
            for org in self.runner.population.organisms
            if org.atp_state.runtime_available > 0.0
            or self.roles.get(org.id) != ROLE_PRIMARY
        ]
        self.runner.population = replace(
            self.runner.population, organisms=tuple(survivors)
        )
        self.graded_affinity_sum.append(aff_sum)
        self.graded_contact_count.append(contacts)
        return debit_count, matched_windows

    def _passage_update(self, matched_windows: Sequence[str], rng: RNGManager) -> None:
        """Mid-κ partial keep-fraction on copassaged; freeze on fixed; empty on absent."""

        if self.passage == PASSAGE_ABSENT:
            self.parasite_windows = []
            self.turnover_kept.append(0)
            self.turnover_replaced.append(0)
            self.turnover_mut_events.append(0)
            self.turnover_churn.append(0)
            return
        n = len(self.parasite_windows) or STRUCT_PARASITE_N
        if self.passage == PASSAGE_FROZEN:
            # Frozen stock: restore ancestral multiset (16-cycle), no κ replace.
            self.parasite_windows = [
                _DISTINCT_WINDOWS[i % len(_DISTINCT_WINDOWS)] for i in range(n)
            ]
            self.turnover_kept.append(n)
            self.turnover_replaced.append(0)
            self.turnover_mut_events.append(0)
            self.turnover_churn.append(0)
            return
        if self.passage != PASSAGE_COEVOLVE:
            self.turnover_kept.append(n)
            self.turnover_replaced.append(0)
            self.turnover_mut_events.append(0)
            self.turnover_churn.append(0)
            return

        kappa = float(self.parasite_keep_fraction)
        keep_n = int(kappa * n)
        if keep_n < 0:
            keep_n = 0
        if keep_n > n:
            keep_n = n
        replace_n = n - keep_n
        current = list(self.parasite_windows)
        before_unique = len(set(current))
        # Keep a random subset (partial replace, not wipe/freeze).
        order = list(range(len(current)))
        for i in range(len(order) - 1, 0, -1):
            j = rng.randrange(0, i + 1)
            order[i], order[j] = order[j], order[i]
        kept = [current[order[i]] for i in range(keep_n)]
        source = list(matched_windows) if matched_windows else list(current)
        if not source:
            source = list(_DISTINCT_WINDOWS)
        nxt = list(kept)
        mut_events = 0
        for _ in range(replace_n):
            parent = source[rng.randrange(0, len(source))]
            window = parent
            if self.parasite_mutation > 0.0 and rng.random() < self.parasite_mutation:
                window = _mutate_window(window, rng)
                mut_events += 1
            nxt.append(window)
        # Pad if keep/replace rounding left short (should not).
        while len(nxt) < n:
            nxt.append(source[rng.randrange(0, len(source))])
        self.parasite_windows = nxt[:n]
        after_unique = len(set(self.parasite_windows))
        self.turnover_kept.append(keep_n)
        self.turnover_replaced.append(replace_n)
        self.turnover_mut_events.append(mut_events)
        self.turnover_churn.append(abs(after_unique - before_unique))

    def _census(self) -> None:
        super()._census()
        hosts = self._hosts()
        windows = [_window(org) for org in hosts]
        joint_counts = Counter(joint_match_class(w) for w in windows if len(w) == MATCH_BIT_WIDTH)
        self.host_joint_class_series.append(tuple(sorted(joint_counts.items())))
        sub_tables: list[tuple[tuple[str, int], ...]] = []
        for locus_i in range(STRUCT_N_SUB_LOCI):
            alleles = []
            for w in windows:
                if len(w) != MATCH_BIT_WIDTH:
                    continue
                alleles.append(sub_loci(w)[locus_i])
            sub_tables.append(tuple(sorted(Counter(alleles).items())))
        self.host_sub_locus_series.append(tuple(sub_tables))
        # Parasite match-class histogram (plugin/arm only; not engine.py).
        p_counts = Counter(
            joint_match_class(w)
            for w in self.parasite_windows
            if len(w) == MATCH_BIT_WIDTH
        )
        self.parasite_class_hist_series.append(tuple(sorted(p_counts.items())))

    def window_snapshot(self, generation: int) -> dict[str, object]:
        """Allelic snapshot at 1-indexed generation (locked windows only)."""

        idx = int(generation) - 1
        empty = {
            "generation": int(generation),
            "census": 0,
            "parasite_n": 0,
            "joint_freq": {},
            "joint_richness": 0,
            "joint_max_freq": 1.0,
            "dominant_joint": None,
            "sub_locus_freqs": [],
            "sub_locus_richness": [],
            "parasite_class_hist": {},
            "parasite_class_hist_lag": [],
        }
        if idx < 0 or idx >= len(self.host_joint_class_series):
            return empty
        joint_pairs = self.host_joint_class_series[idx]
        total = sum(c for _, c in joint_pairs)
        joint_freq = (
            {k: c / total for k, c in joint_pairs} if total > 0 else {}
        )
        richness, max_f = _richness_and_max(joint_freq)
        sub_freqs: list[dict[str, float]] = []
        sub_rich: list[int] = []
        if idx < len(self.host_sub_locus_series):
            for pairs in self.host_sub_locus_series[idx]:
                st = sum(c for _, c in pairs)
                freq = {k: c / st for k, c in pairs} if st > 0 else {}
                sub_freqs.append(freq)
                sub_rich.append(len(freq))
        census = 0
        if idx < len(self.outcross_by_generation) and idx < len(self.selfing_by_generation):
            census = int(self.outcross_by_generation[idx]) + int(
                self.selfing_by_generation[idx]
            )
        parasite_n = 0
        if idx < len(self.parasite_frequencies):
            parasite_n = sum(c for _, c in self.parasite_frequencies[idx])
        # Parasite class hist + lag ring (Zaman memory analog; arm/plugin only).
        parasite_class_hist: dict[str, float] = {}
        if idx < len(self.parasite_class_hist_series):
            p_pairs = self.parasite_class_hist_series[idx]
            p_total = sum(c for _, c in p_pairs)
            parasite_class_hist = (
                {k: c / p_total for k, c in p_pairs} if p_total > 0 else {}
            )
        mem_l = int(self.parasite_class_memory_L)
        if mem_l < 1:
            mem_l = int(STRUCT_PARASITE_CLASS_MEMORY_L)
        lag_start = max(0, idx + 1 - mem_l)
        parasite_class_hist_lag: list[dict[str, float]] = []
        for j in range(lag_start, idx + 1):
            if j >= len(self.parasite_class_hist_series):
                break
            pairs = self.parasite_class_hist_series[j]
            tot = sum(c for _, c in pairs)
            parasite_class_hist_lag.append(
                {k: c / tot for k, c in pairs} if tot > 0 else {}
            )
        return {
            "generation": int(generation),
            "census": census,
            "parasite_n": parasite_n,
            "joint_freq": joint_freq,
            "joint_richness": richness,
            "joint_max_freq": max_f,
            "dominant_joint": _dominant_class(joint_freq),
            "sub_locus_freqs": sub_freqs,
            "sub_locus_richness": sub_rich,
            "parasite_class_hist": parasite_class_hist,
            "parasite_class_hist_lag": parasite_class_hist_lag,
        }

    def turnover_audit(self) -> dict[str, object]:
        if not self.turnover_kept:
            return {
                "mean_keep_fraction": None,
                "mean_replaced": None,
                "mean_mut_events": None,
                "mean_churn": None,
                "mid_keep_ok": False,
            }
        n = len(self.turnover_kept)
        keep_fracs = []
        for kept, replaced in zip(self.turnover_kept, self.turnover_replaced, strict=True):
            denom = kept + replaced
            keep_fracs.append(kept / denom if denom else 0.0)
        # Mid-window mean keep fraction on locked mid gens
        mid_vals = []
        for gen in STRUCT_MID_WINDOWS:
            idx = gen - 1
            if 0 <= idx < len(keep_fracs):
                mid_vals.append(keep_fracs[idx])
        mean_keep = sum(keep_fracs) / n
        mean_mid = sum(mid_vals) / len(mid_vals) if mid_vals else None
        mid_ok = True
        if self.passage == PASSAGE_COEVOLVE and mean_mid is not None:
            lo = STRUCT_KEEP_FRACTION - STRUCT_KAPPA_TOLERANCE
            hi = STRUCT_KEEP_FRACTION + STRUCT_KAPPA_TOLERANCE
            mid_ok = lo <= mean_mid <= hi
        elif self.passage == PASSAGE_FROZEN:
            mid_ok = True  # freeze expected; κ N/A
        return {
            "mean_keep_fraction": mean_keep,
            "mean_mid_keep_fraction": mean_mid,
            "mean_replaced": sum(self.turnover_replaced) / n,
            "mean_mut_events": sum(self.turnover_mut_events) / n,
            "mean_churn": sum(self.turnover_churn) / n,
            "mid_keep_ok": mid_ok,
            "kappa_locked": STRUCT_KEEP_FRACTION,
            "mut_locked": STRUCT_PARASITE_MUTATION,
        }


def _polymorphism_ok(snap: Mapping[str, object]) -> bool:
    """Hold gate on match-class freqs — never soft-K body census as Ne proxy."""

    richness = int(snap.get("joint_richness") or 0)
    max_f = float(snap.get("joint_max_freq") or 1.0)
    if richness >= STRUCT_R_MIN and max_f <= (1.0 - STRUCT_EPSILON):
        return True
    # Alternate prereg clause: ≥2 distinct alleles on ≥2 of 3 sub-loci
    # AND joint max_f ≤ 1-ε
    sub_rich = [int(x) for x in (snap.get("sub_locus_richness") or [])]
    loci_diverse = sum(1 for r in sub_rich if r >= 2)
    if loci_diverse >= 2 and max_f <= (1.0 - STRUCT_EPSILON) and richness >= 2:
        return True
    return False


def classify_structural_outcome(
    *,
    arm_snaps: Mapping[str, Mapping[int, Mapping[str, object]]],
    turnover_by_arm: Mapping[str, Mapping[str, object]],
) -> str:
    """Mutually exclusive typed ladder (storm four-role + regime auxiliaries)."""

    # Parasite extinct on any debit-active arm before terminal
    for arm in DEBIT_ACTIVE_ARMS:
        snaps = arm_snaps.get(arm, {})
        for gen in STRUCT_LOCKED_WINDOWS:
            snap = snaps.get(gen)
            if snap is None:
                return OUTCOME_PARASITE_EXTINCT
            if int(snap.get("parasite_n") or 0) <= 0:
                return OUTCOME_PARASITE_EXTINCT

    # Demographic gate (not Ne proxy): living census floor
    for arm in DEBIT_ACTIVE_ARMS:
        snaps = arm_snaps.get(arm, {})
        for gen in STRUCT_LOCKED_WINDOWS:
            snap = snaps[gen]
            if int(snap.get("census") or 0) < STRUCT_MIN_VIABLE_CENSUS:
                return OUTCOME_REGIME_HOSTILE_NE

    # Stage A contract: founder richness ≫2 already locked; bit-flip locked in boot
    if len(_DISTINCT_WINDOWS) < 8 or STRUCT_HOST_BIT_FLIP <= 0.0:
        return OUTCOME_REGIME_HOSTILE_NE
    if not (50 <= STRUCT_HOST_N <= 100 and 50 <= STRUCT_SOFT_K <= 100):
        return OUTCOME_REGIME_HOSTILE_NE

    # Turnover mid-κ audit on copassaged
    cop_audit = turnover_by_arm.get(ARM_COPASSAGED, {})
    if not bool(cop_audit.get("mid_keep_ok", False)):
        return OUTCOME_REGIME_HOSTILE_TURNOVER

    # Sweep vs hold vs horizon across locked windows on debit-active arms
    mid_all_hold = True
    terminal_all_hold = True
    any_mid_fail = False
    any_terminal_fail = False
    for arm in DEBIT_ACTIVE_ARMS:
        snaps = arm_snaps[arm]
        for gen in STRUCT_MID_WINDOWS:
            ok = _polymorphism_ok(snaps[gen])
            if not ok:
                mid_all_hold = False
                any_mid_fail = True
        tok = _polymorphism_ok(snaps[STRUCT_TERMINAL_WINDOW])
        if not tok:
            terminal_all_hold = False
            any_terminal_fail = True

    if any_mid_fail or any_terminal_fail:
        # Mid holds but terminal fails → horizon_insufficient; else sweep
        if mid_all_hold and any_terminal_fail:
            return OUTCOME_HORIZON_INSUFFICIENT
        return OUTCOME_SWEEP_FIXATION

    if mid_all_hold and terminal_all_hold:
        return OUTCOME_POLYMORPHISM_HOLD

    return OUTCOME_HORIZON_INSUFFICIENT


def _oscillation_on_arm(snaps: Mapping[int, Mapping[str, object]]) -> bool:
    doms = [_dominant_class(snaps[g].get("joint_freq") or {}) for g in STRUCT_LOCKED_WINDOWS]
    if any(d is None for d in doms):
        return False
    changes = 0
    for a, b in zip(doms, doms[1:], strict=False):
        if a != b:
            changes += 1
    return changes >= 2


def apply_cycle_candidate_upgrade(
    *,
    seed_outcomes: Mapping[int, str],
    snaps_by_seed_arm: Mapping[int, Mapping[str, Mapping[int, Mapping[str, object]]]],
) -> dict[int, str]:
    """Observation-only upgrade: polymorphism_hold → cycle_candidate with concordance.

    Never grants red_queen_proved. SPC/CUSUM are not the accept path.
    """

    upgraded = dict(seed_outcomes)
    hold_seeds = [
        s for s, o in seed_outcomes.items() if o == OUTCOME_POLYMORPHISM_HOLD
    ]
    oscillating: list[int] = []
    for seed in hold_seeds:
        arm_map = snaps_by_seed_arm[seed]
        if all(_oscillation_on_arm(arm_map[arm]) for arm in DEBIT_ACTIVE_ARMS):
            oscillating.append(seed)
    # Multi-seed concordance: ≥2 of 3 pilot seeds agree
    if len(oscillating) >= 2:
        for seed in oscillating:
            upgraded[seed] = OUTCOME_CYCLE_CANDIDATE
    return upgraded


@dataclass(frozen=True, slots=True)
class StructuralRQSeedResult:
    seed: int
    typed_outcome: str
    claim_ceiling: str
    snaps_by_arm: dict[str, dict[int, dict[str, object]]]
    turnover_by_arm: dict[str, dict[str, object]]
    terminal_census_by_arm: dict[str, int]
    digest: str
    slowinski_scored: bool
    red_queen_proved: bool
    dense_snaps_by_arm: dict[str, dict[int, dict[str, object]]] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "typed_outcome": self.typed_outcome,
            "claim_ceiling": self.claim_ceiling,
            "snaps_by_arm": self.snaps_by_arm,
            "dense_snaps_by_arm": self.dense_snaps_by_arm,
            "turnover_by_arm": self.turnover_by_arm,
            "terminal_census_by_arm": dict(self.terminal_census_by_arm),
            "digest": self.digest,
            "slowinski_scored": self.slowinski_scored,
            "red_queen_proved": self.red_queen_proved,
            "biological_red_queen_proved": False,
            "estimand": ESTIMAND,
            "substrate": SUBSTRATE_LIFE_LOOP,
            "primary_success_is_polymorphism_hold": True,
            "cycle_candidate_observation_only": True,
        }


@dataclass(frozen=True, slots=True)
class StructuralRQCampaignReport:
    seeds: tuple[int, ...]
    seed_results: tuple[StructuralRQSeedResult, ...]
    typed_outcome_counts: dict[str, int]
    seeds_polymorphism_hold: int
    seeds_cycle_candidate: int
    claim_ceiling: str
    red_queen_proved: bool
    biological_red_queen_proved: bool
    design_digest: str
    document_digest: str
    digest: str
    notes: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "hp_arm01_structural_rq_pilot_v1",
            "prereg_version": PREREG_VERSION,
            "revision": HP_ARM01_STRUCTURAL_RQ_REVISION,
            "slice": SLICE_NAME,
            "estimand": ESTIMAND,
            "substrate": SUBSTRATE_LIFE_LOOP,
            "seeds": list(self.seeds),
            "seed_results": [r.to_dict() for r in self.seed_results],
            "typed_outcome_counts": dict(self.typed_outcome_counts),
            "seeds_polymorphism_hold": self.seeds_polymorphism_hold,
            "seeds_cycle_candidate": self.seeds_cycle_candidate,
            "primary_success": OUTCOME_POLYMORPHISM_HOLD,
            "claim_ceiling": self.claim_ceiling,
            "red_queen_proved": self.red_queen_proved,
            "biological_red_queen_proved": self.biological_red_queen_proved,
            "design_digest": self.design_digest,
            "document_digest": self.document_digest,
            "digest": self.digest,
            "generations": STRUCT_GENERATIONS,
            "locked_windows": list(STRUCT_LOCKED_WINDOWS),
            "snap_stride": STRUCT_SNAP_STRIDE,
            "parasite_class_memory_L": STRUCT_PARASITE_CLASS_MEMORY_L,
            "r_min": STRUCT_R_MIN,
            "epsilon": STRUCT_EPSILON,
            "kappa": STRUCT_KEEP_FRACTION,
            "parasite_mutation": STRUCT_PARASITE_MUTATION,
            "host_bit_flip_rate": STRUCT_HOST_BIT_FLIP,
            "host_n": STRUCT_HOST_N,
            "parasite_n": STRUCT_PARASITE_N,
            "soft_carrying_capacity": STRUCT_SOFT_K,
            "virulence": STRUCT_VIRULENCE,
            "steal_fraction": STRUCT_STEAL_FRACTION,
            "slowinski_scored": False,
            "mating_deferred": True,
            "sealed_fails_untouched": ["214df20", "91ab0c6", "7171d19"],
            "spc_owns_accept_path": False,
            "notes": self.notes,
        }


def run_structural_rq_pilot(
    *,
    seeds: Sequence[int] | None = None,
    generations: int | None = None,
) -> StructuralRQCampaignReport:
    """Run the locked Stage A–D structural RQ pilot (Slowinski unscored)."""

    chosen = tuple(int(s) for s in (seeds if seeds is not None else PILOT_SEEDS))
    gens = int(STRUCT_GENERATIONS if generations is None else generations)
    assert_pilot_seed_policy(chosen)
    if gens < STRUCT_GENERATIONS:
        raise ConfigurationError(
            f"structural RQ pilot horizon locked at {STRUCT_GENERATIONS}; got {gens}"
        )
    assert_ecology_arm_taxonomy()

    design = structural_rq_design_digest()
    document = structural_rq_document_digest()

    raw_outcomes: dict[int, str] = {}
    snaps_by_seed_arm: dict[int, dict[str, dict[int, dict[str, object]]]] = {}
    seed_payloads: list[dict[str, object]] = []

    for seed in chosen:
        arms: dict[str, StructuralRQArm] = {}
        snaps_by_arm: dict[str, dict[int, dict[str, object]]] = {}
        dense_snaps_by_arm: dict[str, dict[int, dict[str, object]]] = {}
        turnover_by_arm: dict[str, dict[str, object]] = {}
        census: dict[str, int] = {}
        for arm_name in ECOLOGY_ARMS:
            arm = StructuralRQArm.boot_structural(arm=arm_name, seed=seed)
            # Verify Stage A co-requirement on same runner
            bf = float(arm.runner.configs.mutation.bit_flip_rate)
            if bf <= 0.0:
                raise ConfigurationError("Stage A requires host bit-flip > 0 on runner")
            if arm.soft_carrying_capacity < 50:
                raise ConfigurationError("Stage A requires soft K in 50–100 on same runner")
            arm.run_generations(gens)
            arms[arm_name] = arm
            snaps_by_arm[arm_name] = {
                int(g): arm.window_snapshot(int(g)) for g in STRUCT_LOCKED_WINDOWS
            }
            turnover_by_arm[arm_name] = arm.turnover_audit()
            census[arm_name] = int(arm.living_host_census())

        typed = classify_structural_outcome(
            arm_snaps=snaps_by_arm, turnover_by_arm=turnover_by_arm
        )
        # Mating/Slowinski deferred: never emit invasion labels; if somehow
        # selfing path invoked, force Slowinski_unscored rather than PASS.
        if typed in {"invasion_pass", "invasion_fail"}:
            typed = OUTCOME_SLOWINSKI_UNSCORED
        raw_outcomes[seed] = typed
        snaps_by_seed_arm[seed] = snaps_by_arm
        seed_payloads.append(
            {
                "seed": seed,
                "typed_raw": typed,
                "snaps_by_arm": snaps_by_arm,
                "dense_snaps_by_arm": dense_snaps_by_arm,
                "turnover_by_arm": turnover_by_arm,
                "terminal_census_by_arm": census,
            }
        )

    final_outcomes = apply_cycle_candidate_upgrade(
        seed_outcomes=raw_outcomes, snaps_by_seed_arm=snaps_by_seed_arm
    )

    hold_or_cycle = any(
        o in {OUTCOME_POLYMORPHISM_HOLD, OUTCOME_CYCLE_CANDIDATE}
        for o in final_outcomes.values()
    )
    # Ceiling: runtime_observation until polymorphism_hold; then ≤ candidate
    # for cycle_candidate only; never RQ proved.
    if any(o == OUTCOME_POLYMORPHISM_HOLD for o in final_outcomes.values()) or any(
        o == OUTCOME_CYCLE_CANDIDATE for o in final_outcomes.values()
    ):
        # Climb allowed only when hold earned; cycle_candidate reporting ≤ candidate
        ceiling = (
            CLAIM_CEILING_CANDIDATE
            if hold_or_cycle
            else CLAIM_CEILING_OBSERVATION
        )
    else:
        ceiling = CLAIM_CEILING_OBSERVATION
    # Hard rule: never equate clocks with RQ; RQ flags stay false
    if not any(
        o == OUTCOME_POLYMORPHISM_HOLD for o in final_outcomes.values()
    ) and not any(o == OUTCOME_CYCLE_CANDIDATE for o in final_outcomes.values()):
        ceiling = CLAIM_CEILING_OBSERVATION

    results: list[StructuralRQSeedResult] = []
    for payload in seed_payloads:
        seed = int(payload["seed"])
        typed = final_outcomes[seed]
        seed_ceiling = (
            CLAIM_CEILING_CANDIDATE
            if typed in {OUTCOME_POLYMORPHISM_HOLD, OUTCOME_CYCLE_CANDIDATE}
            and ceiling == CLAIM_CEILING_CANDIDATE
            else CLAIM_CEILING_OBSERVATION
        )
        body = {
            "seed": seed,
            "typed": typed,
            "census": payload["terminal_census_by_arm"],
            "revision": HP_ARM01_STRUCTURAL_RQ_REVISION,
        }
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        results.append(
            StructuralRQSeedResult(
                seed=seed,
                typed_outcome=typed,
                claim_ceiling=seed_ceiling,
                snaps_by_arm=payload["snaps_by_arm"],  # type: ignore[arg-type]
                turnover_by_arm=payload["turnover_by_arm"],  # type: ignore[arg-type]
                terminal_census_by_arm=payload["terminal_census_by_arm"],  # type: ignore[arg-type]
                digest=digest,
                slowinski_scored=False,
                red_queen_proved=False,
                dense_snaps_by_arm=payload.get("dense_snaps_by_arm", {}),  # type: ignore[arg-type]
            )
        )

    counts = {label: 0 for label in sorted(TYPED_OUTCOMES)}
    for row in results:
        counts[row.typed_outcome] = counts.get(row.typed_outcome, 0) + 1
    n_hold = sum(1 for r in results if r.typed_outcome == OUTCOME_POLYMORPHISM_HOLD)
    n_cycle = sum(1 for r in results if r.typed_outcome == OUTCOME_CYCLE_CANDIDATE)

    report_body = {
        "seeds": list(chosen),
        "counts": counts,
        "design": design,
        "document": document,
        "ceiling": ceiling,
        "revision": HP_ARM01_STRUCTURAL_RQ_REVISION,
    }
    report_digest = hashlib.sha256(
        json.dumps(report_body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    notes = (
        f"primary_success=polymorphism_hold;hold={n_hold};cycle_candidate_obs={n_cycle};"
        f"slowinski_scored=false;red_queen_proved=false;kappa={STRUCT_KEEP_FRACTION};"
        f"host_bit_flip={STRUCT_HOST_BIT_FLIP};N={STRUCT_HOST_N}"
    )
    return StructuralRQCampaignReport(
        seeds=chosen,
        seed_results=tuple(results),
        typed_outcome_counts=counts,
        seeds_polymorphism_hold=n_hold,
        seeds_cycle_candidate=n_cycle,
        claim_ceiling=ceiling,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        design_digest=design,
        document_digest=document,
        digest=report_digest,
        notes=notes,
    )


__all__ = [
    "ESTIMAND",
    "HP_ARM01_STRUCTURAL_RQ_REVISION",
    "OUTCOME_CYCLE_CANDIDATE",
    "OUTCOME_HORIZON_INSUFFICIENT",
    "OUTCOME_PARASITE_EXTINCT",
    "OUTCOME_POLYMORPHISM_HOLD",
    "OUTCOME_REGIME_HOSTILE_NE",
    "OUTCOME_REGIME_HOSTILE_TURNOVER",
    "OUTCOME_SELFING_NONVIABLE",
    "OUTCOME_SLOWINSKI_UNSCORED",
    "OUTCOME_SWEEP_FIXATION",
    "PILOT_SEEDS",
    "PREREG_VERSION",
    "SLICE_NAME",
    "STRUCT_FOUNDERS",
    "STRUCT_GENERATIONS",
    "StructuralRQArm",
    "StructuralRQCampaignReport",
    "StructuralRQSeedResult",
    "TYPED_OUTCOMES",
    "apply_cycle_candidate_upgrade",
    "assert_pilot_seed_policy",
    "classify_structural_outcome",
    "assert_census_series_len",
    "collect_dense_snaps",
    "collect_lag_clock_snaps",
    "dense_snap_generations",
    "graded_affinity",
    "joint_match_class",
    "locked_design_dict",
    "prereg_document_path",
    "run_structural_rq_pilot",
    "structural_rq_design_digest",
    "structural_rq_document_digest",
    "sub_loci",
]
