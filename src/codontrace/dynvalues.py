"""Coercions that call the same constructors ``int`` and ``float`` already call.

Use these where a JSON or registry value is typed ``object``. They do not
reject a value that ``int`` or ``float`` would accept, and they raise the
same exception class the builtin would raise.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, cast


def same_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    if isinstance(value, (bytes, bytearray)):
        return int(value)
    return int(cast(Any, value))


def same_float(value: object) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float, str)):
        return float(value)
    if isinstance(value, (bytes, bytearray)):
        return float(value)
    return float(value)  # type: ignore[arg-type]


def same_str(value: object) -> str:
    if isinstance(value, str):
        return value
    return str(value)


def same_iter(value: object) -> Iterable[object]:
    if isinstance(value, Iterable):
        return value
    return cast(Iterable[object], iter(cast(Any, value)))


def same_mapping(value: object) -> Mapping[object, object]:
    if isinstance(value, Mapping):
        return value
    raise TypeError(
        f"{type(value).__name__!r} object is not a mapping"
    )
