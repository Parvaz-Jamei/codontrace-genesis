"""The defect grid is a planted-defect measurement, not a literature rate."""

from __future__ import annotations

import json
from pathlib import Path

from codontrace.claimgate import audit_bundle
from codontrace.claimgate.adapters.biomedical import bundle_from_device_model_cou
from codontrace.claimgate.defect_grid import anti_gaming_rows, defect_grid_payload
from codontrace.claimgate.ladder_packs import pack_reference
from codontrace.claimgate.schema import ClaimgateOutcome


def test_declared_labels_do_not_raise_the_reference_or_the_device_table() -> None:
    assert all(not row["raised"] for row in anti_gaming_rows(pack_reference()))
    device = bundle_from_device_model_cou(
        question_of_interest="q",
        context_of_use="synthetic table",
        model_influence=2,
        decision_consequence=3,
        treatment_scores=(0.12, 0.11, 0.13),
        control_scores=(0.20, 0.19, 0.21),
        device_software_kind="simd_declared",
        physics_based=True,
    )
    assert all(not row["raised"] for row in anti_gaming_rows(device))


def test_committed_defect_grid_matches_the_live_auditor() -> None:
    live = defect_grid_payload()
    committed = json.loads(Path("docs/claimgate/defect_grid.json").read_text(encoding="utf-8"))
    assert live["not_a_literature_rate"] is True
    assert live["not_a_binomial_sample"] is True
    assert live["population"] == "deterministic_requirement_knockouts"
    assert live["n_caught"] == live["n_knockouts"] == 6
    assert live["role_relabel_probe"]["not_an_escape_trial"] is True
    assert live["anti_gaming_holds"] is True
    assert live["reference_level"] == 4
    assert "escape_rate" not in live
    assert committed == live


def test_extra_rows_per_seed_do_not_carry_the_interval() -> None:
    from dataclasses import replace

    reference = pack_reference()
    assert audit_bundle(reference).achieved_level == 4
    outcome = reference.outcomes[0]
    doubled = {
        name: values + values for name, values in outcome.values_by_arm.items()
    }
    inflated = replace(
        reference,
        outcomes=(ClaimgateOutcome(metric=outcome.metric, values_by_arm=doubled),),
    )
    report = audit_bundle(inflated)
    assert report.achieved_level < 4
    assert "pseudoreplicated_rows_do_not_carry_the_interval" in report.warnings
