"""Public CLAIMS.md §5 ladder (0–5) and the 9-rung internal map.

Correspondence only. Mapping an internal rung to a public level does not
unlock a claim, skip evidence, or grant OEE / Tokyo Type 1.
"""

from __future__ import annotations

from codontrace.errors import ConfigurationError
from codontrace.genesis.claim_gate import (
    INTERNAL_TO_PUBLIC_LEVEL,
    PUBLIC_CLAIM_LEVEL_NAMES,
    public_level_for_internal,
)

PUBLIC_LEVEL_MIN = 0
PUBLIC_LEVEL_MAX = 5

# CLAIMS.md §5 names, index = public level.
PUBLIC_LADDER: tuple[tuple[int, str, str], ...] = (
    (0, "software_capability", "Software capability"),
    (1, "runtime_observation", "Runtime observation"),
    (2, "candidate_evidence", "Candidate evidence"),
    (3, "mechanism_support", "Mechanism support"),
    (4, "replicated_effect", "Replicated effect"),
    (5, "publication_grade", "Publication-grade scientific claim"),
)


def public_level_name(level: int) -> str:
    """Return the CLAIMS.md §5 machine name for a public level."""

    if level < PUBLIC_LEVEL_MIN or level > PUBLIC_LEVEL_MAX:
        raise ConfigurationError("public claim level must be an integer 0–5.")
    return PUBLIC_CLAIM_LEVEL_NAMES[level]


def public_level_title(level: int) -> str:
    """Return the CLAIMS.md §5 display name for a public level."""

    if level < PUBLIC_LEVEL_MIN or level > PUBLIC_LEVEL_MAX:
        raise ConfigurationError("public claim level must be an integer 0–5.")
    return PUBLIC_LADDER[level][2]


def require_public_level(level: int) -> int:
    if not isinstance(level, int) or isinstance(level, bool):
        raise ConfigurationError("public claim level must be an integer 0–5.")
    if level < PUBLIC_LEVEL_MIN or level > PUBLIC_LEVEL_MAX:
        raise ConfigurationError("public claim level must be an integer 0–5.")
    return level


__all__ = [
    "INTERNAL_TO_PUBLIC_LEVEL",
    "PUBLIC_CLAIM_LEVEL_NAMES",
    "PUBLIC_LADDER",
    "PUBLIC_LEVEL_MAX",
    "PUBLIC_LEVEL_MIN",
    "public_level_for_internal",
    "public_level_name",
    "public_level_title",
    "require_public_level",
]
