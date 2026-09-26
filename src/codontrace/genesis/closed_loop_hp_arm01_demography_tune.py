"""HP-ARM01 demography-only tune — Stage 0 before RQ-earn confirm.

Estimand: debit-arm demographic readability under antagonist load.
Does **not** score polymorphism, lagged NFDS, or Red Queen clocks.

Grid (prereg ≤3 cells): bolus×patches ∈ {(24,20), (28,20), (24,24)}.
Seeds 751–758 @ 500 gens. Soft K=64 fixed. min_viable=12.
Primary success: both debit arms census ≥ min_viable at every locked window.
Campaign PASS for a cell: ≥6/8 seeds demography_ok.

Standing locks: no infection in engine.py; red_queen_proved stays False;
sealed 701–708 / FAILS untouched; Soft K not raised as Ne fix.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Mapping, Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import ReproductionMode, SexualRecombinationConfig
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.closed_loop_hp_arm01 import (
    ARM_COPASSAGED,
    ARM_FIXED,
    CLAIM_CEILING_OBSERVATION,
    PASSAGE_REFILL_GENERATION_BOUNDARY,
    SUBSTRATE_LIFE_LOOP,
    LifeLoopEcologyArm,
    assert_ecology_arm_taxonomy,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    DEBIT_ACTIVE_ARMS,
    OUTCOME_HORIZON_INSUFFICIENT,
    OUTCOME_PARASITE_EXTINCT,
    OUTCOME_REGIME_HOSTILE_NE,
    PILOT_SEEDS,
    SEALED_MATING_SEEDS,
    SEALED_P7_SEEDS,
    SEALED_PERSISTENCE_SEEDS,
    SEALED_SELFING_HOLD_SEEDS,
    SEALED_SLOWINSKI_SEEDS,
    STRUCT_BASAL_ATP_COST,
    STRUCT_BIRTH_ATP,
    STRUCT_FOUNDER_SPATIAL_POLICY,
    STRUCT_FOUNDERS,
    STRUCT_HANDLING_TIME,
    STRUCT_HOST_BIT_FLIP,
    STRUCT_HOST_N,
    STRUCT_KEEP_FRACTION,
    STRUCT_MIN_VIABLE_CENSUS,
    STRUCT_PARASITE_MUTATION,
    STRUCT_PARASITE_N,
    STRUCT_SOFT_K,
    STRUCT_STEAL_FRACTION,
    STRUCT_VIRULENCE,
    StructuralRQArm,
    _DISTINCT_WINDOWS,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq_confirm import (
    CONFIRM_SEEDS,
)
from codontrace.genesis.population import MutationConfig

PREREG_VERSION = "hp_arm01_demography_tune_prereg_20260926"
HP_ARM01_DEMOGRAPHY_TUNE_REVISION = "hp-arm01-demography-tune-20260926"
SLICE_NAME = "HP-ARM01-RQ-EARN-DEMOGRAPHY-TUNE"
ESTIMAND = "debit_arm_demographic_readability_under_antagonist_load"
PREREG_RELATIVE_PATH = (
    "docs/handoff/WAVE7_DEMOGRAPHY_TUNE_PREREG_20260926.md"
)

DEMOGRAPHY_SEEDS: tuple[int, ...] = (751, 752, 753, 754, 755, 756, 757, 758)
DEMOGRAPHY_GENERATIONS = 500
DEMOGRAPHY_LOCKED_WINDOWS: tuple[int, ...] = (125, 250, 500)
DEMOGRAPHY_PASS_BAR = 6
DEMOGRAPHY_WORLD_SIZE = 20
DEMOGRAPHY_MIN_VIABLE = STRUCT_MIN_VIABLE_CENSUS  # 12
DEMOGRAPHY_SOFT_K = STRUCT_SOFT_K  # 64 fixed

OUTCOME_DEMOGRAPHY_OK = "demography_ok"
DEMOGRAPHY_TYPED_OUTCOMES: frozenset[str] = frozenset(
    {
        OUTCOME_DEMOGRAPHY_OK,
        OUTCOME_REGIME_HOSTILE_NE,
        OUTCOME_PARASITE_EXTINCT,
        OUTCOME_HORIZON_INSUFFICIENT,
    }
)

# Pre-registered grid ≤3 cells: (bolus, n_patches)
DEMOGRAPHY_GRID: tuple[tuple[float, int], ...] = (
    (24.0, 20),
    (28.0, 20),
    (24.0, 24),
)


def make_food_patches(n_patches: int, *, world_size: int = DEMOGRAPHY_WORLD_SIZE) -> tuple[tuple[int, int], ...]:
    """Build an interleaved food-patch lattice that fits in world_size×world_size."""

    n = int(n_patches)
    if n <= 0:
        raise ConfigurationError("n_patches must be positive")
    w = int(world_size)
    # Prefer a near-rectangular layout (cols × rows) inside the world.
    cols = min(w, max(1, int(round(n ** 0.5))))
    while cols > 1 and (n % cols) != 0 and cols < w:
        # Prefer exact factors when possible; otherwise widen.
        cols += 1
        if cols > w:
            cols = w
            break
    # Fall back: walk row-major until n patches placed.
    patches: list[tuple[int, int]] = []
    for idx in range(n):
        x = idx % w
        y = (idx // w) % w
        patches.append((x, y))
    # Prefer compact rectangular when n factors cleanly.
    for c in range(1, w + 1):
        if n % c == 0:
            r = n // c
            if r <= w:
                patches = [(x, y) for x in range(c) for y in range(r)]
                break
    if len(patches) != n:
        raise ConfigurationError(f"failed to place {n} patches in world {w}")
    # Deduplicate while preserving order.
    seen: set[tuple[int, int]] = set()
    unique: list[tuple[int, int]] = []
    for p in patches:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    if len(unique) != n:
        raise ConfigurationError(
            f"patch lattice collision for n={n} world={w}; got {len(unique)} unique"
        )
    return tuple(unique)


def assert_demography_seed_policy(seeds: Sequence[int] | None = None) -> None:
    chosen = tuple(int(s) for s in (seeds if seeds is not None else DEMOGRAPHY_SEEDS))
    if not chosen:
        raise ConfigurationError("demography seeds must be non-empty")
    if len(set(chosen)) != len(chosen):
        raise ConfigurationError("demography seeds must be unique")
    forbidden = (
        ("P7", SEALED_P7_SEEDS),
        ("Slowinski", SEALED_SLOWINSKI_SEEDS),
        ("persistence", SEALED_PERSISTENCE_SEEDS),
        ("mating", SEALED_MATING_SEEDS),
        ("selfing_hold", SEALED_SELFING_HOLD_SEEDS),
        ("pilot_structural_rq", PILOT_SEEDS),
        ("structural_confirm", CONFIRM_SEEDS),
    )
    for label, sealed in forbidden:
        overlap = sorted(set(chosen) & set(sealed))
        if overlap:
            raise ConfigurationError(
                f"sealed {label} seeds must not be reused; overlap={overlap}"
            )
    # Stage 1 seeds reserved
    rq_earn_reserved = set(range(801, 817))
    overlap_rq = sorted(set(chosen) & rq_earn_reserved)
    if overlap_rq:
        raise ConfigurationError(
            f"RQ-earn confirm seeds must not be reused in Stage 0; overlap={overlap_rq}"
        )


def demography_design_dict(
    *,
    bolus: float,
    n_patches: int,
) -> dict[str, object]:
    patches = make_food_patches(n_patches)
    return {
        "prereg_version": PREREG_VERSION,
        "revision": HP_ARM01_DEMOGRAPHY_TUNE_REVISION,
        "slice": SLICE_NAME,
        "estimand": ESTIMAND,
        "substrate": SUBSTRATE_LIFE_LOOP,
        "seeds": list(DEMOGRAPHY_SEEDS),
        "generations": DEMOGRAPHY_GENERATIONS,
        "locked_windows": list(DEMOGRAPHY_LOCKED_WINDOWS),
        "min_viable_census": DEMOGRAPHY_MIN_VIABLE,
        "soft_carrying_capacity": DEMOGRAPHY_SOFT_K,
        "soft_k_fixed_forbid_raise_as_ne_fix": True,
        "resource_bolus_amount": float(bolus),
        "n_food_patches": int(n_patches),
        "food_patches": [list(p) for p in patches],
        "world_size": DEMOGRAPHY_WORLD_SIZE,
        "host_n": STRUCT_HOST_N,
        "parasite_n": STRUCT_PARASITE_N,
        "virulence": STRUCT_VIRULENCE,
        "steal_fraction": STRUCT_STEAL_FRACTION,
        "kappa": STRUCT_KEEP_FRACTION,
        "host_bit_flip_rate": STRUCT_HOST_BIT_FLIP,
        "parasite_mutation": STRUCT_PARASITE_MUTATION,
        "debit_active_arms": list(DEBIT_ACTIVE_ARMS),
        "score_polymorphism": False,
        "score_lagged_nfds": False,
        "score_rq": False,
        "primary_success": OUTCOME_DEMOGRAPHY_OK,
        "campaign_pass_bar": DEMOGRAPHY_PASS_BAR,
        "campaign_n": len(DEMOGRAPHY_SEEDS),
        "grid_cells": [list(c) for c in DEMOGRAPHY_GRID],
        "typed_outcomes": sorted(DEMOGRAPHY_TYPED_OUTCOMES),
        "red_queen_proved_allowed": False,
        "biological_red_queen_proved_allowed": False,
        "claim_ceiling": CLAIM_CEILING_OBSERVATION,
        "prereg_path": PREREG_RELATIVE_PATH,
        "sealed_fails_untouched": ["214df20", "91ab0c6", "7171d19"],
        "sealed_confirm_701_708_untouched": True,
    }


def demography_design_digest(*, bolus: float, n_patches: int) -> str:
    return canonical_digest(
        demography_design_dict(bolus=bolus, n_patches=n_patches),
        prefix="hp_arm01_demography_tune_design",
    )


class DemographyTuneArm(StructuralRQArm):
    """Structural RQ arm with Stage-0 bolus × patches digest pin."""

    @classmethod
    def boot_demography(
        cls,
        *,
        arm: str,
        seed: int,
        bolus: float,
        n_patches: int,
        world_size: int = DEMOGRAPHY_WORLD_SIZE,
    ) -> DemographyTuneArm:
        if float(STRUCT_SOFT_K) != float(DEMOGRAPHY_SOFT_K):
            raise ConfigurationError("soft K locked at 64 for demography tune")
        patches = make_food_patches(n_patches, world_size=world_size)
        if len(patches) != int(n_patches):
            raise ConfigurationError("patch count mismatch")
        rebuilt = LifeLoopEcologyArm.boot(
            arm=arm,
            virulence=STRUCT_VIRULENCE,
            seed=int(seed),
            handling_time=STRUCT_HANDLING_TIME,
            birth_atp=STRUCT_BIRTH_ATP,
            parasite_n=STRUCT_PARASITE_N,
            parasite_mutation=STRUCT_PARASITE_MUTATION,
            founders=STRUCT_FOUNDERS,
            world_size=int(world_size),
            steal_fraction=STRUCT_STEAL_FRACTION,
            soft_carrying_capacity=DEMOGRAPHY_SOFT_K,
            basal_runtime_atp_cost=STRUCT_BASAL_ATP_COST,
            passage_refill_mode=PASSAGE_REFILL_GENERATION_BOUNDARY,
            resource_bolus_amount=float(bolus),
            food_patches=patches,
            founder_spatial_policy=STRUCT_FOUNDER_SPATIAL_POLICY,
            two_fold_cost_sex=False,
            mating_locus_lock=False,
        )
        configs = rebuilt.runner.configs
        rebuilt.runner.configs = replace(
            configs,
            mutation=MutationConfig(bit_flip_rate=float(STRUCT_HOST_BIT_FLIP)),
            reproduction=replace(
                configs.reproduction,
                reproduction_mode=ReproductionMode.ASEXUAL,
            ),
            sexual_recombination=SexualRecombinationConfig(enabled=False),
        )
        parasite_windows = [
            _DISTINCT_WINDOWS[i % len(_DISTINCT_WINDOWS)]
            for i in range(STRUCT_PARASITE_N)
        ]
        return cls(
            arm=rebuilt.arm,
            passage=rebuilt.passage,
            runner=rebuilt.runner,
            roles=dict(rebuilt.roles),
            hp_env=rebuilt.hp_env,
            parasite_windows=parasite_windows,
            ancestral_window=rebuilt.ancestral_window,
            seed=rebuilt.seed,
            virulence=rebuilt.virulence,
            parasite_mutation=rebuilt.parasite_mutation,
            intro_selfing_freq=rebuilt.intro_selfing_freq,
            two_fold_cost_sex_applied=rebuilt.two_fold_cost_sex_applied,
            birth_atp=rebuilt.birth_atp,
            basal_runtime_atp_cost=rebuilt.basal_runtime_atp_cost,
            soft_carrying_capacity=rebuilt.soft_carrying_capacity,
            passage_refill_mode=rebuilt.passage_refill_mode,
            resource_bolus_amount=rebuilt.resource_bolus_amount,
            food_patches=rebuilt.food_patches,
            cumulative_resource_bolus_placed=rebuilt.cumulative_resource_bolus_placed,
            passage_refill_sync=rebuilt.passage_refill_sync,
            mating_locus_lock=rebuilt.mating_locus_lock,
            selfing_birth_atp_endowment=rebuilt.selfing_birth_atp_endowment,
            mate_search_radius=rebuilt.mate_search_radius,
            outcross_mates_per_generation_cap=rebuilt.outcross_mates_per_generation_cap,
            host_bit_flip_rate=float(STRUCT_HOST_BIT_FLIP),
            parasite_keep_fraction=float(STRUCT_KEEP_FRACTION),
        )


def classify_demography_outcome(
    *,
    arm_snaps: Mapping[str, Mapping[int, Mapping[str, object]]],
) -> str:
    """Floor-only typed ladder on debit arms. No polymorphism / lag / RQ."""

    for arm in DEBIT_ACTIVE_ARMS:
        snaps = arm_snaps.get(arm, {})
        for gen in DEMOGRAPHY_LOCKED_WINDOWS:
            snap = snaps.get(gen)
            if snap is None:
                return OUTCOME_HORIZON_INSUFFICIENT
            if int(snap.get("parasite_n") or 0) <= 0:
                return OUTCOME_PARASITE_EXTINCT

    for arm in DEBIT_ACTIVE_ARMS:
        snaps = arm_snaps[arm]
        for gen in DEMOGRAPHY_LOCKED_WINDOWS:
            if int(snaps[gen].get("census") or 0) < DEMOGRAPHY_MIN_VIABLE:
                return OUTCOME_REGIME_HOSTILE_NE

    return OUTCOME_DEMOGRAPHY_OK


@dataclass(frozen=True, slots=True)
class DemographySeedResult:
    seed: int
    bolus: float
    n_patches: int
    typed_outcome: str
    snaps_by_arm: dict[str, dict[int, dict[str, object]]]
    terminal_census_by_arm: dict[str, int]
    digest: str
    red_queen_proved: bool = False
    biological_red_queen_proved: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "bolus": self.bolus,
            "n_patches": self.n_patches,
            "typed_outcome": self.typed_outcome,
            "snaps_by_arm": self.snaps_by_arm,
            "terminal_census_by_arm": dict(self.terminal_census_by_arm),
            "digest": self.digest,
            "red_queen_proved": False,
            "biological_red_queen_proved": False,
            "estimand": ESTIMAND,
            "claim_ceiling": CLAIM_CEILING_OBSERVATION,
        }


@dataclass(frozen=True, slots=True)
class DemographyCellReport:
    bolus: float
    n_patches: int
    seeds: tuple[int, ...]
    seed_results: tuple[DemographySeedResult, ...]
    typed_outcome_counts: dict[str, int]
    demography_ok_count: int
    campaign_pass: bool
    design_digest: str
    digest: str
    notes: str
    red_queen_proved: bool = False
    biological_red_queen_proved: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "hp_arm01_demography_tune_cell_v1",
            "prereg_version": PREREG_VERSION,
            "revision": HP_ARM01_DEMOGRAPHY_TUNE_REVISION,
            "slice": SLICE_NAME,
            "estimand": ESTIMAND,
            "bolus": self.bolus,
            "n_patches": self.n_patches,
            "seeds": list(self.seeds),
            "seed_results": [r.to_dict() for r in self.seed_results],
            "typed_outcome_counts": dict(self.typed_outcome_counts),
            "demography_ok_count": self.demography_ok_count,
            "campaign_pass_bar": DEMOGRAPHY_PASS_BAR,
            "campaign_pass": self.campaign_pass,
            "design_digest": self.design_digest,
            "digest": self.digest,
            "red_queen_proved": False,
            "biological_red_queen_proved": False,
            "claim_ceiling": CLAIM_CEILING_OBSERVATION,
            "min_viable_census": DEMOGRAPHY_MIN_VIABLE,
            "soft_carrying_capacity": DEMOGRAPHY_SOFT_K,
            "generations": DEMOGRAPHY_GENERATIONS,
            "locked_windows": list(DEMOGRAPHY_LOCKED_WINDOWS),
            "notes": self.notes,
        }


def run_demography_seed(
    *,
    seed: int,
    bolus: float,
    n_patches: int,
    generations: int | None = None,
) -> DemographySeedResult:
    """Run debit arms only; score floor at locked windows."""

    gens = int(DEMOGRAPHY_GENERATIONS if generations is None else generations)
    assert_demography_seed_policy([seed])
    assert_ecology_arm_taxonomy()
    if float(DEMOGRAPHY_SOFT_K) != 64.0:
        raise ConfigurationError("soft K must stay 64")
    if int(DEMOGRAPHY_MIN_VIABLE) != 12:
        raise ConfigurationError("min_viable must stay 12")

    snaps_by_arm: dict[str, dict[int, dict[str, object]]] = {}
    census: dict[str, int] = {}
    for arm_name in DEBIT_ACTIVE_ARMS:
        arm = DemographyTuneArm.boot_demography(
            arm=arm_name, seed=seed, bolus=float(bolus), n_patches=int(n_patches)
        )
        if float(arm.soft_carrying_capacity) != float(DEMOGRAPHY_SOFT_K):
            raise ConfigurationError("soft K digest-pin mismatch")
        if float(arm.resource_bolus_amount) != float(bolus):
            raise ConfigurationError("bolus digest-pin mismatch")
        if len(arm.food_patches) != int(n_patches):
            raise ConfigurationError("patch digest-pin mismatch")
        arm.run_generations(gens)
        snaps_by_arm[arm_name] = {
            int(g): arm.window_snapshot(int(g)) for g in DEMOGRAPHY_LOCKED_WINDOWS
        }
        census[arm_name] = int(arm.living_host_census())

    typed = classify_demography_outcome(arm_snaps=snaps_by_arm)
    body = {
        "seed": int(seed),
        "bolus": float(bolus),
        "n_patches": int(n_patches),
        "typed": typed,
        "census": census,
        "revision": HP_ARM01_DEMOGRAPHY_TUNE_REVISION,
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    return DemographySeedResult(
        seed=int(seed),
        bolus=float(bolus),
        n_patches=int(n_patches),
        typed_outcome=typed,
        snaps_by_arm=snaps_by_arm,
        terminal_census_by_arm=census,
        digest=digest,
        red_queen_proved=False,
        biological_red_queen_proved=False,
    )


def assemble_demography_cell(
    *,
    bolus: float,
    n_patches: int,
    seed_results: Sequence[DemographySeedResult],
) -> DemographyCellReport:
    chosen = tuple(sorted(int(r.seed) for r in seed_results))
    counts = {label: 0 for label in sorted(DEMOGRAPHY_TYPED_OUTCOMES)}
    for row in seed_results:
        counts[row.typed_outcome] = counts.get(row.typed_outcome, 0) + 1
    n_ok = sum(1 for r in seed_results if r.typed_outcome == OUTCOME_DEMOGRAPHY_OK)
    campaign_pass = n_ok >= DEMOGRAPHY_PASS_BAR
    design = demography_design_digest(bolus=bolus, n_patches=n_patches)
    report_body = {
        "bolus": float(bolus),
        "n_patches": int(n_patches),
        "seeds": list(chosen),
        "counts": counts,
        "demography_ok": n_ok,
        "campaign_pass": campaign_pass,
        "design": design,
        "revision": HP_ARM01_DEMOGRAPHY_TUNE_REVISION,
    }
    digest = hashlib.sha256(
        json.dumps(report_body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    notes = (
        f"primary_success=demography_ok;ok={n_ok}/{len(chosen)};"
        f"pass_bar={DEMOGRAPHY_PASS_BAR};campaign_pass={campaign_pass};"
        f"bolus={float(bolus)};patches={int(n_patches)};"
        f"soft_k={DEMOGRAPHY_SOFT_K};min_viable={DEMOGRAPHY_MIN_VIABLE};"
        f"score_polymorphism=false;score_lag=false;score_rq=false;"
        f"red_queen_proved=false"
    )
    return DemographyCellReport(
        bolus=float(bolus),
        n_patches=int(n_patches),
        seeds=chosen,
        seed_results=tuple(seed_results),
        typed_outcome_counts=counts,
        demography_ok_count=n_ok,
        campaign_pass=campaign_pass,
        design_digest=design,
        digest=digest,
        notes=notes,
        red_queen_proved=False,
        biological_red_queen_proved=False,
    )


__all__ = [
    "DEMOGRAPHY_GENERATIONS",
    "DEMOGRAPHY_GRID",
    "DEMOGRAPHY_LOCKED_WINDOWS",
    "DEMOGRAPHY_MIN_VIABLE",
    "DEMOGRAPHY_PASS_BAR",
    "DEMOGRAPHY_SEEDS",
    "DEMOGRAPHY_SOFT_K",
    "DEMOGRAPHY_TYPED_OUTCOMES",
    "DEMOGRAPHY_WORLD_SIZE",
    "DemographyCellReport",
    "DemographySeedResult",
    "DemographyTuneArm",
    "ESTIMAND",
    "HP_ARM01_DEMOGRAPHY_TUNE_REVISION",
    "OUTCOME_DEMOGRAPHY_OK",
    "PREREG_VERSION",
    "SLICE_NAME",
    "assemble_demography_cell",
    "assert_demography_seed_policy",
    "classify_demography_outcome",
    "demography_design_dict",
    "demography_design_digest",
    "make_food_patches",
    "run_demography_seed",
]
