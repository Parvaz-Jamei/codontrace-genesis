"""Shared internal type aliases for codontrace.

This module is the single source of truth for lightweight JSON and
coordinate aliases used across the Core Kernel. It is intentionally
internal because these aliases help implementation consistency rather
than define stable public API objects.
"""

from __future__ import annotations

from typing import TypeAlias

Position: TypeAlias = tuple[int, int]

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
JsonDict: TypeAlias = dict[str, JsonValue]
JsonList: TypeAlias = list[JsonValue]
