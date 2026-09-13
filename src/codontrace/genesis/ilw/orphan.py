"""Fail-first orphan subsystem registry for ILW-0.

Any subsystem declared in the integration DAG without a registered consumer, or
any registered subsystem absent from the DAG, fails loudly before a full-world
claim is allowed.
"""

from __future__ import annotations

from collections.abc import Iterable

from codontrace.errors import ConfigurationError
from codontrace.genesis.ilw.dag import IntegrationDAG, load_integration_dag


class OrphanSubsystemError(ConfigurationError):
    """Raised when subsystems are missing from or extra to the integration DAG."""


class SubsystemRegistry:
    """Tracks which DAG subsystems have a registered implementation/consumer."""

    def __init__(self, dag: IntegrationDAG | None = None) -> None:
        self._dag = dag if dag is not None else load_integration_dag()
        self._registered: set[str] = set()

    @property
    def dag(self) -> IntegrationDAG:
        return self._dag

    @property
    def registered(self) -> frozenset[str]:
        return frozenset(self._registered)

    def register(self, subsystem_id: str) -> None:
        sid = str(subsystem_id).strip()
        if not sid:
            raise OrphanSubsystemError("subsystem_id must be non-empty.")
        if sid not in self._dag.subsystem_ids:
            raise OrphanSubsystemError(
                f"Refusing to register orphan subsystem {sid!r}: "
                "not declared in INTEGRATION_DAG.json."
            )
        self._registered.add(sid)

    def register_many(self, subsystem_ids: Iterable[str]) -> None:
        for subsystem_id in subsystem_ids:
            self.register(subsystem_id)

    def assert_no_orphans(self) -> None:
        missing = sorted(self._dag.subsystem_ids - self._registered)
        if missing:
            raise OrphanSubsystemError(
                "Orphan / unregistered subsystems block full-world claim: "
                + ", ".join(missing)
            )

    def assert_ready_for_world_claim(self, observed_edge_ids: Iterable[str]) -> None:
        """Fail-first gate: no orphan subsystems and all required edges observed."""

        self.assert_no_orphans()
        self._dag.assert_required_edges_present(observed_edge_ids)
