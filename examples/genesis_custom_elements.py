"""Define a custom GENESIS element registry without file loading or dependencies."""

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

from codontrace.genesis import ElementRegistry

registry = ElementRegistry.genesis_v0().define(
    symbol="Pl",
    name="Plasma",
    origin="emergent",
    layer="energy",
    description="Example custom high-energy element for controlled experiments.",
    properties={"energy_density": 3.5, "volatility": 0.9, "toxic": True},
)

print({"symbols": registry.symbols(), "plasma": registry.require("Pl").to_dict()})
