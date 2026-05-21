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

from codontrace.genesis import StatisticalProtocolConfig, estimate_effect_size_lite

protocol = StatisticalProtocolConfig(min_seeds=3, metric_names=("fitness",))
effect = estimate_effect_size_lite("fitness", [1.0, 1.5, 2.0], [1.2, 1.7, 2.4])
print({"protocol_digest": protocol.digest()[:12], "effect": effect.interpretation})
