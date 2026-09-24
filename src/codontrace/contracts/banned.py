"""Banned domain-token gate for kernel contract modules.

Tokens are stored as joinable fragments so this file itself does not
embed the forbidden vocabulary as contiguous words. Discipline labels
belong in module config and honesty profiles only.
"""

from __future__ import annotations

# Each entry is concatenated at import time.
_BANNED_PARTS: tuple[tuple[str, ...], ...] = (
    ("inf", "ection"),
    ("inf", "ect"),
    ("viru", "lence"),
    ("viru", "lent"),
    ("para", "site"),
    ("para", "sitic"),
    ("sym", "biont"),
    ("host_", "para", "site"),
    ("red_", "queen"),
    ("red", "queen"),
    ("vac", "cine"),
    ("pha", "ge"),
    ("cri", "spr"),
    ("claim", "gate"),
    ("claim_", "gate"),
    ("refuse_", "list"),
    ("pha", "ge_", "therapy"),
)

BANNED_DOMAIN_TOKENS: frozenset[str] = frozenset("".join(parts) for parts in _BANNED_PARTS)
