"""Channon 2024 Tokyo Type 1 OEE *measurement* protocol.

This module runs the measurement-step vocabulary from Alastair Channon,
"A Procedure for Testing for Tokyo Type 1 Open-Ended Evolution"
(*Artificial Life*, 2024), using Phase D MODES / Bedau / OEE metric surfaces
when present.

It does **not** pass Tokyo Type 1. The claim ceiling is
``tokyo_type1_measurement_only``. ``tokyo_type1_passed`` is blocked by
construction and by :class:`~codontrace.genesis.claim_gate.ScientificClaimGate`.

Packard et al. 2019 (Tokyo types overview) is the taxonomy this procedure
sits under. Borg et al. 2023 cultural OEE is cited only and is out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.claim_gate import ClaimDecision, ClaimRequest, ScientificClaimGate

_MEASUREMENT_CEILING = "tokyo_type1_measurement_only"
_PASSED_CLAIM = "tokyo_type1_passed"
_PROTOCOL_SCHEMA = "tokyo_type1_measurement_protocol_v1"
_STEP_SCHEMA = "tokyo_type1_measurement_step_v1"

CHANNON_2024_MEASUREMENT_STEPS: tuple[tuple[str, str], ...] = (
    (
        "step_1_activity_components",
        "Define evolutionary activity components from Bedau/MODES presence sets "
        "(Channon 2024 measurement vocabulary; not a pass verdict).",
    ),
    (
        "step_2_evolutionary_activity",
        "Measure novelty, diversity, and cumulative activity over time "
        "(Bedau evolutionary activity statistics as the activity series).",
    ),
    (
        "step_3_adaptive_novelty",
        "Measure persistence-filtered novelty/change (MODES-style axes after "
        "persistence_window_t; Dolson et al. 2019).",
    ),
    (
        "step_4_shadow_normalization",
        "Record shadow / null-model normalization hooks when a real shadow digest "
        "is supplied. Unavailable unless supplied — not an Empirical systematics "
        "shadow run by default.",
    ),
    (
        "step_5_multi_seed_aggregation",
        "Aggregate across independent seeds. Anything above measurement_only "
        "requires a multi-seed protocol; the pass claim remains blocked.",
    ),
    (
        "step_6_claim_gate",
        "ClaimGate ceiling tokyo_type1_measurement_only; tokyo_type1_passed blocked.",
    ),
)

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "channon_2024_tokyo_type1_procedure",
        "Channon 2024 Artificial Life: A Procedure for Testing for Tokyo Type 1 "
        "Open-Ended Evolution — measurement steps only in this library.",
    ),
    (
        "packard_et_al_2019_tokyo_types",
        "Packard et al. 2019 Tokyo workshop types overview: Type 1 = ongoing "
        "generation of adaptive novelty. Taxonomy cite; not a pass test here.",
    ),
    (
        "bedau_evolutionary_activity",
        "Bedau evolutionary activity statistics used as the activity series.",
    ),
    (
        "modes_dolson_2019",
        "Dolson, Vostinar, Wiser, Ofria 2019 MODES toolbox: persistence-filtered "
        "novelty/change inputs to the Type 1 measurement steps.",
    ),
    (
        "borg_et_al_2023_cultural_oee",
        "Borg et al. 2023 cultural OEE — cite only; out of scope for this protocol.",
    ),
)

_FORBIDDEN_PASS_STATUSES = frozenset(
    {
        "tokyo_type1_passed",
        "tokyo_type1_proved",
        "channon_2024_passed",
        "tokyo_type_1_passed",
        "tokyo_type1_oee_proved",
        "proved_open_endedness",
        "open_ended_intelligence",
    }
)


def _optional_digest(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    return text if text and not text.startswith("not_run") else ""


@dataclass(frozen=True, slots=True)
class TokyoType1StepResult:
    """One Channon-2024 measurement step. Never a Type 1 pass bit."""

    step_id: str
    label: str
    status: str
    notes: str = ""
    metric_count: int = 0
    shadow_digest: str = ""
    schema_version: str = _STEP_SCHEMA

    def __post_init__(self) -> None:
        if self.step_id not in {item[0] for item in CHANNON_2024_MEASUREMENT_STEPS}:
            raise ConfigurationError(
                "TokyoType1StepResult.step_id must be a Channon-2024 step label."
            )
        if self.status in _FORBIDDEN_PASS_STATUSES:
            raise ConfigurationError("TokyoType1StepResult must never record a Type 1 pass status.")
        if self.metric_count < 0:
            raise ConfigurationError("metric_count must be non-negative.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "step_id": self.step_id,
            "label": self.label,
            "status": self.status,
            "notes": self.notes,
            "metric_count": self.metric_count,
            "shadow_digest": self.shadow_digest,
            "tokyo_type1_passed": False,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class TokyoType1MeasurementProtocol:
    """Channon-2024 measurement protocol object. Claim-gated; pass blocked.

    Multi-seed is required for any status string above ``measurement_only``.
    Even then the ceiling stays ``tokyo_type1_measurement_only``.
    """

    steps: tuple[TokyoType1StepResult, ...]
    seed_count: int
    persistence_window_t: int
    activity_observed: bool
    novelty_observed: bool
    shadow_normalization_status: str
    shadow_digest: str = ""
    empirical_systematics_shadow_run: bool = False
    source_pack_digest: str = ""
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    measurement_status: str = "measurement_only"
    claim_ceiling: str = _MEASUREMENT_CEILING
    tokyo_type1_passed: bool = False
    schema_version: str = _PROTOCOL_SCHEMA
    digest: str = ""

    def __post_init__(self) -> None:
        if self.tokyo_type1_passed:
            raise ConfigurationError(
                "TokyoType1MeasurementProtocol must never set tokyo_type1_passed."
            )
        if self.claim_ceiling != _MEASUREMENT_CEILING:
            raise ConfigurationError(
                "TokyoType1MeasurementProtocol claim_ceiling must stay "
                "tokyo_type1_measurement_only."
            )
        if self.measurement_status in _FORBIDDEN_PASS_STATUSES:
            raise ConfigurationError(
                "TokyoType1MeasurementProtocol must never record a Type 1 pass status."
            )
        if self.seed_count < 1:
            raise ConfigurationError("seed_count must be >= 1.")
        if self.persistence_window_t < 1:
            raise ConfigurationError("persistence_window_t must be >= 1.")
        expected_ids = tuple(item[0] for item in CHANNON_2024_MEASUREMENT_STEPS)
        observed_ids = tuple(step.step_id for step in self.steps)
        if observed_ids != expected_ids:
            raise ConfigurationError(
                "TokyoType1MeasurementProtocol steps must match Channon-2024 "
                "labels in order."
            )
        if self.empirical_systematics_shadow_run and not _optional_digest(self.shadow_digest):
            raise ConfigurationError(
                "empirical_systematics_shadow_run requires a real shadow digest; "
                "CodonTrace does not invent an Empirical systematics run."
            )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("TokyoType1MeasurementProtocol digest mismatch.")
        object.__setattr__(self, "digest", computed)
        object.__setattr__(self, "tokyo_type1_passed", False)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "steps": [step.to_dict() for step in self.steps],
            "seed_count": self.seed_count,
            "persistence_window_t": self.persistence_window_t,
            "activity_observed": self.activity_observed,
            "novelty_observed": self.novelty_observed,
            "shadow_normalization_status": self.shadow_normalization_status,
            "shadow_digest": self.shadow_digest,
            "empirical_systematics_shadow_run": self.empirical_systematics_shadow_run,
            "source_pack_digest": self.source_pack_digest,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "measurement_status": self.measurement_status,
            "claim_ceiling": self.claim_ceiling,
            "tokyo_type1_passed": False,
            "open_endedness_proved": False,
            "above_measurement_only_requires_multi_seed": True,
            "limitations": [
                "measurement_steps_only_not_tokyo_type1_passed",
                "no_empirical_systematics_shadow_run_unless_supplied",
                "borg_2023_cultural_oee_cite_only",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def _step(
    step_id: str, status: str, *, notes: str = "", metric_count: int = 0, shadow_digest: str = ""
) -> TokyoType1StepResult:
    label = next(item[1] for item in CHANNON_2024_MEASUREMENT_STEPS if item[0] == step_id)
    return TokyoType1StepResult(
        step_id=step_id,
        label=label,
        status=status,
        notes=notes,
        metric_count=metric_count,
        shadow_digest=shadow_digest,
    )


def _bedau_metrics(pack: object) -> tuple[bool, int]:
    surface = getattr(pack, "bedau_surface", None)
    points = tuple(getattr(surface, "points", ()) or ())
    activity = bool(points) and any(
        int(getattr(point, "activity", 0) or 0) > 0 for point in points
    )
    return activity, len(points)


def _modes_metrics(pack: object) -> tuple[bool, int, int]:
    modes = getattr(pack, "modes_assessment", None)
    points = tuple(getattr(modes, "points", ()) or ())
    novelty = bool(points) and any(
        float(getattr(point, "novelty", 0.0) or 0.0) > 0.0 for point in points
    )
    window = int(getattr(modes, "persistence_window_generations", 0) or 0)
    if window <= 0:
        window = int(
            getattr(getattr(pack, "config", None), "persistence_window_generations", 2) or 2
        )
    return novelty, len(points), max(1, window)


def build_tokyo_type1_measurement_protocol(
    pack: object | None = None,
    *,
    seed_count: int = 1,
    shadow_digest: str | None = None,
    empirical_systematics_shadow_run: bool = False,
    persistence_window_t: int | None = None,
) -> TokyoType1MeasurementProtocol:
    """Build a Channon-2024 measurement protocol from a Phase D pack when present.

    ``pack`` may be a ``MultiGenerationEvidencePack`` or ``None`` (empty measurement
    scaffold). Shadow/normalization is recorded as ``unavailable`` unless a real
    digest is passed. This never returns a Type 1 pass.
    """

    if seed_count < 1:
        raise ConfigurationError("seed_count must be >= 1.")
    activity_observed, activity_n = _bedau_metrics(pack) if pack is not None else (False, 0)
    novelty_observed, novelty_n, window = (
        _modes_metrics(pack) if pack is not None else (False, 0, 2)
    )
    resolved_window = persistence_window_t if persistence_window_t is not None else window
    if resolved_window < 1:
        raise ConfigurationError("persistence_window_t must be >= 1.")
    shadow = _optional_digest(shadow_digest)
    if pack is not None:
        report = getattr(pack, "oee_metrics_report", None)
        if not shadow and report is not None and bool(getattr(report, "shadow_adjusted", False)):
            shadow = _optional_digest(getattr(report, "threshold_digest", ""))
    if empirical_systematics_shadow_run and not shadow:
        raise ConfigurationError(
            "empirical_systematics_shadow_run is unsupported without a caller-supplied "
            "shadow digest; no Empirical systematics run is performed here."
        )
    shadow_status = "hook_recorded_not_empirical_systematics" if shadow else "unavailable"
    if seed_count >= 2:
        measurement_status = "multi_seed_measurement_only_still_not_passed"
        multi_seed_step_status = "recorded_below_pass_threshold"
    else:
        measurement_status = "measurement_only"
        multi_seed_step_status = "single_seed_blocks_above_measurement_only"
    source_digest = ""
    if pack is not None:
        source_digest = str(getattr(pack, "digest", "") or "")
    steps = (
        _step(
            "step_1_activity_components",
            "recorded" if activity_n or novelty_n else "empty_components",
            notes="Bedau/MODES presence sets when a Phase D pack is supplied.",
            metric_count=activity_n + novelty_n,
        ),
        _step(
            "step_2_evolutionary_activity",
            "recorded" if activity_observed else "no_positive_activity_metric",
            notes="Bedau activity/diversity/cumulative series.",
            metric_count=activity_n,
        ),
        _step(
            "step_3_adaptive_novelty",
            "recorded" if novelty_observed else "no_positive_novelty_metric",
            notes=f"Persistence-filtered novelty; persistence_window_t={resolved_window}.",
            metric_count=novelty_n,
        ),
        _step(
            "step_4_shadow_normalization",
            shadow_status,
            notes="Shadow hook only; Empirical systematics shadow run is not performed.",
            shadow_digest=shadow,
        ),
        _step(
            "step_5_multi_seed_aggregation",
            multi_seed_step_status,
            notes=f"seed_count={seed_count}; above measurement_only requires >= 2 seeds.",
            metric_count=seed_count,
        ),
        _step(
            "step_6_claim_gate",
            "ceiling_tokyo_type1_measurement_only",
            notes="tokyo_type1_passed remains blocked.",
        ),
    )
    return TokyoType1MeasurementProtocol(
        steps=steps,
        seed_count=seed_count,
        persistence_window_t=resolved_window,
        activity_observed=activity_observed,
        novelty_observed=novelty_observed,
        shadow_normalization_status=shadow_status,
        shadow_digest=shadow,
        empirical_systematics_shadow_run=False,
        source_pack_digest=source_digest,
        measurement_status=measurement_status,
    )


def tokyo_type1_claim_request(protocol: TokyoType1MeasurementProtocol) -> ClaimRequest:
    """Build the measurement-only ClaimGate request. Never requests a pass."""

    flags = {
        "channon_2024_steps_recorded": bool(protocol.steps),
        "oee_metrics": True,
        "tokyo_type1_protocol": True,
        "multi_seed_protocol": protocol.seed_count >= 2,
        "shadow_run_present": bool(protocol.shadow_digest),
        "persistence_window_observed": protocol.persistence_window_t >= 1,
    }
    return ClaimRequest(
        _MEASUREMENT_CEILING,
        flags,
        evidence_digests=(protocol.digest,),
    )


def evaluate_tokyo_type1_measurement_claim(
    protocol: TokyoType1MeasurementProtocol | object,
    gate: ScientificClaimGate | None = None,
) -> ClaimDecision:
    """Allow protocol ``tokyo_type1_measurement_only``; pack path aliases to OEE.

    ``TokyoType1MeasurementProtocol`` keeps the Channon-step measurement ceiling.
    A Phase D evidence pack uses the cheap vocabulary hook and aliases to
    ``oee_measurement_only``. ``tokyo_type1_passed`` is rejected either way.
    """

    if not isinstance(protocol, TokyoType1MeasurementProtocol):
        from codontrace.genesis.multi_generation import (
            evaluate_tokyo_type1_measurement_claim as evaluate_pack_claim,
        )

        return evaluate_pack_claim(protocol, gate=gate)

    resolved = gate or ScientificClaimGate()
    decision = resolved.decide(tokyo_type1_claim_request(protocol))
    blocked = resolved.decide(ClaimRequest(_PASSED_CLAIM, {}, evidence_digests=(protocol.digest,)))
    if blocked.allowed:
        raise ConfigurationError("tokyo_type1_passed must remain blocked.")
    if decision.final_claim == _PASSED_CLAIM:
        raise ConfigurationError("Tokyo Type 1 measurement claim must not upgrade to passed.")
    return decision


def evaluate_tokyo_type1_pass_claim(
    protocol: TokyoType1MeasurementProtocol | None = None,
    gate: ScientificClaimGate | None = None,
) -> ClaimDecision:
    """Explicit blocked path: Tokyo Type 1 pass is never allowed."""

    digests = (protocol.digest,) if protocol is not None else ()
    return (gate or ScientificClaimGate()).decide(
        ClaimRequest(_PASSED_CLAIM, {}, evidence_digests=digests)
    )
