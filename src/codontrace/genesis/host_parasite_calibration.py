"""Phase 10 — Digest-stable calibration fixtures for HostParasiteWorld campaigns.

Directional literature expectations are CodonTrace meter/digest predicates.
Honest FAIL with recorded reasons is allowed. Calibration miss never opens
ClaimGate refuses. No Env.step, no infection physics, no engine.py edits.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.host_parasite_analytics import (
    run_continuum_factorial,
    run_reciprocal_observational_contrast,
)
from codontrace.genesis.host_parasite_world import (
    HostParasiteProfile,
    HostParasiteWorld,
)

SCHEMA_TARGET = "host_parasite_calibration_target_v1"
SCHEMA_OUTCOME = "host_parasite_calibration_outcome_v1"
SCHEMA_REPORT = "host_parasite_calibration_report_v1"

OutcomeKind = Literal["pass", "fail", "deferred"]
ExpectationKind = Literal[
    "freeze_unlock_digest_differs",
    "dual_null_digest_differs",
    "meter_channels_finite",
    "continuum_axis_digest_differs",
    "coexistence_densities_nonneg",
]

EXPECTATIONS: frozenset[str] = frozenset(
    {
        "freeze_unlock_digest_differs",
        "dual_null_digest_differs",
        "meter_channels_finite",
        "continuum_axis_digest_differs",
        "coexistence_densities_nonneg",
    }
)

_CORE_REFUSES: frozenset[str] = frozenset(
    {
        "red_queen_proved",
        "intervention_supported",
        "raises_claim_ladder",
        "calibration_miss_opens_refuses",
        "phage_therapy_cleared",
        "vaccine_efficacy_proved",
        "biosafety_level_certified",
        "clinical_claim",
    }
)


def _as_str(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string.")
    text = value.strip()
    if not text and not allow_empty:
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return text


def _as_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer.")
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}.")
    return value


def _as_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{name} must be a bool.")
    return value


def _refuse_banned_fragment(text: str, name: str) -> str:
    lowered = text.casefold()
    for token in BANNED_DOMAIN_TOKENS:
        if token.casefold() in lowered:
            raise ConfigurationError(f"{name} contains a banned fragment.")
    return text


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


def _merge_refuses(extra: Sequence[str] | None = None) -> tuple[str, ...]:
    items = set(_CORE_REFUSES)
    for item in extra or ():
        items.add(_as_str(item, "refuse").casefold())
    return tuple(sorted(items))


@dataclass(frozen=True, slots=True)
class CalibrationTarget:
    """Directional calibration target (CodonTrace predicates + lit note)."""

    target_id: str
    phenomenon: str
    expectation: str
    literature_note: str
    seed: int = 0
    ticks: int = 2
    smoke_only: bool = True
    refuse_list: tuple[str, ...] = ()
    digest: str = ""

    def __post_init__(self) -> None:
        tid = _refuse_banned_fragment(_as_str(self.target_id, "target_id"), "target_id")
        phen = _as_str(self.phenomenon, "phenomenon")
        exp = _as_str(self.expectation, "expectation").casefold()
        if exp not in EXPECTATIONS:
            raise ConfigurationError(f"unknown expectation {self.expectation!r}.")
        note = _as_str(self.literature_note, "literature_note", allow_empty=True)
        object.__setattr__(self, "target_id", tid)
        object.__setattr__(self, "phenomenon", phen)
        object.__setattr__(self, "expectation", exp)
        object.__setattr__(self, "literature_note", note)
        object.__setattr__(self, "seed", _as_int(self.seed, "seed", minimum=0))
        object.__setattr__(self, "ticks", _as_int(self.ticks, "ticks", minimum=0))
        object.__setattr__(self, "smoke_only", _as_bool(self.smoke_only, "smoke_only"))
        object.__setattr__(self, "refuse_list", _merge_refuses(self.refuse_list))
        computed = canonical_digest(self._body(), prefix="hp_calib_tgt")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "CalibrationTarget")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_TARGET,
            "target_id": self.target_id,
            "phenomenon": self.phenomenon,
            "expectation": self.expectation,
            "literature_note": self.literature_note,
            "seed": self.seed,
            "ticks": self.ticks,
            "smoke_only": self.smoke_only,
            "refuse_list": list(self.refuse_list),
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "calibration_miss_opens_refuses": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class CalibrationOutcome:
    """Single target evaluation: pass / fail / deferred with reason + digests."""

    target_id: str
    outcome: str
    reason: str
    observed_digest: str
    literature_note: str
    target_digest: str
    digest: str = ""

    def __post_init__(self) -> None:
        tid = _refuse_banned_fragment(_as_str(self.target_id, "target_id"), "target_id")
        out = _as_str(self.outcome, "outcome").casefold()
        if out not in {"pass", "fail", "deferred"}:
            raise ConfigurationError("outcome must be pass, fail, or deferred.")
        object.__setattr__(self, "target_id", tid)
        object.__setattr__(self, "outcome", out)
        object.__setattr__(self, "reason", _as_str(self.reason, "reason", allow_empty=True))
        object.__setattr__(
            self,
            "observed_digest",
            _as_str(self.observed_digest, "observed_digest", allow_empty=True),
        )
        object.__setattr__(
            self,
            "literature_note",
            _as_str(self.literature_note, "literature_note", allow_empty=True),
        )
        object.__setattr__(
            self, "target_digest", _as_str(self.target_digest, "target_digest")
        )
        computed = canonical_digest(self._body(), prefix="hp_calib_out")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "CalibrationOutcome")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_OUTCOME,
            "target_id": self.target_id,
            "outcome": self.outcome,
            "reason": self.reason,
            "observed_digest": self.observed_digest,
            "literature_note": self.literature_note,
            "target_digest": self.target_digest,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class CalibrationReport:
    """Aggregate refuse-safe calibration report."""

    report_id: str
    outcomes: tuple[CalibrationOutcome, ...]
    science_grade: bool = False
    red_queen_proved: bool = False
    raises_claim_ladder: bool = False
    calibration_miss_opens_refuses: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        rid = _refuse_banned_fragment(_as_str(self.report_id, "report_id"), "report_id")
        if self.red_queen_proved:
            raise ConfigurationError("CalibrationReport refuses red_queen_proved=True.")
        if self.raises_claim_ladder:
            raise ConfigurationError("CalibrationReport refuses raises_claim_ladder=True.")
        if self.calibration_miss_opens_refuses:
            raise ConfigurationError(
                "CalibrationReport refuses calibration_miss_opens_refuses=True."
            )
        if not self.outcomes:
            raise ConfigurationError("outcomes must be non-empty.")
        if not all(isinstance(o, CalibrationOutcome) for o in self.outcomes):
            raise ConfigurationError("outcomes must be CalibrationOutcome instances.")
        science = _as_bool(self.science_grade, "science_grade")
        object.__setattr__(self, "report_id", rid)
        object.__setattr__(self, "outcomes", tuple(self.outcomes))
        object.__setattr__(self, "science_grade", science)
        object.__setattr__(self, "red_queen_proved", False)
        object.__setattr__(self, "raises_claim_ladder", False)
        object.__setattr__(self, "calibration_miss_opens_refuses", False)
        computed = canonical_digest(self._body(), prefix="hp_calib_rpt")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "CalibrationReport")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_REPORT,
            "report_id": self.report_id,
            "outcomes": [o.to_dict() for o in self.outcomes],
            "science_grade": self.science_grade,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "calibration_miss_opens_refuses": False,
            "epistasis_hgt_lag_status": "deferred",
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CalibrationReport:
        raw = data.get("outcomes")
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            raise ConfigurationError("outcomes must be a sequence.")
        outcomes = tuple(
            CalibrationOutcome(
                target_id=_as_str(item.get("target_id"), "target_id"),
                outcome=_as_str(item.get("outcome"), "outcome"),
                reason=_as_str(item.get("reason", ""), "reason", allow_empty=True),
                observed_digest=_as_str(
                    item.get("observed_digest", ""), "observed_digest", allow_empty=True
                ),
                literature_note=_as_str(
                    item.get("literature_note", ""), "literature_note", allow_empty=True
                ),
                target_digest=_as_str(item.get("target_digest"), "target_digest"),
                digest=_as_str(item.get("digest", ""), "digest", allow_empty=True),
            )
            for item in raw
            if isinstance(item, Mapping)
        )
        return cls(
            report_id=_as_str(data.get("report_id"), "report_id"),
            outcomes=outcomes,
            science_grade=bool(data.get("science_grade", False)),
            red_queen_proved=bool(data.get("red_queen_proved", False)),
            raises_claim_ladder=bool(data.get("raises_claim_ladder", False)),
            calibration_miss_opens_refuses=bool(
                data.get("calibration_miss_opens_refuses", False)
            ),
            digest=_as_str(data.get("digest", ""), "digest", allow_empty=True),
        )


def _eval_freeze_unlock(target: CalibrationTarget) -> CalibrationOutcome:
    result = run_reciprocal_observational_contrast(
        contrast_id=f"cal_{target.target_id}",
        seed=target.seed,
        ticks=max(target.ticks, 1),
        include_replay=True,
        smoke_only=True,
    )
    freeze_d = result.freeze_arm.arm_digest
    unlock_d = result.unlock_arm.arm_digest
    ok = freeze_d != unlock_d
    return CalibrationOutcome(
        target_id=target.target_id,
        outcome="pass" if ok else "fail",
        reason=(
            "freeze_arm_digest_differs_from_unlock"
            if ok
            else "freeze_and_unlock_digests_identical"
        ),
        observed_digest=result.digest,
        literature_note=target.literature_note,
        target_digest=target.digest,
    )


def _eval_dual_null(target: CalibrationTarget) -> CalibrationOutcome:
    none_world = HostParasiteWorld(
        HostParasiteProfile(
            profile_id=f"cal_none_{target.target_id}"[:48],
            seed=target.seed,
            ablation_preset="none",
        )
    )
    dual_world = HostParasiteWorld(
        HostParasiteProfile(
            profile_id=f"cal_dual_{target.target_id}"[:48],
            seed=target.seed,
            ablation_preset="dual_null",
        )
    )
    for _ in range(max(target.ticks, 1)):
        none_world.tick()
        dual_world.tick()
    none_s = none_world.summary()
    dual_s = dual_world.summary()
    ok = none_s["world_digest"] != dual_s["world_digest"]
    observed = canonical_digest(
        {
            "none": none_s["world_digest"],
            "dual_null": dual_s["world_digest"],
        },
        prefix="hp_calib_dual",
    )
    return CalibrationOutcome(
        target_id=target.target_id,
        outcome="pass" if ok else "fail",
        reason=(
            "dual_null_world_digest_differs_from_none"
            if ok
            else "dual_null_and_none_digests_identical"
        ),
        observed_digest=observed,
        literature_note=target.literature_note,
        target_digest=target.digest,
    )


def _eval_meter_finite(target: CalibrationTarget) -> CalibrationOutcome:
    world = HostParasiteWorld(
        HostParasiteProfile(
            profile_id=f"cal_meter_{target.target_id}"[:48],
            seed=target.seed,
            coupling_amount=0.2,
        )
    )
    world.run(max(target.ticks, 1))
    summary = world.metric_summary(claim_role="smoke")
    finite_ok = True
    reasons: list[str] = []
    for key, value in summary.metrics.items():
        try:
            require_finite_float(key, value)
            if float(value) < 0.0:
                finite_ok = False
                reasons.append(f"{key}_negative")
        except ConfigurationError:
            finite_ok = False
            reasons.append(f"{key}_nonfinite")
    return CalibrationOutcome(
        target_id=target.target_id,
        outcome="pass" if finite_ok else "fail",
        reason="meter_channels_finite_nonneg" if finite_ok else ",".join(reasons),
        observed_digest=summary.digest,
        literature_note=target.literature_note,
        target_digest=target.digest,
    )


def _eval_continuum_axis(target: CalibrationTarget) -> CalibrationOutcome:
    result = run_continuum_factorial(
        factorial_id=f"cal_{target.target_id}",
        seeds=(target.seed,),
        ticks=max(target.ticks, 1),
        coupling_levels=(0.1, 0.5),
        spatial_modes=("well_mixed",),
        inherit_levels=(0.0,),
        match_score_scales=(1.0,),
        smoke_only=True,
    )
    ok = len(result.cells) == 2 and result.cells[0].cell_digest != result.cells[1].cell_digest
    return CalibrationOutcome(
        target_id=target.target_id,
        outcome="pass" if ok else "fail",
        reason=(
            "coupling_axis_cell_digests_differ"
            if ok
            else "coupling_axis_cell_digests_identical"
        ),
        observed_digest=result.digest,
        literature_note=target.literature_note,
        target_digest=target.digest,
    )


def _eval_coexistence(target: CalibrationTarget) -> CalibrationOutcome:
    world = HostParasiteWorld(
        HostParasiteProfile(
            profile_id=f"cal_coex_{target.target_id}"[:48],
            seed=target.seed,
            coupling_amount=0.15,
            inherit_probability=0.25,
            inherit_mode="copy",
        )
    )
    world.run(max(target.ticks, 1))
    census = world.census()
    ok = census["primary"] >= 0 and census["secondary"] >= 0
    observed = canonical_digest(dict(census), prefix="hp_calib_coex")
    return CalibrationOutcome(
        target_id=target.target_id,
        outcome="pass" if ok else "fail",
        reason="coexistence_densities_nonneg" if ok else "negative_density",
        observed_digest=observed,
        literature_note=target.literature_note,
        target_digest=target.digest,
    )


_EVALUATORS = {
    "freeze_unlock_digest_differs": _eval_freeze_unlock,
    "dual_null_digest_differs": _eval_dual_null,
    "meter_channels_finite": _eval_meter_finite,
    "continuum_axis_digest_differs": _eval_continuum_axis,
    "coexistence_densities_nonneg": _eval_coexistence,
}


def default_smoke_targets() -> tuple[CalibrationTarget, ...]:
    """Built-in smoke calibration catalog (≥4 directional predicates)."""

    return (
        CalibrationTarget(
            target_id="cal_freeze_unlock",
            phenomenon="schedule_arm_observational_contrast",
            expectation="freeze_unlock_digest_differs",
            literature_note=(
                "Directional: freeze vs unlock schedule arms must diverge on "
                "CodonTrace digests (peer lit: Zaman-style freeze/replay arms as "
                "optional comparison only)."
            ),
            seed=0,
            ticks=2,
            smoke_only=True,
        ),
        CalibrationTarget(
            target_id="cal_dual_null",
            phenomenon="ablation_dual_null_divergence",
            expectation="dual_null_digest_differs",
            literature_note=(
                "Directional: dual_null ablation must change World digest vs none "
                "(content/structure controls; Floreano-style content-null as peer note)."
            ),
            seed=1,
            ticks=2,
            smoke_only=True,
        ),
        CalibrationTarget(
            target_id="cal_continuum_coupling",
            phenomenon="continuum_coupling_axis",
            expectation="continuum_axis_digest_differs",
            literature_note=(
                "Directional: continuum factorial cells differ when coupling_amount "
                "changes (CodonTrace World meters; not a free interaction_value slider)."
            ),
            seed=2,
            ticks=1,
            smoke_only=True,
        ),
        CalibrationTarget(
            target_id="cal_meter_finite",
            phenomenon="meter_channel_finiteness",
            expectation="meter_channels_finite",
            literature_note="Instrumentation: HookMeter-derived metric channels stay finite and non-negative.",
            seed=3,
            ticks=2,
            smoke_only=True,
        ),
        CalibrationTarget(
            target_id="cal_coexistence_density",
            phenomenon="coexistence_density_proxy",
            expectation="coexistence_densities_nonneg",
            literature_note=(
                "Directional coexistence proxy: primary/secondary densities remain "
                "non-negative after ticks (cost-of-generalism lit as optional peer note)."
            ),
            seed=4,
            ticks=2,
            smoke_only=True,
        ),
    )


def run_calibration_target(target: CalibrationTarget) -> CalibrationOutcome:
    """Evaluate one target; never mutates ClaimGate or pins."""

    if not isinstance(target, CalibrationTarget):
        raise ConfigurationError("target must be a CalibrationTarget.")
    evaluator = _EVALUATORS.get(target.expectation)
    if evaluator is None:
        return CalibrationOutcome(
            target_id=target.target_id,
            outcome="deferred",
            reason=f"no_evaluator_for_{target.expectation}",
            observed_digest="",
            literature_note=target.literature_note,
            target_digest=target.digest,
        )
    return evaluator(target)


def run_calibration_suite(
    *,
    report_id: str = "calib_smoke_suite",
    targets: Sequence[CalibrationTarget] | None = None,
    science_grade: bool = False,
) -> CalibrationReport:
    """Run a calibration suite; smoke suites force science_grade=False."""

    rid = _refuse_banned_fragment(_as_str(report_id, "report_id"), "report_id")
    catalog = tuple(targets) if targets is not None else default_smoke_targets()
    if not catalog:
        raise ConfigurationError("targets must be non-empty.")
    if any(t.smoke_only for t in catalog) and science_grade:
        raise ConfigurationError("smoke_only targets refuse science_grade=True.")
    outcomes = tuple(run_calibration_target(t) for t in catalog)
    return CalibrationReport(
        report_id=rid,
        outcomes=outcomes,
        science_grade=False if any(t.smoke_only for t in catalog) else science_grade,
    )


__all__ = [
    "EXPECTATIONS",
    "SCHEMA_OUTCOME",
    "SCHEMA_REPORT",
    "SCHEMA_TARGET",
    "CalibrationOutcome",
    "CalibrationReport",
    "CalibrationTarget",
    "default_smoke_targets",
    "run_calibration_suite",
    "run_calibration_target",
]
