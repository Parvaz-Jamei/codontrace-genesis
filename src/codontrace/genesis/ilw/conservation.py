"""ILW-3 conservation assays for energy/resources.

Honest accounting only: world resources reconcile against harvest + renewal
telemetry; organism energy stays non-negative; harvest conversion matches
``taken * harvest_gain_scale`` after metabolism on the same world step.
Does not claim closed-system energy conservation (metabolism dissipates).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError

if TYPE_CHECKING:
    from codontrace.genesis.ilw.chain_runtime import IlwChainRuntime


class IlwConservationError(ConfigurationError):
    """Raised when an ILW conservation invariant fails."""


@dataclass(frozen=True, slots=True)
class ConservationReport:
    """Result of ILW resource/energy conservation checks."""

    passed: bool
    resource_ok: bool
    energy_nonnegative_ok: bool
    harvest_conversion_ok: bool
    resource_errors: tuple[str, ...]
    energy_errors: tuple[str, ...]
    harvest_errors: tuple[str, ...]
    initial_totals: dict[str, float]
    final_totals: dict[str, float]
    harvested: dict[str, float]
    renewed: dict[str, float]
    atol: float

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "passed": self.passed,
            "resource_ok": self.resource_ok,
            "energy_nonnegative_ok": self.energy_nonnegative_ok,
            "harvest_conversion_ok": self.harvest_conversion_ok,
            "resource_errors": list(self.resource_errors),
            "energy_errors": list(self.energy_errors),
            "harvest_errors": list(self.harvest_errors),
            "initial_totals": dict(self.initial_totals),
            "final_totals": dict(self.final_totals),
            "harvested": dict(self.harvested),
            "renewed": dict(self.renewed),
            "atol": self.atol,
        }


def check_conservation(
    runtime: IlwChainRuntime,
    *,
    atol: float = 1e-9,
    raise_on_fail: bool = False,
) -> ConservationReport:
    """Verify resource reconciliation + energy non-negativity + harvest conversion."""

    if atol < 0:
        raise IlwConservationError("atol must be non-negative.")

    initial = runtime.initial_resource_totals
    final = dict(runtime.world.totals())
    harvested: dict[str, float] = defaultdict(float)
    renewed: dict[str, float] = defaultdict(float)
    resource_errors: list[str] = []
    energy_errors: list[str] = []
    harvest_errors: list[str] = []

    # Resources never negative at end.
    for kind, amount in final.items():
        if amount < -atol:
            resource_errors.append(f"negative final total for {kind!r}: {amount}")

    for event in runtime.ledger.events:
        payload = event.payload
        edge_id = event.edge_id
        if edge_id == "action_to_resource_world":
            kind = str(payload.get("kind", "") or "")
            taken = float(payload.get("taken", 0.0) or 0.0)
            if kind:
                harvested[kind] += taken
            action = str(payload.get("action", ""))
            if action in {"HARVEST_0", "HARVEST_1"} and int(payload.get("applied", 0) or 0) > 0:
                energy_delta = float(payload.get("energy_delta", 0.0) or 0.0)
                expected = taken * float(runtime.harvest_gain_scale) - float(runtime.metabolism)
                if abs(energy_delta - expected) > atol:
                    harvest_errors.append(
                        f"event {payload.get('event_id')}: energy_delta {energy_delta} "
                        f"!= taken*scale - metabolism {expected}"
                    )
            if taken < -atol:
                resource_errors.append(
                    f"negative harvest taken on {payload.get('event_id')}: {taken}"
                )
        elif edge_id == "ecological_feedback":
            deltas = payload.get("renewal_deltas") or {}
            if isinstance(deltas, Mapping):
                for kind, value in deltas.items():
                    renewed[str(kind)] += float(value)

    for kind in sorted(set(initial) | set(final) | set(harvested) | set(renewed)):
        pred = float(initial.get(kind, 0.0)) - float(harvested.get(kind, 0.0)) + float(
            renewed.get(kind, 0.0)
        )
        got = float(final.get(kind, 0.0))
        if abs(pred - got) > atol:
            resource_errors.append(
                f"resource {kind!r}: predicted {pred} != final {got} "
                f"(initial={initial.get(kind, 0.0)}, harvested={harvested.get(kind, 0.0)}, "
                f"renewed={renewed.get(kind, 0.0)})"
            )

    for org in runtime.organisms:
        if org.energy < -atol:
            energy_errors.append(
                f"organism {org.organism_id} has negative energy {org.energy}"
            )

    resource_ok = not resource_errors
    energy_ok = not energy_errors
    harvest_ok = not harvest_errors
    report = ConservationReport(
        passed=resource_ok and energy_ok and harvest_ok,
        resource_ok=resource_ok,
        energy_nonnegative_ok=energy_ok,
        harvest_conversion_ok=harvest_ok,
        resource_errors=tuple(resource_errors),
        energy_errors=tuple(energy_errors),
        harvest_errors=tuple(harvest_errors),
        initial_totals={k: float(v) for k, v in sorted(initial.items())},
        final_totals={k: float(v) for k, v in sorted(final.items())},
        harvested={k: float(v) for k, v in sorted(harvested.items())},
        renewed={k: float(v) for k, v in sorted(renewed.items())},
        atol=float(atol),
    )
    if raise_on_fail and not report.passed:
        details = "; ".join(
            list(report.resource_errors)
            + list(report.energy_errors)
            + list(report.harvest_errors)
        )
        raise IlwConservationError(f"ILW conservation failed: {details}")
    return report
