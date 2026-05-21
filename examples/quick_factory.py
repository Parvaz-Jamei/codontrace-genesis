"""Quick factory example for codontrace current alpha."""

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

from codontrace import CausalReplay, WhiteBoxAgent, World2D

world = World2D.from_ascii(
    """
....
.A*.
....
"""
)

agent = WhiteBoxAgent.quick(
    genome=["101", "111", "000"],
    atp=5.0,
    position=(1, 1),
)

trace = agent.run(world, steps=3)
explanation = CausalReplay.explain_last_action(trace)

print(world.render_ascii())
print(explanation.summary)
