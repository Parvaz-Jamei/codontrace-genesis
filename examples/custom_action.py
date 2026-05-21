"""Custom action example for codontrace current alpha."""

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

from codontrace import ATPAccount, Codon, CodonTable, SemanticGenome, Trace, WhiteBoxAgent, World2D
from codontrace.actions import ActionContext, ActionResult, default_action_registry


def rest_handler(ctx: ActionContext) -> ActionResult:
    return ActionResult.executed(
        reason="rested",
        position_after=ctx.position,
        world_delta={"rest": True},
    )


table = CodonTable.default_minimal().replace(Codon("001", "REST", 0.0, "Recover without moving."))
registry = default_action_registry().extend("REST", rest_handler)
world = World2D.from_ascii(
    """
...
.A.
...
"""
)
agent = WhiteBoxAgent(
    id="a1",
    genome=SemanticGenome.from_codons(["001"]),
    codon_table=table,
    atp_account=ATPAccount(5.0),
    position=(1, 1),
    action_registry=registry,
)
trace = Trace()
event = agent.step(world, trace)

print(event.action)
print(event.reason)
print(trace.to_json())
