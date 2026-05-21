"""Skeleton for a third-party action plugin package.

In a real plugin package, expose this in pyproject.toml:

[project.entry-points."codontrace.actions"]
my_actions = "my_package.actions:register_actions"
"""

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

from codontrace import ActionContext, ActionRegistry, ActionResult, EnergyEffect


def rest_handler(ctx: ActionContext) -> ActionResult:
    return ActionResult.executed(
        reason="rested",
        position_after=ctx.position,
        world_delta={"rest": True},
        energy=EnergyEffect(credit=0.25, reason="rest_recovery"),
    )


def register_actions(registry: ActionRegistry) -> ActionRegistry:
    return registry.extend("REST", rest_handler)


print(register_actions(ActionRegistry()).names())
