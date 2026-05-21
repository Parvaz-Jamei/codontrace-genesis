"""Use WorldObject metadata from a custom research app."""

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

from codontrace import World2D, WorldObject

world = World2D(5, 5)
world.add_object((2, 2), WorldObject(kind="FOOD", amount=3.0, metadata={"label": "sample"}))
print(world.objects_at((2, 2)))
print(world.to_dict()["objects"])
