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

from codontrace.genesis import evaluate_artifact_hygiene

record = evaluate_artifact_hygiene(
    ("src/codontrace/__init__.py", "tests/test_import.py"), "source.zip"
)
print(
    {
        "passed": record.passed,
        "suspicious": len(record.suspicious_entries),
        "digest": record.digest()[:12],
    }
)
