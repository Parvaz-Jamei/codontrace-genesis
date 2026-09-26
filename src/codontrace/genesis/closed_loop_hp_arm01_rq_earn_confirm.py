"""HP-ARM01 RQ-earn confirmatory — Stage 1 after demography pin.

Fork A asexual-clone Red Queen Dynamics estimand (fluctuating selection with
time-lagged host↔parasite class association). Does **not** claim sex
maintained by RQ, biological RQ, or rewrite sealed 701–708 hold-class PASS.

Standing locks
--------------
* ``red_queen_proved`` / ``biological_red_queen_proved`` stay False.
* ClaimGate allowlist / P4 not flipped here (Critic after SUCCESS).
* Pearl passages are true ``PASSAGE_COEVOLVE`` / ``PASSAGE_FROZEN`` /
  ``PASSAGE_ABSENT`` — ecology ``ARM_FIXED`` alone is not Pearl frozen.
* Lag / RQ-earn credit: debit-active only; avirulent never grants credit.
* ``regime_hostile_ne`` excluded from lag pass fraction.
* Soft K fixed; floor 12 fixed; no infection in ``engine.py``.
* Cuscore / SPC observation-only; Fork B / Slowinski DEFER.
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
    LifeLoopEcologyArm,
    assert_ecology_arm_taxonomy,
)
from codontrace.genesis.closed_loop_hp_arm01_demography_tune import (
    DEMOGRAPHY_SEEDS,
    make_food_patches,
)
from codontrace.genesis.closed_loop_hp_arm01_rq_earn import (
    DEFAULT_LAG_TAU,
    DEFAULT_MIN_POINTS,
    DEFAULT_SNAP_STRIDE,
    ESTIMAND_FORK,
    FORK_B_SLOWINSKI_STATUS,
    PEARL_PASSAGE_MODES,
    RQ_EARN_DEBIT_ARMS,
    TWO_FOLD_COST_SEX_STATUS,
    pearl_contrast_stubs,
    score_lagged_nfds_on_debit_arms,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    DEBIT_ACTIVE_ARMS,
    OUTCOME_HORIZON_INSUFFICIENT,
    OUTCOME_PARASITE_EXTINCT,
    OUTCOME_POLYMORPHISM_HOLD,
    OUTCOME_REGIME_HOSTILE_NE,
    OUTCOME_REGIME_HOSTILE_TURNOVER,
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
    STRUCT_PARASITE_CLASS_MEMORY_L,
    STRUCT_PARASITE_MUTATION,
    STRUCT_PARASITE_N,
    STRUCT_R_MIN,
    STRUCT_SOFT_K,
    STRUCT_STEAL_FRACTION,
    STRUCT_VIRULENCE,
    StructuralRQArm,
    _DISTINCT_WINDOWS,
    collect_dense_snaps,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq_confirm import (
    CONFIRM_SEEDS,
    CONFIRM_SNAP_STRIDE,
    _polymorphism_ok_conjunctive,
)
from codontrace.genesis.closed_loop_pearl_spc import (
    PASSAGE_ABSENT,
    PASSAGE_COEVOLVE,
    PASSAGE_FROZEN,
    assert_passage_taxonomy,
)
from codontrace.genesis.measurements.rq_frequency_clocks import (
    DEFAULT_NFDS_THRESHOLD,
    lagged_nfds_score,
)
from codontrace.genesis.population import MutationConfig

PREREG_VERSION = "hp_arm01_rq_earn_confirm_prereg_20260926"
PREREG_RELATIVE_PATH = "docs/handoff/WAVE7_RQ_EARN_CONFIRM_PREREG_20260926.md"
HP_ARM01_RQ_EARN_CONFIRM_REVISION = "hp-arm01-rq-earn-confirm-20260926"
SLICE_NAME = "HP-ARM01-RQ-EARN-CONFIRM"
ESTIMAND = "fork_a_asexual_clone_rqd_lagged_nfds_pearl"

RQ_EARN_CONFIRM_SEEDS: tuple[int, ...] = tuple(range(801, 817))
RQ_EARN_CONFIRM_GENERATIONS = 500
RQ_EARN_CONFIRM_LOCKED_WINDOWS: tuple[int, ...] = (125, 250, 500)
RQ_EARN_CONFIRM_MID_WINDOWS: tuple[int, ...] = (125, 250)
RQ_EARN_CONFIRM_TERMINAL_WINDOW = 500
RQ_EARN_CONFIRM_SNAP_STRIDE = CONFIRM_SNAP_STRIDE  # 25
RQ_EARN_CONFIRM_PASS_BAR = 12  # ≥12/16
RQ_EARN_CONFIRM_N = 16
RQ_EARN_CONFIRM_WORLD_SIZE = 20
RQ_EARN_CONFIRM_LAG_TAU = DEFAULT_LAG_TAU  # 4
RQ_EARN_CONFIRM_MIN_POINTS = DEFAULT_MIN_POINTS  # 20
RQ_EARN_CONFIRM_NFDS_THRESHOLD = DEFAULT_NFDS_THRESHOLD  # 0.3
RQ_EARN_CONFIRM_R_MIN = STRUCT_R_MIN  # 3
RQ_EARN_CONFIRM_EPSILON = STRUCT_EPSILON  # 0.15
RQ_EARN_CONFIRM_MIN_VIABLE = STRUCT_MIN_VIABLE_CENSUS  # 12
RQ_EARN_CONFIRM_SOFT_K = STRUCT_SOFT_K  # 64

# Stage 0 winner pin — overwritten after demography PASS (placeholder 24×20).
STAGE0_WINNER_BOLUS: float = 24.0
STAGE0_WINNER_N_PATCHES: int = 20
STAGE0_WINNER_PINNED: bool = False  # flipped True when Stage 0 paste lands

OUTCOME_RQ_EARN_SEED_PASS = "rq_earn_seed_pass"
OUTCOME_LAG_FAIL = "lag_fail"
OUTCOME_PEARL_FAIL = "pearl_fail"
OUTCOME_CYCLE_CANDIDATE_OBS = "cycle_candidate"

RQ_EARN_TYPED_OUTCOMES: frozenset[str] = frozenset(
    {
        OUTCOME_RQ_EARN_SEED_PASS,
        OUTCOME_POLYMORPHISM_HOLD,
        OUTCOME_CYCLE_CANDIDATE_OBS,
        OUTCOME_LAG_FAIL,
        OUTCOME_PEARL_FAIL,
        OUTCOME_REGIME_HOSTILE_NE,
        OUTCOME_PARASITE_EXTINCT,
        OUTCOME_HORIZON_INSUFFICIENT,
        OUTCOME_REGIME_HOSTILE_TURNOVER,
        OUTCOME_SWEEP_FIXATION,
    }
)

# Ecology arm → Pearl passage (true do-cuts; freeze ≠ absent).
_ARM_TO_PEARL: dict[str, str] = {
    ARM_COPASSAGED: PASSAGE_COEVOLVE,
    ARM_FIXED: PASSAGE_FROZEN,
    ARM_AVIRULENT: PASSAGE_ABSENT,
}


def pin_stage0_winner(*, bolus: float, n_patches: int) -> None:
    """Pin Stage 0 demography winner into module-level constants before run."""

    global STAGE0_WINNER_BOLUS, STAGE0_WINNER_N_PATCHES, STAGE0_WINNER_PINNED
    if float(bolus) <= 0 or int(n_patches) <= 0:
        raise ConfigurationError("Stage 0 winner bolus/patches must be positive")
    STAGE0_WINNER_BOLUS = float(bolus)
    STAGE0_WINNER_N_PATCHES = int(n_patches)
    STAGE0_WINNER_PINNED = True


def prereg_document_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / PREREG_RELATIVE_PATH


def rq_earn_confirm_design_dict() -> dict[str, object]:
    patches = make_food_patches(
        STAGE0_WINNER_N_PATCHES, world_size=RQ_EARN_CONFIRM_WORLD_SIZE
    )
    return {
        "prereg_version": PREREG_VERSION,
        "revision": HP_ARM01_RQ_EARN_CONFIRM_REVISION,
        "slice": SLICE_NAME,
        "estimand": ESTIMAND,
        "estimand_fork": ESTIMAND_FORK,
        "fork_b_slowinski_status": FORK_B_SLOWINSKI_STATUS,
        "two_fold_cost_sex_status": TWO_FOLD_COST_SEX_STATUS,
        "sex_by_rq_claim_allowed": False,
        "substrate": SUBSTRATE_LIFE_LOOP,
        "seeds": list(RQ_EARN_CONFIRM_SEEDS),
        "forbidden_reuse_blocks": {
            "demography_751_758": list(DEMOGRAPHY_SEEDS),
            "structural_confirm_701_708": list(CONFIRM_SEEDS),
            "pilot": list(PILOT_SEEDS),
        },
        "generations": RQ_EARN_CONFIRM_GENERATIONS,
        "locked_windows": list(RQ_EARN_CONFIRM_LOCKED_WINDOWS),
        "snap_stride": RQ_EARN_CONFIRM_SNAP_STRIDE,
        "parasite_class_memory_L": STRUCT_PARASITE_CLASS_MEMORY_L,
        "lag_tau": RQ_EARN_CONFIRM_LAG_TAU,
        "lagged_nfds_threshold": RQ_EARN_CONFIRM_NFDS_THRESHOLD,
        "lagged_nfds_min_points": RQ_EARN_CONFIRM_MIN_POINTS,
        "host_n": STRUCT_HOST_N,
        "soft_carrying_capacity": RQ_EARN_CONFIRM_SOFT_K,
        "parasite_n": STRUCT_PARASITE_N,
        "founders": 16,
        "host_bit_flip_rate": STRUCT_HOST_BIT_FLIP,
        "sub_loci": STRUCT_N_SUB_LOCI,
        "kappa": STRUCT_KEEP_FRACTION,
        "parasite_mutation": STRUCT_PARASITE_MUTATION,
        "virulence": STRUCT_VIRULENCE,
        "steal_fraction": STRUCT_STEAL_FRACTION,
        "resource_bolus_amount": STAGE0_WINNER_BOLUS,
        "n_food_patches": STAGE0_WINNER_N_PATCHES,
        "food_patches": [list(p) for p in patches],
        "world_size": RQ_EARN_CONFIRM_WORLD_SIZE,
        "stage0_winner_pinned": STAGE0_WINNER_PINNED,
        "min_viable_census": RQ_EARN_CONFIRM_MIN_VIABLE,
        "r_min": RQ_EARN_CONFIRM_R_MIN,
        "epsilon": RQ_EARN_CONFIRM_EPSILON,
        "hold_clause": "conjunctive_joint_Rmin_and_max_f_and_ge2_subloci_diverse",
        "or_soft_path_removed": True,
        "arms": list(ECOLOGY_ARMS),
        "debit_active_arms": list(DEBIT_ACTIVE_ARMS),
        "lag_scoring_arms": list(RQ_EARN_DEBIT_ARMS),
        "avi_absent_never_grant_rq_earn_credit": True,
        "pearl_passage_modes": list(PEARL_PASSAGE_MODES),
        "pearl_freeze_neq_absent": True,
        "ecology_arm_fixed_is_not_pearl_frozen_alone": True,
        "regime_hostile_ne_excluded_from_lagged_nfds_pass_fraction": True,
        "lagged_nfds_is_not_oscillation_flip_wrapper": True,
        "primary_success": OUTCOME_RQ_EARN_SEED_PASS,
        "campaign_pass_bar": RQ_EARN_CONFIRM_PASS_BAR,
        "campaign_n": RQ_EARN_CONFIRM_N,
        "red_queen_proved_allowed": False,
        "biological_red_queen_proved_allowed": False,
        "claim_ceiling_until_success": CLAIM_CEILING_OBSERVATION,
        "spc_owns_accept_path": False,
        "cuscore_spc_observation_only_never_rq_accept": True,
        "dense_snap_feeds_floquet_phase_only_not_hold": True,
        "prereg_path": PREREG_RELATIVE_PATH,
        "sealed_fails_untouched": ["214df20", "91ab0c6", "7171d19"],
        "sealed_confirm_701_708_untouched": True,
        "p4_claimgate_allowlist_not_flipped_here": True,
    }


def rq_earn_confirm_design_digest() -> str:
    return canonical_digest(
        rq_earn_confirm_design_dict(), prefix="hp_arm01_rq_earn_confirm_design"
    )


def rq_earn_confirm_document_digest() -> str:
    path = prereg_document_path()
    if not path.is_file():
        raise ConfigurationError(f"missing preregistration file: {PREREG_RELATIVE_PATH}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_rq_earn_confirm_seed_policy(seeds: Sequence[int] | None = None) -> None:
    chosen = tuple(
        int(s) for s in (seeds if seeds is not None else RQ_EARN_CONFIRM_SEEDS)
    )
    if not chosen:
        raise ConfigurationError("RQ-earn confirm seeds must be non-empty")
    if len(set(chosen)) != len(chosen):
        raise ConfigurationError("RQ-earn confirm seeds must be unique")
    for label, sealed in (
        ("P7", SEALED_P7_SEEDS),
        ("Slowinski", SEALED_SLOWINSKI_SEEDS),
        ("persistence", SEALED_PERSISTENCE_SEEDS),
        ("mating", SEALED_MATING_SEEDS),
        ("selfing_hold", SEALED_SELFING_HOLD_SEEDS),
        ("pilot_structural_rq", PILOT_SEEDS),
        ("structural_confirm", CONFIRM_SEEDS),
        ("demography_tune", DEMOGRAPHY_SEEDS),
    ):
        overlap = sorted(set(chosen) & set(sealed))
        if overlap:
            raise ConfigurationError(
                f"sealed {label} seeds must not be reused; overlap={overlap}"
            )


class RQEarnConfirmArm(StructuralRQArm):
    """Structural RQ arm with Stage-0-pinned bolus × patches."""

    @classmethod
    def boot_rq_earn(
        cls,
        *,
        arm: str,
        seed: int,
        bolus: float | None = None,
        n_patches: int | None = None,
    ) -> RQEarnConfirmArm:
        b = float(STAGE0_WINNER_BOLUS if bolus is None else bolus)
        n = int(STAGE0_WINNER_N_PATCHES if n_patches is None else n_patches)
        patches = make_food_patches(n, world_size=RQ_EARN_CONFIRM_WORLD_SIZE)
        rebuilt = LifeLoopEcologyArm.boot(
            arm=arm,
            virulence=STRUCT_VIRULENCE,
            seed=int(seed),
            handling_time=STRUCT_HANDLING_TIME,
            birth_atp=STRUCT_BIRTH_ATP,
            parasite_n=STRUCT_PARASITE_N,
            parasite_mutation=STRUCT_PARASITE_MUTATION,
            founders=STRUCT_FOUNDERS,
            world_size=RQ_EARN_CONFIRM_WORLD_SIZE,
            steal_fraction=STRUCT_STEAL_FRACTION,
            soft_carrying_capacity=RQ_EARN_CONFIRM_SOFT_K,
            basal_runtime_atp_cost=STRUCT_BASAL_ATP_COST,
            passage_refill_mode=PASSAGE_REFILL_GENERATION_BOUNDARY,
            resource_bolus_amount=b,
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
        for gen in RQ_EARN_CONFIRM_MID_WINDOWS:
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


def _freq_maps_from_dense(
    dense_snaps: Mapping[int, Mapping[str, object]],
) -> tuple[dict[int, dict[str, float]], dict[int, dict[str, float]]]:
    host: dict[int, dict[str, float]] = {}
    para: dict[int, dict[str, float]] = {}
    for gen, snap in dense_snaps.items():
        g = int(gen)
        jf = snap.get("joint_freq") or {}
        if isinstance(jf, Mapping):
            host[g] = {str(k): float(v) for k, v in jf.items()}
        ph = snap.get("parasite_class_hist") or {}
        if isinstance(ph, Mapping):
            para[g] = {str(k): float(v) for k, v in ph.items()}
    return host, para


def score_pearl_passage_lag(
    dense_snaps: Mapping[int, Mapping[str, object]],
    *,
    lag: int = RQ_EARN_CONFIRM_LAG_TAU,
    min_points: int = RQ_EARN_CONFIRM_MIN_POINTS,
    threshold: float = RQ_EARN_CONFIRM_NFDS_THRESHOLD,
) -> dict[str, object]:
    """Lag score for a single true Pearl passage run (not ecology-arm alias)."""

    host, para = _freq_maps_from_dense(dense_snaps)
    score = lagged_nfds_score(
        host, para, lag=lag, min_points=min_points, threshold=threshold
    )
    out = dict(score)
    out["red_queen_proved"] = False
    out["biological_red_queen_proved"] = False
    return out


def evaluate_pearl_contrasts(
    dense_snaps_by_arm: Mapping[str, Mapping[int, Mapping[str, object]]],
) -> dict[str, object]:
    """True Pearl do-cuts: coevolve / frozen / absent as separate passage scores.

    Ecology ``ARM_FIXED`` supplies the ``PASSAGE_FROZEN`` run and
    ``ARM_AVIRULENT`` supplies ``PASSAGE_ABSENT``, but the contrast is scored
    as named Pearl passages (freeze ≠ absent), not as a debit-arm aggregate
    alias of fixed-arm lag.
    """

    assert_passage_taxonomy()
    if PASSAGE_FROZEN == PASSAGE_ABSENT:
        raise ConfigurationError("Pearl freeze must not equal absent")

    coevo = score_pearl_passage_lag(dense_snaps_by_arm.get(ARM_COPASSAGED) or {})
    frozen = score_pearl_passage_lag(dense_snaps_by_arm.get(ARM_FIXED) or {})
    absent = score_pearl_passage_lag(dense_snaps_by_arm.get(ARM_AVIRULENT) or {})

    coevolve_lag_pass = bool(coevo.get("pass_prelim") is True)
    frozen_lag_pass = bool(frozen.get("pass_prelim") is True)
    absent_lag_pass = bool(absent.get("pass_prelim") is True)

    # Expected confirmatory pattern
    pearl_ok = coevolve_lag_pass and (not frozen_lag_pass) and (not absent_lag_pass)

    stub = pearl_contrast_stubs(
        coevolve_lag_pass=coevolve_lag_pass,
        frozen_lag_pass=frozen_lag_pass,
        absent_lag_pass=absent_lag_pass,
    )
    stub["scaffold_only"] = False
    stub["live_pearl_passages"] = True
    stub["pearl_ok"] = pearl_ok
    stub["passage_scores"] = {
        PASSAGE_COEVOLVE: coevo,
        PASSAGE_FROZEN: frozen,
        PASSAGE_ABSENT: absent,
    }
    stub["arm_to_pearl"] = dict(_ARM_TO_PEARL)
    stub["freeze_neq_absent"] = True
    stub["ecology_arm_fixed_alone_is_not_pearl_frozen"] = True
    stub["red_queen_proved"] = False
    stub["biological_red_queen_proved"] = False
    return stub


def classify_rq_earn_confirm_outcome(
    *,
    arm_snaps: Mapping[str, Mapping[int, Mapping[str, object]]],
    turnover_by_arm: Mapping[str, Mapping[str, object]],
    dense_snaps_by_arm: Mapping[str, Mapping[int, Mapping[str, object]]],
) -> dict[str, object]:
    """Conjunctive RQ-earn seed classifier. Proved flags always False."""

    # --- Floor / extinction ladder (debit arms) ---
    for arm in DEBIT_ACTIVE_ARMS:
        snaps = arm_snaps.get(arm, {})
        for gen in RQ_EARN_CONFIRM_LOCKED_WINDOWS:
            snap = snaps.get(gen)
            if snap is None:
                return _outcome_payload(OUTCOME_PARASITE_EXTINCT)
            if int(snap.get("parasite_n") or 0) <= 0:
                return _outcome_payload(OUTCOME_PARASITE_EXTINCT)

    for arm in DEBIT_ACTIVE_ARMS:
        snaps = arm_snaps[arm]
        for gen in RQ_EARN_CONFIRM_LOCKED_WINDOWS:
            if int(snaps[gen].get("census") or 0) < RQ_EARN_CONFIRM_MIN_VIABLE:
                # hostile_ne: out of lag fraction; not RQ miss
                return _outcome_payload(
                    OUTCOME_REGIME_HOSTILE_NE,
                    excluded_from_lag_fraction=True,
                )

    cop_audit = turnover_by_arm.get(ARM_COPASSAGED, {})
    if not bool(cop_audit.get("mid_keep_ok", False)):
        return _outcome_payload(OUTCOME_REGIME_HOSTILE_TURNOVER)

    # --- Conjunctive polymorphism hold (mid+terminal, both debit arms) ---
    mid_all_hold = True
    terminal_all_hold = True
    any_mid_fail = False
    any_terminal_fail = False
    for arm in DEBIT_ACTIVE_ARMS:
        snaps = arm_snaps[arm]
        for gen in RQ_EARN_CONFIRM_MID_WINDOWS:
            ok = _polymorphism_ok_conjunctive(snaps[gen])
            if not ok:
                mid_all_hold = False
                any_mid_fail = True
        tok = _polymorphism_ok_conjunctive(snaps[RQ_EARN_CONFIRM_TERMINAL_WINDOW])
        if not tok:
            terminal_all_hold = False
            any_terminal_fail = True

    if any_mid_fail or any_terminal_fail:
        if mid_all_hold and any_terminal_fail:
            return _outcome_payload(OUTCOME_HORIZON_INSUFFICIENT)
        return _outcome_payload(OUTCOME_SWEEP_FIXATION)

    if not (mid_all_hold and terminal_all_hold):
        return _outcome_payload(OUTCOME_HORIZON_INSUFFICIENT)

    # Hold achieved — now lag + Pearl
    lagged = score_lagged_nfds_on_debit_arms(
        dense_snaps_by_arm,
        lag=RQ_EARN_CONFIRM_LAG_TAU,
        min_points=RQ_EARN_CONFIRM_MIN_POINTS,
        threshold=RQ_EARN_CONFIRM_NFDS_THRESHOLD,
        typed_outcome=None,  # not hostile_ne
    )
    # Avirulent must not appear in debit scores
    if ARM_AVIRULENT in (lagged.get("arm_scores") or {}):
        raise ConfigurationError("avirulent must not receive lag credit")

    pearl = evaluate_pearl_contrasts(dense_snaps_by_arm)

    if lagged.get("pass_prelim") is not True:
        return _outcome_payload(
            OUTCOME_LAG_FAIL,
            polymorphism_hold=True,
            lagged_nfds=lagged,
            pearl=pearl,
        )

    if pearl.get("pearl_ok") is not True:
        return _outcome_payload(
            OUTCOME_PEARL_FAIL,
            polymorphism_hold=True,
            lagged_nfds=lagged,
            pearl=pearl,
        )

    return _outcome_payload(
        OUTCOME_RQ_EARN_SEED_PASS,
        polymorphism_hold=True,
        lagged_nfds=lagged,
        pearl=pearl,
        rq_earn_seed_pass=True,
    )


def _outcome_payload(
    typed: str,
    *,
    excluded_from_lag_fraction: bool = False,
    polymorphism_hold: bool = False,
    lagged_nfds: dict[str, object] | None = None,
    pearl: dict[str, object] | None = None,
    rq_earn_seed_pass: bool = False,
) -> dict[str, object]:
    return {
        "typed_outcome": typed,
        "rq_earn_seed_pass": bool(rq_earn_seed_pass),
        "polymorphism_hold": bool(polymorphism_hold),
        "excluded_from_lag_fraction": bool(excluded_from_lag_fraction),
        "lagged_nfds": lagged_nfds or {},
        "pearl": pearl or {},
        "red_queen_proved": False,
        "biological_red_queen_proved": False,
    }


@dataclass(frozen=True, slots=True)
class RQEarnConfirmSeedResult:
    seed: int
    typed_outcome: str
    rq_earn_seed_pass: bool
    polymorphism_hold: bool
    excluded_from_lag_fraction: bool
    claim_ceiling: str
    snaps_by_arm: dict[str, dict[int, dict[str, object]]]
    dense_snaps_by_arm: dict[str, dict[int, dict[str, object]]]
    turnover_by_arm: dict[str, dict[str, object]]
    terminal_census_by_arm: dict[str, int]
    lagged_nfds: dict[str, object]
    pearl: dict[str, object]
    digest: str
    red_queen_proved: bool = False
    biological_red_queen_proved: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "typed_outcome": self.typed_outcome,
            "rq_earn_seed_pass": self.rq_earn_seed_pass,
            "polymorphism_hold": self.polymorphism_hold,
            "excluded_from_lag_fraction": self.excluded_from_lag_fraction,
            "claim_ceiling": self.claim_ceiling,
            "snaps_by_arm": self.snaps_by_arm,
            "dense_snaps_by_arm": self.dense_snaps_by_arm,
            "turnover_by_arm": self.turnover_by_arm,
            "terminal_census_by_arm": dict(self.terminal_census_by_arm),
            "lagged_nfds": self.lagged_nfds,
            "pearl": self.pearl,
            "digest": self.digest,
            "red_queen_proved": False,
            "biological_red_queen_proved": False,
            "estimand": ESTIMAND,
            "estimand_fork": ESTIMAND_FORK,
            "bolus": STAGE0_WINNER_BOLUS,
            "n_patches": STAGE0_WINNER_N_PATCHES,
        }


@dataclass(frozen=True, slots=True)
class RQEarnConfirmCampaignReport:
    seeds: tuple[int, ...]
    seed_results: tuple[RQEarnConfirmSeedResult, ...]
    typed_outcome_counts: dict[str, int]
    rq_earn_seed_pass_count: int
    campaign_success: bool
    campaign_mixed: bool
    campaign_fail: bool
    claim_ceiling: str
    design_digest: str
    document_digest: str
    digest: str
    notes: str
    red_queen_proved: bool = False
    biological_red_queen_proved: bool = False
    stage0_bolus: float = STAGE0_WINNER_BOLUS
    stage0_n_patches: int = STAGE0_WINNER_N_PATCHES

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "hp_arm01_rq_earn_confirm_v1",
            "prereg_version": PREREG_VERSION,
            "revision": HP_ARM01_RQ_EARN_CONFIRM_REVISION,
            "slice": SLICE_NAME,
            "estimand": ESTIMAND,
            "estimand_fork": ESTIMAND_FORK,
            "seeds": list(self.seeds),
            "seed_results": [r.to_dict() for r in self.seed_results],
            "typed_outcome_counts": dict(self.typed_outcome_counts),
            "rq_earn_seed_pass_count": self.rq_earn_seed_pass_count,
            "campaign_pass_bar": RQ_EARN_CONFIRM_PASS_BAR,
            "campaign_n": RQ_EARN_CONFIRM_N,
            "campaign_success": self.campaign_success,
            "campaign_mixed": self.campaign_mixed,
            "campaign_fail": self.campaign_fail,
            "claim_ceiling": self.claim_ceiling,
            "red_queen_proved": False,
            "biological_red_queen_proved": False,
            "design_digest": self.design_digest,
            "document_digest": self.document_digest,
            "digest": self.digest,
            "generations": RQ_EARN_CONFIRM_GENERATIONS,
            "locked_windows": list(RQ_EARN_CONFIRM_LOCKED_WINDOWS),
            "snap_stride": RQ_EARN_CONFIRM_SNAP_STRIDE,
            "lag_tau": RQ_EARN_CONFIRM_LAG_TAU,
            "lagged_nfds_threshold": RQ_EARN_CONFIRM_NFDS_THRESHOLD,
            "lagged_nfds_min_points": RQ_EARN_CONFIRM_MIN_POINTS,
            "r_min": RQ_EARN_CONFIRM_R_MIN,
            "epsilon": RQ_EARN_CONFIRM_EPSILON,
            "min_viable_census": RQ_EARN_CONFIRM_MIN_VIABLE,
            "soft_carrying_capacity": RQ_EARN_CONFIRM_SOFT_K,
            "resource_bolus_amount": self.stage0_bolus,
            "n_food_patches": self.stage0_n_patches,
            "pearl_freeze_neq_absent": True,
            "regime_hostile_ne_excluded_from_lag_fraction": True,
            "avi_ignored_for_lag_credit": True,
            "p4_claimgate_allowlist_not_flipped_here": True,
            "sealed_fails_untouched": ["214df20", "91ab0c6", "7171d19"],
            "notes": self.notes,
        }


def run_rq_earn_confirm_seed(
    *,
    seed: int,
    generations: int | None = None,
    bolus: float | None = None,
    n_patches: int | None = None,
) -> RQEarnConfirmSeedResult:
    """Run one RQ-earn confirm seed (ecology arms + Pearl contrasts)."""

    gens = int(RQ_EARN_CONFIRM_GENERATIONS if generations is None else generations)
    assert_rq_earn_confirm_seed_policy([seed])
    assert_ecology_arm_taxonomy()
    assert_passage_taxonomy()
    if not STAGE0_WINNER_PINNED and bolus is None:
        # Allow explicit bolus override for tests; campaign requires pin.
        pass
    if float(RQ_EARN_CONFIRM_SOFT_K) != 64.0:
        raise ConfigurationError("soft K must stay 64")
    if int(RQ_EARN_CONFIRM_MIN_VIABLE) != 12:
        raise ConfigurationError("min_viable must stay 12")

    snaps_by_arm: dict[str, dict[int, dict[str, object]]] = {}
    dense_snaps_by_arm: dict[str, dict[int, dict[str, object]]] = {}
    turnover_by_arm: dict[str, dict[str, object]] = {}
    census: dict[str, int] = {}

    for arm_name in ECOLOGY_ARMS:
        arm = RQEarnConfirmArm.boot_rq_earn(
            arm=arm_name, seed=seed, bolus=bolus, n_patches=n_patches
        )
        if float(arm.soft_carrying_capacity) != float(RQ_EARN_CONFIRM_SOFT_K):
            raise ConfigurationError("soft K digest-pin mismatch")
        arm.run_generations(gens)
        snaps_by_arm[arm_name] = {
            int(g): arm.window_snapshot(int(g)) for g in RQ_EARN_CONFIRM_LOCKED_WINDOWS
        }
        dense_snaps_by_arm[arm_name] = collect_dense_snaps(
            arm, horizon=gens, snap_stride=RQ_EARN_CONFIRM_SNAP_STRIDE
        )
        turnover_by_arm[arm_name] = arm.turnover_audit()
        census[arm_name] = int(arm.living_host_census())

    classified = classify_rq_earn_confirm_outcome(
        arm_snaps=snaps_by_arm,
        turnover_by_arm=turnover_by_arm,
        dense_snaps_by_arm=dense_snaps_by_arm,
    )
    typed = str(classified["typed_outcome"])
    rq_pass = bool(classified["rq_earn_seed_pass"])
    seed_ceiling = (
        CLAIM_CEILING_CANDIDATE if rq_pass else CLAIM_CEILING_OBSERVATION
    )
    body = {
        "seed": int(seed),
        "typed": typed,
        "rq_pass": rq_pass,
        "census": census,
        "bolus": float(bolus if bolus is not None else STAGE0_WINNER_BOLUS),
        "n_patches": int(n_patches if n_patches is not None else STAGE0_WINNER_N_PATCHES),
        "revision": HP_ARM01_RQ_EARN_CONFIRM_REVISION,
        "red_queen_proved": False,
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    return RQEarnConfirmSeedResult(
        seed=int(seed),
        typed_outcome=typed,
        rq_earn_seed_pass=rq_pass,
        polymorphism_hold=bool(classified["polymorphism_hold"]),
        excluded_from_lag_fraction=bool(classified["excluded_from_lag_fraction"]),
        claim_ceiling=seed_ceiling,
        snaps_by_arm=snaps_by_arm,
        dense_snaps_by_arm=dense_snaps_by_arm,
        turnover_by_arm=turnover_by_arm,
        terminal_census_by_arm=census,
        lagged_nfds=classified.get("lagged_nfds") or {},  # type: ignore[arg-type]
        pearl=classified.get("pearl") or {},  # type: ignore[arg-type]
        digest=digest,
        red_queen_proved=False,
        biological_red_queen_proved=False,
    )


def assemble_rq_earn_confirm_campaign(
    seed_results: Sequence[RQEarnConfirmSeedResult],
) -> RQEarnConfirmCampaignReport:
    chosen = tuple(sorted(int(r.seed) for r in seed_results))
    counts = {label: 0 for label in sorted(RQ_EARN_TYPED_OUTCOMES)}
    for row in seed_results:
        counts[row.typed_outcome] = counts.get(row.typed_outcome, 0) + 1
    n_pass = sum(1 for r in seed_results if r.rq_earn_seed_pass)
    campaign_success = n_pass >= RQ_EARN_CONFIRM_PASS_BAR
    campaign_fail = n_pass <= 7
    campaign_mixed = (not campaign_success) and (not campaign_fail)
    # Ceiling: observation until SUCCESS evidence; still proved=false
    ceiling = (
        CLAIM_CEILING_CANDIDATE if campaign_success else CLAIM_CEILING_OBSERVATION
    )
    design = rq_earn_confirm_design_digest()
    document = rq_earn_confirm_document_digest()
    report_body = {
        "seeds": list(chosen),
        "counts": counts,
        "rq_earn_seed_pass": n_pass,
        "campaign_success": campaign_success,
        "design": design,
        "document": document,
        "bolus": STAGE0_WINNER_BOLUS,
        "n_patches": STAGE0_WINNER_N_PATCHES,
        "revision": HP_ARM01_RQ_EARN_CONFIRM_REVISION,
        "red_queen_proved": False,
    }
    digest = hashlib.sha256(
        json.dumps(report_body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    notes = (
        f"primary_success=rq_earn_seed_pass;pass={n_pass}/{len(chosen)};"
        f"bar={RQ_EARN_CONFIRM_PASS_BAR};campaign_success={campaign_success};"
        f"bolus={STAGE0_WINNER_BOLUS};patches={STAGE0_WINNER_N_PATCHES};"
        f"lag_tau={RQ_EARN_CONFIRM_LAG_TAU};thr={RQ_EARN_CONFIRM_NFDS_THRESHOLD};"
        f"pearl_freeze_neq_absent=true;hostile_ne_excluded=true;"
        f"avi_ignored_for_lag=true;red_queen_proved=false;"
        f"p4_allowlist_not_flipped=true"
    )
    # Hard invariant
    if any(r.red_queen_proved or r.biological_red_queen_proved for r in seed_results):
        raise ConfigurationError("RQ-earn confirm must not set proved flags")
    return RQEarnConfirmCampaignReport(
        seeds=chosen,
        seed_results=tuple(seed_results),
        typed_outcome_counts=counts,
        rq_earn_seed_pass_count=n_pass,
        campaign_success=campaign_success,
        campaign_mixed=campaign_mixed,
        campaign_fail=campaign_fail,
        claim_ceiling=ceiling,
        design_digest=design,
        document_digest=document,
        digest=digest,
        notes=notes,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        stage0_bolus=STAGE0_WINNER_BOLUS,
        stage0_n_patches=STAGE0_WINNER_N_PATCHES,
    )


__all__ = [
    "ESTIMAND",
    "ESTIMAND_FORK",
    "HP_ARM01_RQ_EARN_CONFIRM_REVISION",
    "OUTCOME_LAG_FAIL",
    "OUTCOME_PEARL_FAIL",
    "OUTCOME_RQ_EARN_SEED_PASS",
    "PREREG_VERSION",
    "RQEarnConfirmArm",
    "RQEarnConfirmCampaignReport",
    "RQEarnConfirmSeedResult",
    "RQ_EARN_CONFIRM_GENERATIONS",
    "RQ_EARN_CONFIRM_LAG_TAU",
    "RQ_EARN_CONFIRM_LOCKED_WINDOWS",
    "RQ_EARN_CONFIRM_MIN_POINTS",
    "RQ_EARN_CONFIRM_MIN_VIABLE",
    "RQ_EARN_CONFIRM_NFDS_THRESHOLD",
    "RQ_EARN_CONFIRM_N",
    "RQ_EARN_CONFIRM_PASS_BAR",
    "RQ_EARN_CONFIRM_SEEDS",
    "RQ_EARN_CONFIRM_SNAP_STRIDE",
    "RQ_EARN_TYPED_OUTCOMES",
    "SLICE_NAME",
    "STAGE0_WINNER_BOLUS",
    "STAGE0_WINNER_N_PATCHES",
    "STAGE0_WINNER_PINNED",
    "assemble_rq_earn_confirm_campaign",
    "assert_rq_earn_confirm_seed_policy",
    "classify_rq_earn_confirm_outcome",
    "evaluate_pearl_contrasts",
    "pin_stage0_winner",
    "prereg_document_path",
    "rq_earn_confirm_design_dict",
    "rq_earn_confirm_design_digest",
    "rq_earn_confirm_document_digest",
    "run_rq_earn_confirm_seed",
    "score_pearl_passage_lag",
]
