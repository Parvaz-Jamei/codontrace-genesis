"""Plugin discovery for third-party codontrace action packages."""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import cast

from codontrace.actions import ActionRegistry, default_action_registry
from codontrace.errors import PluginError

RegisterActions = Callable[[ActionRegistry], ActionRegistry]


def discover_action_plugins(
    registry: ActionRegistry | None = None,
    *,
    group: str = "codontrace.actions",
) -> ActionRegistry:
    """Discover and apply action plugins registered via package entry points.

    A plugin entry point must load a callable with signature::

        def register_actions(registry: ActionRegistry) -> ActionRegistry: ...
    """

    resolved = registry or default_action_registry()
    try:
        discovered = entry_points(group=group)
    except Exception as exc:  # pragma: no cover - defensive around package metadata
        msg = f"Could not read action plugin entry points for group {group!r}."
        raise PluginError(msg) from exc
    for entry_point in discovered:
        try:
            raw_register = entry_point.load()
        except Exception as exc:
            msg = f"Could not load codontrace action plugin {entry_point.name!r}."
            raise PluginError(msg) from exc
        if not callable(raw_register):
            msg = f"Action plugin {entry_point.name!r} did not load a callable."
            raise PluginError(msg)
        register = cast(RegisterActions, raw_register)
        try:
            updated = register(resolved)
        except Exception as exc:
            msg = f"Action plugin {entry_point.name!r} failed while registering actions."
            raise PluginError(msg) from exc
        if not isinstance(updated, ActionRegistry):
            msg = f"Action plugin {entry_point.name!r} must return an ActionRegistry."
            raise PluginError(msg)
        resolved = updated
    return resolved
