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
from codontrace.claimgate.adapters.biomedical import bundle_from_biomedical_cou  # noqa: E402


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


if __name__ == "__main__":
    main()
