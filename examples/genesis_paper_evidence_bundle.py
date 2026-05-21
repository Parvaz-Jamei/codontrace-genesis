try:
    from ._path_bootstrap import ensure_src_path
except ImportError:  # direct script or runpy execution outside the examples package
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from codontrace import __version__
from codontrace.genesis import PaperEvidenceBundle

bundle = PaperEvidenceBundle(
    paper_bundle_id="paper-demo",
    library_version=__version__,
    scenario_suite_digest="scenario",
    evidence_pack_digest="evidence",
    validation_matrix_digest="matrix",
    reproducibility_summary_digest="repro",
    limitations_digest="limits",
    claim_audit_digest="claims",
)
print({"bundle": bundle.paper_bundle_id, "ceiling": bundle.allowed_claim_ceiling})
