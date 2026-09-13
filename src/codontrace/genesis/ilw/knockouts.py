"""ILW edge knockout controls (ILW-2).

Each knockout severs one causal edge (or a declared cut set) while still
emitting attempt telemetry. Cost/throughput matching for sham/yoked controls
is declared but not silently faked into fitness outcomes.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.ilw.dag import IntegrationDAG, load_integration_dag


class IlwKnockoutError(ConfigurationError):
    """Raised when an ILW knockout configuration is invalid."""


@dataclass(frozen=True, slots=True)
class KnockoutConfig:
    """Active edge knockouts for one ILW run."""

    active: frozenset[str] = field(default_factory=frozenset)
    dag: IntegrationDAG = field(default_factory=load_integration_dag, repr=False)

    def __post_init__(self) -> None:
        unknown = sorted(self.active - set(self.dag.knockout_ids))
        if unknown:
            raise IlwKnockoutError(
                "Unknown knockout_id(s): " + ", ".join(unknown)
            )

    @classmethod
    def none(cls, dag: IntegrationDAG | None = None) -> KnockoutConfig:
        return cls(active=frozenset(), dag=dag or load_integration_dag())

    @classmethod
    def only(cls, knockout_id: str, dag: IntegrationDAG | None = None) -> KnockoutConfig:
        return cls(active=frozenset({str(knockout_id)}), dag=dag or load_integration_dag())

    @classmethod
    def from_iterable(
        cls, knockout_ids: Iterable[str], dag: IntegrationDAG | None = None
    ) -> KnockoutConfig:
        return cls(
            active=frozenset(str(item) for item in knockout_ids),
            dag=dag or load_integration_dag(),
        )

    def cuts_edge(self, edge_id: str) -> bool:
        eid = str(edge_id)
        for knockout_id in self.active:
            for raw in self.dag.raw.get("knockouts", ()):
                if not isinstance(raw, Mapping):
                    continue
                if str(raw.get("knockout_id", "")) != knockout_id:
                    continue
                cuts = raw.get("cuts_edge_ids", ())
                if eid in {str(item) for item in cuts}:
                    return True
        return False

    def blocked_reason(self, edge_id: str) -> str | None:
        if not self.cuts_edge(edge_id):
            return None
        for knockout_id in sorted(self.active):
            for raw in self.dag.raw.get("knockouts", ()):
                if not isinstance(raw, Mapping):
                    continue
                if str(raw.get("knockout_id", "")) != knockout_id:
                    continue
                cuts = {str(item) for item in raw.get("cuts_edge_ids", ())}
                if str(edge_id) in cuts:
                    return knockout_id
        return "edge_knockout"

    def to_dict(self) -> dict[str, Any]:
        return {"active": sorted(self.active)}
