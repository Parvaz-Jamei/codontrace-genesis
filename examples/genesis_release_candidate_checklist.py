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
from codontrace.genesis import (
    ReleaseCandidateChecklist,
    ReleaseGateRecord,
    ReleaseGateStatus,
    evaluate_release_candidate,
)

required = (
    "compileall",
    "pytest",
    "ruff",
    "mypy",
    "build",
    "twine",
    "wheel_smoke",
    "claim_audit",
    "api_audit",
    "zip_hygiene",
)
checklist = ReleaseCandidateChecklist(
    version=__version__,
    artifact_name="codontrace-current alpha.zip",
    gates=tuple(ReleaseGateRecord(name, ReleaseGateStatus.PASS) for name in required),
    api_snapshot_digest="api",
    claim_audit_digest="claim",
)
decision = evaluate_release_candidate(checklist)
print(
    {
        "accepted_for_testpypi": decision.accepted_for_testpypi,
        "accepted_for_pypi": decision.accepted_for_pypi,
    }
)
