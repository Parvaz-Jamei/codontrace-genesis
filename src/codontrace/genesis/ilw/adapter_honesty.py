"""ILW adapter honesty guards (ILW-1).

ILW must not inject fixture outcomes into ClaimGate adapters or the event
ledger. Claim ceiling remains ``runtime_observation``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.ilw.dag import CLAIM_CEILING

FORBIDDEN_OUTCOME_INJECTION_KEYS: frozenset[str] = frozenset(
    {
        "fixture_outcome",
        "injected_outcome",
        "oracle_outcome",
        "treatment_oracle",
        "fitness_shortcut",
        "fabricated_fitness",
    }
)


class AdapterHonestyError(ConfigurationError):
    """Raised when fixture / oracle outcome injection is detected."""


def assert_no_fixture_outcome_injection(payload: Mapping[str, Any]) -> None:
    """Reject payloads that attempt to inject fixture or oracle outcomes."""

    banned = sorted(key for key in payload if key in FORBIDDEN_OUTCOME_INJECTION_KEYS)
    if banned:
        raise AdapterHonestyError(
            "Fixture/oracle outcome injection is forbidden in ILW adapters: "
            + ", ".join(banned)
        )


def assert_claim_ceiling_runtime_observation(ceiling: str = CLAIM_CEILING) -> None:
    if ceiling != CLAIM_CEILING:
        raise AdapterHonestyError(
            f"ILW ClaimGate ceiling must remain {CLAIM_CEILING!r}; got {ceiling!r}."
        )
