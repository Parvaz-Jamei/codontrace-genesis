"""Planted-defect checks and the anti-gaming property.

The knockouts are deterministic predicates, not a binomial sample and
not a rate for the published literature. The role-relabel builder still
keeps a confirmatory negative-control arm; its extra flags are unread,
so that row is a probe, not an escape trial.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from codontrace.claimgate.auditor import audit_bundle
from codontrace.claimgate.ladder_packs import (
    pack_drop_confirmatory_keep_sensitivity_role,
    pack_empty_limitations,
    pack_identical_arms,
    pack_no_paired_comparison,
    pack_no_replay,
    pack_reference,
    pack_three_seeds,
    pack_zero_width_ci,
)
from codontrace.claimgate.schema import ClaimgateBundle
from codontrace.genesis.canonical import canonical_digest, canonical_payload

SHOULD_DROP: tuple[tuple[str, Callable[[], ClaimgateBundle]], ...] = (
    ("identical_arms", pack_identical_arms),
    ("zero_width_ci", pack_zero_width_ci),
    ("no_paired_comparison", pack_no_paired_comparison),
    ("no_replay", pack_no_replay),
    ("empty_limitations", pack_empty_limitations),
    ("three_seeds", pack_three_seeds),
)

NAMED_PROBE = ("role_relabel_sensitivity", pack_drop_confirmatory_keep_sensitivity_role)

_LABELS: tuple[Mapping[str, object], ...] = (
    {"model_influence": 3, "decision_consequence": 3, "model_risk": 3},
    {"device_software_kind": "simd_declared", "iec_62304_class": "C", "imdrf_n12_category": "IV"},
    {"fda_2023_evidence": [1, 3, 4, 8], "physics_based": True, "asme_vv40": "passed_label"},
    {"knowledge": "adequate", "importance": "high", "measured": True},
)


def _with_labels(bundle: ClaimgateBundle, labels: Mapping[str, object]) -> ClaimgateBundle:
    extra = dict(bundle.extra or {})
    extra.update(labels)
    extra["label_inflation"] = True
    return ClaimgateBundle(
        software=bundle.software,
        seeds=bundle.seeds,
        config_digest=bundle.config_digest,
        arms=bundle.arms,
        outcomes=bundle.outcomes,
        comparisons=bundle.comparisons,
        replay=bundle.replay,
        artifacts=bundle.artifacts,
        limitations=bundle.limitations,
        preregistration_digest=bundle.preregistration_digest,
        doi=bundle.doi,
        extra=extra,
        schema=bundle.schema,
    )


def anti_gaming_rows(bundle: ClaimgateBundle) -> list[dict[str, object]]:
    """Declared labels must not raise the audited level."""

    base = audit_bundle(bundle).achieved_level
    rows: list[dict[str, object]] = []
    for labels in _LABELS:
        audited = audit_bundle(_with_labels(bundle, labels))
        rows.append(
            {
                "labels": {str(key): labels[key] for key in sorted(labels)},
                "base_level": base,
                "audited_level": audited.achieved_level,
                "raised": audited.achieved_level > base,
            }
        )
    return rows


def defect_grid_payload() -> dict[str, object]:
    reference = audit_bundle(pack_reference()).achieved_level
    rows: list[dict[str, object]] = []
    for name, builder in SHOULD_DROP:
        level = audit_bundle(builder()).achieved_level
        rows.append(
            {
                "defect": name,
                "class": "requirement_knockout",
                "auditor_level": level,
                "caught": level < reference,
            }
        )
    probe_name, probe_builder = NAMED_PROBE
    probe_level = audit_bundle(probe_builder()).achieved_level
    gaming = anti_gaming_rows(pack_reference())
    body: dict[str, object] = {
        "schema": "claimgate_defect_grid_v1",
        "reference_level": reference,
        "n_knockouts": len(rows),
        "n_caught": sum(1 for row in rows if row["caught"]),
        "knockouts": rows,
        "role_relabel_probe": {
            "defect": probe_name,
            "auditor_level": probe_level,
            "confirmatory_arm_still_present": True,
            "flags_read": False,
            "not_an_escape_trial": True,
        },
        "anti_gaming": gaming,
        "anti_gaming_holds": all(not row["raised"] for row in gaming),
        "population": "deterministic_requirement_knockouts",
        "not_a_literature_rate": True,
        "not_a_binomial_sample": True,
        "external_raters": False,
    }
    return {**body, "digest": canonical_digest(canonical_payload(body))}
