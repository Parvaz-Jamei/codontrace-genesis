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

from codontrace.genesis import SecurityEvidenceRecord, audit_documentation_sections

docs = {
    "README.md": (
        "installation quickstart GENESIS alignment non-goals claim limitations "
        "API overview examples release evidence citation security"
    )
}
result = audit_documentation_sections(
    docs,
    (
        "installation",
        "quickstart",
        "GENESIS alignment",
        "non-goals",
        "claim limitations",
        "API overview",
        "examples",
        "release evidence",
        "citation",
        "security",
    ),
)
security = SecurityEvidenceRecord(
    "pip-audit", "NOT COMPLETED", "pip-audit", limitations=("sandbox",)
)
print({"docs_ok": result.succeeded, "security_status": security.status})
