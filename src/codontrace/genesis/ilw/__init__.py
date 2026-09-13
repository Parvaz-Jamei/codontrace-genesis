"""Integrated Living World (ILW) scaffolding.

ILW-0: integration DAG, fail-first orphan subsystem checks, event consumer.
ILW-1: shared WorldSpec, run-scoped scheduler, append-only event ledger, and
deterministic seed namespace.
ILW-2: full genome→lineage causal chain in a dual-resource world under one
run_id / WorldSpec / scheduler / ledger.

Claim ceiling stays ``runtime_observation``; scientific name is
``integrated eco-evolutionary runtime`` (not intelligence / AGI / CI).
Adapters must not inject fixture outcomes.
"""

from __future__ import annotations

from codontrace.genesis.ilw.adapter_honesty import (
    FORBIDDEN_OUTCOME_INJECTION_KEYS,
    AdapterHonestyError,
    assert_claim_ceiling_runtime_observation,
    assert_no_fixture_outcome_injection,
)
from codontrace.genesis.ilw.chain_runtime import (
    CapsuleRecord,
    IlwChainError,
    IlwChainRuntime,
    IlwOrganism,
)
from codontrace.genesis.ilw.dag import (
    CLAIM_CEILING,
    REQUIRED_TELEMETRY_FIELDS,
    SCIENTIFIC_NAME,
    IntegrationDAG,
    IntegrationDAGError,
    load_integration_dag,
)
from codontrace.genesis.ilw.dual_resource_world import DualResourceWorld, DualResourceWorldError
from codontrace.genesis.ilw.event_consumer import (
    OrphanEventError,
    RegisteredEventConsumer,
)
from codontrace.genesis.ilw.event_ledger import (
    LEDGER_CORE_REQUIRED_FIELDS,
    EventLedger,
    EventLedgerError,
    LedgerEvent,
)
from codontrace.genesis.ilw.knockouts import IlwKnockoutError, KnockoutConfig
from codontrace.genesis.ilw.orphan import (
    OrphanSubsystemError,
    SubsystemRegistry,
)
from codontrace.genesis.ilw.scheduler import IlwScheduler, IlwSchedulerError
from codontrace.genesis.ilw.seed_namespace import SeedNamespace, SeedNamespaceError
from codontrace.genesis.ilw.world_spec import WORLD_SPEC_SCHEMA, WorldSpec, WorldSpecError

__all__ = [
    "CLAIM_CEILING",
    "FORBIDDEN_OUTCOME_INJECTION_KEYS",
    "LEDGER_CORE_REQUIRED_FIELDS",
    "REQUIRED_TELEMETRY_FIELDS",
    "SCIENTIFIC_NAME",
    "WORLD_SPEC_SCHEMA",
    "AdapterHonestyError",
    "CapsuleRecord",
    "DualResourceWorld",
    "DualResourceWorldError",
    "EventLedger",
    "EventLedgerError",
    "IlwChainError",
    "IlwChainRuntime",
    "IlwKnockoutError",
    "IlwOrganism",
    "IlwScheduler",
    "IlwSchedulerError",
    "IntegrationDAG",
    "IntegrationDAGError",
    "KnockoutConfig",
    "LedgerEvent",
    "OrphanEventError",
    "OrphanSubsystemError",
    "RegisteredEventConsumer",
    "SeedNamespace",
    "SeedNamespaceError",
    "SubsystemRegistry",
    "WorldSpec",
    "WorldSpecError",
    "assert_claim_ceiling_runtime_observation",
    "assert_no_fixture_outcome_injection",
    "load_integration_dag",
]
