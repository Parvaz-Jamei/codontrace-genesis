"""HP-ARM01 selfing hold: transmission contract, mate-limitation, mid+terminal gates.

Constants match
``docs/handoff/CLOSED_LOOP_HP_ARM01_SELFING_HOLD_PREREG_20260926.md``.
Sealed Slowinski (214df20 / 201–208), persistence (91ab0c6 / 301–308), mating
ledger (7171d19 / 401–408), and P7 seeds 101–108 are not reused or retuned.
SPC never owns accept or Red Queen flags.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.closed_loop_hp_arm01 import (
    ARM_AVIRULENT,
    ARM_COPASSAGED,
    ARM_FIXED,
    CLAIM_CEILING_CANDIDATE,
    CLAIM_CEILING_OBSERVATION,
    ECOLOGY_ARMS,
    HP_ARM01_ESTIMAND,
    PASSAGE_REFILL_GENERATION_BOUNDARY,
    SUBSTRATE_LIFE_LOOP,
    ThreeArmCampaignReport,
    max_allowed_claim_ceiling,
)
from codontrace.genesis.closed_loop_hp_arm01_mating import assay_validity_gate

PREREG_VERSION = "hp_arm01_selfing_hold_prereg_20260926"
PREREG_RELATIVE_PATH = (
    "docs/handoff/CLOSED_LOOP_HP_ARM01_SELFING_HOLD_PREREG_20260926.md"
)
HP_ARM01_SELFING_HOLD_REVISION = "hp-arm01-selfing-hold-20260926"
SLICE_TRANSMISSION = "HP-ARM01-SELFING-TRANSMISSION-CONTRACT"
SLICE_MATE_LIMIT = "HP-ARM01-MATE-LIMITATION-PROCESS"
SLICE_AVI_HOLD = "HP-ARM01-AVI-HOLD-GATE"
SLICE_BASELINE_HOLD = "HP-ARM01-BASELINE-HOLD-GATE"

OUTCOME_PERSISTENCE_FAIL = "persistence_fail"
OUTCOME_SELFING_NONVIABLE = "selfing_nonviable"
OUTCOME_INVASION_FAIL = "invasion_fail"
OUTCOME_INVASION_PASS = "invasion_pass"
TYPED_OUTCOMES = frozenset(
    {
        OUTCOME_PERSISTENCE_FAIL,
        OUTCOME_SELFING_NONVIABLE,
        OUTCOME_INVASION_FAIL,
        OUTCOME_INVASION_PASS,
    }
)

HOLD_SEEDS: tuple[int, ...] = (501, 502, 503, 504, 505, 506, 507, 508)
SEALED_P7_SEEDS: tuple[int, ...] = (101, 102, 103, 104, 105, 106, 107, 108)
SEALED_SLOWINSKI_SEEDS: tuple[int, ...] = (201, 202, 203, 204, 205, 206, 207, 208)
SEALED_PERSISTENCE_SEEDS: tuple[int, ...] = (301, 302, 303, 304, 305, 306, 307, 308)
SEALED_MATING_SEEDS: tuple[int, ...] = (401, 402, 403, 404, 405, 406, 407, 408)

HOLD_GENERATIONS = 48
HOLD_MID_WINDOWS: tuple[int, ...] = (16, 32)
HOLD_EPSILON = 0.05
HOLD_VIRULENCE = 32.0
HOLD_PARASITE_MUTATION = 0.5
HOLD_HOST_BIT_FLIP = 0.0
HOLD_HOST_N = 10
HOLD_PARASITE_N = 8
HOLD_INTRO_SELFING_FREQ = 0.2
HOLD_BIRTH_ATP = 48.0
HOLD_BASAL_ATP_COST = 0.05
HOLD_HANDLING_TIME = 0.0
HOLD_SOFT_K = 32
HOLD_RESOURCE_BOLUS_AMOUNT = 20.0
HOLD_PASSAGE_REFILL_MODE = PASSAGE_REFILL_GENERATION_BOUNDARY
HOLD_PASSAGE_REFILL_SYNC = "generation_boundary"
HOLD_STEAL_FRACTION = 0.25
HOLD_FOUNDER_SPATIAL_POLICY = "food_patch_interleaved"
HOLD_FOOD_PATCHES: tuple[tuple[int, int], ...] = tuple(
    (x, y) for x in range(4) for y in range(2)
)
HOLD_MIN_VIABLE_CENSUS = 8
HOLD_INVASION_PASS_BAR = 6
HOLD_ASSAY_VALID_BAR = 6
HOLD_TWO_FOLD_COST_SEX = True
HOLD_THIN_CHEMOSTAT_ATP = 0.0
HOLD_MATING_LOCUS_LOCK = True
HOLD_SELFING_BIRTH_ATP_ENDOWMENT = 48.0
HOLD_MATE_SEARCH_RADIUS = 1
HOLD_OUTCROSS_MATES_PER_GENERATION_CAP = 1
HOLD_CHAMBER_MAX_BIRTH_WAIT_TICKS = 2
HOLD_CHAMBER_TIMEOUT_POLICY = "fail"

_INVASION_FOUNDERS: tuple[tuple[str, str], ...] = (
    ("outcross", "000111"),
    ("outcross", "000111"),
    ("outcross", "000111"),
    ("outcross", "111000"),
    ("outcross", "111000"),
    ("outcross", "111000"),
    ("outcross", "000111"),
    ("outcross", "111000"),
    ("selfing", "000111"),
    ("selfing", "111000"),
)


def prereg_document_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / PREREG_RELATIVE_PATH


def locked_design_dict() -> dict[str, object]:
    return {
        "prereg_version": PREREG_VERSION,
        "revision": HP_ARM01_SELFING_HOLD_REVISION,
        "slices": [
            SLICE_TRANSMISSION,
            SLICE_MATE_LIMIT,
            SLICE_AVI_HOLD,
            SLICE_BASELINE_HOLD,
        ],
        "estimand": HP_ARM01_ESTIMAND,
        "estimand_conditional_on_assay_valid_and_avi_hold": True,
        "substrate": SUBSTRATE_LIFE_LOOP,
        "seeds": list(HOLD_SEEDS),
        "sealed_p7_seeds_untouched": list(SEALED_P7_SEEDS),
        "sealed_slowinski_seeds_untouched": list(SEALED_SLOWINSKI_SEEDS),
        "sealed_persistence_seeds_untouched": list(SEALED_PERSISTENCE_SEEDS),
        "sealed_mating_seeds_untouched": list(SEALED_MATING_SEEDS),
        "generations": HOLD_GENERATIONS,
        "mid_hold_windows": list(HOLD_MID_WINDOWS),
        "avirulent_selfing_hold_epsilon": HOLD_EPSILON,
        "virulence": HOLD_VIRULENCE,
        "parasite_mutation": HOLD_PARASITE_MUTATION,
        "host_bit_flip_rate": HOLD_HOST_BIT_FLIP,
        "host_n": HOLD_HOST_N,
        "parasite_n": HOLD_PARASITE_N,
        "intro_selfing_freq": HOLD_INTRO_SELFING_FREQ,
        "birth_atp": HOLD_BIRTH_ATP,
        "basal_runtime_atp_cost": HOLD_BASAL_ATP_COST,
        "handling_time": HOLD_HANDLING_TIME,
        "soft_carrying_capacity": HOLD_SOFT_K,
        "passage_refill_mode": HOLD_PASSAGE_REFILL_MODE,
        "passage_refill_sync": HOLD_PASSAGE_REFILL_SYNC,
        "resource_bolus_amount": HOLD_RESOURCE_BOLUS_AMOUNT,
        "food_patches": [list(p) for p in HOLD_FOOD_PATCHES],
        "thin_chemostat_atp_inflow": HOLD_THIN_CHEMOSTAT_ATP,
        "steal_fraction": HOLD_STEAL_FRACTION,
        "founder_spatial_policy": HOLD_FOUNDER_SPATIAL_POLICY,
        "min_viable_census": HOLD_MIN_VIABLE_CENSUS,
        "invasion_pass_bar": HOLD_INVASION_PASS_BAR,
        "assay_valid_bar": HOLD_ASSAY_VALID_BAR,
        "two_fold_cost_sex": HOLD_TWO_FOLD_COST_SEX,
        "transmission_contract": {
            "mode_true_birth": True,
            "mating_locus_lock": HOLD_MATING_LOCUS_LOCK,
            "selfing_birth_atp_endowment": HOLD_SELFING_BIRTH_ATP_ENDOWMENT,
        },
        "mate_limitation": {
            "mode": "local_radius_plus_per_capita_cap",
            "mate_search_radius": HOLD_MATE_SEARCH_RADIUS,
            "outcross_mates_per_generation_cap": HOLD_OUTCROSS_MATES_PER_GENERATION_CAP,
            "chamber_max_birth_wait_ticks": HOLD_CHAMBER_MAX_BIRTH_WAIT_TICKS,
            "chamber_timeout_policy": HOLD_CHAMBER_TIMEOUT_POLICY,
        },
        "founders": [list(row) for row in _INVASION_FOUNDERS],
        "arms": [ARM_AVIRULENT, ARM_FIXED, ARM_COPASSAGED],
        "typed_outcomes": sorted(TYPED_OUTCOMES),
        "prereg_path": PREREG_RELATIVE_PATH,
        "accept_path": HP_ARM01_ESTIMAND,
        "spc_owns_accept_path": False,
        "spc_owns_red_queen": False,
        "spc_owns_baseline": False,
        "legacy_three_freq_is_accept_path": False,
        "shared_modifier_refused_as_primary": True,
        "red_queen_proved_allowed": False,
        "biological_red_queen_proved_allowed": False,
        "last_live_is_slowinski_pass": False,
        "early_bump_is_baseline": False,
        "soft_green_prior_slowinski_prereg_forbidden": True,
        "soft_green_prior_persistence_prereg_forbidden": True,
        "soft_green_prior_mating_prereg_forbidden": True,
        "debit_gain_schedule": {
            "virulence": HOLD_VIRULENCE,
            "steal_fraction": HOLD_STEAL_FRACTION,
            "birth_atp": HOLD_BIRTH_ATP,
            "resource_bolus_amount": HOLD_RESOURCE_BOLUS_AMOUNT,
            "soft_carrying_capacity": HOLD_SOFT_K,
        },
    }


def selfing_hold_design_digest() -> str:
    return canonical_digest(locked_design_dict(), prefix="hp_arm01_selfing_hold_design")


def selfing_hold_document_digest() -> str:
    path = prereg_document_path()
    if not path.is_file():
        raise ConfigurationError(f"missing preregistration file: {PREREG_RELATIVE_PATH}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_hold_seed_policy(seeds: Sequence[int] | None = None) -> None:
    chosen = tuple(int(s) for s in (seeds if seeds is not None else HOLD_SEEDS))
    if not chosen:
        raise ConfigurationError("selfing-hold confirmatory seeds must be non-empty")
    if len(set(chosen)) != len(chosen):
        raise ConfigurationError("selfing-hold confirmatory seeds must be unique")
    for label, sealed in (
        ("P7", SEALED_P7_SEEDS),
        ("Slowinski", SEALED_SLOWINSKI_SEEDS),
        ("persistence", SEALED_PERSISTENCE_SEEDS),
        ("mating", SEALED_MATING_SEEDS),
    ):
        overlap = sorted(set(chosen) & set(sealed))
        if overlap:
            raise ConfigurationError(
                f"sealed {label} seeds must not be reused; overlap={overlap}"
            )
    if seeds is None and tuple(chosen) != HOLD_SEEDS:
        raise ConfigurationError("default selfing-hold seed tuple was altered")


def assert_hold_locked_horizon(*, generations: int) -> None:
    if int(generations) < HOLD_GENERATIONS:
        raise ConfigurationError(
            f"selfing-hold confirmatory horizon is locked at {HOLD_GENERATIONS} "
            f"generations; got {generations}"
        )


def _freq_at_generation(
    outcross_by_generation: Sequence[int],
    selfing_by_generation: Sequence[int],
    *,
    generation: int,
) -> float | None:
    """Selfing frequency after ``generation`` steps (1-indexed generation number)."""

    idx = int(generation) - 1
    if idx < 0 or idx >= len(selfing_by_generation) or idx >= len(outcross_by_generation):
        return None
    out_n = int(outcross_by_generation[idx])
    self_n = int(selfing_by_generation[idx])
    denom = out_n + self_n
    if denom <= 0:
        return None
    return self_n / denom


def avirulent_selfing_hold_series(
    *,
    outcross_by_generation: Sequence[int],
    selfing_by_generation: Sequence[int],
    mid_windows: Sequence[int] = HOLD_MID_WINDOWS,
    terminal_generation: int = HOLD_GENERATIONS,
    epsilon: float = HOLD_EPSILON,
) -> dict[str, object]:
    """Evaluate mid+terminal hold; bump-then-purge fails."""

    checks: dict[str, float | None] = {}
    held = True
    for window in mid_windows:
        freq = _freq_at_generation(
            outcross_by_generation, selfing_by_generation, generation=int(window)
        )
        checks[f"mid_{int(window)}"] = freq
        if freq is None or float(freq) < float(epsilon):
            held = False
    terminal = _freq_at_generation(
        outcross_by_generation,
        selfing_by_generation,
        generation=int(terminal_generation),
    )
    checks["terminal"] = terminal
    if terminal is None or float(terminal) < float(epsilon):
        held = False
    series = [
        (int(o), int(s))
        for o, s in zip(outcross_by_generation, selfing_by_generation, strict=False)
    ]
    digest = hashlib.sha256(
        json.dumps(
            {"series": series, "epsilon": float(epsilon), "mids": list(mid_windows)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return {
        "hold_passes": held,
        "frequencies": checks,
        "epsilon": float(epsilon),
        "mid_windows": [int(w) for w in mid_windows],
        "baseline_series_digest": digest,
        "series_out_self": series,
    }


def classify_typed_outcome(
    *,
    assay_valid: bool,
    avirulent_selfing_hold: bool,
    slowinski_invasion_holds: bool,
) -> str:
    if not assay_valid:
        return OUTCOME_PERSISTENCE_FAIL
    if not avirulent_selfing_hold:
        return OUTCOME_SELFING_NONVIABLE
    if slowinski_invasion_holds:
        return OUTCOME_INVASION_PASS
    return OUTCOME_INVASION_FAIL


@dataclass(frozen=True, slots=True)
class SelfingHoldSeedResult:
    seed: int
    typed_outcome: str
    assay_valid: bool
    avirulent_selfing_hold: bool
    slowinski_invasion_holds: bool | None
    selfing_freq_by_arm: dict[str, float | None]
    terminal_census_by_arm: dict[str, int]
    intro_selfing_freq: float
    claim_ceiling: str
    max_allowed_ceiling: str
    digest: str
    clocks_complete: bool
    per_arm_clocks_ok: bool
    life_loop_bound: bool
    two_fold_cost_sex_applied: bool
    birth_atp: float
    basal_runtime_atp_cost: float
    soft_carrying_capacity: int
    steal_fraction: float
    founder_spatial_policy: str
    passage_refill_mode: str
    resource_bolus_amount: float
    passage_refill_sync: str
    cumulative_resource_bolus_by_arm: dict[str, float]
    avi_hold_frequencies: dict[str, float | None]
    baseline_series_digest: str
    avi_selfing_series: list[tuple[int, int]]
    report: ThreeArmCampaignReport

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "typed_outcome": self.typed_outcome,
            "assay_valid": self.assay_valid,
            "avirulent_selfing_hold": self.avirulent_selfing_hold,
            "slowinski_invasion_holds": self.slowinski_invasion_holds,
            "selfing_freq_by_arm": dict(self.selfing_freq_by_arm),
            "terminal_census_by_arm": dict(self.terminal_census_by_arm),
            "intro_selfing_freq": self.intro_selfing_freq,
            "claim_ceiling": self.claim_ceiling,
            "max_allowed_ceiling": self.max_allowed_ceiling,
            "digest": self.digest,
            "clocks_complete": self.clocks_complete,
            "per_arm_clocks_ok": self.per_arm_clocks_ok,
            "life_loop_bound": self.life_loop_bound,
            "two_fold_cost_sex_applied": self.two_fold_cost_sex_applied,
            "birth_atp": self.birth_atp,
            "basal_runtime_atp_cost": self.basal_runtime_atp_cost,
            "soft_carrying_capacity": self.soft_carrying_capacity,
            "steal_fraction": self.steal_fraction,
            "founder_spatial_policy": self.founder_spatial_policy,
            "passage_refill_mode": self.passage_refill_mode,
            "resource_bolus_amount": self.resource_bolus_amount,
            "passage_refill_sync": self.passage_refill_sync,
            "cumulative_resource_bolus_by_arm": dict(self.cumulative_resource_bolus_by_arm),
            "avi_hold_frequencies": dict(self.avi_hold_frequencies),
            "baseline_series_digest": self.baseline_series_digest,
            "estimand": HP_ARM01_ESTIMAND,
            "substrate": SUBSTRATE_LIFE_LOOP,
            "last_live_used_as_pass": False,
            "early_bump_used_as_baseline": False,
        }


@dataclass(frozen=True, slots=True)
class SelfingHoldConfirmReport:
    seeds: tuple[int, ...]
    seed_results: tuple[SelfingHoldSeedResult, ...]
    typed_outcome_counts: dict[str, int]
    seeds_assay_valid: int
    seeds_selfing_hold: int
    seeds_invasion_passed: int
    assay_valid_bar: int
    invasion_pass_bar: int
    assay_campaign_pass: bool
    invasion_campaign_pass: bool
    claim_ceiling: str
    max_allowed_ceiling: str
    two_fold_cost_sex_applied: bool
    red_queen_proved: bool
    biological_red_queen_proved: bool
    design_digest: str
    document_digest: str
    generations: int
    virulence: float
    parasite_mutation: float
    intro_selfing_freq: float
    birth_atp: float
    basal_runtime_atp_cost: float
    soft_carrying_capacity: int
    steal_fraction: float
    founder_spatial_policy: str
    passage_refill_mode: str
    resource_bolus_amount: float
    passage_refill_sync: str
    revision: str
    notes: str
    digest: str
    baseline_series_digest_campaign: str

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": "hp_arm01_selfing_hold_confirm_v1",
            "prereg_version": PREREG_VERSION,
            "revision": self.revision,
            "slices": [
                SLICE_TRANSMISSION,
                SLICE_MATE_LIMIT,
                SLICE_AVI_HOLD,
                SLICE_BASELINE_HOLD,
            ],
            "estimand": HP_ARM01_ESTIMAND,
            "estimand_conditional_on_assay_valid_and_avi_hold": True,
            "accept_path": HP_ARM01_ESTIMAND,
            "substrate": SUBSTRATE_LIFE_LOOP,
            "seeds": list(self.seeds),
            "seed_results": [row.to_dict() for row in self.seed_results],
            "typed_outcome_counts": dict(self.typed_outcome_counts),
            "seeds_assay_valid": self.seeds_assay_valid,
            "seeds_selfing_hold": self.seeds_selfing_hold,
            "seeds_invasion_passed": self.seeds_invasion_passed,
            "assay_valid_bar": self.assay_valid_bar,
            "invasion_pass_bar": self.invasion_pass_bar,
            "assay_campaign_pass": self.assay_campaign_pass,
            "invasion_campaign_pass": self.invasion_campaign_pass,
            "slowinski_invasion_campaign_holds": self.invasion_campaign_pass,
            "claim_ceiling": self.claim_ceiling,
            "max_allowed_ceiling": self.max_allowed_ceiling,
            "two_fold_cost_sex_applied": self.two_fold_cost_sex_applied,
            "two_fold_cost_sex_note": (
                "paid under this lock (Avida TWO_FOLD_COST_SEX / one chamber "
                "product); Ashby 2020 sex!=RQD; RQ flags stay false"
            ),
            "red_queen_proved": self.red_queen_proved,
            "biological_red_queen_proved": self.biological_red_queen_proved,
            "design_digest": self.design_digest,
            "document_digest": self.document_digest,
            "baseline_series_digest_campaign": self.baseline_series_digest_campaign,
            "generations": self.generations,
            "mid_hold_windows": list(HOLD_MID_WINDOWS),
            "avirulent_selfing_hold_epsilon": HOLD_EPSILON,
            "virulence": self.virulence,
            "parasite_mutation": self.parasite_mutation,
            "intro_selfing_freq": self.intro_selfing_freq,
            "host_n": HOLD_HOST_N,
            "parasite_n": HOLD_PARASITE_N,
            "birth_atp": self.birth_atp,
            "basal_runtime_atp_cost": self.basal_runtime_atp_cost,
            "soft_carrying_capacity": self.soft_carrying_capacity,
            "steal_fraction": self.steal_fraction,
            "founder_spatial_policy": self.founder_spatial_policy,
            "passage_refill_mode": self.passage_refill_mode,
            "resource_bolus_amount": self.resource_bolus_amount,
            "passage_refill_sync": self.passage_refill_sync,
            "thin_chemostat_atp_inflow": HOLD_THIN_CHEMOSTAT_ATP,
            "min_viable_census": HOLD_MIN_VIABLE_CENSUS,
            "handling_time": HOLD_HANDLING_TIME,
            "mating_locus_lock": HOLD_MATING_LOCUS_LOCK,
            "selfing_birth_atp_endowment": HOLD_SELFING_BIRTH_ATP_ENDOWMENT,
            "mate_search_radius": HOLD_MATE_SEARCH_RADIUS,
            "outcross_mates_per_generation_cap": HOLD_OUTCROSS_MATES_PER_GENERATION_CAP,
            "spc_owns_accept_path": False,
            "spc_owns_red_queen": False,
            "spc_owns_baseline": False,
            "legacy_three_freq_is_accept_path": False,
            "shared_modifier_refused_as_primary_substrate": True,
            "sealed_p7_seeds_untouched": True,
            "sealed_slowinski_prereg_untouched": True,
            "sealed_persistence_prereg_untouched": True,
            "sealed_mating_prereg_untouched": True,
            "last_live_used_as_pass": False,
            "early_bump_used_as_baseline": False,
            "notes": self.notes,
        }
        payload["digest"] = self.digest
        return payload


def run_selfing_hold_confirm_campaign(
    *,
    seeds: Sequence[int] | None = None,
    generations: int | None = None,
    virulence: float | None = None,
    parasite_mutation: float | None = None,
    attach_pearl_measurement: bool = False,
) -> SelfingHoldConfirmReport:
    """Run the locked selfing-hold confirmatory campaign."""

    chosen_seeds = tuple(int(s) for s in (seeds if seeds is not None else HOLD_SEEDS))
    gens = int(HOLD_GENERATIONS if generations is None else generations)
    vir = float(HOLD_VIRULENCE if virulence is None else virulence)
    pmut = float(HOLD_PARASITE_MUTATION if parasite_mutation is None else parasite_mutation)

    assert_hold_seed_policy(chosen_seeds)
    assert_hold_locked_horizon(generations=gens)
    if abs(vir - HOLD_VIRULENCE) > 1e-12:
        raise ConfigurationError(
            f"selfing-hold virulence is locked at {HOLD_VIRULENCE}; got {vir}"
        )
    if abs(pmut - HOLD_PARASITE_MUTATION) > 1e-12:
        raise ConfigurationError(
            f"selfing-hold parasite_mutation is locked at {HOLD_PARASITE_MUTATION}; "
            f"got {pmut}"
        )

    design = selfing_hold_design_digest()
    document = selfing_hold_document_digest()

    from codontrace.genesis.closed_loop_hp_arm01 import (
        ARM_TO_PASSAGE,
        INVASION_CLOCKS,
        REQUIRED_CLOCKS,
        LifeLoopEcologyArm,
        assert_ecology_arm_taxonomy,
        per_arm_clocks_complete,
        refuse_shared_modifier_as_slowinski_pass,
        required_clocks_complete,
        slowinski_invasion_contrast,
        slowinski_selfing_invasion_contrast,
    )
    from codontrace.genesis.closed_loop_hp_arm01 import ThreeArmCampaignReport as _TAR
    import hashlib as _hashlib
    import json as _json

    results: list[SelfingHoldSeedResult] = []
    campaign_series_parts: list[dict[str, object]] = []

    for seed in chosen_seeds:
        assert_ecology_arm_taxonomy()
        arms: dict[str, LifeLoopEcologyArm] = {}
        clocks_by_arm: dict = {}
        freqs: dict[str, float | None] = {}
        census: dict[str, int] = {}
        bolus_by_arm: dict[str, float] = {}
        hp_env_ids: dict[str, int] = {}
        intro_freq = 0.0
        avi_hold_info: dict[str, object] = {}

        for arm_name in ECOLOGY_ARMS:
            arm = LifeLoopEcologyArm.boot(
                arm=arm_name,
                virulence=vir,
                seed=seed,
                handling_time=HOLD_HANDLING_TIME,
                parasite_mutation=pmut,
                birth_atp=HOLD_BIRTH_ATP,
                parasite_n=HOLD_PARASITE_N,
                founders=_INVASION_FOUNDERS,
                soft_carrying_capacity=HOLD_SOFT_K,
                basal_runtime_atp_cost=HOLD_BASAL_ATP_COST,
                passage_refill_mode=HOLD_PASSAGE_REFILL_MODE,
                resource_bolus_amount=HOLD_RESOURCE_BOLUS_AMOUNT,
                food_patches=HOLD_FOOD_PATCHES,
                steal_fraction=HOLD_STEAL_FRACTION,
                founder_spatial_policy=HOLD_FOUNDER_SPATIAL_POLICY,
                two_fold_cost_sex=HOLD_TWO_FOLD_COST_SEX,
                mating_locus_lock=HOLD_MATING_LOCUS_LOCK,
                selfing_birth_atp_endowment=HOLD_SELFING_BIRTH_ATP_ENDOWMENT,
                mate_search_radius=HOLD_MATE_SEARCH_RADIUS,
                outcross_mates_per_generation_cap=HOLD_OUTCROSS_MATES_PER_GENERATION_CAP,
                chamber_max_birth_wait_ticks=HOLD_CHAMBER_MAX_BIRTH_WAIT_TICKS,
                chamber_timeout_policy=HOLD_CHAMBER_TIMEOUT_POLICY,
            )
            arm.run_generations(gens)
            arms[arm_name] = arm
            clocks_by_arm[arm_name] = arm.build_clocks()
            freqs[arm_name] = arm.terminal_selfing_freq()
            census[arm_name] = int(arm.living_host_census())
            bolus_by_arm[arm_name] = float(arm.cumulative_resource_bolus_placed)
            hp_env_ids[arm_name] = id(arm.hp_env)
            intro_freq = arm.intro_selfing_freq
            if arm_name == ARM_AVIRULENT:
                avi_hold_info = avirulent_selfing_hold_series(
                    outcross_by_generation=arm.outcross_by_generation,
                    selfing_by_generation=arm.selfing_by_generation,
                )

        treatment_clocks = clocks_by_arm[ARM_COPASSAGED]
        campaign_clocks = {
            name: treatment_clocks[name]
            for name in list(REQUIRED_CLOCKS) + list(INVASION_CLOCKS)
            if name in treatment_clocks
        }
        clocks_ok = required_clocks_complete(campaign_clocks)
        per_arm_ok = per_arm_clocks_complete(clocks_by_arm)
        life_ok = True
        treatment_control = True

        assay_ok = assay_validity_gate(
            terminal_census_by_arm=census,
            min_viable_census=HOLD_MIN_VIABLE_CENSUS,
        )
        hold_ok = bool(avi_hold_info.get("hold_passes")) if assay_ok else False
        hold_freqs = dict(avi_hold_info.get("frequencies") or {})
        series_digest = str(avi_hold_info.get("baseline_series_digest") or "")
        series_pairs = list(avi_hold_info.get("series_out_self") or [])
        campaign_series_parts.append(
            {"seed": seed, "baseline_series_digest": series_digest, "hold": hold_ok}
        )

        if assay_ok and hold_ok:
            invasion = slowinski_invasion_contrast(
                intro_selfing_freq=intro_freq,
                final_selfing_avirulent=freqs[ARM_AVIRULENT],
                final_selfing_fixed=freqs[ARM_FIXED],
                final_selfing_copassaged=freqs[ARM_COPASSAGED],
            )
        else:
            invasion = False

        legacy = slowinski_selfing_invasion_contrast(
            selfing_freq_avirulent=freqs[ARM_AVIRULENT],
            selfing_freq_fixed=freqs[ARM_FIXED],
            selfing_freq_copassaged=freqs[ARM_COPASSAGED],
        )
        refuse_shared_modifier_as_slowinski_pass(
            substrate=SUBSTRATE_LIFE_LOOP, contrast_holds=invasion
        )

        ceiling_cap = max_allowed_claim_ceiling(
            clocks_complete=clocks_ok,
            treatment_control_present=treatment_control,
            substrate_life_loop_bound=life_ok,
            per_arm_clocks_ok=per_arm_ok,
            slowinski_invasion_holds=bool(assay_ok and hold_ok and invasion),
        )
        if not (assay_ok and hold_ok and invasion):
            ceiling_cap = CLAIM_CEILING_OBSERVATION
        reported_ceiling = (
            CLAIM_CEILING_CANDIDATE
            if assay_ok and hold_ok and invasion and ceiling_cap == CLAIM_CEILING_CANDIDATE
            else CLAIM_CEILING_OBSERVATION
        )

        typed = classify_typed_outcome(
            assay_valid=assay_ok,
            avirulent_selfing_hold=hold_ok if assay_ok else False,
            slowinski_invasion_holds=bool(invasion) if (assay_ok and hold_ok) else False,
        )
        invasion_scored: bool | None = (
            bool(invasion) if (assay_ok and hold_ok) else None
        )

        pearl_attached = False
        pearl_notes = ""
        if attach_pearl_measurement and per_arm_ok:
            pearl_attached = True
            pearl_notes = "pearl_spc_measurement_only_spc_does_not_own_accept_or_baseline"

        note = (
            f"typed_outcome={typed};assay_valid={assay_ok};"
            f"avirulent_selfing_hold={hold_ok};"
            f"mate_search_radius={HOLD_MATE_SEARCH_RADIUS};"
            f"two_fold={HOLD_TWO_FOLD_COST_SEX}"
        )
        if pearl_notes:
            note = f"{note};{pearl_notes}"

        digest_body = {
            "arms": list(ECOLOGY_ARMS),
            "freqs": freqs,
            "census": census,
            "assay_valid": assay_ok,
            "avirulent_selfing_hold": hold_ok,
            "hold_frequencies": hold_freqs,
            "invasion": invasion_scored,
            "typed": typed,
            "seed": seed,
            "revision": HP_ARM01_SELFING_HOLD_REVISION,
        }
        arm_digest = _hashlib.sha256(
            _json.dumps(digest_body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

        two_fold_applied = any(a.two_fold_cost_sex_applied for a in arms.values())
        report = _TAR(
            arms_present=tuple(ECOLOGY_ARMS),
            passage_map={a: ARM_TO_PASSAGE[a] for a in ECOLOGY_ARMS},
            clocks=campaign_clocks,
            clocks_by_arm=clocks_by_arm,
            clocks_complete=clocks_ok,
            per_arm_clocks_ok=per_arm_ok,
            treatment_control_present=treatment_control,
            substrate=SUBSTRATE_LIFE_LOOP,
            life_loop_bound=life_ok,
            estimand=HP_ARM01_ESTIMAND,
            slowinski_contrast_holds=bool(invasion) if (assay_ok and hold_ok) else False,
            slowinski_invasion_holds=bool(invasion) if (assay_ok and hold_ok) else False,
            legacy_three_freq_contrast_holds=bool(legacy),
            selfing_freq_by_arm=freqs,
            intro_selfing_freq=float(intro_freq),
            pearl_measurement_attached=pearl_attached,
            two_fold_cost_sex_applied=two_fold_applied,
            claim_ceiling=reported_ceiling,
            max_allowed_ceiling=ceiling_cap,
            red_queen_proved=False,
            biological_red_queen_proved=False,
            confirmatory_horizon_deferred=gens < HOLD_GENERATIONS,
            revision=HP_ARM01_SELFING_HOLD_REVISION,
            digest=arm_digest,
            notes=note,
            hp_env_ids_by_arm=hp_env_ids,
        )

        if abs(intro_freq - HOLD_INTRO_SELFING_FREQ) > 1e-12:
            raise ConfigurationError(
                "intro selfing frequency drifted from locked 0.2; refuse soft-pass"
            )
        if not report.two_fold_cost_sex_applied:
            raise ConfigurationError("two-fold cost must be applied under this lock")
        if report.red_queen_proved or report.biological_red_queen_proved:
            raise ConfigurationError("Red Queen flags must stay false")

        results.append(
            SelfingHoldSeedResult(
                seed=seed,
                typed_outcome=typed,
                assay_valid=assay_ok,
                avirulent_selfing_hold=bool(assay_ok and hold_ok),
                slowinski_invasion_holds=invasion_scored,
                selfing_freq_by_arm=dict(freqs),
                terminal_census_by_arm=dict(census),
                intro_selfing_freq=float(intro_freq),
                claim_ceiling=reported_ceiling,
                max_allowed_ceiling=ceiling_cap,
                digest=arm_digest,
                clocks_complete=clocks_ok,
                per_arm_clocks_ok=per_arm_ok,
                life_loop_bound=life_ok,
                two_fold_cost_sex_applied=True,
                birth_atp=HOLD_BIRTH_ATP,
                basal_runtime_atp_cost=HOLD_BASAL_ATP_COST,
                soft_carrying_capacity=HOLD_SOFT_K,
                steal_fraction=HOLD_STEAL_FRACTION,
                founder_spatial_policy=HOLD_FOUNDER_SPATIAL_POLICY,
                passage_refill_mode=HOLD_PASSAGE_REFILL_MODE,
                resource_bolus_amount=HOLD_RESOURCE_BOLUS_AMOUNT,
                passage_refill_sync=HOLD_PASSAGE_REFILL_SYNC,
                cumulative_resource_bolus_by_arm=dict(bolus_by_arm),
                avi_hold_frequencies={k: v for k, v in hold_freqs.items()},
                baseline_series_digest=series_digest,
                avi_selfing_series=[(int(a), int(b)) for a, b in series_pairs],
                report=report,
            )
        )

    counts = {
        OUTCOME_PERSISTENCE_FAIL: 0,
        OUTCOME_SELFING_NONVIABLE: 0,
        OUTCOME_INVASION_FAIL: 0,
        OUTCOME_INVASION_PASS: 0,
    }
    for row in results:
        counts[row.typed_outcome] = counts.get(row.typed_outcome, 0) + 1

    seeds_assay_valid = sum(1 for row in results if row.assay_valid)
    seeds_hold = sum(1 for row in results if row.avirulent_selfing_hold)
    seeds_invasion = sum(
        1 for row in results if row.typed_outcome == OUTCOME_INVASION_PASS
    )
    assay_campaign_pass = seeds_assay_valid >= HOLD_ASSAY_VALID_BAR
    invasion_campaign_pass = seeds_invasion >= HOLD_INVASION_PASS_BAR

    campaign_ceiling = CLAIM_CEILING_OBSERVATION
    if (
        invasion_campaign_pass
        and assay_campaign_pass
        and seeds_hold >= HOLD_ASSAY_VALID_BAR
    ):
        campaign_ceiling = CLAIM_CEILING_CANDIDATE

    baseline_campaign = hashlib.sha256(
        json.dumps(campaign_series_parts, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    notes = (
        f"typed_counts={json.dumps(counts, sort_keys=True)};"
        f"assay_valid={seeds_assay_valid}/{len(results)};"
        f"selfing_hold={seeds_hold}/{len(results)};"
        f"invasion_pass={seeds_invasion}/{len(results)};"
        f"ceiling={campaign_ceiling}"
    )

    draft = SelfingHoldConfirmReport(
        seeds=chosen_seeds,
        seed_results=tuple(results),
        typed_outcome_counts=counts,
        seeds_assay_valid=seeds_assay_valid,
        seeds_selfing_hold=seeds_hold,
        seeds_invasion_passed=seeds_invasion,
        assay_valid_bar=HOLD_ASSAY_VALID_BAR,
        invasion_pass_bar=HOLD_INVASION_PASS_BAR,
        assay_campaign_pass=assay_campaign_pass,
        invasion_campaign_pass=invasion_campaign_pass,
        claim_ceiling=campaign_ceiling,
        max_allowed_ceiling=campaign_ceiling,
        two_fold_cost_sex_applied=True,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        design_digest=design,
        document_digest=document,
        generations=gens,
        virulence=vir,
        parasite_mutation=pmut,
        intro_selfing_freq=HOLD_INTRO_SELFING_FREQ,
        birth_atp=HOLD_BIRTH_ATP,
        basal_runtime_atp_cost=HOLD_BASAL_ATP_COST,
        soft_carrying_capacity=HOLD_SOFT_K,
        steal_fraction=HOLD_STEAL_FRACTION,
        founder_spatial_policy=HOLD_FOUNDER_SPATIAL_POLICY,
        passage_refill_mode=HOLD_PASSAGE_REFILL_MODE,
        resource_bolus_amount=HOLD_RESOURCE_BOLUS_AMOUNT,
        passage_refill_sync=HOLD_PASSAGE_REFILL_SYNC,
        revision=HP_ARM01_SELFING_HOLD_REVISION,
        notes=notes,
        digest="",
        baseline_series_digest_campaign=baseline_campaign,
    )
    body = draft.to_dict()
    body.pop("digest", None)
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SelfingHoldConfirmReport(
        seeds=draft.seeds,
        seed_results=draft.seed_results,
        typed_outcome_counts=draft.typed_outcome_counts,
        seeds_assay_valid=draft.seeds_assay_valid,
        seeds_selfing_hold=draft.seeds_selfing_hold,
        seeds_invasion_passed=draft.seeds_invasion_passed,
        assay_valid_bar=draft.assay_valid_bar,
        invasion_pass_bar=draft.invasion_pass_bar,
        assay_campaign_pass=draft.assay_campaign_pass,
        invasion_campaign_pass=draft.invasion_campaign_pass,
        claim_ceiling=draft.claim_ceiling,
        max_allowed_ceiling=draft.max_allowed_ceiling,
        two_fold_cost_sex_applied=True,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        design_digest=design,
        document_digest=document,
        generations=draft.generations,
        virulence=draft.virulence,
        parasite_mutation=draft.parasite_mutation,
        intro_selfing_freq=draft.intro_selfing_freq,
        birth_atp=draft.birth_atp,
        basal_runtime_atp_cost=draft.basal_runtime_atp_cost,
        soft_carrying_capacity=draft.soft_carrying_capacity,
        steal_fraction=draft.steal_fraction,
        founder_spatial_policy=draft.founder_spatial_policy,
        passage_refill_mode=draft.passage_refill_mode,
        resource_bolus_amount=draft.resource_bolus_amount,
        passage_refill_sync=draft.passage_refill_sync,
        revision=draft.revision,
        notes=draft.notes,
        digest=digest,
        baseline_series_digest_campaign=baseline_campaign,
    )


def summarize_selfing_hold_terminals(
    report: SelfingHoldConfirmReport,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in report.seed_results:
        rows.append(
            {
                "seed": row.seed,
                "typed_outcome": row.typed_outcome,
                "assay_valid": row.assay_valid,
                "avirulent_selfing_hold": row.avirulent_selfing_hold,
                "invasion_holds": row.slowinski_invasion_holds,
                "avirulent": row.selfing_freq_by_arm.get(ARM_AVIRULENT),
                "fixed": row.selfing_freq_by_arm.get(ARM_FIXED),
                "copassaged": row.selfing_freq_by_arm.get(ARM_COPASSAGED),
                "census": dict(row.terminal_census_by_arm),
                "avi_hold_frequencies": dict(row.avi_hold_frequencies),
                "baseline_series_digest": row.baseline_series_digest,
                "intro": row.intro_selfing_freq,
                "digest": row.digest,
            }
        )
    return rows


__all__ = [
    "HOLD_ASSAY_VALID_BAR",
    "HOLD_EPSILON",
    "HOLD_GENERATIONS",
    "HOLD_INVASION_PASS_BAR",
    "HOLD_MID_WINDOWS",
    "HOLD_MIN_VIABLE_CENSUS",
    "HOLD_SEEDS",
    "HOLD_TWO_FOLD_COST_SEX",
    "HP_ARM01_SELFING_HOLD_REVISION",
    "OUTCOME_INVASION_FAIL",
    "OUTCOME_INVASION_PASS",
    "OUTCOME_PERSISTENCE_FAIL",
    "OUTCOME_SELFING_NONVIABLE",
    "PREREG_RELATIVE_PATH",
    "PREREG_VERSION",
    "SelfingHoldConfirmReport",
    "SelfingHoldSeedResult",
    "assert_hold_locked_horizon",
    "assert_hold_seed_policy",
    "avirulent_selfing_hold_series",
    "classify_typed_outcome",
    "locked_design_dict",
    "prereg_document_path",
    "run_selfing_hold_confirm_campaign",
    "selfing_hold_design_digest",
    "selfing_hold_document_digest",
    "summarize_selfing_hold_terminals",
]
