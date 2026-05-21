"""Strict finite numeric validation for GENESIS evidence-bearing paths."""

from __future__ import annotations

import json
import math
from typing import Any

from codontrace.errors import ConfigurationError


def finite_float(
    name: str,
    value: object,
    *,
    non_negative: bool = False,
    probability: bool = False,
    allow_none: bool = False,
) -> float | None:
    """Return ``value`` as a finite float or raise ``ConfigurationError``.

    Python accepts ``NaN``/``Inf`` in many float and JSON paths by default, but those
    values are not valid JSON numbers and poison deterministic comparisons/digests.
    GENESIS evidence uses this validator at construction and archive/export edges.
    """

    if value is None and allow_none:
        return None
    if isinstance(value, bool):
        raise ConfigurationError(f"{name} must be numeric, not boolean")
    try:
        out = float(value)  # type: ignore[arg-type]
    except Exception as exc:  # pragma: no cover - defensive conversion guard
        raise ConfigurationError(f"{name} must be numeric") from exc
    if not math.isfinite(out):
        raise ConfigurationError(f"{name} must be finite")
    if non_negative and out < 0.0:
        raise ConfigurationError(f"{name} must be non-negative")
    if probability and not (0.0 <= out <= 1.0):
        raise ConfigurationError(f"{name} must be in [0, 1]")
    return out


def finite_json_dumps(payload: Any, **kwargs: Any) -> str:
    """JSON serializer for evidence/digest payloads with ``allow_nan=False``."""

    return json.dumps(payload, allow_nan=False, **kwargs)
