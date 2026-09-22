"""Executable PIRT plus weakest-submodel cap. Not a device credibility grade.

Print-only. The ranks are declared, not measured. The worksheet cannot
raise the ClaimGate ladder and does not start the engine.
"""

from __future__ import annotations

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from codontrace.claimgate import audit_bundle  # noqa: E402
from codontrace.claimgate.adapters.biomedical import (  # noqa: E402
    attach_credibility_worksheet,
    bundle_from_device_model_cou,
)


def main() -> None:
    bundle = bundle_from_device_model_cou(
        question_of_interest="Which recorded gap blocks a coupled device-patient claim?",
        context_of_use="Declared worksheet only; no ISO 14879-1 test; no implant.",
        model_influence=2,
        decision_consequence=3,
        treatment_scores=(0.12, 0.11, 0.13),
        control_scores=(0.20, 0.19, 0.21),
        device_software_kind="simd_declared",
        iec_62304_class="B",
        physics_based=True,
        metric="declared_peak_stress_toy",
    )
    annotated = attach_credibility_worksheet(
        bundle,
        phenomena=(
            {"name": "contact_stress", "importance": "high", "knowledge": "partial"},
            {"name": "wear_debris", "importance": "high", "knowledge": "none"},
            {"name": "packaging", "importance": "low", "knowledge": "none"},
        ),
        submodels=(
            {
                "name": "device_fea",
                "role": "device",
                "level": 3,
                "evidence_categories": (1, 3),
            },
            {
                "name": "patient_geometry",
                "role": "patient",
                "level": 4,
                "identifiable": False,
                "evidence_categories": (2,),
            },
        ),
    )
    sheet = annotated.extra["credibility_worksheet"]
    print("claim_ladder", audit_bundle(annotated).achieved_level)
    print("open_gaps", sheet["open_gaps"])
    print("limiting_submodel", sheet["limiting_submodel"])
    print("coupled_ceiling", sheet["coupled_ceiling"])
    print("raises_claim_ladder", sheet["raises_claim_ladder"])


if __name__ == "__main__":
    main()
