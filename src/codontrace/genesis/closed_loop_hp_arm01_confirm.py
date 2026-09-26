"""Locked Slowinski invasion confirmatory campaign (HP-ARM01).

Constants match
``docs/handoff/CLOSED_LOOP_HP_ARM01_SLOWINSKI_INVASION_PREREG_20260926.md``.
Sealed P7 seeds 101–108 are not reused. Outcomes are not stored in this
module. Soft-pass by retuning after inspection is refused.
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
    HP_ARM01_ESTIMAND,
    SUBSTRATE_LIFE_LOOP,
    ThreeArmCampaignReport,
    max_allowed_claim_ceiling,
    run_three_arm_frequency_campaign,
)

PREREG_VERSION = "hp_arm01_slowinski_invasion_prereg_20260926"
PREREG_RELATIVE_PATH = (
    "docs/handoff/CLOSED_LOOP_HP_ARM01_SLOWINSKI_INVASION_PREREG_20260926.md"
)
HP_ARM01_CONFIRM_REVISION = "hp-arm01-slowinski-confirm-20260926"

# Locked design (written before outcomes). Do not edit after inspection.
CONFIRM_SEEDS: tuple[int, ...] = (201, 202, 203, 204, 205, 206, 207, 208)
SEALED_P7_SEEDS: tuple[int, ...] = (101, 102, 103, 104, 105, 106, 107, 108)
CONFIRM_GENERATIONS = 48
CONFIRM_VIRULENCE = 32.0
CONFIRM_PARASITE_MUTATION = 0.5
CONFIRM_HOST_BIT_FLIP = 0.0
CONFIRM_HOST_N = 10
CONFIRM_PARASITE_N = 8
CONFIRM_INTRO_SELFING_FREQ = 0.2
CONFIRM_BIRTH_ATP = 40.0
CONFIRM_HANDLING_TIME = 0.0
CONFIRM_PASS_BAR = 6
CONFIRM_TWO_FOLD_COST_SEX = False

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
        "revision": HP_ARM01_CONFIRM_REVISION,
        "estimand": HP_ARM01_ESTIMAND,
        "substrate": SUBSTRATE_LIFE_LOOP,
        "seeds": list(CONFIRM_SEEDS),
        "sealed_p7_seeds_untouched": list(SEALED_P7_SEEDS),
        "generations": CONFIRM_GENERATIONS,
        "virulence": CONFIRM_VIRULENCE,
        "parasite_mutation": CONFIRM_PARASITE_MUTATION,
        "host_bit_flip_rate": CONFIRM_HOST_BIT_FLIP,
        "host_n": CONFIRM_HOST_N,
        "parasite_n": CONFIRM_PARASITE_N,
        "intro_selfing_freq": CONFIRM_INTRO_SELFING_FREQ,
        "birth_atp": CONFIRM_BIRTH_ATP,
        "handling_time": CONFIRM_HANDLING_TIME,
        "two_fold_cost_sex": CONFIRM_TWO_FOLD_COST_SEX,
        "pass_bar": CONFIRM_PASS_BAR,
        "founders": [list(row) for row in _INVASION_FOUNDERS],
        "arms": [ARM_AVIRULENT, ARM_FIXED, ARM_COPASSAGED],
        "prereg_path": PREREG_RELATIVE_PATH,
        "accept_path": HP_ARM01_ESTIMAND,
        "legacy_three_freq_is_accept_path": False,
        "shared_modifier_refused_as_primary": True,
        "red_queen_proved_allowed": False,
        "biological_red_queen_proved_allowed": False,
    }


def slowinski_confirm_design_digest() -> str:
    return canonical_digest(locked_design_dict(), prefix="hp_arm01_slowinski_design")


def slowinski_confirm_document_digest() -> str:
    path = prereg_document_path()
    if not path.is_file():
        raise ConfigurationError(f"missing preregistration file: {PREREG_RELATIVE_PATH}")
    raw = path.read_bytes()
    return hashlib.sha256(raw).hexdigest()


def assert_confirm_seed_policy(seeds: Sequence[int] | None = None) -> None:
    """Refuse reuse of sealed P7 seeds and empty / duplicate lists."""

    chosen = tuple(int(s) for s in (seeds if seeds is not None else CONFIRM_SEEDS))
    if not chosen:
        raise ConfigurationError("confirmatory seeds must be non-empty")
    if len(set(chosen)) != len(chosen):
        raise ConfigurationError("confirmatory seeds must be unique")
    overlap = sorted(set(chosen) & set(SEALED_P7_SEEDS))
    if overlap:
        raise ConfigurationError(
            f"sealed P7 seeds 101–108 must not be reused; overlap={overlap}"
        )
    if tuple(chosen) != CONFIRM_SEEDS and seeds is None:
        raise ConfigurationError("default confirmatory seed tuple was altered")


def assert_locked_horizon(*, generations: int) -> None:
    """Refuse gens=4 theater labeled as confirmatory."""

    if int(generations) < CONFIRM_GENERATIONS:
        raise ConfigurationError(
            f"confirmatory horizon is locked at {CONFIRM_GENERATIONS} generations; "
            f"got {generations} (short scaffold is not confirmatory)"
        )


@dataclass(frozen=True, slots=True)
class SlowinskiSeedResult:
    seed: int
    slowinski_invasion_holds: bool
    selfing_freq_by_arm: dict[str, float | None]
    intro_selfing_freq: float
    claim_ceiling: str
    max_allowed_ceiling: str
    digest: str
    clocks_complete: bool
    per_arm_clocks_ok: bool
    life_loop_bound: bool
    two_fold_cost_sex_applied: bool
    confirmatory_horizon_deferred: bool
    report: ThreeArmCampaignReport

    def to_dict(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "slowinski_invasion_holds": self.slowinski_invasion_holds,
            "selfing_freq_by_arm": dict(self.selfing_freq_by_arm),
            "intro_selfing_freq": self.intro_selfing_freq,
            "claim_ceiling": self.claim_ceiling,
            "max_allowed_ceiling": self.max_allowed_ceiling,
            "digest": self.digest,
            "clocks_complete": self.clocks_complete,
            "per_arm_clocks_ok": self.per_arm_clocks_ok,
            "life_loop_bound": self.life_loop_bound,
            "two_fold_cost_sex_applied": self.two_fold_cost_sex_applied,
            "confirmatory_horizon_deferred": self.confirmatory_horizon_deferred,
            "estimand": HP_ARM01_ESTIMAND,
            "substrate": SUBSTRATE_LIFE_LOOP,
        }


@dataclass(frozen=True, slots=True)
class SlowinskiConfirmReport:
    """Multi-seed confirmatory report. Flags stay false."""

    seeds: tuple[int, ...]
    seed_results: tuple[SlowinskiSeedResult, ...]
    seeds_passed: int
    pass_bar: int
    campaign_pass: bool
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
    revision: str
    notes: str
    digest: str

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": "hp_arm01_slowinski_confirm_v1",
            "prereg_version": PREREG_VERSION,
            "revision": self.revision,
            "estimand": HP_ARM01_ESTIMAND,
            "accept_path": HP_ARM01_ESTIMAND,
            "substrate": SUBSTRATE_LIFE_LOOP,
            "seeds": list(self.seeds),
            "seed_results": [row.to_dict() for row in self.seed_results],
            "seeds_passed": self.seeds_passed,
            "pass_bar": self.pass_bar,
            "campaign_pass": self.campaign_pass,
            "slowinski_invasion_campaign_holds": self.campaign_pass,
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
            "host_n": CONFIRM_HOST_N,
            "parasite_n": CONFIRM_PARASITE_N,
            "birth_atp": CONFIRM_BIRTH_ATP,
            "handling_time": CONFIRM_HANDLING_TIME,
            "legacy_three_freq_is_accept_path": False,
            "shared_modifier_refused_as_primary_substrate": True,
            "sealed_p7_seeds_untouched": True,
            "notes": self.notes,
        }
        payload["digest"] = self.digest
        return payload


def _seed_result_from_report(seed: int, report: ThreeArmCampaignReport) -> SlowinskiSeedResult:
    return SlowinskiSeedResult(
        seed=seed,
        slowinski_invasion_holds=bool(report.slowinski_invasion_holds),
        selfing_freq_by_arm=dict(report.selfing_freq_by_arm),
        intro_selfing_freq=float(report.intro_selfing_freq),
        claim_ceiling=str(report.claim_ceiling),
        max_allowed_ceiling=str(report.max_allowed_ceiling),
        digest=str(report.digest),
        clocks_complete=bool(report.clocks_complete),
        per_arm_clocks_ok=bool(report.per_arm_clocks_ok),
        life_loop_bound=bool(report.life_loop_bound),
        two_fold_cost_sex_applied=bool(report.two_fold_cost_sex_applied),
        confirmatory_horizon_deferred=bool(report.confirmatory_horizon_deferred),
        report=report,
    )


def run_slowinski_confirm_campaign(
    *,
    seeds: Sequence[int] | None = None,
    generations: int | None = None,
    virulence: float | None = None,
    parasite_mutation: float | None = None,
    attach_pearl_measurement: bool = False,
) -> SlowinskiConfirmReport:
    """Run the locked confirmatory invasion campaign on the life-loop path.

    Defaults are the prereg lock. Passing a shorter ``generations`` raises.
    Retuning after inspection is a process violation, not a soft-pass path.
    """

    chosen_seeds = tuple(int(s) for s in (seeds if seeds is not None else CONFIRM_SEEDS))
    gens = int(CONFIRM_GENERATIONS if generations is None else generations)
    vir = float(CONFIRM_VIRULENCE if virulence is None else virulence)
    pmut = float(CONFIRM_PARASITE_MUTATION if parasite_mutation is None else parasite_mutation)

    assert_confirm_seed_policy(chosen_seeds)
    assert_locked_horizon(generations=gens)
    if abs(vir - CONFIRM_VIRULENCE) > 1e-12:
        raise ConfigurationError(
            f"confirmatory virulence is locked at {CONFIRM_VIRULENCE}; got {vir}"
        )
    if abs(pmut - CONFIRM_PARASITE_MUTATION) > 1e-12:
        raise ConfigurationError(
            f"confirmatory parasite_mutation is locked at {CONFIRM_PARASITE_MUTATION}; got {pmut}"
        )

    design = slowinski_confirm_design_digest()
    document = slowinski_confirm_document_digest()

    results: list[SlowinskiSeedResult] = []
    for seed in chosen_seeds:
        report = run_three_arm_frequency_campaign(
            virulence=vir,
            generations=gens,
            seed=seed,
            attach_pearl_measurement=attach_pearl_measurement,
            handling_time=CONFIRM_HANDLING_TIME,
            parasite_mutation=pmut,
            birth_atp=CONFIRM_BIRTH_ATP,
            parasite_n=CONFIRM_PARASITE_N,
            founders=_INVASION_FOUNDERS,
        )
        if abs(report.intro_selfing_freq - CONFIRM_INTRO_SELFING_FREQ) > 1e-12:
            raise ConfigurationError(
                "intro selfing frequency drifted from locked 0.2; refuse soft-pass"
            )
        if report.confirmatory_horizon_deferred:
            raise ConfigurationError(
                "confirmatory run must not remain marked deferred after locked horizon"
            )
        if report.substrate != SUBSTRATE_LIFE_LOOP or not report.life_loop_bound:
            raise ConfigurationError("confirmatory campaign must stay on life-loop substrate")
        if report.two_fold_cost_sex_applied:
            raise ConfigurationError("two-fold cost must remain unpaid on this confirmatory lock")
        if report.red_queen_proved or report.biological_red_queen_proved:
            raise ConfigurationError("Red Queen flags must stay false")
        results.append(_seed_result_from_report(seed, report))

    seeds_passed = sum(1 for row in results if row.slowinski_invasion_holds)
    campaign_pass = seeds_passed >= CONFIRM_PASS_BAR

    clocks_ok = all(row.clocks_complete for row in results)
    per_arm_ok = all(row.per_arm_clocks_ok for row in results)
    life_ok = all(row.life_loop_bound for row in results)
    treatment_control = True
    ceiling_cap = max_allowed_claim_ceiling(
        clocks_complete=clocks_ok,
        treatment_control_present=treatment_control,
        substrate_life_loop_bound=life_ok,
        per_arm_clocks_ok=per_arm_ok,
        slowinski_invasion_holds=campaign_pass,
    )
    reported_ceiling = (
        CLAIM_CEILING_CANDIDATE
        if campaign_pass and ceiling_cap == CLAIM_CEILING_CANDIDATE
        else CLAIM_CEILING_OBSERVATION
    )

    note = (
        "slowinski_invasion_campaign_pass"
        if campaign_pass
        else "slowinski_invasion_campaign_fail_recorded_honestly"
    )
    note = f"{note};seeds_passed={seeds_passed}/{len(results)};pass_bar={CONFIRM_PASS_BAR}"

    draft = SlowinskiConfirmReport(
        seeds=chosen_seeds,
        seed_results=tuple(results),
        seeds_passed=seeds_passed,
        pass_bar=CONFIRM_PASS_BAR,
        campaign_pass=campaign_pass,
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
        intro_selfing_freq=CONFIRM_INTRO_SELFING_FREQ,
        revision=HP_ARM01_CONFIRM_REVISION,
        notes=note,
        digest="",
    )
    # Digest excludes nested report objects; use to_dict without digest field.
    body = {k: v for k, v in draft.to_dict().items() if k != "digest"}
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    return SlowinskiConfirmReport(
        seeds=draft.seeds,
        seed_results=draft.seed_results,
        seeds_passed=draft.seeds_passed,
        pass_bar=draft.pass_bar,
        campaign_pass=draft.campaign_pass,
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
        revision=draft.revision,
        notes=draft.notes,
        digest=digest,
    )


def summarize_seed_terminals(report: SlowinskiConfirmReport) -> list[dict[str, object]]:
    """Compact terminal frequency table for evidence packages."""

    rows: list[dict[str, object]] = []
    for row in report.seed_results:
        rows.append(
            {
                "seed": row.seed,
                "passed": row.slowinski_invasion_holds,
                "avirulent": row.selfing_freq_by_arm.get(ARM_AVIRULENT),
                "fixed": row.selfing_freq_by_arm.get(ARM_FIXED),
                "copassaged": row.selfing_freq_by_arm.get(ARM_COPASSAGED),
                "intro": row.intro_selfing_freq,
                "digest": row.digest,
            }
        )
    return rows


__all__ = [
    "CONFIRM_BIRTH_ATP",
    "CONFIRM_GENERATIONS",
    "CONFIRM_HANDLING_TIME",
    "CONFIRM_HOST_BIT_FLIP",
    "CONFIRM_HOST_N",
    "CONFIRM_INTRO_SELFING_FREQ",
    "CONFIRM_PARASITE_MUTATION",
    "CONFIRM_PARASITE_N",
    "CONFIRM_PASS_BAR",
    "CONFIRM_SEEDS",
    "CONFIRM_TWO_FOLD_COST_SEX",
    "CONFIRM_VIRULENCE",
    "HP_ARM01_CONFIRM_REVISION",
    "PREREG_RELATIVE_PATH",
    "PREREG_VERSION",
    "SEALED_P7_SEEDS",
    "SlowinskiConfirmReport",
    "SlowinskiSeedResult",
    "assert_confirm_seed_policy",
    "assert_locked_horizon",
    "locked_design_dict",
    "prereg_document_path",
    "run_slowinski_confirm_campaign",
    "slowinski_confirm_design_digest",
    "slowinski_confirm_document_digest",
    "summarize_seed_terminals",
]
