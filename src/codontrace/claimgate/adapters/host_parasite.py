"""Host–parasite / microbe–virus port: a DomainProfile, not a second engine.

This adapter is claim-labeling only. It does not implement infection physics,
does not certify vaccines, antivirals, phage therapy, epidemic forecasts, or
biosafety levels, and must not be read as a clinical pathogen model.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from codontrace.genesis.host_parasite_campaign import HostParasiteCampaignResult
    from codontrace.genesis.host_parasite_continuum import ContinuumFactorialResult
    from codontrace.genesis.host_parasite_cornish import CornishCampaignResult
    from codontrace.genesis.host_parasite_diagnostics import CoevolutionDiagnostics
    from codontrace.genesis.host_parasite_env import HostParasiteEnv
    from codontrace.genesis.host_parasite_evolvability import (
        EvolvabilityFalsificationResult,
    )
    from codontrace.genesis.host_parasite_zaman import ZamanCampaignResult

from codontrace._types import JsonValue
from codontrace.claimgate.domain import HOST_PARASITE, bundle_from_declared_scores
from codontrace.claimgate.schema import ClaimgateBundle
from codontrace.errors import ConfigurationError

BLOCKED_HOST_PARASITE_CLAIMS = HOST_PARASITE.blocked_claims

# Declared COU / risk label vocabulary (labels only; not clearance).
COU_RISK_LABELS = frozenset(
    {
        "asme_vv40",
        "fda_2023",
        "certification",
        "infection_physics",
        "clinical_scope",
        "engine",
    }
)

# Intervention kinds allowed on the declared menu stub (digital falsification
# planning only). Not an executed campaign and not a clinical protocol.
DECLARED_INTERVENTION_KINDS = frozenset(
    {
        "remove_parasites",
        "freeze_host_evolution",
        "break_spatial_structure",
        "content_null_payload",
        "structure_null_overlap",
        "abiotic_only_arm",
        "steal_fraction_ablation",
        "transmission_mode_switch",
    }
)

_MENU_NOTE = "Declared intervention menu does not raise the claim ladder."


def assert_claim_allowed(claimed: str) -> str:
    """Fail closed if ``claimed`` is blocked on the host_parasite profile.

    Returns the normalized claim string. Does not grant evidence or run the
    engine.
    """

    if not isinstance(claimed, str) or not claimed.strip():
        raise ConfigurationError("claimed must be a non-empty string.")
    claim = claimed.strip().lower()
    if claim in HOST_PARASITE.blocked_claims:
        raise ConfigurationError(
            f"{claimed!r} is blocked on domain profile {HOST_PARASITE.name!r}."
        )
    return claim


def declared_cou_risk_labels(
    *,
    asme_vv40: str | None = None,
    fda_2023: str | None = None,
    certification: str | None = None,
    infection_physics: str | None = None,
    clinical_scope: str | None = None,
) -> dict[str, str]:
    """Return declared COU/risk labels merged with profile defaults.

    Callers may override only with the same conservative vocabulary already
    used by the profile. Overrides cannot invent clearance language.
    """

    defaults = dict(HOST_PARASITE.extra_defaults)
    overrides: dict[str, str | None] = {
        "asme_vv40": asme_vv40,
        "fda_2023": fda_2023,
        "certification": certification,
        "infection_physics": infection_physics,
        "clinical_scope": clinical_scope,
    }
    allowed_values = {
        "asme_vv40": frozenset({"complement_only"}),
        "fda_2023": frozenset({"declared_labels_only"}),
        "certification": frozenset({"none"}),
        "infection_physics": frozenset({"not_implemented", "optional_env_outside_core"}),
        "clinical_scope": frozenset({"blocked"}),
    }
    out: dict[str, str] = {
        key: str(defaults[key]) for key in COU_RISK_LABELS if key in defaults
    }
    for key, raw in overrides.items():
        if raw is None:
            continue
        if not isinstance(raw, str) or not raw.strip():
            raise ConfigurationError(f"{key} override must be a non-empty string.")
        value = raw.strip().lower()
        if value not in allowed_values[key]:
            raise ConfigurationError(
                f"{key} must stay in {sorted(allowed_values[key])}; got {raw!r}."
            )
        out[key] = value
    return out


@dataclass(frozen=True, slots=True)
class DeclaredIntervention:
    """One declared falsification hook. Declaration is not execution."""

    intervention_id: str
    kind: str
    description: str
    expected_digital_effect: str

    def to_dict(self) -> dict[str, object]:
        return {
            "intervention_id": self.intervention_id,
            "kind": self.kind,
            "description": self.description,
            "expected_digital_effect": self.expected_digital_effect,
            "executed": False,
            "raises_claim_ladder": False,
        }


@dataclass(frozen=True, slots=True)
class DeclaredInterventionMenu:
    """Schema stub for later intervention falsification (Cornish-style).

    Recording a menu does not run interventions, grant evidence, or raise the
    public ClaimGate ladder.
    """

    question_of_interest: str
    context_of_use: str
    interventions: tuple[DeclaredIntervention, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "host_parasite_declared_intervention_menu_v1",
            "question_of_interest": self.question_of_interest,
            "context_of_use": self.context_of_use,
            "interventions": [item.to_dict() for item in self.interventions],
            "executed": False,
            "raises_claim_ladder": False,
            "source": "declared_menu_stub_not_a_campaign",
        }


def _text_required(raw: object, field: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ConfigurationError(f"{field} is required.")
    return raw.strip()


def declared_intervention_menu(
    *,
    question_of_interest: str,
    context_of_use: str,
    interventions: Sequence[Mapping[str, object]],
) -> DeclaredInterventionMenu:
    """Validate and freeze a declared intervention menu schema stub.

    Empty menus are rejected: a COU that promises falsification must name at
    least one digital hook. Intervention ids must be unique and must not reuse
    blocked clinical claim aliases.
    """

    qoi = _text_required(question_of_interest, "question_of_interest")
    cou = _text_required(context_of_use, "context_of_use")
    if not interventions:
        raise ConfigurationError("declared intervention menu needs at least one row.")
    seen: set[str] = set()
    rows: list[DeclaredIntervention] = []
    for index, raw in enumerate(interventions):
        if not isinstance(raw, Mapping):
            raise ConfigurationError(f"interventions[{index}] must be a mapping.")
        iid = _text_required(raw.get("intervention_id"), f"interventions[{index}].intervention_id")
        iid_key = iid.lower()
        if iid_key in seen:
            raise ConfigurationError(f"duplicate intervention_id {iid!r}.")
        if iid_key in HOST_PARASITE.blocked_claims:
            raise ConfigurationError(
                f"intervention_id {iid!r} collides with a blocked host_parasite claim."
            )
        seen.add(iid_key)
        kind_raw = raw.get("kind")
        if not isinstance(kind_raw, str) or not kind_raw.strip():
            raise ConfigurationError(f"interventions[{index}].kind is required.")
        kind = kind_raw.strip().lower()
        if kind not in DECLARED_INTERVENTION_KINDS:
            raise ConfigurationError(
                f"interventions[{index}].kind must be one of "
                f"{sorted(DECLARED_INTERVENTION_KINDS)}; got {kind_raw!r}."
            )
        description = _text_required(
            raw.get("description"), f"interventions[{index}].description"
        )
        effect = _text_required(
            raw.get("expected_digital_effect"),
            f"interventions[{index}].expected_digital_effect",
        )
        rows.append(
            DeclaredIntervention(
                intervention_id=iid,
                kind=kind,
                description=description,
                expected_digital_effect=effect,
            )
        )
    return DeclaredInterventionMenu(qoi, cou, tuple(rows))


def attach_declared_intervention_menu(
    bundle: ClaimgateBundle,
    *,
    interventions: Sequence[Mapping[str, object]],
    question_of_interest: str | None = None,
    context_of_use: str | None = None,
) -> ClaimgateBundle:
    """Store a declared menu on the bundle. Public ladder stays unchanged."""

    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_declared_intervention_menu requires a host_parasite domain bundle."
        )
    if "declared_intervention_menu" in extra:
        raise ConfigurationError(
            "declared_intervention_menu is already attached; refuse silent overwrite."
        )
    qoi = question_of_interest or str(extra.get("question_of_interest") or "")
    cou = context_of_use or str(extra.get("context_of_use") or "")
    menu = declared_intervention_menu(
        question_of_interest=qoi,
        context_of_use=cou,
        interventions=interventions,
    )
    extra["declared_intervention_menu"] = cast(JsonValue, menu.to_dict())
    limitations = bundle.limitations
    if _MENU_NOTE not in limitations:
        limitations = limitations + (_MENU_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


def bundle_from_host_parasite_cou(
    *,
    question_of_interest: str,
    context_of_use: str,
    model_influence: int,
    decision_consequence: int,
    treatment_scores: Sequence[float],
    control_scores: Sequence[float],
    metric: str = "declared_score",
    software_name: str = "external-host-parasite-table",
    software_version: str = "unspecified",
    claimed: str = "runtime_observation",
    device_software_kind: str = "analog_table",
    iec_62304_class: str = "undeclared",
    imdrf_n12_category: str = "undeclared",
    fda_2023_evidence: Sequence[int] = (),
    physics_based: bool = False,
    cou_risk_overrides: Mapping[str, str] | None = None,
) -> ClaimgateBundle:
    """Wrap declared digital coevolution scores under the host_parasite profile.

    Engine ticks are not invoked. Infection / transmission physics are not
    implemented. Clinical and therapy claims stay blocked.
    """

    assert_claim_allowed(claimed)
    overrides = dict(cou_risk_overrides or {})
    allowed_override_keys = frozenset(
        {
            "asme_vv40",
            "fda_2023",
            "certification",
            "infection_physics",
            "clinical_scope",
        }
    )
    unknown = sorted(set(overrides) - allowed_override_keys)
    if unknown:
        raise ConfigurationError(
            f"cou_risk_overrides has unknown keys: {unknown}."
        )
    labels = declared_cou_risk_labels(
        asme_vv40=overrides.get("asme_vv40"),
        fda_2023=overrides.get("fda_2023"),
        certification=overrides.get("certification"),
        infection_physics=overrides.get("infection_physics"),
        clinical_scope=overrides.get("clinical_scope"),
    )
    bundle = bundle_from_declared_scores(
        profile=HOST_PARASITE,
        question_of_interest=question_of_interest,
        context_of_use=context_of_use,
        model_influence=model_influence,
        decision_consequence=decision_consequence,
        treatment_scores=treatment_scores,
        control_scores=control_scores,
        metric=metric,
        software_name=software_name,
        software_version=software_version,
        claimed=claimed,
        device_software_kind=device_software_kind,
        iec_62304_class=iec_62304_class,
        imdrf_n12_category=imdrf_n12_category,
        fda_2023_evidence=fda_2023_evidence,
        physics_based=physics_based,
    )
    # Profile defaults already land via bundle_from_declared_scores; re-apply
    # validated overrides so optional_env_outside_core can be declared later.
    extra = dict(bundle.extra or {})
    extra.update(labels)
    return replace(bundle, extra=extra)


# ---------------------------------------------------------------------------
# Phase 3 — intervention falsification, multilevel gate, ARD/FSD labels
# ---------------------------------------------------------------------------

_TRANSITION_BLOCKED = frozenset(
    {
        "major_transition_proved",
        "transition_to_individuality_proved",
        "fitness_reorganization_proved",
    }
)

_DYNAMICS_LABELS = frozenset({"undeclared", "ard_candidate", "fsd_candidate", "ard_fsd_mixed_candidate"})
_WORKSHEET_NOTE_HP = "Multilevel worksheet does not raise the claim ladder."
_FALSIFICATION_NOTE = "Digital intervention falsification does not grant intervention_supported by itself."


@dataclass(frozen=True, slots=True)
class MultilevelTransitionWorksheet:
    """Gate for transition-language honesty (Michod / Okasha caution).

    A typed reorganization sketch cannot prove a major transition. Open gaps
    keep `major_transition_proved` and kin blocked. The worksheet never raises
    the public ClaimGate ladder.
    """

    open_gaps: tuple[str, ...]
    readiness_documented: bool
    limiting_note: str

    @property
    def transition_claim_allowed(self) -> bool:
        """Always False: readiness never unlocks transition claim language."""

        return False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "host_parasite_multilevel_worksheet_v1",
            "open_gaps": list(self.open_gaps),
            "readiness_documented": self.readiness_documented,
            "transition_claim_allowed": False,
            "limiting_note": self.limiting_note,
            "raises_claim_ladder": False,
            "sources": ["michod_nedelcu_2003", "okasha_multilevel_2022", "okasha_otsuka_2020"],
        }


def multilevel_transition_worksheet(
    *,
    within_host_conflict_measured: bool = False,
    between_host_export_measured: bool = False,
    fitness_reorganization_documented: bool = False,
    price_partition_only: bool = True,
    requested_transition_claim: str = "",
) -> MultilevelTransitionWorksheet:
    """Build a multilevel gate. Price-only summaries keep transitions blocked."""

    gaps: list[str] = []
    if not within_host_conflict_measured:
        gaps.append("within_host_conflict_unmeasured")
    if not between_host_export_measured:
        gaps.append("between_host_export_unmeasured")
    if not fitness_reorganization_documented:
        gaps.append("fitness_reorganization_undocumented")
    if price_partition_only:
        gaps.append("price_partition_is_not_causal")
    claim = requested_transition_claim.strip().lower()
    transition_aliases = _TRANSITION_BLOCKED | {
        "major_transition",
        "fitness_reorganization",
        "transition_to_individuality",
    } | set(HOST_PARASITE.blocked_claims)
    if claim and claim in transition_aliases:
        gaps.append(f"blocked_claim:{claim}")
    ready = not gaps
    note = (
        "Multilevel readiness documented; transition claim language still blocked."
        if ready
        else "Transition strings stay blocked while multilevel gaps remain open."
    )
    return MultilevelTransitionWorksheet(tuple(gaps), ready, note)


def assert_transition_claim_allowed(
    claimed: str,
    worksheet: MultilevelTransitionWorksheet,
) -> str:
    """Fail closed on transition strings.

    The worksheet documents multilevel readiness. It does **not** unlock
    transition claim language. Only ordinary digital claims such as
    ``runtime_observation`` may pass.
    """

    claim = assert_claim_allowed(claimed)
    transition_aliases = _TRANSITION_BLOCKED | {
        "major_transition",
        "fitness_reorganization",
        "transition_to_individuality",
    }
    if claim in transition_aliases:
        raise ConfigurationError(
            f"{claimed!r} stays blocked; multilevel worksheet gaps="
            f"{list(worksheet.open_gaps)} readiness="
            f"{worksheet.transition_claim_allowed}."
        )
    if not worksheet.transition_claim_allowed and claim not in {
        "runtime_observation",
        "declared_score",
    }:
        # Non-transition claims still ok; worksheet gaps do not block ordinary labels.
        pass
    return claim


@dataclass(frozen=True, slots=True)
class DynamicsLabels:
    """Optional ARD / FSD candidate labels without proving Red Queen."""

    label: str
    red_queen_proved: bool
    note: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": "host_parasite_dynamics_labels_v1",
            "label": self.label,
            "red_queen_proved": self.red_queen_proved,
            "note": self.note,
            "raises_claim_ladder": False,
        }


def declared_dynamics_labels(label: str = "undeclared") -> DynamicsLabels:
    """Declare ARD/FSD candidate language. Never sets red_queen_proved."""

    if not isinstance(label, str) or not label.strip():
        raise ConfigurationError("dynamics label must be a non-empty string.")
    key = label.strip().lower()
    if key not in _DYNAMICS_LABELS:
        raise ConfigurationError(
            f"dynamics label must be one of {sorted(_DYNAMICS_LABELS)}; got {label!r}."
        )
    if key == "undeclared":
        note = "No ARD/FSD candidate declared."
    else:
        note = (
            f"{key} is a digital candidate label only; Red Queen dynamics are not proved."
        )
    return DynamicsLabels(key, False, note)


@dataclass(frozen=True, slots=True)
class InterventionFalsificationResult:
    """Digital falsification report. Does not grant intervention_supported."""

    intervention_id: str
    kind: str
    passed: bool
    control_score: float
    intervention_score: float
    score_delta: float
    reason: str
    claim_ceiling: str

    def to_dict(self) -> dict[str, object]:
        return {
            "intervention_id": self.intervention_id,
            "kind": self.kind,
            "passed": self.passed,
            "control_score": self.control_score,
            "intervention_score": self.intervention_score,
            "score_delta": self.score_delta,
            "reason": self.reason,
            "claim_ceiling": self.claim_ceiling,
            "grants_intervention_supported": False,
            "raises_claim_ladder": False,
        }


def _env_pair(
    *,
    host_tasks: Sequence[str],
    parasite_tasks: Sequence[str],
    payload: Sequence[int],
    steal_fraction: float,
    null_kind: str,
) -> HostParasiteEnv:
    from codontrace.genesis.host_parasite_env import HostParasiteEnv, dual_null_template

    env = HostParasiteEnv(
        steal_fraction=steal_fraction,
        null_template=dual_null_template(null_kind),
    )
    env.add_host("H0", host_tasks)
    env.try_horizontal_inject(
        host_id="H0",
        parasite_id="P0",
        parasite_tasks=parasite_tasks,
        payload=payload,
    )
    return env


def run_intervention_falsification(
    *,
    kind: str,
    host_tasks: Sequence[str],
    parasite_tasks: Sequence[str],
    payload: Sequence[int] = (1, 2, 3),
    steal_fraction: float = 0.8,
    intervention_id: str = "I_auto",
    expected_direction: str = "intervention_score_ge_control",
) -> InterventionFalsificationResult:
    """Execute one digital falsification hook against HostParasiteEnv.

    Control = intact infection. Intervention arms:

    - ``remove_parasites``: no inject attempted (abiotic host only)
    - ``content_null_payload``: content-null template
    - ``structure_null_overlap``: structure-null template
    - ``steal_fraction_ablation``: steal_fraction forced to 0
    - ``abiotic_only_arm``: alias of remove_parasites

    A pass means the digital score moved in the expected direction. This never
    sets claim ceiling above ``runtime_observation`` and never grants
    ``intervention_supported``.
    """

    if not isinstance(kind, str) or not kind.strip():
        raise ConfigurationError("falsification kind is required.")
    key = kind.strip().lower()
    allowed = frozenset(
        {
            "remove_parasites",
            "content_null_payload",
            "structure_null_overlap",
            "steal_fraction_ablation",
            "abiotic_only_arm",
        }
    )
    if key not in allowed:
        raise ConfigurationError(
            f"falsification kind must be one of {sorted(allowed)}; got {kind!r}."
        )
    if expected_direction not in {
        "intervention_score_ge_control",
        "intervention_score_le_control",
        "scores_differ",
    }:
        raise ConfigurationError("unsupported expected_direction.")

    from codontrace.genesis.host_parasite_env import HostParasiteEnv

    probe = HostParasiteEnv(steal_fraction=steal_fraction)
    eligible, _overlap = probe.infection_eligible(host_tasks, parasite_tasks)
    if not eligible:
        raise ConfigurationError(
            "run_intervention_falsification requires task overlap so the control arm can infect."
        )

    control = _env_pair(
        host_tasks=host_tasks,
        parasite_tasks=parasite_tasks,
        payload=payload,
        steal_fraction=steal_fraction,
        null_kind="none",
    )
    control_score = control.population_outcome_score()

    if key in {"remove_parasites", "abiotic_only_arm"}:
        from codontrace.genesis.host_parasite_env import HostParasiteEnv

        intervened = HostParasiteEnv(steal_fraction=steal_fraction)
        intervened.add_host("H0", host_tasks)
        # No parasite inject — remove-parasites / abiotic-only arm.
        intervention_score = intervened.population_outcome_score()
        reason = "parasites_absent"
    elif key == "content_null_payload":
        intervened = _env_pair(
            host_tasks=host_tasks,
            parasite_tasks=parasite_tasks,
            payload=payload,
            steal_fraction=steal_fraction,
            null_kind="content_null",
        )
        intervention_score = intervened.population_outcome_score()
        reason = "content_null_applied"
    elif key == "structure_null_overlap":
        intervened = _env_pair(
            host_tasks=host_tasks,
            parasite_tasks=parasite_tasks,
            payload=payload,
            steal_fraction=steal_fraction,
            null_kind="structure_null",
        )
        intervention_score = intervened.population_outcome_score()
        reason = "structure_null_applied"
    else:  # steal_fraction_ablation
        intervened = _env_pair(
            host_tasks=host_tasks,
            parasite_tasks=parasite_tasks,
            payload=payload,
            steal_fraction=0.0,
            null_kind="none",
        )
        intervention_score = intervened.population_outcome_score()
        reason = "steal_fraction_zeroed"

    delta = round(intervention_score - control_score, 10)
    if expected_direction == "intervention_score_ge_control":
        passed = intervention_score >= control_score and delta != 0.0
    elif expected_direction == "intervention_score_le_control":
        passed = intervention_score <= control_score and delta != 0.0
    else:
        passed = delta != 0.0
    if not passed and delta == 0.0:
        reason = f"{reason};assay_invalid_no_score_change"
    return InterventionFalsificationResult(
        intervention_id=intervention_id,
        kind=key,
        passed=passed,
        control_score=control_score,
        intervention_score=intervention_score,
        score_delta=delta,
        reason=reason,
        claim_ceiling="runtime_observation",
    )


def attach_phase3_honesty(
    bundle: ClaimgateBundle,
    *,
    falsification: InterventionFalsificationResult | None = None,
    worksheet: MultilevelTransitionWorksheet | None = None,
    dynamics: DynamicsLabels | None = None,
) -> ClaimgateBundle:
    """Attach Phase 3 honesty records without raising the public ladder."""

    if falsification is None and worksheet is None and dynamics is None:
        raise ConfigurationError(
            "attach_phase3_honesty requires falsification, worksheet, or dynamics."
        )
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_phase3_honesty requires a host_parasite domain bundle."
        )
    limitations = bundle.limitations
    if falsification is not None:
        if "intervention_falsification" in extra:
            raise ConfigurationError("intervention_falsification already attached.")
        extra["intervention_falsification"] = cast(JsonValue, falsification.to_dict())
        if _FALSIFICATION_NOTE not in limitations:
            limitations = limitations + (_FALSIFICATION_NOTE,)
    if worksheet is not None:
        if "multilevel_transition_worksheet" in extra:
            raise ConfigurationError("multilevel_transition_worksheet already attached.")
        extra["multilevel_transition_worksheet"] = cast(JsonValue, worksheet.to_dict())
        if _WORKSHEET_NOTE_HP not in limitations:
            limitations = limitations + (_WORKSHEET_NOTE_HP,)
    if dynamics is not None:
        if "dynamics_labels" in extra:
            raise ConfigurationError("dynamics_labels already attached.")
        if dynamics.red_queen_proved:
            raise ConfigurationError("dynamics_labels cannot claim red_queen_proved.")
        extra["dynamics_labels"] = cast(JsonValue, dynamics.to_dict())
    return replace(bundle, extra=extra, limitations=limitations)


# ---------------------------------------------------------------------------
# Phase 4 — campaign digests + fail-closed ClaimGate bundle factory
# ---------------------------------------------------------------------------

_CAMPAIGN_NOTE = (
    "Host–parasite campaign digests do not raise the public ClaimGate ladder "
    "above the campaign claim_ceiling."
)
_ALLOWED_CAMPAIGN_CEILINGS = frozenset({"runtime_observation", "candidate_evidence"})


def _campaign_scores(
    campaign: HostParasiteCampaignResult,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Derive treatment/control score vectors from campaign arm means."""

    by_arm = {item.arm: item.mean_score for item in campaign.arm_results}
    if "intact" not in by_arm:
        raise ConfigurationError(
            "bundle_from_host_parasite_campaign requires an intact arm."
        )
    treatment = tuple(
        float(outcome.mean_retained_cpu)
        for arm in campaign.arm_results
        if arm.arm == "intact"
        for outcome in arm.seed_outcomes
    )
    control_arm = None
    for name in ("abiotic_only", "dual_null", "content_null", "structure_null"):
        if name in by_arm:
            control_arm = name
            break
    if control_arm is None:
        raise ConfigurationError(
            "bundle_from_host_parasite_campaign needs an abiotic or null control arm."
        )
    control = tuple(
        float(outcome.mean_retained_cpu)
        for arm in campaign.arm_results
        if arm.arm == control_arm
        for outcome in arm.seed_outcomes
    )
    if not treatment or not control:
        raise ConfigurationError("campaign score vectors must be non-empty.")
    return treatment, control


def bundle_from_host_parasite_campaign(
    campaign: HostParasiteCampaignResult,
    *,
    question_of_interest: str,
    context_of_use: str,
    model_influence: int = 2,
    decision_consequence: int = 2,
    claimed: str = "runtime_observation",
    software_name: str = "codontrace-host-parasite-campaign",
    software_version: str = "host_parasite_campaign_v1",
) -> ClaimgateBundle:
    """Build a ClaimGate bundle from a HostParasiteCampaignResult.

    Attaches per-arm and campaign digests. Refuses public claim strings above
    ``candidate_evidence``. ``candidate_evidence`` requires
    ``falsification_rules_passed`` on the campaign. The factory never sets
    ``red_queen_proved`` and never grants ``intervention_supported``.
    """

    from codontrace.genesis.host_parasite_campaign import HostParasiteCampaignResult

    if not isinstance(campaign, HostParasiteCampaignResult):
        raise ConfigurationError(
            "campaign must be a HostParasiteCampaignResult from "
            "run_host_parasite_campaign."
        )
    claim = assert_claim_allowed(claimed)
    if claim not in _ALLOWED_CAMPAIGN_CEILINGS:
        raise ConfigurationError(
            f"campaign bundle refuses claim ceilings above candidate_evidence; "
            f"got {claimed!r}."
        )
    if claim == "candidate_evidence" and not campaign.falsification_rules_passed:
        raise ConfigurationError(
            "candidate_evidence refused without passing campaign falsification rules."
        )
    if claim == "candidate_evidence" and campaign.claim_ceiling != "candidate_evidence":
        raise ConfigurationError(
            "candidate_evidence refused: campaign claim_ceiling is "
            f"{campaign.claim_ceiling!r}."
        )
    if campaign.red_queen_proved:
        raise ConfigurationError("campaign.red_queen_proved must remain False.")

    treatment, control = _campaign_scores(campaign)
    bundle = bundle_from_host_parasite_cou(
        question_of_interest=question_of_interest,
        context_of_use=context_of_use,
        model_influence=model_influence,
        decision_consequence=decision_consequence,
        treatment_scores=treatment,
        control_scores=control,
        metric="host_parasite_campaign_mean_retained_cpu",
        software_name=software_name,
        software_version=software_version,
        claimed=claim,
        device_software_kind="analog_table",
        cou_risk_overrides={"infection_physics": "optional_env_outside_core"},
    )
    payload = campaign.to_dict()
    extra = dict(bundle.extra or {})
    if "host_parasite_campaign" in extra:
        raise ConfigurationError("host_parasite_campaign already attached.")
    extra["host_parasite_campaign"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "arm_digests": payload["arm_digests"],
            "seeds": payload["seeds"],
            "arms": payload["arms"],
            "falsification_rules_passed": payload["falsification_rules_passed"],
            "claim_ceiling": payload["claim_ceiling"],
            "red_queen_proved": False,
            "grants_intervention_supported": False,
            "raises_claim_ladder": False,
        },
    )
    limitations = bundle.limitations
    if _CAMPAIGN_NOTE not in limitations:
        limitations = limitations + (_CAMPAIGN_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


def attach_host_parasite_campaign(
    bundle: ClaimgateBundle,
    campaign: HostParasiteCampaignResult,
) -> ClaimgateBundle:
    """Attach campaign digests to an existing host_parasite bundle.

    Does not raise the public ladder. Refuses attach when the bundle's claimed
    level is above the campaign ceiling or when falsification is required but
    missing.
    """

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_campaign import HostParasiteCampaignResult

    if not isinstance(campaign, HostParasiteCampaignResult):
        raise ConfigurationError(
            "campaign must be a HostParasiteCampaignResult."
        )
    require_preregistration_before_campaign_attach(bundle)
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_host_parasite_campaign requires a host_parasite domain bundle."
        )
    if "host_parasite_campaign" in extra:
        raise ConfigurationError("host_parasite_campaign already attached.")
    if campaign.red_queen_proved:
        raise ConfigurationError("campaign.red_queen_proved must remain False.")
    raw_claimed = extra.get("requested_claim")
    if not isinstance(raw_claimed, str) or not raw_claimed.strip():
        raise ConfigurationError(
            "attach_host_parasite_campaign requires bundle.extra['requested_claim']."
        )
    payload_claimed = raw_claimed.strip().lower()
    if payload_claimed not in _ALLOWED_CAMPAIGN_CEILINGS:
        raise ConfigurationError(
            "attach refuses ceilings above candidate_evidence; bundle requested_claim "
            f"{raw_claimed!r}."
        )
    if (
        payload_claimed == "candidate_evidence"
        and not campaign.falsification_rules_passed
    ):
        raise ConfigurationError(
            "attach refuses candidate_evidence without falsification_rules_passed."
        )
    if (
        payload_claimed == "candidate_evidence"
        and campaign.claim_ceiling != "candidate_evidence"
    ):
        raise ConfigurationError(
            "attach refuses candidate_evidence when campaign claim_ceiling is "
            f"{campaign.claim_ceiling!r}."
        )
    payload = campaign.to_dict()
    extra["host_parasite_campaign"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "arm_digests": payload["arm_digests"],
            "seeds": payload["seeds"],
            "arms": payload["arms"],
            "falsification_rules_passed": payload["falsification_rules_passed"],
            "claim_ceiling": payload["claim_ceiling"],
            "red_queen_proved": False,
            "grants_intervention_supported": False,
            "raises_claim_ladder": False,
        },
    )
    limitations = bundle.limitations
    if _CAMPAIGN_NOTE not in limitations:
        limitations = limitations + (_CAMPAIGN_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


# ---------------------------------------------------------------------------
# Phase 5 — coevolution range diagnostics (ARD/FSD-like labels only)
# ---------------------------------------------------------------------------

_DIAGNOSTICS_NOTE = (
    "Coevolution range diagnostics are digital ARD/FSD-like labels only; "
    "Red Queen dynamics are not proved."
)


def attach_coevolution_diagnostics(
    bundle: ClaimgateBundle,
    diagnostics: CoevolutionDiagnostics,
) -> ClaimgateBundle:
    """Attach ARD/FSD-like diagnostics without raising the public ladder."""

    from codontrace.genesis.host_parasite_diagnostics import CoevolutionDiagnostics

    if not isinstance(diagnostics, CoevolutionDiagnostics):
        raise ConfigurationError(
            "diagnostics must be a CoevolutionDiagnostics result."
        )
    if diagnostics.red_queen_proved:
        raise ConfigurationError("diagnostics.red_queen_proved must remain False.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_coevolution_diagnostics requires a host_parasite domain bundle."
        )
    if "coevolution_diagnostics" in extra:
        raise ConfigurationError("coevolution_diagnostics already attached.")
    extra["coevolution_diagnostics"] = cast(JsonValue, diagnostics.to_dict())
    limitations = bundle.limitations
    if _DIAGNOSTICS_NOTE not in limitations:
        limitations = limitations + (_DIAGNOSTICS_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


# ---------------------------------------------------------------------------
# Phase 7 — Zaman freeze / replay / reciprocal attach (complexity unproved)
# ---------------------------------------------------------------------------

_ZAMAN_NOTE = (
    "Zaman three-arm digests are digital freeze/replay/reciprocal analogues only; "
    "complexity emergence and Red Queen dynamics are not proved."
)


def attach_zaman_campaign(
    bundle: ClaimgateBundle,
    campaign: ZamanCampaignResult,
) -> ClaimgateBundle:
    """Attach Zaman three-arm digests without raising the public ladder."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_zaman import ZamanCampaignResult

    if not isinstance(campaign, ZamanCampaignResult):
        raise ConfigurationError("campaign must be a ZamanCampaignResult.")
    require_preregistration_before_campaign_attach(bundle)
    if campaign.complexity_emergence_proved:
        raise ConfigurationError("campaign.complexity_emergence_proved must remain False.")
    if campaign.red_queen_proved:
        raise ConfigurationError("campaign.red_queen_proved must remain False.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_zaman_campaign requires a host_parasite domain bundle."
        )
    if "zaman_three_arm_campaign" in extra:
        raise ConfigurationError("zaman_three_arm_campaign already attached.")
    payload = campaign.to_dict()
    extra["zaman_three_arm_campaign"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "arm_digests": payload["arm_digests"],
            "seeds": payload["seeds"],
            "arms": payload["arms"],
            "steps": payload["steps"],
            "arms_are_distinct": payload["arms_are_distinct"],
            "claim_ceiling": payload["claim_ceiling"],
            "complexity_emergence_proved": False,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "zaman_scope": payload["zaman_scope"],
        },
    )
    limitations = bundle.limitations
    if _ZAMAN_NOTE not in limitations:
        limitations = limitations + (_ZAMAN_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


# ---------------------------------------------------------------------------
# Phase 8 — parasitism–mutualism continuum + VT × spatial factorial
# ---------------------------------------------------------------------------

_CONTINUUM_NOTE = (
    "Interaction continuum declares antagonism→mutualism digitally; "
    "mutualism is not success and does not raise the ClaimGate ladder."
)


def declare_interaction_continuum(
    *,
    interaction_value: float,
) -> dict[str, object]:
    """Declare continuum extras for ClaimGate. Mutualism ≠ success."""

    number = float(interaction_value)
    if number != number or number < -1.0 or number > 1.0:
        raise ConfigurationError("interaction_value must be in [-1, +1].")
    if number < -1e-12:
        pole = "antagonism"
    elif number > 1e-12:
        pole = "mutualism"
    else:
        pole = "neutral"
    return {
        "schema": "host_parasite_interaction_continuum_v1",
        "interaction_value": number,
        "pole": pole,
        "interaction_continuum": "antagonism_to_mutualism",
        "mutualism_equals_success": False,
        "raises_claim_ladder": False,
        "red_queen_proved": False,
        "blocked_claims_unchanged": True,
    }


def attach_interaction_continuum(
    bundle: ClaimgateBundle,
    *,
    interaction_value: float,
) -> ClaimgateBundle:
    """Attach continuum declaration without changing blocked claims."""

    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_interaction_continuum requires a host_parasite domain bundle."
        )
    if "interaction_continuum" in extra:
        raise ConfigurationError("interaction_continuum already attached.")
    record = declare_interaction_continuum(interaction_value=interaction_value)
    extra["interaction_continuum"] = cast(JsonValue, record)
    # Blocked claims must remain exactly the profile set.
    if set(HOST_PARASITE.blocked_claims) != set(BLOCKED_HOST_PARASITE_CLAIMS):
        raise ConfigurationError("blocked host_parasite claims drifted.")
    limitations = bundle.limitations
    if _CONTINUUM_NOTE not in limitations:
        limitations = limitations + (_CONTINUUM_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


def attach_vt_spatial_factorial(
    bundle: ClaimgateBundle,
    factorial: ContinuumFactorialResult,
) -> ClaimgateBundle:
    """Attach VT × spatial factorial digests; mutualism never equals success."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_continuum import ContinuumFactorialResult

    if not isinstance(factorial, ContinuumFactorialResult):
        raise ConfigurationError("factorial must be a ContinuumFactorialResult.")
    require_preregistration_before_campaign_attach(bundle)
    if factorial.mutualism_equals_success:
        raise ConfigurationError("mutualism_equals_success must remain False.")
    if factorial.red_queen_proved:
        raise ConfigurationError("factorial.red_queen_proved must remain False.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_vt_spatial_factorial requires a host_parasite domain bundle."
        )
    if "vt_spatial_factorial" in extra:
        raise ConfigurationError("vt_spatial_factorial already attached.")
    payload = factorial.to_dict()
    extra["vt_spatial_factorial"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "factorial_digest": payload["factorial_digest"],
            "cell_digests": payload["cell_digests"],
            "seeds": payload["seeds"],
            "vt_levels": payload["vt_levels"],
            "spatial_modes": payload["spatial_modes"],
            "interaction_value": payload["interaction_value"],
            "claim_ceiling": payload["claim_ceiling"],
            "mutualism_equals_success": False,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
        },
    )
    limitations = bundle.limitations
    if _CONTINUUM_NOTE not in limitations:
        limitations = limitations + (_CONTINUUM_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


# ---------------------------------------------------------------------------
# Phase 9 — evolvability falsification + Cornish refusal + HE_HP attach
# ---------------------------------------------------------------------------

_EVOLVABILITY_NOTE = (
    "Evolvability falsification can reject 'parasites always raise repertoire'; "
    "it does not prove Red Queen dynamics."
)
_CORNISH_NOTE = (
    "Observational match alone never grants intervention_supported (Cornish rule)."
)


def attach_evolvability_falsification(
    bundle: ClaimgateBundle,
    assay: EvolvabilityFalsificationResult,
) -> ClaimgateBundle:
    """Attach evolvability assay without raising the public ladder."""

    from codontrace.genesis.host_parasite_evolvability import (
        EvolvabilityFalsificationResult,
    )

    if not isinstance(assay, EvolvabilityFalsificationResult):
        raise ConfigurationError("assay must be an EvolvabilityFalsificationResult.")
    if assay.red_queen_proved:
        raise ConfigurationError("assay.red_queen_proved must remain False.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_evolvability_falsification requires a host_parasite domain bundle."
        )
    if "evolvability_falsification" in extra:
        raise ConfigurationError("evolvability_falsification already attached.")
    extra["evolvability_falsification"] = cast(JsonValue, assay.to_dict())
    limitations = bundle.limitations
    if _EVOLVABILITY_NOTE not in limitations:
        limitations = limitations + (_EVOLVABILITY_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


def attach_cornish_campaign(
    bundle: ClaimgateBundle,
    campaign: CornishCampaignResult,
) -> ClaimgateBundle:
    """Attach Cornish campaign; refuse intervention_supported from obs match."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_cornish import CornishCampaignResult

    if not isinstance(campaign, CornishCampaignResult):
        raise ConfigurationError("campaign must be a CornishCampaignResult.")
    require_preregistration_before_campaign_attach(bundle)
    if campaign.intervention_supported:
        raise ConfigurationError(
            "attach refuses intervention_supported=True on Cornish campaigns."
        )
    if campaign.observational_match and campaign.intervention_supported:
        raise ConfigurationError(
            "observational match alone must never grant intervention_supported."
        )
    if campaign.red_queen_proved:
        raise ConfigurationError("campaign.red_queen_proved must remain False.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_cornish_campaign requires a host_parasite domain bundle."
        )
    if "cornish_intervention_campaign" in extra:
        raise ConfigurationError("cornish_intervention_campaign already attached.")
    # Cross-check prereg digest is present on the bundle.
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_cornish_campaign requires preregistration digest on the bundle."
        )
    if str(prereg["digest"]).lower() != campaign.preregistration_digest.lower():
        raise ConfigurationError(
            "Cornish campaign preregistration_digest must match bundle prereg digest."
        )
    payload = campaign.to_dict()
    # Force honesty on the attached record.
    attached_record = {
        "schema": payload["schema"],
        "campaign_digest": payload["campaign_digest"],
        "arm_digests": payload["arm_digests"],
        "seeds": payload["seeds"],
        "observational_match": payload["observational_match"],
        "interventions_executed": payload["interventions_executed"],
        "intervention_supported": False,
        "claim_ceiling": payload["claim_ceiling"],
        "red_queen_proved": False,
        "raises_claim_ladder": False,
        "cornish_rule": payload["cornish_rule"],
        "preregistration_digest": payload["preregistration_digest"],
    }
    extra["cornish_intervention_campaign"] = cast(JsonValue, attached_record)
    limitations = bundle.limitations
    if _CORNISH_NOTE not in limitations:
        limitations = limitations + (_CORNISH_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)
