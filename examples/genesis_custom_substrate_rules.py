"""Use custom substrate rules as Python objects."""

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

from codontrace.genesis import ElementGrid, ElementRegistry, SubstrateRuleConfig

registry = (
    ElementRegistry.genesis_v0()
    .define(symbol="Pl", name="Plasma", origin="emergent", layer="energy")
    .define(symbol="St", name="Steam", origin="emergent", layer="medium")
)
rules = SubstrateRuleConfig.empty().add(inputs=("Pl", "Aq"), output="St", efficiency=0.5)
grid = ElementGrid.from_cells(
    1,
    1,
    {(0, 0): {"Pl": 2.0, "Aq": 2.0}},
    registry=registry,
    rules=rules,
)
result = grid.step()
print({"steam": grid.amount((0, 0), "St"), "result": result.to_dict()})
