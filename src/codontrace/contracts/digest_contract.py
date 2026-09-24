"""Life-loop digest contract: (seed, config_digest) -> world_digest.

Uses ``canonical_digest`` so life-loop extensions share one semantic hash
surface with existing GENESIS evidence artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_real_evidence_digest

SCHEMA_VERSION = "life_loop_digest_v1"


def world_digest(
    seed: int,
    config_digest: str,
    *,
    extras: Mapping[str, Any] | None = None,
    prefix: str = "world",
) -> str:
    """Return a stable world digest from seed + config digest (+ optional extras)."""

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ConfigurationError("seed must be an integer.")
    cfg = require_real_evidence_digest("config_digest", config_digest)
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "seed": seed,
        "config_digest": cfg,
    }
    if extras is not None:
        if not isinstance(extras, Mapping):
            raise ConfigurationError("extras must be a mapping.")
        payload["extras"] = dict(extras)
    return canonical_digest(payload, prefix=prefix)
