"""Integrated Living World (ILW) scaffolding.

ILW-0 provides the integration DAG, fail-first orphan subsystem checks, and an
event consumer that rejects orphan / unregistered edges before any full-world
claim. Claim ceiling stays ``runtime_observation``; scientific name is
``integrated eco-evolutionary runtime`` (not intelligence / AGI / CI).
"""

from __future__ import annotations

from codontrace.genesis.ilw.dag import (
    CLAIM_CEILING,
    REQUIRED_TELEMETRY_FIELDS,
    SCIENTIFIC_NAME,
    IntegrationDAG,
    IntegrationDAGError,
    load_integration_dag,
)
from codontrace.genesis.ilw.event_consumer import (
    OrphanEventError,
    RegisteredEventConsumer,
)
from codontrace.genesis.ilw.orphan import (
    OrphanSubsystemError,
    SubsystemRegistry,
)

__all__ = [
    "CLAIM_CEILING",
    "REQUIRED_TELEMETRY_FIELDS",
    "SCIENTIFIC_NAME",
    "IntegrationDAG",
    "IntegrationDAGError",
    "OrphanEventError",
    "OrphanSubsystemError",
    "RegisteredEventConsumer",
    "SubsystemRegistry",
    "load_integration_dag",
]
