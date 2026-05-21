from __future__ import annotations

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

import codontrace.genesis as genesis
from codontrace import __version__
from codontrace.genesis import build_api_stability_map, validate_api_stability_map_against_exports

exports = tuple(genesis.__all__)
stability = build_api_stability_map(__version__, exports)
errors = validate_api_stability_map_against_exports(stability, exports)

print({"covered": len(stability.covered_symbols), "missing": len(errors), "errors": errors})
