"""Configurable action status semantics for GENESIS trace analysis."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType

from codontrace._types import JsonValue


@dataclass(frozen=True, slots=True)
class ActionStatusDefinition:
    name: str
    category: str
    counts_as_executed: bool
    counts_as_blocked: bool
    counts_as_failed: bool
    counts_as_deferred: bool = False

    def __post_init__(self) -> None:
        if not self.name or not self.category:
            msg = "ActionStatusDefinition name/category must not be empty."
            raise ValueError(msg)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "category": self.category,
            "counts_as_executed": self.counts_as_executed,
            "counts_as_blocked": self.counts_as_blocked,
            "counts_as_failed": self.counts_as_failed,
            "counts_as_deferred": self.counts_as_deferred,
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ActionStatusDefinition:
        name = data.get("name")
        category = data.get("category")
        if not isinstance(name, str) or not isinstance(category, str):
            msg = "ActionStatusDefinition requires string name/category."
            raise ValueError(msg)
        return cls(
            name=name,
            category=category,
            counts_as_executed=_bool(data, "counts_as_executed", False),
            counts_as_blocked=_bool(data, "counts_as_blocked", False),
            counts_as_failed=_bool(data, "counts_as_failed", False),
            counts_as_deferred=_bool(data, "counts_as_deferred", False),
        )


class ActionStatusRegistry:
    """Immutable registry for trace status categories."""

    def __init__(
        self,
        definitions: tuple[ActionStatusDefinition, ...] = (),
        *,
        open_statuses: bool = False,
    ) -> None:
        mapping: dict[str, ActionStatusDefinition] = {}
        for definition in definitions:
            if definition.name in mapping:
                msg = f"Duplicate action status {definition.name!r}."
                raise ValueError(msg)
            mapping[definition.name] = definition
        self._definitions = MappingProxyType(mapping)
        self.open_statuses = open_statuses

    @classmethod
    def genesis_v0(cls) -> ActionStatusRegistry:
        return cls(
            (
                ActionStatusDefinition("executed", "executed", True, False, False),
                ActionStatusDefinition("blocked", "blocked", False, True, False),
                ActionStatusDefinition("failed", "failed", False, False, True),
            )
        )

    def define(
        self,
        name: str,
        category: str,
        *,
        counts_as_executed: bool,
        counts_as_blocked: bool,
        counts_as_failed: bool,
        counts_as_deferred: bool = False,
    ) -> ActionStatusRegistry:
        definition = ActionStatusDefinition(
            name,
            category,
            counts_as_executed,
            counts_as_blocked,
            counts_as_failed,
            counts_as_deferred,
        )
        if definition.name in self._definitions:
            msg = f"Action status {definition.name!r} is already registered."
            raise ValueError(msg)
        return ActionStatusRegistry(
            (*self._definitions.values(), definition), open_statuses=self.open_statuses
        )

    def get(self, name: str) -> ActionStatusDefinition:
        if name in self._definitions:
            return self._definitions[name]
        if self.open_statuses:
            return ActionStatusDefinition(name, "custom", False, False, False)
        msg = f"Unknown action status {name!r}."
        raise ValueError(msg)

    def category(self, name: str) -> str:
        return self.get(name).category

    def counts_as_executed(self, name: str) -> bool:
        return self.get(name).counts_as_executed

    def counts_as_blocked(self, name: str) -> bool:
        definition = self.get(name)
        return definition.counts_as_blocked or definition.counts_as_failed

    def counts_as_failed(self, name: str) -> bool:
        return self.get(name).counts_as_failed

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "open_statuses": self.open_statuses,
            "definitions": [
                self._definitions[name].to_dict() for name in sorted(self._definitions)
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, JsonValue]) -> ActionStatusRegistry:
        raw = data.get("definitions")
        if not isinstance(raw, list):
            msg = "ActionStatusRegistry.definitions must be a list."
            raise ValueError(msg)
        definitions = []
        for item in raw:
            if not isinstance(item, dict):
                msg = "ActionStatusRegistry entries must be objects."
                raise ValueError(msg)
            definitions.append(ActionStatusDefinition.from_dict(item))
        return cls(tuple(definitions), open_statuses=_bool(data, "open_statuses", False))

    def digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _bool(data: dict[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        msg = f"{key} must be a boolean."
        raise ValueError(msg)
    return value
