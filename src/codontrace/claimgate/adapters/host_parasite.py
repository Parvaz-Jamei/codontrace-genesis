"""Host–parasite / microbe–virus port: a DomainProfile, not a second engine.

This adapter is claim-labeling only. It does not implement infection physics,
does not certify vaccines, antivirals, phage therapy, epidemic forecasts, or
biosafety levels, and must not be read as a clinical pathogen model.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import cast

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
