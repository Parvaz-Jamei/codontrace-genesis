"""HP-ARM01 structural RQ confirmatory — Stage A–D landed regime, 8×500.

Constants match
``docs/handoff/CLOSED_LOOP_HP_ARM01_STRUCTURAL_RQ_CONFIRM_20260926.md``.

Confirms the pilot Stage A–D knobs under a NEW seed block, longer horizon,
conjunctive hold, and digest-pinned bolus 24.0 × 20 patches. Sealed
Slowinski (214df20 / 201–208), persistence (91ab0c6 / 301–308), mating
ledger (7171d19 / 401–408), and pilot seeds 601–603 stay untouched.
``red_queen_proved`` stays false. HP physics stays out of ``engine.py``.
Primary success: ``polymorphism_hold``. ``cycle_candidate`` is
observation-only / secondary. Campaign PASS iff hold-class ≥ 6/8.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Mapping, Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import ReproductionMode, SexualRecombinationConfig
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.closed_loop_hp_arm01 import (
    ARM_AVIRULENT,
    ARM_COPASSAGED,
    ARM_FIXED,
    CLAIM_CEILING_CANDIDATE,
    CLAIM_CEILING_OBSERVATION,
    ECOLOGY_ARMS,
    PASSAGE_REFILL_GENERATION_BOUNDARY,
    SUBSTRATE_LIFE_LOOP,
    assert_ecology_arm_taxonomy,
)
from codontrace.genesis.closed_loop_hp_arm01 import LifeLoopEcologyArm
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    DEBIT_ACTIVE_ARMS,
    STRUCT_PARASITE_CLASS_MEMORY_L,
    collect_dense_snaps,
    OUTCOME_CYCLE_CANDIDATE,
    OUTCOME_HORIZON_INSUFFICIENT,
    OUTCOME_PARASITE_EXTINCT,
    OUTCOME_POLYMORPHISM_HOLD,
    OUTCOME_REGIME_HOSTILE_NE,
    OUTCOME_REGIME_HOSTILE_TURNOVER,
    OUTCOME_SELFING_NONVIABLE,
    OUTCOME_SLOWINSKI_UNSCORED,
    OUTCOME_SWEEP_FIXATION,
    PILOT_SEEDS,
    SEALED_MATING_SEEDS,
    SEALED_P7_SEEDS,
    SEALED_PERSISTENCE_SEEDS,
    SEALED_SELFING_HOLD_SEEDS,
    SEALED_SLOWINSKI_SEEDS,
    STRUCT_BASAL_ATP_COST,
    STRUCT_BIRTH_ATP,
    STRUCT_EPSILON,
    STRUCT_FOUNDER_SPATIAL_POLICY,
    STRUCT_FOUNDERS,
    STRUCT_HANDLING_TIME,
    STRUCT_HOST_BIT_FLIP,
    STRUCT_HOST_N,
    STRUCT_KEEP_FRACTION,
    STRUCT_KAPPA_TOLERANCE,
    STRUCT_MIN_VIABLE_CENSUS,
    STRUCT_N_SUB_LOCI,
    STRUCT_PARASITE_MUTATION,
    STRUCT_PARASITE_N,
    STRUCT_PASSAGE_REFILL_MODE,
    STRUCT_R_MIN,
    STRUCT_SOFT_K,
    STRUCT_STEAL_FRACTION,
    STRUCT_VIRULENCE,
    StructuralRQArm,
    TYPED_OUTCOMES,
    _DISTINCT_WINDOWS,
    _dominant_class,
)
from codontrace.genesis.closed_loop_pearl_spc import (
    PASSAGE_COEVOLVE,
    PASSAGE_FROZEN,
)
from codontrace.genesis.population import MutationConfig

PREREG_VERSION = "hp_arm01_structural_rq_confirm_prereg_20260926"
PREREG_RELATIVE_PATH = (
    "docs/handoff/CLOSED_LOOP_HP_ARM01_STRUCTURAL_RQ_CONFIRM_20260926.md"
)
HP_ARM01_STRUCTURAL_RQ_CONFIRM_REVISION = "hp-arm01-structural-rq-confirm-20260926"
SLICE_NAME = "HP-ARM01-STRUCTURAL-RQ-CONFIRM"
ESTIMAND = "structural_polymorphism_hold_under_large_N_multilocus_mid_turnover"

CONFIRM_SEEDS: tuple[int, ...] = (701, 702, 703, 704, 705, 706, 707, 708)
CONFIRM_GENERATIONS = 500
CONFIRM_MID_WINDOWS: tuple[int, ...] = (125, 250)
CONFIRM_TERMINAL_WINDOW = 500
CONFIRM_LOCKED_WINDOWS: tuple[int, ...] = (125, 250, 500)
CONFIRM_SNAP_STRIDE = 25
CONFIRM_PASS_BAR = 6
CONFIRM_RESOURCE_BOLUS_AMOUNT = 24.0
CONFIRM_WORLD_SIZE = 20
CONFIRM_FOOD_PATCHES: tuple[tuple[int, int], ...] = tuple(
    (x, y) for x in range(5) for y in range(4)
)  # 20 patches
assert len(CONFIRM_FOOD_PATCHES) == 20


def prereg_document_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / PREREG_RELATIVE_PATH


def locked_design_dict() -> dict[str, object]:
    return {
        "prereg_version": PREREG_VERSION,
        "revision": HP_ARM01_STRUCTURAL_RQ_CONFIRM_REVISION,
        "slice": SLICE_NAME,
        "estimand": ESTIMAND,
        "substrate": SUBSTRATE_LIFE_LOOP,
        "seeds": list(CONFIRM_SEEDS),
        "sealed_p7_seeds_untouched": list(SEALED_P7_SEEDS),
        "sealed_slowinski_seeds_untouched": list(SEALED_SLOWINSKI_SEEDS),
        "sealed_persistence_seeds_untouched": list(SEALED_PERSISTENCE_SEEDS),
        "sealed_mating_seeds_untouched": list(SEALED_MATING_SEEDS),
        "sealed_selfing_hold_seeds_untouched": list(SEALED_SELFING_HOLD_SEEDS),
        "pilot_seeds_never_reused": list(PILOT_SEEDS),
        "generations": CONFIRM_GENERATIONS,
        "locked_windows": list(CONFIRM_LOCKED_WINDOWS),
        "snap_stride": CONFIRM_SNAP_STRIDE,
        "parasite_class_memory_L": STRUCT_PARASITE_CLASS_MEMORY_L,
        "mid_windows": list(CONFIRM_MID_WINDOWS),
        "terminal_window": CONFIRM_TERMINAL_WINDOW,
        "r_min": STRUCT_R_MIN,
        "epsilon": STRUCT_EPSILON,
        "hold_clause": "conjunctive_joint_Rmin_and_max_f_and_ge2_subloci_diverse",
        "or_soft_path_removed": True,
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
        "resource_bolus_amount": CONFIRM_RESOURCE_BOLUS_AMOUNT,
        "food_patches": [list(p) for p in CONFIRM_FOOD_PATCHES],
        "n_food_patches": len(CONFIRM_FOOD_PATCHES),
        "world_size": CONFIRM_WORLD_SIZE,
        "founder_spatial_policy": STRUCT_FOUNDER_SPATIAL_POLICY,
        "min_viable_census": STRUCT_MIN_VIABLE_CENSUS,
        "distinct_match_founders": list(_DISTINCT_WINDOWS),
        "n_distinct_match_founders": len(_DISTINCT_WINDOWS),
        "sub_locus_partition": {
            "n_sub_loci": STRUCT_N_SUB_LOCI,
            "sub_locus_width": 2,
            "ranges": [[0, 2], [2, 4], [4, 6]],
            "affinity_rule": "feature_overlap",
            "and_collapse_forbidden": True,
        },
        "arms": list(ECOLOGY_ARMS),
        "debit_active_arms": list(DEBIT_ACTIVE_ARMS),
        "typed_outcomes": sorted(TYPED_OUTCOMES),
        "primary_success": OUTCOME_POLYMORPHISM_HOLD,
        "cycle_candidate_secondary_observation_only": True,
        "campaign_pass_bar": CONFIRM_PASS_BAR,
        "campaign_n": len(CONFIRM_SEEDS),
        "slowinski_scored": False,
        "mating_deferred": True,
        "red_queen_proved_allowed": False,
        "biological_red_queen_proved_allowed": False,
        "spc_owns_accept_path": False,
        "body_census_is_ne_proxy": False,
        "second_population_registry": False,
        "reproduction_mode": "asexual",
        "mating_deferred_asexual_substrate": True,
        "pilot_prior_observation_only": True,
        "pilot_commits_cited_not_soft_greened": ["645e68d", "2ab9ec9"],
        "sealed_fails_untouched": ["214df20", "91ab0c6", "7171d19"],
        "prereg_path": PREREG_RELATIVE_PATH,
    }


def structural_rq_confirm_design_digest() -> str:
    return canonical_digest(
        locked_design_dict(), prefix="hp_arm01_structural_rq_confirm_design"
    )


def structural_rq_confirm_document_digest() -> str:
    path = prereg_document_path()
    if not path.is_file():
        raise ConfigurationError(f"missing preregistration file: {PREREG_RELATIVE_PATH}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_confirm_seed_policy(seeds: Sequence[int] | None = None) -> None:
    chosen = tuple(int(s) for s in (seeds if seeds is not None else CONFIRM_SEEDS))
    if not chosen:
        raise ConfigurationError("structural RQ confirmatory seeds must be non-empty")
    if len(set(chosen)) != len(chosen):
        raise ConfigurationError("structural RQ confirmatory seeds must be unique")
    for label, sealed in (
        ("P7", SEALED_P7_SEEDS),
        ("Slowinski", SEALED_SLOWINSKI_SEEDS),
        ("persistence", SEALED_PERSISTENCE_SEEDS),
        ("mating", SEALED_MATING_SEEDS),
        ("selfing_hold", SEALED_SELFING_HOLD_SEEDS),
        ("pilot_structural_rq", PILOT_SEEDS),
    ):
        overlap = sorted(set(chosen) & set(sealed))
        if overlap:
            raise ConfigurationError(
                f"sealed {label} seeds must not be reused; overlap={overlap}"
            )


def _polymorphism_ok_conjunctive(snap: Mapping[str, object]) -> bool:
    """Conjunctive hold only — OR soft-path removed for confirmatory."""

    richness = int(snap.get("joint_richness") or 0)
    max_f = float(snap.get("joint_max_freq") or 1.0)
    sub_rich = [int(x) for x in (snap.get("sub_locus_richness") or [])]
    loci_diverse = sum(1 for r in sub_rich if r >= 2)
    return (
        richness >= STRUCT_R_MIN
        and max_f <= (1.0 - STRUCT_EPSILON)
        and loci_diverse >= 2
    )


class StructuralRQConfirmArm(StructuralRQArm):
    """Structural RQ arm with confirmatory bolus / patch / world digest-pin."""

    @classmethod
    def boot_confirm(cls, *, arm: str, seed: int) -> StructuralRQConfirmArm:
        # Confirmatory resource geometry (Elena–Lenski bolus×patches digest-pin).
        rebuilt = LifeLoopEcologyArm.boot(
            arm=arm,
            virulence=STRUCT_VIRULENCE,
            seed=int(seed),
            handling_time=STRUCT_HANDLING_TIME,
            birth_atp=STRUCT_BIRTH_ATP,
            parasite_n=STRUCT_PARASITE_N,
            parasite_mutation=STRUCT_PARASITE_MUTATION,
            founders=STRUCT_FOUNDERS,
            world_size=CONFIRM_WORLD_SIZE,
            steal_fraction=STRUCT_STEAL_FRACTION,
            soft_carrying_capacity=STRUCT_SOFT_K,
            basal_runtime_atp_cost=STRUCT_BASAL_ATP_COST,
            passage_refill_mode=PASSAGE_REFILL_GENERATION_BOUNDARY,
            resource_bolus_amount=CONFIRM_RESOURCE_BOLUS_AMOUNT,
            food_patches=CONFIRM_FOOD_PATCHES,
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
        for kept, replaced in zip(
            self.turnover_kept, self.turnover_replaced, strict=True
        ):
            denom = kept + replaced
            keep_fracs.append(kept / denom if denom else 0.0)
        mid_vals = []
        for gen in CONFIRM_MID_WINDOWS:
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
            mid_ok = True
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


def classify_structural_confirm_outcome(
    *,
    arm_snaps: Mapping[str, Mapping[int, Mapping[str, object]]],
    turnover_by_arm: Mapping[str, Mapping[str, object]],
) -> str:
    """Mutually exclusive typed ladder under conjunctive hold."""

    for arm in DEBIT_ACTIVE_ARMS:
        snaps = arm_snaps.get(arm, {})
        for gen in CONFIRM_LOCKED_WINDOWS:
            snap = snaps.get(gen)
            if snap is None:
                return OUTCOME_PARASITE_EXTINCT
            if int(snap.get("parasite_n") or 0) <= 0:
                return OUTCOME_PARASITE_EXTINCT

    for arm in DEBIT_ACTIVE_ARMS:
        snaps = arm_snaps.get(arm, {})
        for gen in CONFIRM_LOCKED_WINDOWS:
            snap = snaps[gen]
            if int(snap.get("census") or 0) < STRUCT_MIN_VIABLE_CENSUS:
                return OUTCOME_REGIME_HOSTILE_NE

    if len(_DISTINCT_WINDOWS) < 8 or STRUCT_HOST_BIT_FLIP <= 0.0:
        return OUTCOME_REGIME_HOSTILE_NE
    if not (50 <= STRUCT_HOST_N <= 100 and 50 <= STRUCT_SOFT_K <= 100):
        return OUTCOME_REGIME_HOSTILE_NE

    cop_audit = turnover_by_arm.get(ARM_COPASSAGED, {})
    if not bool(cop_audit.get("mid_keep_ok", False)):
        return OUTCOME_REGIME_HOSTILE_TURNOVER

    mid_all_hold = True
    terminal_all_hold = True
    any_mid_fail = False
    any_terminal_fail = False
    for arm in DEBIT_ACTIVE_ARMS:
        snaps = arm_snaps[arm]
        for gen in CONFIRM_MID_WINDOWS:
            ok = _polymorphism_ok_conjunctive(snaps[gen])
            if not ok:
                mid_all_hold = False
                any_mid_fail = True
        tok = _polymorphism_ok_conjunctive(snaps[CONFIRM_TERMINAL_WINDOW])
        if not tok:
            terminal_all_hold = False
            any_terminal_fail = True

    if any_mid_fail or any_terminal_fail:
        if mid_all_hold and any_terminal_fail:
            return OUTCOME_HORIZON_INSUFFICIENT
        return OUTCOME_SWEEP_FIXATION

    if mid_all_hold and terminal_all_hold:
        return OUTCOME_POLYMORPHISM_HOLD

    return OUTCOME_HORIZON_INSUFFICIENT


def _oscillation_on_arm(snaps: Mapping[int, Mapping[str, object]]) -> bool:
    doms = [
        _dominant_class(snaps[g].get("joint_freq") or {})
        for g in CONFIRM_LOCKED_WINDOWS
    ]
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
    """Observation-only upgrade; never grants red_queen_proved."""

    upgraded = dict(seed_outcomes)
    hold_seeds = [
        s for s, o in seed_outcomes.items() if o == OUTCOME_POLYMORPHISM_HOLD
    ]
    oscillating: list[int] = []
    for seed in hold_seeds:
        arm_map = snaps_by_seed_arm[seed]
        if all(_oscillation_on_arm(arm_map[arm]) for arm in DEBIT_ACTIVE_ARMS):
            oscillating.append(seed)
    if len(oscillating) >= 2:
        for seed in oscillating:
            upgraded[seed] = OUTCOME_CYCLE_CANDIDATE
    return upgraded


@dataclass(frozen=True, slots=True)
class StructuralRQConfirmSeedResult:
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
class StructuralRQConfirmCampaignReport:
    seeds: tuple[int, ...]
    seed_results: tuple[StructuralRQConfirmSeedResult, ...]
    typed_outcome_counts: dict[str, int]
    seeds_polymorphism_hold: int
    seeds_cycle_candidate: int
    seeds_hold_class: int
    campaign_pass: bool
    campaign_mixed: bool
    campaign_fail: bool
    claim_ceiling: str
    red_queen_proved: bool
    biological_red_queen_proved: bool
    design_digest: str
    document_digest: str
    digest: str
    notes: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "hp_arm01_structural_rq_confirm_v1",
            "prereg_version": PREREG_VERSION,
            "revision": HP_ARM01_STRUCTURAL_RQ_CONFIRM_REVISION,
            "slice": SLICE_NAME,
            "estimand": ESTIMAND,
            "substrate": SUBSTRATE_LIFE_LOOP,
            "seeds": list(self.seeds),
            "seed_results": [r.to_dict() for r in self.seed_results],
            "typed_outcome_counts": dict(self.typed_outcome_counts),
            "seeds_polymorphism_hold": self.seeds_polymorphism_hold,
            "seeds_cycle_candidate": self.seeds_cycle_candidate,
            "seeds_hold_class": self.seeds_hold_class,
            "campaign_pass_bar": CONFIRM_PASS_BAR,
            "campaign_pass": self.campaign_pass,
            "campaign_mixed": self.campaign_mixed,
            "campaign_fail": self.campaign_fail,
            "primary_success": OUTCOME_POLYMORPHISM_HOLD,
            "claim_ceiling": self.claim_ceiling,
            "red_queen_proved": self.red_queen_proved,
            "biological_red_queen_proved": self.biological_red_queen_proved,
            "design_digest": self.design_digest,
            "document_digest": self.document_digest,
            "digest": self.digest,
            "generations": CONFIRM_GENERATIONS,
            "locked_windows": list(CONFIRM_LOCKED_WINDOWS),
            "snap_stride": CONFIRM_SNAP_STRIDE,
            "parasite_class_memory_L": STRUCT_PARASITE_CLASS_MEMORY_L,
            "r_min": STRUCT_R_MIN,
            "epsilon": STRUCT_EPSILON,
            "hold_clause": "conjunctive",
            "kappa": STRUCT_KEEP_FRACTION,
            "parasite_mutation": STRUCT_PARASITE_MUTATION,
            "host_bit_flip_rate": STRUCT_HOST_BIT_FLIP,
            "host_n": STRUCT_HOST_N,
            "parasite_n": STRUCT_PARASITE_N,
            "soft_carrying_capacity": STRUCT_SOFT_K,
            "virulence": STRUCT_VIRULENCE,
            "steal_fraction": STRUCT_STEAL_FRACTION,
            "resource_bolus_amount": CONFIRM_RESOURCE_BOLUS_AMOUNT,
            "n_food_patches": len(CONFIRM_FOOD_PATCHES),
            "world_size": CONFIRM_WORLD_SIZE,
            "min_viable_census": STRUCT_MIN_VIABLE_CENSUS,
            "slowinski_scored": False,
            "mating_deferred": True,
            "sealed_fails_untouched": ["214df20", "91ab0c6", "7171d19"],
            "pilot_prior_observation_only": True,
            "spc_owns_accept_path": False,
            "notes": self.notes,
        }


def run_structural_rq_confirm(
    *,
    seeds: Sequence[int] | None = None,
    generations: int | None = None,
) -> StructuralRQConfirmCampaignReport:
    """Run the locked Stage A–D structural RQ confirmatory campaign."""

    chosen = tuple(int(s) for s in (seeds if seeds is not None else CONFIRM_SEEDS))
    gens = int(CONFIRM_GENERATIONS if generations is None else generations)
    assert_confirm_seed_policy(chosen)
    if gens < CONFIRM_GENERATIONS:
        raise ConfigurationError(
            f"structural RQ confirmatory horizon locked at {CONFIRM_GENERATIONS}; "
            f"got {gens}"
        )
    if len(CONFIRM_FOOD_PATCHES) != 20:
        raise ConfigurationError("confirmatory food patch count locked at 20")
    if CONFIRM_RESOURCE_BOLUS_AMOUNT != 24.0:
        raise ConfigurationError("confirmatory bolus locked at 24.0")
    assert_ecology_arm_taxonomy()

    design = structural_rq_confirm_design_digest()
    document = structural_rq_confirm_document_digest()

    raw_outcomes: dict[int, str] = {}
    snaps_by_seed_arm: dict[int, dict[str, dict[int, dict[str, object]]]] = {}
    seed_payloads: list[dict[str, object]] = []

    for seed in chosen:
        snaps_by_arm: dict[str, dict[int, dict[str, object]]] = {}
        dense_snaps_by_arm: dict[str, dict[int, dict[str, object]]] = {}
        turnover_by_arm: dict[str, dict[str, object]] = {}
        census: dict[str, int] = {}
        for arm_name in ECOLOGY_ARMS:
            arm = StructuralRQConfirmArm.boot_confirm(arm=arm_name, seed=seed)
            bf = float(arm.runner.configs.mutation.bit_flip_rate)
            if bf <= 0.0:
                raise ConfigurationError("Stage A requires host bit-flip > 0 on runner")
            if arm.soft_carrying_capacity < 50:
                raise ConfigurationError(
                    "Stage A requires soft K in 50–100 on same runner"
                )
            if float(arm.resource_bolus_amount) != CONFIRM_RESOURCE_BOLUS_AMOUNT:
                raise ConfigurationError("confirmatory bolus digest-pin mismatch")
            if len(arm.food_patches) != 20:
                raise ConfigurationError("confirmatory patch digest-pin mismatch")
            arm.run_generations(gens)
            # Hold clause: locked windows only (conjunctive; no OR soft-path).
            snaps_by_arm[arm_name] = {
                int(g): arm.window_snapshot(int(g)) for g in CONFIRM_LOCKED_WINDOWS
            }
            # Dense series for lag/phase clocks only — never softens hold.
            dense_snaps_by_arm[arm_name] = collect_dense_snaps(
                arm, horizon=gens, snap_stride=CONFIRM_SNAP_STRIDE
            )
            turnover_by_arm[arm_name] = arm.turnover_audit()
            census[arm_name] = int(arm.living_host_census())

        typed = classify_structural_confirm_outcome(
            arm_snaps=snaps_by_arm, turnover_by_arm=turnover_by_arm
        )
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
    ceiling = (
        CLAIM_CEILING_CANDIDATE if hold_or_cycle else CLAIM_CEILING_OBSERVATION
    )

    results: list[StructuralRQConfirmSeedResult] = []
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
            "revision": HP_ARM01_STRUCTURAL_RQ_CONFIRM_REVISION,
        }
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        results.append(
            StructuralRQConfirmSeedResult(
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
    n_hold_class = n_hold + n_cycle
    campaign_pass = n_hold_class >= CONFIRM_PASS_BAR
    campaign_fail = n_hold_class <= 2
    campaign_mixed = (not campaign_pass) and (not campaign_fail)

    report_body = {
        "seeds": list(chosen),
        "counts": counts,
        "design": design,
        "document": document,
        "ceiling": ceiling,
        "revision": HP_ARM01_STRUCTURAL_RQ_CONFIRM_REVISION,
        "hold_class": n_hold_class,
        "campaign_pass": campaign_pass,
    }
    report_digest = hashlib.sha256(
        json.dumps(report_body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    notes = (
        f"primary_success=polymorphism_hold;hold={n_hold};cycle_candidate_obs={n_cycle};"
        f"hold_class={n_hold_class}/8;campaign_pass={campaign_pass};"
        f"slowinski_scored=false;red_queen_proved=false;"
        f"bolus={CONFIRM_RESOURCE_BOLUS_AMOUNT};patches={len(CONFIRM_FOOD_PATCHES)};"
        f"kappa={STRUCT_KEEP_FRACTION};host_bit_flip={STRUCT_HOST_BIT_FLIP};"
        f"N={STRUCT_HOST_N};conjunctive_hold=true"
    )
    return StructuralRQConfirmCampaignReport(
        seeds=chosen,
        seed_results=tuple(results),
        typed_outcome_counts=counts,
        seeds_polymorphism_hold=n_hold,
        seeds_cycle_candidate=n_cycle,
        seeds_hold_class=n_hold_class,
        campaign_pass=campaign_pass,
        campaign_mixed=campaign_mixed,
        campaign_fail=campaign_fail,
        claim_ceiling=ceiling,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        design_digest=design,
        document_digest=document,
        digest=report_digest,
        notes=notes,
    )


__all__ = [
    "CONFIRM_FOOD_PATCHES",
    "CONFIRM_GENERATIONS",
    "CONFIRM_LOCKED_WINDOWS",
    "CONFIRM_PASS_BAR",
    "CONFIRM_RESOURCE_BOLUS_AMOUNT",
    "CONFIRM_SEEDS",
    "CONFIRM_SNAP_STRIDE",
    "CONFIRM_WORLD_SIZE",
    "ESTIMAND",
    "HP_ARM01_STRUCTURAL_RQ_CONFIRM_REVISION",
    "PREREG_VERSION",
    "SLICE_NAME",
    "StructuralRQConfirmArm",
    "StructuralRQConfirmCampaignReport",
    "StructuralRQConfirmSeedResult",
    "apply_cycle_candidate_upgrade",
    "assert_confirm_seed_policy",
    "classify_structural_confirm_outcome",
    "locked_design_dict",
    "prereg_document_path",
    "run_structural_rq_confirm",
    "structural_rq_confirm_design_digest",
    "structural_rq_confirm_document_digest",
    "_polymorphism_ok_conjunctive",
]
