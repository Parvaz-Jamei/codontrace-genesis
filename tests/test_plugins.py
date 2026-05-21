from __future__ import annotations

from dataclasses import dataclass

from codontrace import ActionRegistry
from codontrace.actions import ActionContext, ActionResult, default_action_registry
from codontrace.plugins import discover_action_plugins


def rest(ctx: ActionContext) -> ActionResult:
    return ActionResult(status="executed", reason="rested", position_after=ctx.position)


@dataclass(frozen=True)
class FakeEntryPoint:
    name: str = "fake"

    def load(self):  # type: ignore[no-untyped-def]
        def register(registry: ActionRegistry) -> ActionRegistry:
            return registry.extend("REST", rest)

        return register


def test_discover_action_plugins_with_mocked_entry_points(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setattr("codontrace.plugins.entry_points", lambda group: (FakeEntryPoint(),))

    registry = discover_action_plugins(default_action_registry())

    assert registry.get("REST") is not None
