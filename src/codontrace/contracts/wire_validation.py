"""Wire-level validators and canonical JSON for untrusted external payloads.

Domain-free helpers shared by device protocols, frame exports and console
readers. Every function raises ``ValueError`` with a short, payload-free
message so callers can return it to an untrusted client. Standard library
only; nothing here imports the rest of the engine.

``wire_canonical`` is the byte format used for wire messages, swarm
journals, checkpoints and their SHA-256 links: ``json.dumps`` with sorted
keys, no whitespace, ASCII escaping and no NaN/Infinity. It is deterministic
for one Python implementation but it is not RFC 8785 (JCS): keys sort by
code point rather than UTF-16 code unit and floats use Python ``repr``.
Changing it would change every journal digest, so it is frozen.
"""
from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from typing import Any

__all__ = ['IDENTIFIER_PATTERN', 'bounded_int', 'bounded_text', 'exact_keys', 'finite_number', 'identifier',
           'wire_canonical']

IDENTIFIER_PATTERN = r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}'
_IDENTIFIER = re.compile(IDENTIFIER_PATTERN)


def identifier(value: Any) -> str:
    """ASCII letter/digit first, then up to 63 letters, digits, ``_`` or ``-``."""
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError('invalid identifier')
    return value


def finite_number(value: Any, *, low: float = -1e12, high: float = 1e12) -> float:
    """A finite int or float (not bool) within ``[low, high]``, returned as float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('finite number required')
    # Range-check integers before float conversion to avoid OverflowError on hostile JSON.
    if not low <= value <= high:
        raise ValueError('number outside supported range')
    if not math.isfinite(value):
        raise ValueError('finite number required')
    return float(value)


def bounded_int(value: Any, *, high: int = 2**53 - 1) -> int:
    """An exact ``int`` (not bool, not a subclass) within ``[0, high]``."""
    if type(value) is not int or not 0 <= value <= high:
        raise ValueError('bounded nonnegative integer required')
    return value


def bounded_text(value: Any, maximum: int = 96) -> str:
    """A string with non-whitespace content and at most ``maximum`` characters."""
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError('bounded nonempty string required')
    return value


def exact_keys(value: Any, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    """A mapping with every ``required`` key, optionally some ``optional`` keys, nothing else."""
    if not isinstance(value, Mapping) or not required <= value.keys() or value.keys() - required - (optional or set()):
        raise ValueError('missing or unknown fields')
    return dict(value)


def wire_canonical(value: Any) -> str:
    """Frozen canonical JSON text (see module docstring); hash its UTF-8 encoding."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
