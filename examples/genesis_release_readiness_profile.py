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

from codontrace.genesis import ReleaseReadinessProfile

profile = ReleaseReadinessProfile.testpypi()
print(
    {
        "profile": profile.profile_name,
        "gate_count": len(profile.required_gates),
        "digest": profile.digest()[:12],
    }
)
