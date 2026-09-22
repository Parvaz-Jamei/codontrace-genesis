"""Toy biomedical context-of-use wrap. Not a clinical study.

Print-only. Synthetic scores. Does not claim SaMD, FDA, CE, or ASME pass.
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
    bundle_from_biomedical_cou,
    bundle_from_device_model_cou,
)


def main() -> None:
    bundle = bundle_from_biomedical_cou(
        question_of_interest="Would this in-silico score table support a screening claim?",
        context_of_use="Retrospective synthetic table only; no bedside use.",
        model_influence=2,
        decision_consequence=3,
        treatment_scores=(0.71, 0.68, 0.73),
        control_scores=(0.50, 0.52, 0.49),
        metric="auroc_toy",
    )
    report = audit_bundle(bundle)
    extra = bundle.extra or {}
    print("domain", extra.get("domain"))
    print("model_risk", extra.get("model_risk"))
    print("asme_vv40", extra.get("asme_vv40"))
    print("public_level", report.achieved_level)
    print("public_name", report.public_name)
    print("replay_verified", bundle.replay.verified)
    print("certification", extra.get("certification"))
    print("device_software_kind", extra.get("device_software_kind"))
    print("fda_2023_scope", extra.get("fda_2023_scope"))

    device = bundle_from_device_model_cou(
        question_of_interest="Would this bench-like score table license a worst-case size pick?",
        context_of_use="Synthetic table only; no ISO 14879-1 test; no implant.",
        model_influence=2,
        decision_consequence=3,
        treatment_scores=(0.12, 0.11, 0.13),
        control_scores=(0.20, 0.19, 0.21),
        device_software_kind="simd_declared",
        iec_62304_class="B",
        imdrf_n12_category="II",
        fda_2023_evidence=(1, 3, 8),
        physics_based=True,
        metric="declared_peak_stress_toy",
    )
    device_report = audit_bundle(device)
    device_extra = device.extra or {}
    print("simd_kind", device_extra.get("device_software_kind"))
    print("iec_62304_class", device_extra.get("iec_62304_class"))
    print("fda_2023_evidence", device_extra.get("fda_2023_evidence"))
    print("device_public_level", device_report.achieved_level)


if __name__ == "__main__":
    main()
