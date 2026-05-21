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

from codontrace.genesis import (
    BehaviorDescriptorSchema,
    QDArchiveConfig,
    validate_digest_stability,
    validate_roundtrip,
)

schema = BehaviorDescriptorSchema(
    descriptor_names=("novelty",),
    bins_per_descriptor={"novelty": 4},
    min_values={"novelty": 0.0},
    max_values={"novelty": 1.0},
)
config = QDArchiveConfig(schema=schema)
print(
    {
        "roundtrip": validate_roundtrip(config).succeeded,
        "digest": validate_digest_stability(config).succeeded,
    }
)
