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

from codontrace.genesis import FinalExamplesMatrix, FinalExamplesMatrixSummary

items = (
    FinalExamplesMatrix("genesis_final_release_manifest.py", "mature_alpha", smoke_status="PASS"),
    FinalExamplesMatrix("genesis_claim_audit.py", "validation", smoke_status="PASS"),
)
summary = FinalExamplesMatrixSummary(items)
print(
    {
        "passed": summary.passed_examples,
        "total": summary.total_examples,
        "categories": summary.categories,
    }
)
