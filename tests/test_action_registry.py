from __future__ import annotations

import pytest

from codontrace import ActionContext, ActionResult, default_action_registry
from codontrace.world import World2D


def rest_handler(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        status="executed",
        reason="rested",
        position_after=ctx.position,
        world_delta={"rest": True},
    )


def test_action_registry_extend_does_not_mutate_original() -> None:
    base = default_action_registry()
    extended = base.extend("REST", rest_handler)
    assert base.get("REST") is None
    assert extended.get("REST") is rest_handler


def test_action_registry_replace_does_not_mutate_original() -> None:
    base = default_action_registry()
    replaced = base.replace("WAIT", rest_handler)
    world = World2D(3, 3)
    ctx = ActionContext("a", (1, 1), "000", "WAIT", 0, world)
    assert base.get("WAIT") is not rest_handler
    assert replaced.get("WAIT") is rest_handler
    assert replaced.get("WAIT") is not None
    assert replaced.get("WAIT")(ctx).reason == "rested"


def test_action_registry_rejects_invalid_names() -> None:
    with pytest.raises(ValueError):
        default_action_registry().extend("rest", rest_handler)
