"""The defect grid is a planted-defect measurement, not a literature rate."""

from __future__ import annotations

import json
from pathlib import Path

from codontrace.claimgate.adapters.biomedical import bundle_from_device_model_cou
from codontrace.claimgate.defect_grid import anti_gaming_rows, defect_grid_payload
from codontrace.claimgate.ladder_packs import pack_reference


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
    assert live["population"] == "planted_defects_on_the_reference_pack"
    assert live["anti_gaming_holds"] is True
    assert live["reference_level"] == 4
    assert committed == live
