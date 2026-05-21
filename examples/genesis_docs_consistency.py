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
from codontrace.genesis import evaluate_docs_consistency

docs = {
    "README.md": "CodonTrace current alpha is an evidence scaffold. It does not prove discovery."
}
record = evaluate_docs_consistency(docs, __version__)
print(
    {
        "passed": record.passed,
        "sections": len(record.checked_sections),
        "digest": record.digest()[:12],
    }
)
