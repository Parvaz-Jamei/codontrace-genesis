"""HP-ARM01 persistence ledger + passage refill confirmatory campaign.

Constants match
``docs/handoff/CLOSED_LOOP_HP_ARM01_PERSISTENCE_LEDGER_PREREG_20260926.md``.
Sealed Slowinski prereg (214df20 / seeds 201–208) and P7 seeds 101–108 are
not reused or retuned. Typed outcomes separate persistence_fail
(assay_invalid) from invasion_fail / invasion_pass. SPC never owns accept
or Red Queen flags.
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

PREREG_VERSION = "hp_arm01_persistence_ledger_prereg_20260926"
PREREG_RELATIVE_PATH = (
    "docs/handoff/CLOSED_LOOP_HP_ARM01_PERSISTENCE_LEDGER_PREREG_20260926.md"
)
HP_ARM01_PERSISTENCE_REVISION = "hp-arm01-persistence-ledger-20260926"
SLICE_PERSISTENCE_LEDGER = "HP-ARM01-PERSISTENCE-LEDGER"
SLICE_PASSAGE_REFILL = "HP-ARM01-PASSAGE-REFILL"
SLICE_ASSAY_VALIDITY_GATE = "ASSAY-VALIDITY-GATE"

OUTCOME_PERSISTENCE_FAIL = "persistence_fail"
OUTCOME_INVASION_FAIL = "invasion_fail"
OUTCOME_INVASION_PASS = "invasion_pass"
TYPED_OUTCOMES = frozenset(
    {OUTCOME_PERSISTENCE_FAIL, OUTCOME_INVASION_FAIL, OUTCOME_INVASION_PASS}
)

# Locked design (written before outcomes). Do not edit after inspection.
PERSIST_SEEDS: tuple[int, ...] = (301, 302, 303, 304, 305, 306, 307, 308)
SEALED_P7_SEEDS: tuple[int, ...] = (101, 102, 103, 104, 105, 106, 107, 108)
SEALED_SLOWINSKI_SEEDS: tuple[int, ...] = (201, 202, 203, 204, 205, 206, 207, 208)
PERSIST_GENERATIONS = 48
PERSIST_VIRULENCE = 32.0
PERSIST_PARASITE_MUTATION = 0.5
PERSIST_HOST_BIT_FLIP = 0.0
PERSIST_HOST_N = 10
PERSIST_PARASITE_N = 8
PERSIST_INTRO_SELFING_FREQ = 0.2
PERSIST_BIRTH_ATP = 40.0
PERSIST_BASAL_ATP_COST = 0.05
PERSIST_HANDLING_TIME = 0.0
PERSIST_SOFT_K = 32
PERSIST_RESOURCE_BOLUS_AMOUNT = 16.0
PERSIST_PASSAGE_REFILL_MODE = PASSAGE_REFILL_GENERATION_BOUNDARY
PERSIST_PASSAGE_REFILL_SYNC = "generation_boundary"
PERSIST_FOOD_PATCHES: tuple[tuple[int, int], ...] = tuple(
    (x, y) for x in range(4) for y in range(2)
)
PERSIST_MIN_VIABLE_CENSUS = 1
PERSIST_INVASION_PASS_BAR = 6
PERSIST_ASSAY_VALID_BAR = 6
PERSIST_TWO_FOLD_COST_SEX = False
PERSIST_THIN_CHEMOSTAT_ATP = 0.0

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
        "revision": HP_ARM01_PERSISTENCE_REVISION,
        "slices": [
            SLICE_PERSISTENCE_LEDGER,
            SLICE_PASSAGE_REFILL,
            SLICE_ASSAY_VALIDITY_GATE,
        ],
        "estimand": HP_ARM01_ESTIMAND,
        "estimand_conditional_on_assay_valid": True,
        "substrate": SUBSTRATE_LIFE_LOOP,
        "seeds": list(PERSIST_SEEDS),
        "sealed_p7_seeds_untouched": list(SEALED_P7_SEEDS),
        "sealed_slowinski_seeds_untouched": list(SEALED_SLOWINSKI_SEEDS),
        "generations": PERSIST_GENERATIONS,
        "virulence": PERSIST_VIRULENCE,
        "parasite_mutation": PERSIST_PARASITE_MUTATION,
        "host_bit_flip_rate": PERSIST_HOST_BIT_FLIP,
        "host_n": PERSIST_HOST_N,
        "parasite_n": PERSIST_PARASITE_N,
        "intro_selfing_freq": PERSIST_INTRO_SELFING_FREQ,
        "birth_atp": PERSIST_BIRTH_ATP,
        "basal_runtime_atp_cost": PERSIST_BASAL_ATP_COST,
        "handling_time": PERSIST_HANDLING_TIME,
        "soft_carrying_capacity": PERSIST_SOFT_K,
        "passage_refill_mode": PERSIST_PASSAGE_REFILL_MODE,
        "passage_refill_sync": PERSIST_PASSAGE_REFILL_SYNC,
        "resource_bolus_amount": PERSIST_RESOURCE_BOLUS_AMOUNT,
        "food_patches": [list(p) for p in PERSIST_FOOD_PATCHES],
        "thin_chemostat_atp_inflow": PERSIST_THIN_CHEMOSTAT_ATP,
        "min_viable_census": PERSIST_MIN_VIABLE_CENSUS,
        "invasion_pass_bar": PERSIST_INVASION_PASS_BAR,
        "assay_valid_bar": PERSIST_ASSAY_VALID_BAR,
        "two_fold_cost_sex": PERSIST_TWO_FOLD_COST_SEX,
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
    }


def persistence_ledger_design_digest() -> str:
    return canonical_digest(locked_design_dict(), prefix="hp_arm01_persistence_design")


def persistence_ledger_document_digest() -> str:
    path = prereg_document_path()
    if not path.is_file():
        raise ConfigurationError(f"missing preregistration file: {PREREG_RELATIVE_PATH}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_persist_seed_policy(seeds: Sequence[int] | None = None) -> None:
    chosen = tuple(int(s) for s in (seeds if seeds is not None else PERSIST_SEEDS))
    if not chosen:
        raise ConfigurationError("persistence confirmatory seeds must be non-empty")
    if len(set(chosen)) != len(chosen):
        raise ConfigurationError("persistence confirmatory seeds must be unique")
    overlap_p7 = sorted(set(chosen) & set(SEALED_P7_SEEDS))
    if overlap_p7:
        raise ConfigurationError(
            f"sealed P7 seeds 101–108 must not be reused; overlap={overlap_p7}"
        )
    overlap_sk = sorted(set(chosen) & set(SEALED_SLOWINSKI_SEEDS))
    if overlap_sk:
        raise ConfigurationError(
            f"sealed Slowinski seeds 201–208 must not be reused; overlap={overlap_sk}"
        )
    if seeds is None and tuple(chosen) != PERSIST_SEEDS:
        raise ConfigurationError("default persistence seed tuple was altered")


def assert_persist_locked_horizon(*, generations: int) -> None:
    if int(generations) < PERSIST_GENERATIONS:
        raise ConfigurationError(
            f"persistence confirmatory horizon is locked at {PERSIST_GENERATIONS} "
            f"generations; got {generations}"
        )


def assay_validity_gate(
    *,
    terminal_census_by_arm: dict[str, int],
    min_viable_census: int = PERSIST_MIN_VIABLE_CENSUS,
) -> bool:
    """ASSAY-VALIDITY-GATE: all ecology arms must meet terminal living census."""

    if int(min_viable_census) < 1:
        raise ConfigurationError("min_viable_census must be >= 1")
    for arm in ECOLOGY_ARMS:
        if arm not in terminal_census_by_arm:
            return False
        raw = terminal_census_by_arm[arm]
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ConfigurationError(f"terminal census for {arm} must be an int")
        if int(raw) < int(min_viable_census):
            return False
    return True



def classify_typed_outcome(
    *,
    assay_valid: bool,
    slowinski_invasion_holds: bool,
) -> str:
    if not assay_valid:
        return OUTCOME_PERSISTENCE_FAIL
    if slowinski_invasion_holds:
        return OUTCOME_INVASION_PASS
    return OUTCOME_INVASION_FAIL


@dataclass(frozen=True, slots=True)
class PersistenceSeedResult:
    seed: int
    typed_outcome: str
    assay_valid: bool
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
            "passage_refill_mode": self.passage_refill_mode,
            "resource_bolus_amount": self.resource_bolus_amount,
            "passage_refill_sync": self.passage_refill_sync,
            "cumulative_resource_bolus_by_arm": dict(self.cumulative_resource_bolus_by_arm),
            "estimand": HP_ARM01_ESTIMAND,
            "substrate": SUBSTRATE_LIFE_LOOP,
            "last_live_used_as_pass": False,
        }


@dataclass(frozen=True, slots=True)
class PersistenceConfirmReport:
    seeds: tuple[int, ...]
    seed_results: tuple[PersistenceSeedResult, ...]
    typed_outcome_counts: dict[str, int]
    seeds_assay_valid: int
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
    passage_refill_mode: str
    resource_bolus_amount: float
    passage_refill_sync: str
    revision: str
    notes: str
    digest: str

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": "hp_arm01_persistence_ledger_confirm_v1",
            "prereg_version": PREREG_VERSION,
            "revision": self.revision,
            "slices": [
                SLICE_PERSISTENCE_LEDGER,
                SLICE_PASSAGE_REFILL,
                SLICE_ASSAY_VALIDITY_GATE,
            ],
            "estimand": HP_ARM01_ESTIMAND,
            "estimand_conditional_on_assay_valid": True,
            "accept_path": HP_ARM01_ESTIMAND,
            "substrate": SUBSTRATE_LIFE_LOOP,
            "seeds": list(self.seeds),
            "seed_results": [row.to_dict() for row in self.seed_results],
            "typed_outcome_counts": dict(self.typed_outcome_counts),
            "seeds_assay_valid": self.seeds_assay_valid,
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
            "host_n": PERSIST_HOST_N,
            "parasite_n": PERSIST_PARASITE_N,
            "birth_atp": self.birth_atp,
            "basal_runtime_atp_cost": self.basal_runtime_atp_cost,
            "soft_carrying_capacity": self.soft_carrying_capacity,
            "passage_refill_mode": self.passage_refill_mode,
            "resource_bolus_amount": self.resource_bolus_amount,
            "passage_refill_sync": self.passage_refill_sync,
            "thin_chemostat_atp_inflow": PERSIST_THIN_CHEMOSTAT_ATP,
            "min_viable_census": PERSIST_MIN_VIABLE_CENSUS,
            "handling_time": PERSIST_HANDLING_TIME,
            "spc_owns_accept_path": False,
            "spc_owns_red_queen": False,
            "legacy_three_freq_is_accept_path": False,
            "shared_modifier_refused_as_primary_substrate": True,
            "sealed_p7_seeds_untouched": True,
            "sealed_slowinski_prereg_untouched": True,
            "last_live_used_as_pass": False,
            "notes": self.notes,
        }
        payload["digest"] = self.digest
        return payload


def run_persistence_confirm_campaign(
    *,
    seeds: Sequence[int] | None = None,
    generations: int | None = None,
    virulence: float | None = None,
    parasite_mutation: float | None = None,
    attach_pearl_measurement: bool = False,
) -> PersistenceConfirmReport:
    """Run the locked persistence-ledger confirmatory campaign."""

    chosen_seeds = tuple(int(s) for s in (seeds if seeds is not None else PERSIST_SEEDS))
    gens = int(PERSIST_GENERATIONS if generations is None else generations)
    vir = float(PERSIST_VIRULENCE if virulence is None else virulence)
    pmut = float(PERSIST_PARASITE_MUTATION if parasite_mutation is None else parasite_mutation)

    assert_persist_seed_policy(chosen_seeds)
    assert_persist_locked_horizon(generations=gens)
    if abs(vir - PERSIST_VIRULENCE) > 1e-12:
        raise ConfigurationError(
            f"persistence virulence is locked at {PERSIST_VIRULENCE}; got {vir}"
        )
    if abs(pmut - PERSIST_PARASITE_MUTATION) > 1e-12:
        raise ConfigurationError(
            f"persistence parasite_mutation is locked at {PERSIST_PARASITE_MUTATION}; "
            f"got {pmut}"
        )

    design = persistence_ledger_design_digest()
    document = persistence_ledger_document_digest()

    results: list[PersistenceSeedResult] = []
    for seed in chosen_seeds:
        # Import arm class locally to collect census without changing sealed path.
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
                handling_time=PERSIST_HANDLING_TIME,
                parasite_mutation=pmut,
                birth_atp=PERSIST_BIRTH_ATP,
                parasite_n=PERSIST_PARASITE_N,
                founders=_INVASION_FOUNDERS,
                soft_carrying_capacity=PERSIST_SOFT_K,
                basal_runtime_atp_cost=PERSIST_BASAL_ATP_COST,
                passage_refill_mode=PERSIST_PASSAGE_REFILL_MODE,
                resource_bolus_amount=PERSIST_RESOURCE_BOLUS_AMOUNT,
                food_patches=PERSIST_FOOD_PATCHES,
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
            min_viable_census=PERSIST_MIN_VIABLE_CENSUS,
        )

        if assay_ok:
            invasion = slowinski_invasion_contrast(
                intro_selfing_freq=intro_freq,
                final_selfing_avirulent=freqs[ARM_AVIRULENT],
                final_selfing_fixed=freqs[ARM_FIXED],
                final_selfing_copassaged=freqs[ARM_COPASSAGED],
            )
        else:
            invasion = False  # unscored; typed outcome is persistence_fail

        legacy = slowinski_selfing_invasion_contrast(
            selfing_freq_avirulent=freqs[ARM_AVIRULENT],
            selfing_freq_fixed=freqs[ARM_FIXED],
            selfing_freq_copassaged=freqs[ARM_COPASSAGED],
        )
        refuse_shared_modifier_as_slowinski_pass(
            substrate=SUBSTRATE_LIFE_LOOP, contrast_holds=invasion
        )

        # Ceiling: never above observation until living census on demes AND invasion.
        ceiling_cap = max_allowed_claim_ceiling(
            clocks_complete=clocks_ok,
            treatment_control_present=treatment_control,
            substrate_life_loop_bound=life_ok,
            per_arm_clocks_ok=per_arm_ok,
            slowinski_invasion_holds=bool(assay_ok and invasion),
        )
        # Hard rule from this prereg: stay at observation until living gen-48 census
        # exists on treatment and control; even then invasion must hold for candidate.
        if not assay_ok:
            ceiling_cap = CLAIM_CEILING_OBSERVATION
        reported_ceiling = (
            CLAIM_CEILING_CANDIDATE
            if assay_ok and invasion and ceiling_cap == CLAIM_CEILING_CANDIDATE
            else CLAIM_CEILING_OBSERVATION
        )

        typed = classify_typed_outcome(
            assay_valid=assay_ok,
            slowinski_invasion_holds=bool(invasion) if assay_ok else False,
        )
        # When assay invalid, invasion is unscored (None in report fields).
        invasion_scored: bool | None = bool(invasion) if assay_ok else None

        pearl_attached = False
        pearl_notes = ""
        if attach_pearl_measurement and per_arm_ok:
            # Measurement-only; SPC never owns accept / RQ.
            pearl_attached = True
            pearl_notes = "pearl_spc_measurement_only_spc_does_not_own_accept"

        deferred = gens < PERSIST_GENERATIONS
        note = (
            f"typed_outcome={typed};assay_valid={assay_ok};"
            f"passage_refill_sync={PERSIST_PASSAGE_REFILL_SYNC}"
        )
        if pearl_notes:
            note = f"{note};{pearl_notes}"

        # Build a ThreeArmCampaignReport-compatible object for nesting.
        digest_body = {
            "arms": list(ECOLOGY_ARMS),
            "freqs": freqs,
            "census": census,
            "assay_valid": assay_ok,
            "invasion": invasion_scored,
            "typed": typed,
            "seed": seed,
            "revision": HP_ARM01_PERSISTENCE_REVISION,
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
            slowinski_contrast_holds=bool(invasion) if assay_ok else False,
            slowinski_invasion_holds=bool(invasion) if assay_ok else False,
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
            revision=HP_ARM01_PERSISTENCE_REVISION,
            digest=arm_digest,
            notes=note,
            hp_env_ids_by_arm=hp_env_ids,
        )

        if abs(intro_freq - PERSIST_INTRO_SELFING_FREQ) > 1e-12:
            raise ConfigurationError(
                "intro selfing frequency drifted from locked 0.2; refuse soft-pass"
            )
        if report.two_fold_cost_sex_applied:
            raise ConfigurationError("two-fold cost must remain unpaid")
        if report.red_queen_proved or report.biological_red_queen_proved:
            raise ConfigurationError("Red Queen flags must stay false")

        results.append(
            PersistenceSeedResult(
                seed=seed,
                typed_outcome=typed,
                assay_valid=assay_ok,
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
                birth_atp=PERSIST_BIRTH_ATP,
                basal_runtime_atp_cost=PERSIST_BASAL_ATP_COST,
                soft_carrying_capacity=PERSIST_SOFT_K,
                passage_refill_mode=PERSIST_PASSAGE_REFILL_MODE,
                resource_bolus_amount=PERSIST_RESOURCE_BOLUS_AMOUNT,
                passage_refill_sync=PERSIST_PASSAGE_REFILL_SYNC,
                cumulative_resource_bolus_by_arm=dict(bolus_by_arm),
                report=report,
            )
        )

    counts = {
        OUTCOME_PERSISTENCE_FAIL: 0,
        OUTCOME_INVASION_FAIL: 0,
        OUTCOME_INVASION_PASS: 0,
    }
    for row in results:
        counts[row.typed_outcome] = counts.get(row.typed_outcome, 0) + 1

    seeds_assay_valid = sum(1 for row in results if row.assay_valid)
    seeds_invasion_passed = sum(
        1 for row in results if row.typed_outcome == OUTCOME_INVASION_PASS
    )
    assay_campaign_pass = seeds_assay_valid >= PERSIST_ASSAY_VALID_BAR
    invasion_campaign_pass = seeds_invasion_passed >= PERSIST_INVASION_PASS_BAR

    clocks_ok = all(row.clocks_complete for row in results)
    per_arm_ok = all(row.per_arm_clocks_ok for row in results)
    life_ok = all(row.life_loop_bound for row in results)
    ceiling_cap = max_allowed_claim_ceiling(
        clocks_complete=clocks_ok,
        treatment_control_present=True,
        substrate_life_loop_bound=life_ok,
        per_arm_clocks_ok=per_arm_ok,
        slowinski_invasion_holds=invasion_campaign_pass,
    )
    if not assay_campaign_pass:
        ceiling_cap = CLAIM_CEILING_OBSERVATION
    reported_ceiling = (
        CLAIM_CEILING_CANDIDATE
        if invasion_campaign_pass and ceiling_cap == CLAIM_CEILING_CANDIDATE
        else CLAIM_CEILING_OBSERVATION
    )

    note = (
        f"assay_valid={seeds_assay_valid}/{len(results)};"
        f"invasion_pass={seeds_invasion_passed}/{len(results)};"
        f"typed={counts};"
        f"passage_refill_sync={PERSIST_PASSAGE_REFILL_SYNC}"
    )

    draft = PersistenceConfirmReport(
        seeds=chosen_seeds,
        seed_results=tuple(results),
        typed_outcome_counts=counts,
        seeds_assay_valid=seeds_assay_valid,
        seeds_invasion_passed=seeds_invasion_passed,
        assay_valid_bar=PERSIST_ASSAY_VALID_BAR,
        invasion_pass_bar=PERSIST_INVASION_PASS_BAR,
        assay_campaign_pass=assay_campaign_pass,
        invasion_campaign_pass=invasion_campaign_pass,
        claim_ceiling=reported_ceiling,
        max_allowed_ceiling=ceiling_cap,
        two_fold_cost_sex_applied=False,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        design_digest=design,
        document_digest=document,
        generations=gens,
        virulence=vir,
        parasite_mutation=pmut,
        intro_selfing_freq=PERSIST_INTRO_SELFING_FREQ,
        birth_atp=PERSIST_BIRTH_ATP,
        basal_runtime_atp_cost=PERSIST_BASAL_ATP_COST,
        soft_carrying_capacity=PERSIST_SOFT_K,
        passage_refill_mode=PERSIST_PASSAGE_REFILL_MODE,
        resource_bolus_amount=PERSIST_RESOURCE_BOLUS_AMOUNT,
        passage_refill_sync=PERSIST_PASSAGE_REFILL_SYNC,
        revision=HP_ARM01_PERSISTENCE_REVISION,
        notes=note,
        digest="",
    )
    body = {k: v for k, v in draft.to_dict().items() if k != "digest"}
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    return PersistenceConfirmReport(
        seeds=draft.seeds,
        seed_results=draft.seed_results,
        typed_outcome_counts=draft.typed_outcome_counts,
        seeds_assay_valid=draft.seeds_assay_valid,
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
        design_digest=draft.design_digest,
        document_digest=draft.document_digest,
        generations=draft.generations,
        virulence=draft.virulence,
        parasite_mutation=draft.parasite_mutation,
        intro_selfing_freq=draft.intro_selfing_freq,
        birth_atp=draft.birth_atp,
        basal_runtime_atp_cost=draft.basal_runtime_atp_cost,
        soft_carrying_capacity=draft.soft_carrying_capacity,
        passage_refill_mode=draft.passage_refill_mode,
        resource_bolus_amount=draft.resource_bolus_amount,
        passage_refill_sync=draft.passage_refill_sync,
        revision=draft.revision,
        notes=draft.notes,
        digest=digest,
    )


def summarize_persistence_terminals(
    report: PersistenceConfirmReport,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in report.seed_results:
        rows.append(
            {
                "seed": row.seed,
                "typed_outcome": row.typed_outcome,
                "assay_valid": row.assay_valid,
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
    "HP_ARM01_PERSISTENCE_REVISION",
    "OUTCOME_INVASION_FAIL",
    "OUTCOME_INVASION_PASS",
    "OUTCOME_PERSISTENCE_FAIL",
    "PERSIST_ASSAY_VALID_BAR",
    "PERSIST_BASAL_ATP_COST",
    "PERSIST_BIRTH_ATP",
    "PERSIST_GENERATIONS",
    "PERSIST_INVASION_PASS_BAR",
    "PERSIST_MIN_VIABLE_CENSUS",
    "PERSIST_PASSAGE_REFILL_MODE",
    "PERSIST_PASSAGE_REFILL_SYNC",
    "PERSIST_RESOURCE_BOLUS_AMOUNT",
    "PERSIST_SEEDS",
    "PERSIST_SOFT_K",
    "PERSIST_VIRULENCE",
    "PREREG_RELATIVE_PATH",
    "PREREG_VERSION",
    "SEALED_P7_SEEDS",
    "SEALED_SLOWINSKI_SEEDS",
    "SLICE_ASSAY_VALIDITY_GATE",
    "SLICE_PASSAGE_REFILL",
    "SLICE_PERSISTENCE_LEDGER",
    "TYPED_OUTCOMES",
    "PersistenceConfirmReport",
    "PersistenceSeedResult",
    "assay_validity_gate",
    "assert_persist_locked_horizon",
    "assert_persist_seed_policy",
    "classify_typed_outcome",
    "locked_design_dict",
    "persistence_ledger_design_digest",
    "persistence_ledger_document_digest",
    "prereg_document_path",
    "run_persistence_confirm_campaign",
    "summarize_persistence_terminals",
]
