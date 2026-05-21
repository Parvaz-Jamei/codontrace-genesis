"""Canonical payload, finite-number, and digest helpers for GENESIS evidence.

All Phase 2 scientific artifacts should use this path rather than ad-hoc JSON
serialization.  It rejects NaN/Infinity, sorts mappings, canonicalizes tuples,
and avoids process-specific object representations in digest payloads.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

from codontrace._numeric import finite_float, finite_json_dumps
from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError



_PLACEHOLDER_DIGEST_VALUES = {
    "",
    "none",
    "null",
    "placeholder",
    "default",
    "fake",
    "disabled",
    "not_run",
    "not_configured",
    "fixed_default",
    "sha256:placeholder",
}
_REAL_HEX_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSIONED_DIGEST_RE = re.compile(r"^[a-z][a-z0-9_\-]*:[0-9a-f]{32,}$")


PHASE3_STATUS_VALUES = {
    "measured",
    "runtime_effective",
    "claim_ready",
    "provisional",
    "empty_but_available",
    "not_run",
    "disabled_by_config",
    "not_applicable",
    "negative_result_pack",
    "incomplete_evidence",
    "replay_bundle_missing",
    "claim_manifest_missing",
    "placeholder_digest_rejected",
}
PHASE3_CLAIM_GRADE_STATUSES = {"measured", "runtime_effective", "claim_ready"}


def require_phase3_status(name: str, value: object) -> str:
    if not isinstance(value, str) or value not in PHASE3_STATUS_VALUES:
        raise ConfigurationError(f"{name} must be one of the canonical Phase 3 statuses.")
    return value


def is_real_evidence_digest(value: object) -> bool:
    """Return True only for deterministic, non-placeholder evidence digests.

    This deliberately rejects ``fake``, ``placeholder``, ``default``,
    ``not_run:*`` and ``disabled:*`` strings so final scientific claim objects
    cannot look measured while pointing at absent evidence.  Plain SHA-256 hex
    digests and versioned digests such as ``replay:<hex>`` are accepted.
    """

    if not isinstance(value, str):
        return False
    text = value.strip()
    lowered = text.lower()
    if lowered in _PLACEHOLDER_DIGEST_VALUES:
        return False
    if lowered.startswith(("not_run:", "disabled:", "fake:", "placeholder:", "default:")):
        return False
    if _REAL_HEX_DIGEST_RE.fullmatch(lowered):
        return True
    return bool(_VERSIONED_DIGEST_RE.fullmatch(lowered))


def require_real_evidence_digest(name: str, value: object) -> str:
    """Return a real evidence digest or raise ``ConfigurationError``."""

    if not is_real_evidence_digest(value):
        raise ConfigurationError(f"{name} must be a real evidence digest.")
    return str(value).strip()


def require_finite_float(name: str, value: object, *, non_negative: bool = False, probability: bool = False) -> float:
    """Return a finite float or raise ``ConfigurationError``."""

    out = finite_float(name, value, non_negative=non_negative, probability=probability)
    assert out is not None
    return out


def canonical_payload(value: Any) -> JsonValue:
    """Return a deterministic JSON-compatible payload and reject NaN/Inf.

    Objects with ``to_dict`` are accepted as evidence objects.  Raw arbitrary
    objects are rejected because their repr/address would make digests unstable.
    """

    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return require_finite_float("payload_float", value)
    if isinstance(value, Mapping):
        return {str(k): canonical_payload(value[k]) for k in sorted(value, key=lambda item: str(item))}
    if isinstance(value, tuple | list):
        return [canonical_payload(item) for item in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return canonical_payload(to_dict())
    raise ConfigurationError(f"Unsupported non-canonical payload type: {type(value).__name__}")


def reject_nan_inf_payload(value: Any) -> JsonValue:
    """Alias used by validators that need a named non-finite guard."""

    return canonical_payload(value)


def canonical_json(value: Any) -> str:
    payload = canonical_payload(value)
    return finite_json_dumps(payload, sort_keys=True, separators=(",", ":"))


def canonical_digest(value: Any, *, prefix: str | None = None) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}" if prefix else digest
