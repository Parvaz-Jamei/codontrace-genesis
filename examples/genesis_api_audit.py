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

from codontrace.genesis import collect_genesis_public_api, validate_genesis_exports

symbols = collect_genesis_public_api(("QDArchive", "ValidationBundle", "ClaimAuditResult"))
result = validate_genesis_exports(tuple(symbol.name for symbol in symbols))
print({"symbols": result.public_symbol_count, "succeeded": result.succeeded})
