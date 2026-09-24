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
    from codontrace.genesis.host_parasite_genome_diversity import (
        GenomeDiversityCampaignResult,
    )
    from codontrace.genesis.host_parasite_genome_zaman import GenomeZamanCampaignResult
    from codontrace.genesis.host_parasite_hgt import HgtCampaignResult
    from codontrace.genesis.host_parasite_task_gene import TaskGeneMapResult
    from codontrace.genesis.host_parasite_mode_contrast import ModeContrastResult
    from codontrace.genesis.host_parasite_genome_factorial import GenomeFactorialResult
    from codontrace.genesis.host_parasite_virulence_quality import VirulenceQualityResult
    from codontrace.genesis.host_parasite_price_caution import PriceCautionResult
    from codontrace.genesis.host_parasite_attach_registry import JournalAttachRegistryPacket
    from codontrace.genesis.host_parasite_ard_fsd_transition import ArdFsdTransitionResult
    from codontrace.genesis.host_parasite_resource_dynamics import ResourceDynamicsResult
    from codontrace.genesis.host_parasite_contingency import ContingencyCampaignResult
    from codontrace.genesis.host_parasite_cornish_sequential import SequentialCornishResult
    from codontrace.genesis.host_parasite_mutator import MutatorCampaignResult
    from codontrace.genesis.host_parasite_wave6_smoke import Wave6JournalSmokeResult
    from codontrace.genesis.host_parasite_he_hp_refresh import HeHpLockedDigestRefreshNote
    from codontrace.genesis.host_parasite_entropy_contingency_bridge import (
        EntropyContingencyBridgeResult,
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
        "hgt_analogue_segment_copy",
        "hgt_analogue_noise_transfer",
        "intracellular_seat_constraint",
        "free_living_horizontal_inject",
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

# ---------------------------------------------------------------------------
# Phase 10 — genome-aware dual digests on Zaman arms
# ---------------------------------------------------------------------------

_GENOME_ZAMAN_NOTE = (
    "Genome-aware Zaman digests layer SemanticGenome digests on freeze/replay/"
    "reciprocal arms; complexity emergence and Red Queen remain unproved."
)


def attach_genome_zaman_campaign(
    bundle: ClaimgateBundle,
    campaign: GenomeZamanCampaignResult,
) -> ClaimgateBundle:
    """Attach genome Zaman digests without raising the public ladder."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_genome_zaman import GenomeZamanCampaignResult

    if not isinstance(campaign, GenomeZamanCampaignResult):
        raise ConfigurationError("campaign must be a GenomeZamanCampaignResult.")
    require_preregistration_before_campaign_attach(bundle)
    if campaign.complexity_emergence_proved:
        raise ConfigurationError("campaign.complexity_emergence_proved must remain False.")
    if campaign.red_queen_proved:
        raise ConfigurationError("campaign.red_queen_proved must remain False.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_genome_zaman_campaign requires a host_parasite domain bundle."
        )
    if "genome_zaman_campaign" in extra:
        raise ConfigurationError("genome_zaman_campaign already attached.")
    payload = campaign.to_dict()
    if payload.get("schema") != "host_parasite_genome_zaman_campaign_v1":
        raise ConfigurationError("genome Zaman campaign schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_genome_zaman_campaign requires preregistration digest on the bundle."
        )
    extra["genome_zaman_campaign"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "arm_digests": payload["arm_digests"],
            "seeds": payload["seeds"],
            "arms": payload["arms"],
            "steps": payload["steps"],
            "genome_length": payload["genome_length"],
            "arms_are_distinct": payload["arms_are_distinct"],
            "claim_ceiling": payload["claim_ceiling"],
            "complexity_emergence_proved": False,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "zaman_scope": payload["zaman_scope"],
            "repertoire_campaign_digest": payload["repertoire_campaign_digest"],
            "preregistration_digest": str(prereg["digest"]),
        },
    )
    limitations = bundle.limitations
    if _GENOME_ZAMAN_NOTE not in limitations:
        limitations = limitations + (_GENOME_ZAMAN_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)

# ---------------------------------------------------------------------------
# Phase 11 — codon-entropy / Hamming dual-null (HE02 honesty)
# ---------------------------------------------------------------------------

_GENOME_DIVERSITY_NOTE = (
    "Genome diversity dual-null can reject parasites_always_raise_codon_entropy; "
    "it does not prove Red Queen dynamics."
)


def attach_genome_diversity_campaign(
    bundle: ClaimgateBundle,
    campaign: GenomeDiversityCampaignResult,
) -> ClaimgateBundle:
    """Attach genotype diversity assay without raising the public ladder."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_genome_diversity import (
        GenomeDiversityCampaignResult,
    )

    if not isinstance(campaign, GenomeDiversityCampaignResult):
        raise ConfigurationError("campaign must be a GenomeDiversityCampaignResult.")
    require_preregistration_before_campaign_attach(bundle)
    if campaign.red_queen_proved:
        raise ConfigurationError("campaign.red_queen_proved must remain False.")
    if campaign.hypothesis_supported and not campaign.failure_reason:
        # Supported universal claim must not be attached as a falsification success.
        pass
    if (not campaign.hypothesis_supported) and not str(campaign.failure_reason).strip():
        raise ConfigurationError(
            "falsified diversity campaign requires a non-empty failure_reason."
        )
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_genome_diversity_campaign requires a host_parasite domain bundle."
        )
    if "genome_diversity_campaign" in extra:
        raise ConfigurationError("genome_diversity_campaign already attached.")
    payload = campaign.to_dict()
    if payload.get("schema") != "host_parasite_genome_diversity_campaign_v1":
        raise ConfigurationError("genome diversity campaign schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_genome_diversity_campaign requires preregistration digest on the bundle."
        )
    extra["genome_diversity_campaign"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "arm_digests": payload["arm_digests"],
            "seeds": payload["seeds"],
            "arms": payload["arms"],
            "hypothesis": payload["hypothesis"],
            "hypothesis_supported": payload["hypothesis_supported"],
            "failure_reason": payload["failure_reason"],
            "claim_ceiling": payload["claim_ceiling"],
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "preregistration_digest": str(prereg["digest"]),
            "he02_honesty": payload["he02_honesty"],
        },
    )
    limitations = bundle.limitations
    if _GENOME_DIVERSITY_NOTE not in limitations:
        limitations = limitations + (_GENOME_DIVERSITY_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)

# ---------------------------------------------------------------------------
# Phase 12 — HGT-analogue + intracellular / free-living pack
# ---------------------------------------------------------------------------

_HGT_NOTE = (
    "HGT-analogue and compartment arms are digital labels only; wet HGT, "
    "conjugation, and CRISPR spacer acquisition are not claimed."
)


def attach_hgt_compartment_campaign(
    bundle: ClaimgateBundle,
    campaign: HgtCampaignResult,
) -> ClaimgateBundle:
    """Attach HGT/compartment digests without raising the public ladder."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_hgt import HgtCampaignResult

    if not isinstance(campaign, HgtCampaignResult):
        raise ConfigurationError("campaign must be a HgtCampaignResult.")
    require_preregistration_before_campaign_attach(bundle)
    if campaign.red_queen_proved:
        raise ConfigurationError("campaign.red_queen_proved must remain False.")
    if (not campaign.hypothesis_supported) and not str(campaign.failure_reason).strip():
        raise ConfigurationError(
            "falsified HGT campaign requires a non-empty failure_reason."
        )
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_hgt_compartment_campaign requires a host_parasite domain bundle."
        )
    if "hgt_compartment_campaign" in extra:
        raise ConfigurationError("hgt_compartment_campaign already attached.")
    payload = campaign.to_dict()
    if payload.get("schema") != "host_parasite_hgt_compartment_campaign_v1":
        raise ConfigurationError("HGT compartment campaign schema mismatch.")
    if payload.get("wet_hgt_claimed") or payload.get("crispr_identity_proved"):
        raise ConfigurationError("attach refuses wet HGT or CRISPR identity claims.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_hgt_compartment_campaign requires preregistration digest on the bundle."
        )
    extra["hgt_compartment_campaign"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "arm_digests": payload["arm_digests"],
            "seeds": payload["seeds"],
            "arms": payload["arms"],
            "hypothesis": payload["hypothesis"],
            "hypothesis_supported": payload["hypothesis_supported"],
            "failure_reason": payload["failure_reason"],
            "claim_ceiling": payload["claim_ceiling"],
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "cou_labels": payload["cou_labels"],
            "hgt_scope": payload["hgt_scope"],
            "wet_hgt_claimed": False,
            "crispr_identity_proved": False,
            "preregistration_digest": str(prereg["digest"]),
        },
    )
    limitations = bundle.limitations
    if _HGT_NOTE not in limitations:
        limitations = limitations + (_HGT_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)

# ---------------------------------------------------------------------------
# Phase 13 — declared task–gene map digests (optional earn-in)
# ---------------------------------------------------------------------------

_TASK_GENE_NOTE = (
    "Task–gene map digests are declared digital phenotype links only; "
    "gene identity and CRISPR identity remain unproved."
)


def attach_task_gene_map(
    bundle: ClaimgateBundle,
    mapping: TaskGeneMapResult,
) -> ClaimgateBundle:
    """Attach declared task–gene map; refuse gene-identity claims."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_task_gene import TaskGeneMapResult

    if not isinstance(mapping, TaskGeneMapResult):
        raise ConfigurationError("mapping must be a TaskGeneMapResult.")
    require_preregistration_before_campaign_attach(bundle)
    if mapping.gene_identity_proved:
        raise ConfigurationError("gene_identity_proved must remain False.")
    if mapping.red_queen_proved:
        raise ConfigurationError("red_queen_proved must remain False.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_task_gene_map requires a host_parasite domain bundle."
        )
    if "task_gene_map" in extra:
        raise ConfigurationError("task_gene_map already attached.")
    payload = mapping.to_dict()
    if payload.get("schema") != "host_parasite_task_gene_map_v1":
        raise ConfigurationError("task–gene map schema mismatch.")
    if not payload.get("windows"):
        raise ConfigurationError("task–gene map requires at least one declared window.")
    if not str(payload.get("map_digest") or "").strip():
        raise ConfigurationError("task–gene map_digest must be non-empty.")
    if payload.get("gene_identity_proved") or payload.get("crispr_identity_proved"):
        raise ConfigurationError("attach refuses gene/CRISPR identity claims.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_task_gene_map requires preregistration digest on the bundle."
        )
    extra["task_gene_map"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "map_digest": payload["map_digest"],
            "seed": payload["seed"],
            "host_genome_digest": payload["host_genome_digest"],
            "window_count": len(payload["windows"]),
            "claim_ceiling": payload["claim_ceiling"],
            "gene_identity_proved": False,
            "crispr_identity_proved": False,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "preregistration_digest": str(prereg["digest"]),
            "scope": payload["scope"],
        },
    )
    limitations = bundle.limitations
    if _TASK_GENE_NOTE not in limitations:
        limitations = limitations + (_TASK_GENE_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)

# ---------------------------------------------------------------------------
# Phase 14 — transmission-mode contrast + mode-completeness hardening
# ---------------------------------------------------------------------------

_MODE_CONTRAST_NOTE = (
    "Transmission-mode contrast digests show horizontal / vertical / mixed "
    "are distinct; mixed blends both pathways. Digital labels only."
)


def attach_transmission_mode_contrast(
    bundle: ClaimgateBundle,
    contrast: "ModeContrastResult",
) -> ClaimgateBundle:
    """Attach transmission-mode contrast digests without raising the ladder."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_mode_contrast import ModeContrastResult

    if not isinstance(contrast, ModeContrastResult):
        raise ConfigurationError("contrast must be a ModeContrastResult.")
    require_preregistration_before_campaign_attach(bundle)
    if contrast.red_queen_proved:
        raise ConfigurationError("contrast.red_queen_proved must remain False.")
    if contrast.virulence_optimized_for_humans:
        raise ConfigurationError("virulence_optimized_for_humans must remain False.")
    if contrast.major_transition_proved:
        raise ConfigurationError("major_transition_proved must remain False.")
    if not contrast.mixed_blends_horizontal_and_vertical:
        raise ConfigurationError("attach requires mixed mode to blend H+V.")
    if not contrast.modes_are_distinct:
        raise ConfigurationError("attach requires pairwise-distinct mode digests.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_transmission_mode_contrast requires a host_parasite domain bundle."
        )
    if "transmission_mode_contrast" in extra:
        raise ConfigurationError("transmission_mode_contrast already attached.")
    payload = contrast.to_dict()
    if payload.get("schema") != "host_parasite_transmission_mode_contrast_v1":
        raise ConfigurationError("transmission-mode contrast schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_transmission_mode_contrast requires preregistration digest on the bundle."
        )
    extra["transmission_mode_contrast"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "mode_digests": payload["mode_digests"],
            "seeds": payload["seeds"],
            "modes": payload["modes"],
            "claim_ceiling": payload["claim_ceiling"],
            "modes_are_distinct": True,
            "mixed_blends_horizontal_and_vertical": True,
            "red_queen_proved": False,
            "virulence_optimized_for_humans": False,
            "major_transition_proved": False,
            "raises_claim_ladder": False,
            "preregistration_digest": str(prereg["digest"]),
        },
    )
    limitations = bundle.limitations
    if _MODE_CONTRAST_NOTE not in limitations:
        limitations = limitations + (_MODE_CONTRAST_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)

# ---------------------------------------------------------------------------
# Phase 15 — genome × VT × spatial × continuum factorial
# ---------------------------------------------------------------------------

_GENOME_FACTORIAL_NOTE = (
    "Genome×VT×spatial×continuum factorial digests are digital cross-wave "
    "observables; mutualism is never success and major transition stays unproved."
)


def attach_genome_vt_spatial_continuum_factorial(
    bundle: ClaimgateBundle,
    factorial: "GenomeFactorialResult",
) -> ClaimgateBundle:
    """Attach genome×continuum factorial digests without raising the ladder."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_genome_factorial import GenomeFactorialResult

    if not isinstance(factorial, GenomeFactorialResult):
        raise ConfigurationError("factorial must be a GenomeFactorialResult.")
    require_preregistration_before_campaign_attach(bundle)
    if factorial.red_queen_proved:
        raise ConfigurationError("factorial.red_queen_proved must remain False.")
    if factorial.major_transition_proved:
        raise ConfigurationError("major_transition_proved must remain False.")
    if factorial.mutualism_equals_success:
        raise ConfigurationError("mutualism_equals_success must remain False.")
    if not factorial.cells_are_distinct:
        raise ConfigurationError("attach requires pairwise-distinct factorial cell digests.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_genome_vt_spatial_continuum_factorial requires a host_parasite domain bundle."
        )
    if "genome_vt_spatial_continuum_factorial" in extra:
        raise ConfigurationError("genome_vt_spatial_continuum_factorial already attached.")
    payload = factorial.to_dict()
    if payload.get("schema") != "host_parasite_genome_vt_spatial_continuum_factorial_v1":
        raise ConfigurationError("genome factorial schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_genome_vt_spatial_continuum_factorial requires preregistration digest."
        )
    extra["genome_vt_spatial_continuum_factorial"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "factorial_digest": payload["factorial_digest"],
            "cell_digests": payload["cell_digests"],
            "seeds": payload["seeds"],
            "vt_levels": payload["vt_levels"],
            "spatial_modes": payload["spatial_modes"],
            "interaction_values": payload["interaction_values"],
            "claim_ceiling": payload["claim_ceiling"],
            "cells_are_distinct": True,
            "mutualism_equals_success": False,
            "red_queen_proved": False,
            "major_transition_proved": False,
            "raises_claim_ladder": False,
            "preregistration_digest": str(prereg["digest"]),
            "cross_wave": payload["cross_wave"],
        },
    )
    limitations = bundle.limitations
    if _GENOME_FACTORIAL_NOTE not in limitations:
        limitations = limitations + (_GENOME_FACTORIAL_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


# ---------------------------------------------------------------------------
# Phase 16 — virulence / resistance quality proxies (S7)
# ---------------------------------------------------------------------------

_VIRULENCE_QUALITY_NOTE = (
    "Virulence/resistance quality proxies are digital labels only; "
    "virulence_optimized_for_humans remains blocked."
)


def attach_virulence_resistance_quality(
    bundle: ClaimgateBundle,
    campaign: "VirulenceQualityResult",
) -> ClaimgateBundle:
    """Attach virulence-quality digests; keep human-virulence claim blocked."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_virulence_quality import VirulenceQualityResult

    if not isinstance(campaign, VirulenceQualityResult):
        raise ConfigurationError("campaign must be a VirulenceQualityResult.")
    require_preregistration_before_campaign_attach(bundle)
    if campaign.red_queen_proved:
        raise ConfigurationError("campaign.red_queen_proved must remain False.")
    if campaign.virulence_optimized_for_humans:
        raise ConfigurationError("virulence_optimized_for_humans must remain False.")
    if (not campaign.hypothesis_supported) and not str(campaign.failure_reason).strip():
        raise ConfigurationError("falsified virulence campaign requires failure_reason.")
    # Hard refuse: blocked claim must still raise if asserted at attach time.
    blocked = False
    try:
        assert_claim_allowed("virulence_optimized_for_humans")
    except ConfigurationError:
        blocked = True
    if not blocked:
        raise ConfigurationError("virulence_optimized_for_humans must stay blocked.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_virulence_resistance_quality requires a host_parasite domain bundle."
        )
    if "virulence_resistance_quality" in extra:
        raise ConfigurationError("virulence_resistance_quality already attached.")
    payload = campaign.to_dict()
    if payload.get("schema") != "host_parasite_virulence_resistance_quality_v1":
        raise ConfigurationError("virulence-quality schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_virulence_resistance_quality requires preregistration digest."
        )
    extra["virulence_resistance_quality"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "arm_digests": payload["arm_digests"],
            "seeds": payload["seeds"],
            "arms": payload["arms"],
            "hypothesis": payload["hypothesis"],
            "hypothesis_supported": payload["hypothesis_supported"],
            "failure_reason": payload["failure_reason"],
            "claim_ceiling": payload["claim_ceiling"],
            "arms_are_distinct": payload["arms_are_distinct"],
            "red_queen_proved": False,
            "virulence_optimized_for_humans": False,
            "raises_claim_ladder": False,
            "preregistration_digest": str(prereg["digest"]),
            "challenge": payload["challenge"],
        },
    )
    limitations = bundle.limitations
    if _VIRULENCE_QUALITY_NOTE not in limitations:
        limitations = limitations + (_VIRULENCE_QUALITY_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)

# ---------------------------------------------------------------------------
# Phase 17 — Price≠causality refusal assay (S8, optional earn-in)
# ---------------------------------------------------------------------------

_PRICE_CAUTION_NOTE = (
    "Price-style covariance summaries are diagnostics only; they do not prove "
    "major transitions or causal multilevel selection."
)


def attach_price_causality_caution(
    bundle: ClaimgateBundle,
    assay: "PriceCautionResult",
) -> ClaimgateBundle:
    """Attach Price caution digests; never unlock major_transition_proved."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_price_caution import PriceCautionResult

    if not isinstance(assay, PriceCautionResult):
        raise ConfigurationError("assay must be a PriceCautionResult.")
    require_preregistration_before_campaign_attach(bundle)
    if assay.major_transition_proved or assay.price_summary_is_causal or assay.red_queen_proved:
        raise ConfigurationError("Price caution flags must remain unproved/non-causal.")
    if not assay.refusal_assay_passed:
        raise ConfigurationError("Price refusal assay must pass before attach.")
    blocked = False
    try:
        assert_claim_allowed("major_transition_proved")
    except ConfigurationError:
        blocked = True
    if not blocked:
        raise ConfigurationError("major_transition_proved must stay blocked.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_price_causality_caution requires a host_parasite domain bundle."
        )
    if "price_causality_caution" in extra:
        raise ConfigurationError("price_causality_caution already attached.")
    payload = assay.to_dict()
    if payload.get("schema") != "host_parasite_price_causality_caution_v1":
        raise ConfigurationError("Price caution schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_price_causality_caution requires preregistration digest."
        )
    extra["price_causality_caution"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "summary_digest": payload["summary_digest"],
            "seeds": payload["seeds"],
            "price_covariance": payload["price_covariance"],
            "claim_ceiling": payload["claim_ceiling"],
            "price_summary_is_causal": False,
            "major_transition_proved": False,
            "red_queen_proved": False,
            "refusal_assay_passed": True,
            "raises_claim_ladder": False,
            "preregistration_digest": str(prereg["digest"]),
            "challenge": payload["challenge"],
        },
    )
    limitations = bundle.limitations
    if _PRICE_CAUTION_NOTE not in limitations:
        limitations = limitations + (_PRICE_CAUTION_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


# ---------------------------------------------------------------------------
# Phase 18 — soft-complete journal ClaimGate attach-registry packet
# ---------------------------------------------------------------------------

_JOURNAL_REGISTRY_NOTE = (
    "Journal attach-registry soft-complete invents no biology claims; it "
    "documents Phases 1–17 attach keys and the blocked-claim matrix only."
)


def attach_journal_attach_registry(
    bundle: ClaimgateBundle,
    packet: "JournalAttachRegistryPacket",
) -> ClaimgateBundle:
    """Attach Phase 18 soft-complete registry packet without raising the ladder."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_attach_registry import (
        JournalAttachRegistryPacket,
        assert_registry_covers_phases_1_to_17,
    )

    if not isinstance(packet, JournalAttachRegistryPacket):
        raise ConfigurationError("packet must be a JournalAttachRegistryPacket.")
    require_preregistration_before_campaign_attach(bundle)
    assert_registry_covers_phases_1_to_17(packet)
    if packet.raises_claim_ladder or packet.red_queen_proved or packet.major_transition_proved:
        raise ConfigurationError("journal registry packet must keep proved flags False.")
    # Re-check a representative blocked claim stays fail-closed.
    blocked = False
    try:
        assert_claim_allowed("red_queen_proved")
    except ConfigurationError:
        blocked = True
    if not blocked:
        raise ConfigurationError("red_queen_proved must stay blocked on host_parasite.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_journal_attach_registry requires a host_parasite domain bundle."
        )
    if "journal_attach_registry" in extra:
        raise ConfigurationError("journal_attach_registry already attached.")
    payload = packet.to_dict()
    if payload.get("schema") != "host_parasite_journal_attach_registry_v1":
        raise ConfigurationError("journal attach-registry schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_journal_attach_registry requires preregistration digest."
        )
    extra["journal_attach_registry"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "registry_digest": payload["registry_digest"],
            "required_attach_keys": payload["required_attach_keys"],
            "blocked_claim_matrix": payload["blocked_claim_matrix"],
            "phases_covered": payload["phases_covered"],
            "claim_ceiling": payload["claim_ceiling"],
            "soft_complete": True,
            "raises_claim_ladder": False,
            "red_queen_proved": False,
            "major_transition_proved": False,
            "preregistration_digest": str(prereg["digest"]),
            "wave": 5,
            "phase": 18,
        },
    )
    limitations = bundle.limitations
    if _JOURNAL_REGISTRY_NOTE not in limitations:
        limitations = limitations + (_JOURNAL_REGISTRY_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)

# ---------------------------------------------------------------------------
# Phase 19 — ARD→FSD transition + cost-of-generalism digests
# ---------------------------------------------------------------------------

_ARD_FSD_TRANSITION_NOTE = (
    "ARD→FSD transition digests and cost-of-generalism proxies are digital "
    "protocol labels only; red_queen_proved remains blocked."
)


def attach_ard_fsd_transition(
    bundle: ClaimgateBundle,
    campaign: "ArdFsdTransitionResult",
) -> ClaimgateBundle:
    """Attach ARD→FSD transition digests without proving Red Queen."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_ard_fsd_transition import ArdFsdTransitionResult

    if not isinstance(campaign, ArdFsdTransitionResult):
        raise ConfigurationError("campaign must be an ArdFsdTransitionResult.")
    require_preregistration_before_campaign_attach(bundle)
    if campaign.red_queen_proved:
        raise ConfigurationError("campaign.red_queen_proved must remain False.")
    if not campaign.slices_are_distinct:
        raise ConfigurationError("attach requires pairwise-distinct slice digests.")
    blocked = False
    try:
        assert_claim_allowed("red_queen_proved")
    except ConfigurationError:
        blocked = True
    if not blocked:
        raise ConfigurationError("red_queen_proved must stay blocked.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_ard_fsd_transition requires a host_parasite domain bundle."
        )
    if "ard_fsd_transition" in extra:
        raise ConfigurationError("ard_fsd_transition already attached.")
    payload = campaign.to_dict()
    if payload.get("schema") != "host_parasite_ard_fsd_transition_v1":
        raise ConfigurationError("ARD→FSD transition schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_ard_fsd_transition requires preregistration digest."
        )
    extra["ard_fsd_transition"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "arm_digests": payload["arm_digests"],
            "slice_digests": payload["slice_digests"],
            "seeds": payload["seeds"],
            "arms": payload["arms"],
            "hypothesis": payload["hypothesis"],
            "hypothesis_supported": payload["hypothesis_supported"],
            "failure_reason": payload["failure_reason"],
            "transition_observed": payload["transition_observed"],
            "slices_are_distinct": True,
            "claim_ceiling": payload["claim_ceiling"],
            "red_queen_proved": False,
            "wet_ard_fsd_identity": False,
            "raises_claim_ladder": False,
            "preregistration_digest": str(prereg["digest"]),
        },
    )
    limitations = bundle.limitations
    if _ARD_FSD_TRANSITION_NOTE not in limitations:
        limitations = limitations + (_ARD_FSD_TRANSITION_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)

# ---------------------------------------------------------------------------
# Phase 20 — resource × coevolution-dynamics factorial
# ---------------------------------------------------------------------------

_RESOURCE_DYNAMICS_NOTE = (
    "Resource×dynamics factorial digests use outside-engine productivity knobs; "
    "never a wet resource–virulence or clinical dosing claim."
)


def attach_resource_dynamics_factorial(
    bundle: ClaimgateBundle,
    factorial: "ResourceDynamicsResult",
) -> ClaimgateBundle:
    """Attach resource×dynamics factorial digests without wet claims."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_resource_dynamics import ResourceDynamicsResult

    if not isinstance(factorial, ResourceDynamicsResult):
        raise ConfigurationError("factorial must be a ResourceDynamicsResult.")
    require_preregistration_before_campaign_attach(bundle)
    if factorial.red_queen_proved:
        raise ConfigurationError("factorial.red_queen_proved must remain False.")
    if not factorial.cells_are_distinct:
        raise ConfigurationError("attach requires pairwise-distinct factorial cell digests.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_resource_dynamics_factorial requires a host_parasite domain bundle."
        )
    if "resource_dynamics_factorial" in extra:
        raise ConfigurationError("resource_dynamics_factorial already attached.")
    payload = factorial.to_dict()
    if payload.get("schema") != "host_parasite_resource_dynamics_factorial_v1":
        raise ConfigurationError("resource-dynamics factorial schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_resource_dynamics_factorial requires preregistration digest."
        )
    extra["resource_dynamics_factorial"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "factorial_digest": payload["factorial_digest"],
            "cell_digests": payload["cell_digests"],
            "seeds": payload["seeds"],
            "resource_levels": payload["resource_levels"],
            "biotic_levels": payload["biotic_levels"],
            "hypothesis": payload["hypothesis"],
            "hypothesis_supported": payload["hypothesis_supported"],
            "failure_reason": payload["failure_reason"],
            "cells_are_distinct": True,
            "claim_ceiling": payload["claim_ceiling"],
            "red_queen_proved": False,
            "wet_resource_virulence_proof": False,
            "raises_claim_ladder": False,
            "preregistration_digest": str(prereg["digest"]),
            "literature_map": payload["literature_map"],
        },
    )
    limitations = bundle.limitations
    if _RESOURCE_DYNAMICS_NOTE not in limitations:
        limitations = limitations + (_RESOURCE_DYNAMICS_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)

# ---------------------------------------------------------------------------
# Phase 21 — multi-seed contingency / repeatability under parasitism (S1)
# ---------------------------------------------------------------------------

_CONTINGENCY_NOTE = (
    "Multi-seed contingency digests report variance under parasitism; "
    "complexity_emergence_proved stays False and Zaman complexity is not a law."
)


def attach_multi_seed_contingency(
    bundle: ClaimgateBundle,
    campaign: "ContingencyCampaignResult",
) -> ClaimgateBundle:
    """Attach S1 contingency digests; never prove complexity emergence."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_contingency import ContingencyCampaignResult

    if not isinstance(campaign, ContingencyCampaignResult):
        raise ConfigurationError("campaign must be a ContingencyCampaignResult.")
    require_preregistration_before_campaign_attach(bundle)
    if campaign.complexity_emergence_proved or campaign.red_queen_proved:
        raise ConfigurationError("contingency proved flags must remain False.")
    if not campaign.seed_digests_are_distinct:
        raise ConfigurationError("attach requires pairwise-distinct seed digests.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_multi_seed_contingency requires a host_parasite domain bundle."
        )
    if "multi_seed_contingency" in extra:
        raise ConfigurationError("multi_seed_contingency already attached.")
    payload = campaign.to_dict()
    if payload.get("schema") != "host_parasite_multi_seed_contingency_v1":
        raise ConfigurationError("multi-seed contingency schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_multi_seed_contingency requires preregistration digest."
        )
    extra["multi_seed_contingency"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "arm_digests": payload["arm_digests"],
            "seed_digests": payload["seed_digests"],
            "seeds": payload["seeds"],
            "arms": payload["arms"],
            "hypothesis": payload["hypothesis"],
            "hypothesis_supported": payload["hypothesis_supported"],
            "failure_reason": payload["failure_reason"],
            "seed_digests_are_distinct": True,
            "cross_seed_variance": payload["cross_seed_variance"],
            "claim_ceiling": payload["claim_ceiling"],
            "complexity_emergence_proved": False,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "preregistration_digest": str(prereg["digest"]),
            "challenge": payload["challenge"],
            "success_criterion": payload["success_criterion"],
        },
    )
    limitations = bundle.limitations
    if _CONTINGENCY_NOTE not in limitations:
        limitations = limitations + (_CONTINGENCY_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)

# ---------------------------------------------------------------------------
# Phase 22 — sequential Cornish multi-intervention deepening
# ---------------------------------------------------------------------------

_SEQUENTIAL_CORNISH_NOTE = (
    "Sequential Cornish deepening: observational match alone never grants "
    "intervention_supported; not clinical decision support."
)


def attach_sequential_cornish_campaign(
    bundle: ClaimgateBundle,
    campaign: "SequentialCornishResult",
) -> ClaimgateBundle:
    """Attach sequential Cornish digests; refuse intervention_supported from obs match."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_cornish_sequential import SequentialCornishResult

    if not isinstance(campaign, SequentialCornishResult):
        raise ConfigurationError("campaign must be a SequentialCornishResult.")
    require_preregistration_before_campaign_attach(bundle)
    if campaign.red_queen_proved:
        raise ConfigurationError("campaign.red_queen_proved must remain False.")
    if campaign.intervention_supported:
        raise ConfigurationError(
            "intervention_supported must remain False (observational match alone never grants it)."
        )
    if not campaign.observational_match:
        raise ConfigurationError("attach requires observational baseline match record.")
    if not campaign.interventions_executed:
        raise ConfigurationError("attach requires at least one executed intervention step.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_sequential_cornish_campaign requires a host_parasite domain bundle."
        )
    if "cornish_sequential_campaign" in extra:
        raise ConfigurationError("cornish_sequential_campaign already attached.")
    payload = campaign.to_dict()
    if payload.get("schema") != "host_parasite_cornish_sequential_v1":
        raise ConfigurationError("sequential Cornish schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_sequential_cornish_campaign requires preregistration digest."
        )
    # Bundle prereg digest should agree with campaign prereg when both present.
    if str(prereg["digest"]).lower() != str(campaign.preregistration_digest).lower():
        raise ConfigurationError(
            "sequential Cornish preregistration_digest must match bundle prereg digest."
        )
    extra["cornish_sequential_campaign"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "step_digests": payload["step_digests"],
            "seeds": payload["seeds"],
            "schedule": payload["schedule"],
            "observational_match": payload["observational_match"],
            "later_intervention_failed": payload["later_intervention_failed"],
            "interventions_executed": True,
            "intervention_supported": False,
            "claim_ceiling": payload["claim_ceiling"],
            "red_queen_proved": False,
            "clinical_decision_support": False,
            "raises_claim_ladder": False,
            "preregistration_digest": str(prereg["digest"]),
            "cornish_rule": payload["cornish_rule"],
        },
    )
    limitations = bundle.limitations
    if _SEQUENTIAL_CORNISH_NOTE not in limitations:
        limitations = limitations + (_SEQUENTIAL_CORNISH_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)

# ---------------------------------------------------------------------------
# Phase 23 — Scanlan mutator / abiotic-constraint dual-null (earn-in)
# ---------------------------------------------------------------------------

_MUTATOR_NOTE = (
    "Scanlan mutator dual-null digests are genome-layer digital assays; "
    "gene_identity_proved and CRISPR identity stay False."
)


def attach_scanlan_mutator_campaign(
    bundle: ClaimgateBundle,
    campaign: "MutatorCampaignResult",
) -> ClaimgateBundle:
    """Attach Scanlan mutator digests; refuse gene identity / CRISPR claims."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_mutator import MutatorCampaignResult

    if not isinstance(campaign, MutatorCampaignResult):
        raise ConfigurationError("campaign must be a MutatorCampaignResult.")
    require_preregistration_before_campaign_attach(bundle)
    if campaign.gene_identity_proved or campaign.red_queen_proved:
        raise ConfigurationError("mutator proved flags must remain False.")
    if not campaign.arms_are_distinct:
        raise ConfigurationError("attach requires pairwise-distinct mutator arm digests.")
    blocked = False
    try:
        assert_claim_allowed("crispr_identity_proved")
    except ConfigurationError:
        blocked = True
    if not blocked:
        raise ConfigurationError("crispr_identity_proved must stay blocked.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_scanlan_mutator_campaign requires a host_parasite domain bundle."
        )
    if "scanlan_mutator_campaign" in extra:
        raise ConfigurationError("scanlan_mutator_campaign already attached.")
    payload = campaign.to_dict()
    if payload.get("schema") != "host_parasite_scanlan_mutator_dual_null_v1":
        raise ConfigurationError("Scanlan mutator schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_scanlan_mutator_campaign requires preregistration digest."
        )
    extra["scanlan_mutator_campaign"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "arm_digests": payload["arm_digests"],
            "seeds": payload["seeds"],
            "arms": payload["arms"],
            "hypothesis": payload["hypothesis"],
            "hypothesis_supported": payload["hypothesis_supported"],
            "failure_reason": payload["failure_reason"],
            "arms_are_distinct": True,
            "claim_ceiling": payload["claim_ceiling"],
            "gene_identity_proved": False,
            "crispr_identity_proved": False,
            "red_queen_proved": False,
            "wet_mutator_gene_identity": False,
            "raises_claim_ladder": False,
            "preregistration_digest": str(prereg["digest"]),
            "literature_map": payload["literature_map"],
        },
    )
    limitations = bundle.limitations
    if _MUTATOR_NOTE not in limitations:
        limitations = limitations + (_MUTATOR_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


# ---------------------------------------------------------------------------
# Phase 24 — Wave 6 journal packet integration smoke (Phases 18–23)
# ---------------------------------------------------------------------------

_WAVE6_SMOKE_NOTE = (
    "Wave 6 journal smoke attaches Phases 18–23 digests on one prereg-bound "
    "bundle for soft-complete inventory hygiene; ladder must not rise and "
    "blocked claims stay fail-closed."
)


def attach_wave6_journal_smoke(
    bundle: ClaimgateBundle,
    smoke: "Wave6JournalSmokeResult",
) -> ClaimgateBundle:
    """Attach Phase 24 smoke digest without raising the ClaimGate ladder."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_wave6_smoke import Wave6JournalSmokeResult

    if not isinstance(smoke, Wave6JournalSmokeResult):
        raise ConfigurationError("smoke must be a Wave6JournalSmokeResult.")
    require_preregistration_before_campaign_attach(bundle)
    if smoke.raises_claim_ladder or smoke.red_queen_proved:
        raise ConfigurationError("wave6 smoke must keep proved / ladder flags False.")
    if not smoke.ladder_unchanged:
        raise ConfigurationError("wave6 smoke requires ladder_unchanged=True.")
    if not smoke.soft_complete_wave5_surface:
        raise ConfigurationError("wave6 smoke requires soft_complete_wave5_surface.")
    blocked = False
    try:
        assert_claim_allowed("red_queen_proved")
    except ConfigurationError:
        blocked = True
    if not blocked:
        raise ConfigurationError("red_queen_proved must stay blocked.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_wave6_journal_smoke requires a host_parasite domain bundle."
        )
    if "wave6_journal_smoke" in extra:
        raise ConfigurationError("wave6_journal_smoke already attached.")
    payload = smoke.to_dict()
    if payload.get("schema") != "host_parasite_wave6_journal_smoke_v1":
        raise ConfigurationError("wave6 journal smoke schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_wave6_journal_smoke requires preregistration digest."
        )
    extra["wave6_journal_smoke"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "smoke_digest": payload["smoke_digest"],
            "attach_order": payload["attach_order"],
            "attached_keys": payload["attached_keys"],
            "campaign_digests": payload["campaign_digests"],
            "ladder_before": payload["ladder_before"],
            "ladder_after": payload["ladder_after"],
            "ladder_unchanged": True,
            "blocked_spot_check": payload["blocked_spot_check"],
            "claim_ceiling": payload["claim_ceiling"],
            "raises_claim_ladder": False,
            "red_queen_proved": False,
            "complexity_emergence_proved": False,
            "intervention_supported": False,
            "gene_identity_proved": False,
            "soft_complete_wave5_surface": True,
            "preregistration_digest": str(prereg["digest"]),
            "wave": 6,
            "phase": 24,
        },
    )
    limitations = bundle.limitations
    if _WAVE6_SMOKE_NOTE not in limitations:
        limitations = limitations + (_WAVE6_SMOKE_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


# ---------------------------------------------------------------------------
# Phase 25 — HE_HP locked-digest refresh note (Wave 5 stack honesty)
# ---------------------------------------------------------------------------

_HE_HP_REFRESH_NOTE = (
    "HE_HP locked-digest refresh confirms Phase 7–9 campaign digests still "
    "replay after Waves 5–6; BAIC pins remain byte-identical."
)


def attach_he_hp_locked_digest_refresh(
    bundle: ClaimgateBundle,
    note: "HeHpLockedDigestRefreshNote",
) -> ClaimgateBundle:
    """Attach Phase 25 HE_HP refresh note; refuse pin edits and ladder rise."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_he_hp_refresh import HeHpLockedDigestRefreshNote

    if not isinstance(note, HeHpLockedDigestRefreshNote):
        raise ConfigurationError("note must be a HeHpLockedDigestRefreshNote.")
    require_preregistration_before_campaign_attach(bundle)
    if note.raises_claim_ladder or note.red_queen_proved:
        raise ConfigurationError("HE_HP refresh must keep proved / ladder flags False.")
    if not note.baic_pins_untouched:
        raise ConfigurationError("HE_HP refresh requires baic_pins_untouched=True.")
    if not note.locks_still_valid:
        raise ConfigurationError("HE_HP refresh requires locks_still_valid=True.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_he_hp_locked_digest_refresh requires a host_parasite domain bundle."
        )
    if "he_hp_locked_digest_refresh" in extra:
        raise ConfigurationError("he_hp_locked_digest_refresh already attached.")
    payload = note.to_dict()
    if payload.get("schema") != "host_parasite_he_hp_locked_digest_refresh_v1":
        raise ConfigurationError("HE_HP refresh schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_he_hp_locked_digest_refresh requires preregistration digest."
        )
    extra["he_hp_locked_digest_refresh"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "refresh_digest": payload["refresh_digest"],
            "locked_digest": payload["locked_digest"],
            "campaign_lock_status": payload["campaign_lock_status"],
            "baic_pins_untouched": True,
            "locks_still_valid": True,
            "wave5_does_not_invalidate_he_hp": True,
            "raises_claim_ladder": False,
            "red_queen_proved": False,
            "preregistration_digest": str(prereg["digest"]),
            "wave": 6,
            "phase": 25,
        },
    )
    limitations = bundle.limitations
    if _HE_HP_REFRESH_NOTE not in limitations:
        limitations = limitations + (_HE_HP_REFRESH_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


# ---------------------------------------------------------------------------
# Phase 26 — Phase 11×21 entropy × contingency bridge
# ---------------------------------------------------------------------------

_ENTROPY_CONTINGENCY_NOTE = (
    "Entropy×contingency bridge pairs Phase 11 codon-entropy dual-null with "
    "Phase 21 seed contingency; complexity_emergence_proved stays False."
)


def attach_entropy_contingency_bridge(
    bundle: ClaimgateBundle,
    bridge: "EntropyContingencyBridgeResult",
) -> ClaimgateBundle:
    """Attach Phase 26 bridge digests without proving complexity emergence."""

    from codontrace.claimgate.adapters.host_parasite_prereg import (
        require_preregistration_before_campaign_attach,
    )
    from codontrace.genesis.host_parasite_entropy_contingency_bridge import (
        EntropyContingencyBridgeResult,
    )

    if not isinstance(bridge, EntropyContingencyBridgeResult):
        raise ConfigurationError("bridge must be an EntropyContingencyBridgeResult.")
    require_preregistration_before_campaign_attach(bundle)
    if bridge.complexity_emergence_proved or bridge.red_queen_proved:
        raise ConfigurationError("bridge proved flags must remain False.")
    if not bridge.seed_digests_are_distinct:
        raise ConfigurationError("attach requires pairwise-distinct bridge seed digests.")
    blocked = False
    try:
        assert_claim_allowed("red_queen_proved")
    except ConfigurationError:
        blocked = True
    if not blocked:
        raise ConfigurationError("red_queen_proved must stay blocked.")
    extra = dict(bundle.extra or {})
    if extra.get("domain") != HOST_PARASITE.name:
        raise ConfigurationError(
            "attach_entropy_contingency_bridge requires a host_parasite domain bundle."
        )
    if "entropy_contingency_bridge" in extra:
        raise ConfigurationError("entropy_contingency_bridge already attached.")
    payload = bridge.to_dict()
    if payload.get("schema") != "host_parasite_entropy_contingency_bridge_v1":
        raise ConfigurationError("entropy×contingency bridge schema mismatch.")
    prereg = extra.get("host_parasite_preregistration")
    if not isinstance(prereg, Mapping) or "digest" not in prereg:
        raise ConfigurationError(
            "attach_entropy_contingency_bridge requires preregistration digest."
        )
    extra["entropy_contingency_bridge"] = cast(
        JsonValue,
        {
            "schema": payload["schema"],
            "campaign_digest": payload["campaign_digest"],
            "seed_digests": payload["seed_digests"],
            "seeds": payload["seeds"],
            "hypothesis": payload["hypothesis"],
            "hypothesis_supported": payload["hypothesis_supported"],
            "failure_reason": payload["failure_reason"],
            "seed_digests_are_distinct": True,
            "claim_ceiling": payload["claim_ceiling"],
            "complexity_emergence_proved": False,
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "phase11_schema": payload["phase11_schema"],
            "phase21_schema": payload["phase21_schema"],
            "preregistration_digest": str(prereg["digest"]),
            "wave": 6,
            "phase": 26,
        },
    )
    limitations = bundle.limitations
    if _ENTROPY_CONTINGENCY_NOTE not in limitations:
        limitations = limitations + (_ENTROPY_CONTINGENCY_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)
