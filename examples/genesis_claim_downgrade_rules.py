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
from codontrace.genesis import ScientificEvidencePack, apply_claim_downgrade_rules

pack = ScientificEvidencePack("demo-pack", __version__, claim_ceiling="EVIDENCE_SUPPORTED")
result = apply_claim_downgrade_rules(pack)
print(
    {
        "original": result.original_ceiling,
        "final": result.final_ceiling,
        "rules": len(result.applied_rules),
    }
)
