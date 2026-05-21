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
from codontrace.genesis import FinalGateSummary

summary = FinalGateSummary(
    version=__version__,
    code_gates_passed=True,
    docs_gates_passed=True,
    claim_gates_passed=True,
    package_gates_passed=True,
    scientific_evidence_gates_passed=True,
    external_release_gates_passed=False,
    blocked_for_public_release=True,
    accepted_as_code_level_mature_alpha=True,
    reasons=("hosted_ci_not_run", "pip_audit_not_completed"),
)
print(
    {
        "code_level": summary.accepted_as_code_level_mature_alpha,
        "public_blocked": summary.blocked_for_public_release,
    }
)
