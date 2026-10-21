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

__all__ = ['IDENTIFIER_PATTERN', 'MAX_JSON_DEPTH', 'bounded_int', 'bounded_text', 'exact_keys',
           'finite_number', 'identifier', 'json_depth_within', 'wire_canonical']

# Untrusted JSON may nest at most this many arrays/objects. CPython's json
# decoder recurses once per level, so a deep body (e.g. 5000 '[') raises
# RecursionError, which is not a ValueError. Wire messages nest < 10 levels.
MAX_JSON_DEPTH = 64


def json_depth_within(text: str | bytes, limit: int = MAX_JSON_DEPTH) -> bool:
    """True when the JSON text never nests more than ``limit`` arrays/objects.

    A linear scan before ``json.loads``: brackets inside strings (including
    escaped quotes) are ignored. It does not validate the JSON; the parser
    still does that. ``limit`` must be >= 1.
    """
    data = text.encode('utf-8', 'surrogatepass') if isinstance(text, str) else bytes(text)
    depth = 0
    in_string = False
    escaped = False
    for byte in data:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:  # backslash
                escaped = True
            elif byte == 0x22:  # quote
                in_string = False
        elif byte == 0x22:
            in_string = True
        elif byte in (0x5B, 0x7B):  # [ {
            depth += 1
            if depth > limit:
                return False
        elif byte in (0x5D, 0x7D):  # ] }
            depth -= 1
    return True


def loads_bounded(text: str | bytes, limit: int = MAX_JSON_DEPTH, **kwargs: Any) -> Any:
    """``json.loads`` that rejects nesting deeper than ``limit`` before parsing.

    Too-deep input raises ``json.JSONDecodeError`` (a ``ValueError``), the
    same exception as any other malformed JSON, so callers keep one error
    path and never see RecursionError. Other argument types go straight to
    ``json.loads``, which raises TypeError as before.
    """
    if isinstance(text, (str, bytes, bytearray)) and not json_depth_within(bytes(text) if isinstance(text, bytearray) else text, limit):
        doc = text if isinstance(text, str) else bytes(text).decode('utf-8', 'replace')
        raise json.JSONDecodeError(f'JSON nesting deeper than {limit} levels', doc, 0)
    return json.loads(text, **kwargs)


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
