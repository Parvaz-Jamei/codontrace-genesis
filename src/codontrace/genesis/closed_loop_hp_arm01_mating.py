"""HP-ARM01 mating ledger + selfing baseline + debit-gain confirmatory campaign.

Constants match
``docs/handoff/CLOSED_LOOP_HP_ARM01_MATING_LEDGER_PREREG_20260926.md``.
Sealed Slowinski prereg (214df20 / seeds 201–208), persistence ledger
(91ab0c6 / seeds 301–308), and P7 seeds 101–108 are not reused or retuned.
Typed outcomes separate persistence_fail, selfing_nonviable, invasion_fail,
and invasion_pass. SPC never owns accept or Red Queen flags.
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

PREREG_VERSION = "hp_arm01_mating_ledger_prereg_20260926"
PREREG_RELATIVE_PATH = (
    "docs/handoff/CLOSED_LOOP_HP_ARM01_MATING_LEDGER_PREREG_20260926.md"
)
HP_ARM01_MATING_REVISION = "hp-arm01-mating-ledger-20260926"
SLICE_MATING_LEDGER = "HP-ARM01-MATING-LEDGER"
SLICE_SELFING_BASELINE = "HP-ARM01-SELFING-BASELINE"
SLICE_CLAIMGATE_TAXONOMY = "HP-ARM01-CLAIMGATE-SELFING-TAXONOMY"
SLICE_DEBIT_GAIN = "HP-ARM01-DEBIT-GAIN-ASSURANCE"

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

MATING_SEEDS: tuple[int, ...] = (401, 402, 403, 404, 405, 406, 407, 408)
SEALED_P7_SEEDS: tuple[int, ...] = (101, 102, 103, 104, 105, 106, 107, 108)
SEALED_SLOWINSKI_SEEDS: tuple[int, ...] = (201, 202, 203, 204, 205, 206, 207, 208)
SEALED_PERSISTENCE_SEEDS: tuple[int, ...] = (301, 302, 303, 304, 305, 306, 307, 308)

MATING_GENERATIONS = 48
MATING_VIRULENCE = 32.0
MATING_PARASITE_MUTATION = 0.5
MATING_HOST_BIT_FLIP = 0.0
MATING_HOST_N = 10
MATING_PARASITE_N = 8
MATING_INTRO_SELFING_FREQ = 0.2
MATING_BIRTH_ATP = 48.0
MATING_BASAL_ATP_COST = 0.05
MATING_HANDLING_TIME = 0.0
MATING_SOFT_K = 32
MATING_RESOURCE_BOLUS_AMOUNT = 20.0
MATING_PASSAGE_REFILL_MODE = PASSAGE_REFILL_GENERATION_BOUNDARY
MATING_PASSAGE_REFILL_SYNC = "generation_boundary"
MATING_STEAL_FRACTION = 0.25
MATING_FOUNDER_SPATIAL_POLICY = "food_patch_interleaved"
MATING_FOOD_PATCHES: tuple[tuple[int, int], ...] = tuple(
    (x, y) for x in range(4) for y in range(2)
)
MATING_MIN_VIABLE_CENSUS = 8
MATING_AVIRULENT_SELFING_BASELINE_MIN = 0.0
MATING_INVASION_PASS_BAR = 6
MATING_ASSAY_VALID_BAR = 6
MATING_TWO_FOLD_COST_SEX = False
MATING_THIN_CHEMOSTAT_ATP = 0.0

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
    """Frozen design payload (no outcomes)."""

    return {
        "prereg_version": PREREG_VERSION,
        "revision": HP_ARM01_MATING_REVISION,
        "slices": [
            SLICE_MATING_LEDGER,
            SLICE_SELFING_BASELINE,
            SLICE_CLAIMGATE_TAXONOMY,
            SLICE_DEBIT_GAIN,
        ],
        "estimand": HP_ARM01_ESTIMAND,
        "estimand_conditional_on_assay_valid_and_selfing_baseline": True,
        "substrate": SUBSTRATE_LIFE_LOOP,
        "seeds": list(MATING_SEEDS),
        "sealed_p7_seeds_untouched": list(SEALED_P7_SEEDS),
        "sealed_slowinski_seeds_untouched": list(SEALED_SLOWINSKI_SEEDS),
        "sealed_persistence_seeds_untouched": list(SEALED_PERSISTENCE_SEEDS),
        "generations": MATING_GENERATIONS,
        "virulence": MATING_VIRULENCE,
        "parasite_mutation": MATING_PARASITE_MUTATION,
        "host_bit_flip_rate": MATING_HOST_BIT_FLIP,
        "host_n": MATING_HOST_N,
        "parasite_n": MATING_PARASITE_N,
        "intro_selfing_freq": MATING_INTRO_SELFING_FREQ,
        "birth_atp": MATING_BIRTH_ATP,
        "basal_runtime_atp_cost": MATING_BASAL_ATP_COST,
        "handling_time": MATING_HANDLING_TIME,
        "soft_carrying_capacity": MATING_SOFT_K,
        "passage_refill_mode": MATING_PASSAGE_REFILL_MODE,
        "passage_refill_sync": MATING_PASSAGE_REFILL_SYNC,
        "resource_bolus_amount": MATING_RESOURCE_BOLUS_AMOUNT,
        "food_patches": [list(p) for p in MATING_FOOD_PATCHES],
        "thin_chemostat_atp_inflow": MATING_THIN_CHEMOSTAT_ATP,
        "steal_fraction": MATING_STEAL_FRACTION,
        "founder_spatial_policy": MATING_FOUNDER_SPATIAL_POLICY,
        "min_viable_census": MATING_MIN_VIABLE_CENSUS,
        "avirulent_selfing_baseline_min": MATING_AVIRULENT_SELFING_BASELINE_MIN,
        "invasion_pass_bar": MATING_INVASION_PASS_BAR,
        "assay_valid_bar": MATING_ASSAY_VALID_BAR,
        "two_fold_cost_sex": MATING_TWO_FOLD_COST_SEX,
        "founders": [list(row) for row in _INVASION_FOUNDERS],
        "arms": [ARM_AVIRULENT, ARM_FIXED, ARM_COPASSAGED],
        "typed_outcomes": sorted(TYPED_OUTCOMES),
        "prereg_path": PREREG_RELATIVE_PATH,
        "accept_path": HP_ARM01_ESTIMAND,
        "spc_owns_accept_path": False,
        "spc_owns_red_queen": False,
        "legacy_three_freq_is_accept_path": False,
        "shared_modifier_refused_as_primary": True,
        "red_queen_proved_allowed": False,
        "biological_red_queen_proved_allowed": False,
        "last_live_is_slowinski_pass": False,
        "soft_green_prior_slowinski_prereg_forbidden": True,
        "soft_green_prior_persistence_prereg_forbidden": True,
        "debit_gain_schedule": {
            "virulence": MATING_VIRULENCE,
            "steal_fraction": MATING_STEAL_FRACTION,
            "birth_atp": MATING_BIRTH_ATP,
            "resource_bolus_amount": MATING_RESOURCE_BOLUS_AMOUNT,
            "soft_carrying_capacity": MATING_SOFT_K,
        },
    }


def mating_ledger_design_digest() -> str:
    return canonical_digest(locked_design_dict(), prefix="hp_arm01_mating_design")


def mating_ledger_document_digest() -> str:
    path = prereg_document_path()
    if not path.is_file():
        raise ConfigurationError(f"missing preregistration file: {PREREG_RELATIVE_PATH}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_mating_seed_policy(seeds: Sequence[int] | None = None) -> None:
    chosen = tuple(int(s) for s in (seeds if seeds is not None else MATING_SEEDS))
    if not chosen:
        raise ConfigurationError("mating confirmatory seeds must be non-empty")
    if len(set(chosen)) != len(chosen):
        raise ConfigurationError("mating confirmatory seeds must be unique")
    for label, sealed in (
        ("P7", SEALED_P7_SEEDS),
        ("Slowinski", SEALED_SLOWINSKI_SEEDS),
        ("persistence", SEALED_PERSISTENCE_SEEDS),
    ):
        overlap = sorted(set(chosen) & set(sealed))
        if overlap:
            raise ConfigurationError(
                f"sealed {label} seeds must not be reused; overlap={overlap}"
            )
    if seeds is None and tuple(chosen) != MATING_SEEDS:
        raise ConfigurationError("default mating seed tuple was altered")


def assert_mating_locked_horizon(*, generations: int) -> None:
    if int(generations) < MATING_GENERATIONS:
        raise ConfigurationError(
            f"mating confirmatory horizon is locked at {MATING_GENERATIONS} "
            f"generations; got {generations}"
        )


def assay_validity_gate(
    *,
    terminal_census_by_arm: dict[str, int],
    min_viable_census: int = MATING_MIN_VIABLE_CENSUS,
) -> bool:
    """Raised census floor: all ecology arms must meet terminal living census."""

    if int(min_viable_census) < 2:
        raise ConfigurationError(
            "mating min_viable_census must be >= 2 (N=1 theater refused)"
        )
    for arm in ECOLOGY_ARMS:
        if arm not in terminal_census_by_arm:
            return False
        raw = terminal_census_by_arm[arm]
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ConfigurationError(f"terminal census for {arm} must be an int")
        if int(raw) < int(min_viable_census):
            return False
    return True


def avirulent_selfing_baseline_holds(
    *,
    selfing_freq_avirulent: float | None,
    baseline_min: float = MATING_AVIRULENT_SELFING_BASELINE_MIN,
) -> bool:
    """Strictly positive avirulent selfing (above locked baseline_min, default 0)."""

    if selfing_freq_avirulent is None:
        return False
    if isinstance(selfing_freq_avirulent, bool) or not isinstance(
        selfing_freq_avirulent, (int, float)
    ):
        raise ConfigurationError("selfing_freq_avirulent must be a finite number or None")
    freq = float(selfing_freq_avirulent)
    if freq != freq:  # NaN
        return False
    return freq > float(baseline_min)


def classify_typed_outcome(
    *,
    assay_valid: bool,
    avirulent_selfing_baseline: bool,
    slowinski_invasion_holds: bool,
) -> str:
    if not assay_valid:
        return OUTCOME_PERSISTENCE_FAIL
    if not avirulent_selfing_baseline:
        return OUTCOME_SELFING_NONVIABLE
    if slowinski_invasion_holds:
        return OUTCOME_INVASION_PASS
    return OUTCOME_INVASION_FAIL


@dataclass(frozen=True, slots=True)
class MatingSeedResult:
    seed: int
    typed_outcome: str
    assay_valid: bool
    avirulent_selfing_baseline: bool
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
    report: ThreeArmCampaignReport

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "typed_outcome": self.typed_outcome,
            "assay_valid": self.assay_valid,
            "avirulent_selfing_baseline": self.avirulent_selfing_baseline,
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
            "estimand": HP_ARM01_ESTIMAND,
            "substrate": SUBSTRATE_LIFE_LOOP,
            "last_live_used_as_pass": False,
        }


@dataclass(frozen=True, slots=True)
class MatingConfirmReport:
    seeds: tuple[int, ...]
    seed_results: tuple[MatingSeedResult, ...]
    typed_outcome_counts: dict[str, int]
    seeds_assay_valid: int
    seeds_selfing_baseline: int
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

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": "hp_arm01_mating_ledger_confirm_v1",
            "prereg_version": PREREG_VERSION,
            "revision": self.revision,
            "slices": [
                SLICE_MATING_LEDGER,
                SLICE_SELFING_BASELINE,
                SLICE_CLAIMGATE_TAXONOMY,
                SLICE_DEBIT_GAIN,
            ],
            "estimand": HP_ARM01_ESTIMAND,
            "estimand_conditional_on_assay_valid_and_selfing_baseline": True,
            "accept_path": HP_ARM01_ESTIMAND,
            "substrate": SUBSTRATE_LIFE_LOOP,
            "seeds": list(self.seeds),
            "seed_results": [row.to_dict() for row in self.seed_results],
            "typed_outcome_counts": dict(self.typed_outcome_counts),
            "seeds_assay_valid": self.seeds_assay_valid,
            "seeds_selfing_baseline": self.seeds_selfing_baseline,
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
                "unpaid; mating-effort ATP only; not Maynard Smith / Hamilton two-fold"
            ),
            "red_queen_proved": self.red_queen_proved,
            "biological_red_queen_proved": self.biological_red_queen_proved,
            "design_digest": self.design_digest,
            "document_digest": self.document_digest,
            "generations": self.generations,
            "virulence": self.virulence,
            "parasite_mutation": self.parasite_mutation,
            "intro_selfing_freq": self.intro_selfing_freq,
            "host_n": MATING_HOST_N,
            "parasite_n": MATING_PARASITE_N,
            "birth_atp": self.birth_atp,
            "basal_runtime_atp_cost": self.basal_runtime_atp_cost,
            "soft_carrying_capacity": self.soft_carrying_capacity,
            "steal_fraction": self.steal_fraction,
            "founder_spatial_policy": self.founder_spatial_policy,
            "passage_refill_mode": self.passage_refill_mode,
            "resource_bolus_amount": self.resource_bolus_amount,
            "passage_refill_sync": self.passage_refill_sync,
            "thin_chemostat_atp_inflow": MATING_THIN_CHEMOSTAT_ATP,
            "min_viable_census": MATING_MIN_VIABLE_CENSUS,
            "avirulent_selfing_baseline_min": MATING_AVIRULENT_SELFING_BASELINE_MIN,
            "handling_time": MATING_HANDLING_TIME,
            "spc_owns_accept_path": False,
            "spc_owns_red_queen": False,
            "legacy_three_freq_is_accept_path": False,
            "shared_modifier_refused_as_primary_substrate": True,
            "sealed_p7_seeds_untouched": True,
            "sealed_slowinski_prereg_untouched": True,
            "sealed_persistence_prereg_untouched": True,
            "last_live_used_as_pass": False,
            "notes": self.notes,
        }
        payload["digest"] = self.digest
        return payload


def run_mating_confirm_campaign(
    *,
    seeds: Sequence[int] | None = None,
    generations: int | None = None,
    virulence: float | None = None,
    parasite_mutation: float | None = None,
    attach_pearl_measurement: bool = False,
) -> MatingConfirmReport:
    """Run the locked mating-ledger confirmatory campaign."""

    chosen_seeds = tuple(int(s) for s in (seeds if seeds is not None else MATING_SEEDS))
    gens = int(MATING_GENERATIONS if generations is None else generations)
    vir = float(MATING_VIRULENCE if virulence is None else virulence)
    pmut = float(MATING_PARASITE_MUTATION if parasite_mutation is None else parasite_mutation)

    assert_mating_seed_policy(chosen_seeds)
    assert_mating_locked_horizon(generations=gens)
    if abs(vir - MATING_VIRULENCE) > 1e-12:
        raise ConfigurationError(
            f"mating virulence is locked at {MATING_VIRULENCE}; got {vir}"
        )
    if abs(pmut - MATING_PARASITE_MUTATION) > 1e-12:
        raise ConfigurationError(
            f"mating parasite_mutation is locked at {MATING_PARASITE_MUTATION}; "
            f"got {pmut}"
        )

    design = mating_ledger_design_digest()
    document = mating_ledger_document_digest()

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

    results: list[MatingSeedResult] = []
    for seed in chosen_seeds:
        assert_ecology_arm_taxonomy()
        arms: dict[str, LifeLoopEcologyArm] = {}
        clocks_by_arm: dict = {}
        freqs: dict[str, float | None] = {}
        census: dict[str, int] = {}
        bolus_by_arm: dict[str, float] = {}
        hp_env_ids: dict[str, int] = {}
        intro_freq = 0.0

        for arm_name in ECOLOGY_ARMS:
            arm = LifeLoopEcologyArm.boot(
                arm=arm_name,
                virulence=vir,
                seed=seed,
                handling_time=MATING_HANDLING_TIME,
                parasite_mutation=pmut,
                birth_atp=MATING_BIRTH_ATP,
                parasite_n=MATING_PARASITE_N,
                founders=_INVASION_FOUNDERS,
                soft_carrying_capacity=MATING_SOFT_K,
                basal_runtime_atp_cost=MATING_BASAL_ATP_COST,
                passage_refill_mode=MATING_PASSAGE_REFILL_MODE,
                resource_bolus_amount=MATING_RESOURCE_BOLUS_AMOUNT,
                food_patches=MATING_FOOD_PATCHES,
                steal_fraction=MATING_STEAL_FRACTION,
                founder_spatial_policy=MATING_FOUNDER_SPATIAL_POLICY,
            )
            arm.run_generations(gens)
            arms[arm_name] = arm
            clocks_by_arm[arm_name] = arm.build_clocks()
            freqs[arm_name] = arm.terminal_selfing_freq()
            census[arm_name] = int(arm.living_host_census())
            bolus_by_arm[arm_name] = float(arm.cumulative_resource_bolus_placed)
            hp_env_ids[arm_name] = id(arm.hp_env)
            intro_freq = arm.intro_selfing_freq

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
            min_viable_census=MATING_MIN_VIABLE_CENSUS,
        )
        baseline_ok = avirulent_selfing_baseline_holds(
            selfing_freq_avirulent=freqs[ARM_AVIRULENT],
            baseline_min=MATING_AVIRULENT_SELFING_BASELINE_MIN,
        )

        if assay_ok and baseline_ok:
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
            slowinski_invasion_holds=bool(assay_ok and baseline_ok and invasion),
        )
        # Hard ceiling: observation until raised census + positive avi selfing + invasion.
        if not (assay_ok and baseline_ok and invasion):
            ceiling_cap = CLAIM_CEILING_OBSERVATION
        reported_ceiling = (
            CLAIM_CEILING_CANDIDATE
            if assay_ok and baseline_ok and invasion and ceiling_cap == CLAIM_CEILING_CANDIDATE
            else CLAIM_CEILING_OBSERVATION
        )

        typed = classify_typed_outcome(
            assay_valid=assay_ok,
            avirulent_selfing_baseline=baseline_ok if assay_ok else False,
            slowinski_invasion_holds=bool(invasion) if (assay_ok and baseline_ok) else False,
        )
        invasion_scored: bool | None = (
            bool(invasion) if (assay_ok and baseline_ok) else None
        )

        pearl_attached = False
        pearl_notes = ""
        if attach_pearl_measurement and per_arm_ok:
            pearl_attached = True
            pearl_notes = "pearl_spc_measurement_only_spc_does_not_own_accept"

        deferred = gens < MATING_GENERATIONS
        note = (
            f"typed_outcome={typed};assay_valid={assay_ok};"
            f"avirulent_selfing_baseline={baseline_ok};"
            f"founder_spatial_policy={MATING_FOUNDER_SPATIAL_POLICY};"
            f"steal_fraction={MATING_STEAL_FRACTION};"
            f"passage_refill_sync={MATING_PASSAGE_REFILL_SYNC}"
        )
        if pearl_notes:
            note = f"{note};{pearl_notes}"

        digest_body = {
            "arms": list(ECOLOGY_ARMS),
            "freqs": freqs,
            "census": census,
            "assay_valid": assay_ok,
            "avirulent_selfing_baseline": baseline_ok,
            "invasion": invasion_scored,
            "typed": typed,
            "seed": seed,
            "revision": HP_ARM01_MATING_REVISION,
        }
        arm_digest = _hashlib.sha256(
            _json.dumps(digest_body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

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
            slowinski_contrast_holds=bool(invasion) if (assay_ok and baseline_ok) else False,
            slowinski_invasion_holds=bool(invasion) if (assay_ok and baseline_ok) else False,
            legacy_three_freq_contrast_holds=bool(legacy),
            selfing_freq_by_arm=freqs,
            intro_selfing_freq=float(intro_freq),
            pearl_measurement_attached=pearl_attached,
            two_fold_cost_sex_applied=False,
            claim_ceiling=reported_ceiling,
            max_allowed_ceiling=ceiling_cap,
            red_queen_proved=False,
            biological_red_queen_proved=False,
            confirmatory_horizon_deferred=deferred,
            revision=HP_ARM01_MATING_REVISION,
            digest=arm_digest,
            notes=note,
            hp_env_ids_by_arm=hp_env_ids,
        )

        if abs(intro_freq - MATING_INTRO_SELFING_FREQ) > 1e-12:
            raise ConfigurationError(
                "intro selfing frequency drifted from locked 0.2; refuse soft-pass"
            )
        if report.two_fold_cost_sex_applied:
            raise ConfigurationError("two-fold cost must remain unpaid")
        if report.red_queen_proved or report.biological_red_queen_proved:
            raise ConfigurationError("Red Queen flags must stay false")

        results.append(
            MatingSeedResult(
                seed=seed,
                typed_outcome=typed,
                assay_valid=assay_ok,
                avirulent_selfing_baseline=bool(assay_ok and baseline_ok),
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
                two_fold_cost_sex_applied=False,
                birth_atp=MATING_BIRTH_ATP,
                basal_runtime_atp_cost=MATING_BASAL_ATP_COST,
                soft_carrying_capacity=MATING_SOFT_K,
                steal_fraction=MATING_STEAL_FRACTION,
                founder_spatial_policy=MATING_FOUNDER_SPATIAL_POLICY,
                passage_refill_mode=MATING_PASSAGE_REFILL_MODE,
                resource_bolus_amount=MATING_RESOURCE_BOLUS_AMOUNT,
                passage_refill_sync=MATING_PASSAGE_REFILL_SYNC,
                cumulative_resource_bolus_by_arm=dict(bolus_by_arm),
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
    seeds_baseline = sum(1 for row in results if row.avirulent_selfing_baseline)
    seeds_invasion = sum(
        1 for row in results if row.typed_outcome == OUTCOME_INVASION_PASS
    )
    assay_campaign_pass = seeds_assay_valid >= MATING_ASSAY_VALID_BAR
    invasion_campaign_pass = seeds_invasion >= MATING_INVASION_PASS_BAR

    campaign_ceiling = CLAIM_CEILING_OBSERVATION
    if invasion_campaign_pass and assay_campaign_pass and seeds_baseline >= MATING_ASSAY_VALID_BAR:
        campaign_ceiling = CLAIM_CEILING_CANDIDATE

    notes = (
        f"typed_counts={json.dumps(counts, sort_keys=True)};"
        f"assay_valid={seeds_assay_valid}/{len(results)};"
        f"selfing_baseline={seeds_baseline}/{len(results)};"
        f"invasion_pass={seeds_invasion}/{len(results)};"
        f"ceiling={campaign_ceiling}"
    )

    draft = MatingConfirmReport(
        seeds=chosen_seeds,
        seed_results=tuple(results),
        typed_outcome_counts=counts,
        seeds_assay_valid=seeds_assay_valid,
        seeds_selfing_baseline=seeds_baseline,
        seeds_invasion_passed=seeds_invasion,
        assay_valid_bar=MATING_ASSAY_VALID_BAR,
        invasion_pass_bar=MATING_INVASION_PASS_BAR,
        assay_campaign_pass=assay_campaign_pass,
        invasion_campaign_pass=invasion_campaign_pass,
        claim_ceiling=campaign_ceiling,
        max_allowed_ceiling=campaign_ceiling,
        two_fold_cost_sex_applied=False,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        design_digest=design,
        document_digest=document,
        generations=gens,
        virulence=vir,
        parasite_mutation=pmut,
        intro_selfing_freq=MATING_INTRO_SELFING_FREQ,
        birth_atp=MATING_BIRTH_ATP,
        basal_runtime_atp_cost=MATING_BASAL_ATP_COST,
        soft_carrying_capacity=MATING_SOFT_K,
        steal_fraction=MATING_STEAL_FRACTION,
        founder_spatial_policy=MATING_FOUNDER_SPATIAL_POLICY,
        passage_refill_mode=MATING_PASSAGE_REFILL_MODE,
        resource_bolus_amount=MATING_RESOURCE_BOLUS_AMOUNT,
        passage_refill_sync=MATING_PASSAGE_REFILL_SYNC,
        revision=HP_ARM01_MATING_REVISION,
        notes=notes,
        digest="",
    )
    body = draft.to_dict()
    body.pop("digest", None)
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return MatingConfirmReport(
        seeds=draft.seeds,
        seed_results=draft.seed_results,
        typed_outcome_counts=draft.typed_outcome_counts,
        seeds_assay_valid=draft.seeds_assay_valid,
        seeds_selfing_baseline=draft.seeds_selfing_baseline,
        seeds_invasion_passed=draft.seeds_invasion_passed,
        assay_valid_bar=draft.assay_valid_bar,
        invasion_pass_bar=draft.invasion_pass_bar,
        assay_campaign_pass=draft.assay_campaign_pass,
        invasion_campaign_pass=draft.invasion_campaign_pass,
        claim_ceiling=draft.claim_ceiling,
        max_allowed_ceiling=draft.max_allowed_ceiling,
        two_fold_cost_sex_applied=False,
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
    )


def summarize_mating_terminals(report: MatingConfirmReport) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in report.seed_results:
        rows.append(
            {
                "seed": row.seed,
                "typed_outcome": row.typed_outcome,
                "assay_valid": row.assay_valid,
                "avirulent_selfing_baseline": row.avirulent_selfing_baseline,
                "invasion_holds": row.slowinski_invasion_holds,
                "avirulent": row.selfing_freq_by_arm.get(ARM_AVIRULENT),
                "fixed": row.selfing_freq_by_arm.get(ARM_FIXED),
                "copassaged": row.selfing_freq_by_arm.get(ARM_COPASSAGED),
                "census": dict(row.terminal_census_by_arm),
                "intro": row.intro_selfing_freq,
                "digest": row.digest,
            }
        )
    return rows


__all__ = [
    "HP_ARM01_MATING_REVISION",
    "MATING_ASSAY_VALID_BAR",
    "MATING_AVIRULENT_SELFING_BASELINE_MIN",
    "MATING_BASAL_ATP_COST",
    "MATING_BIRTH_ATP",
    "MATING_FOUNDER_SPATIAL_POLICY",
    "MATING_GENERATIONS",
    "MATING_INVASION_PASS_BAR",
    "MATING_MIN_VIABLE_CENSUS",
    "MATING_PASSAGE_REFILL_MODE",
    "MATING_PASSAGE_REFILL_SYNC",
    "MATING_RESOURCE_BOLUS_AMOUNT",
    "MATING_SEEDS",
    "MATING_SOFT_K",
    "MATING_STEAL_FRACTION",
    "MATING_VIRULENCE",
    "OUTCOME_INVASION_FAIL",
    "OUTCOME_INVASION_PASS",
    "OUTCOME_PERSISTENCE_FAIL",
    "OUTCOME_SELFING_NONVIABLE",
    "PREREG_RELATIVE_PATH",
    "PREREG_VERSION",
    "SEALED_P7_SEEDS",
    "SEALED_PERSISTENCE_SEEDS",
    "SEALED_SLOWINSKI_SEEDS",
    "SLICE_CLAIMGATE_TAXONOMY",
    "SLICE_DEBIT_GAIN",
    "SLICE_MATING_LEDGER",
    "SLICE_SELFING_BASELINE",
    "TYPED_OUTCOMES",
    "MatingConfirmReport",
    "MatingSeedResult",
    "assay_validity_gate",
    "assert_mating_locked_horizon",
    "assert_mating_seed_policy",
    "avirulent_selfing_baseline_holds",
    "classify_typed_outcome",
    "locked_design_dict",
    "mating_ledger_design_digest",
    "mating_ledger_document_digest",
    "prereg_document_path",
    "run_mating_confirm_campaign",
    "summarize_mating_terminals",
]
