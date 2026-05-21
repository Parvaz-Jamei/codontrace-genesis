"""Run artifact, manifest, snapshot, and evidence schemas for GENESIS UI/API use.

The core library returns ordinary Python objects. Exporters are optional and do
not write files unless a caller explicitly asks.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NewType, Protocol, cast

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.claim_gate import ClaimDecision

_PACKAGE_VERSION = "0.3.0a1"

RunId = NewType("RunId", str)
ConfigHash = NewType("ConfigHash", str)
ArtifactDigest = NewType("ArtifactDigest", str)


@dataclass(frozen=True, slots=True)
class ReviewStatus:
    """Review state included in manifests and UI snapshots."""

    status: str = "not_reviewed"
    reviewer: str | None = None
    decision_digest: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "status": self.status,
            "reviewer": self.reviewer,
            "decision_digest": self.decision_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ReviewStatus:
        return _review_status_from_dict(cls, data)


@dataclass(frozen=True, slots=True)
class AgentSnapshot:
    """Serializable snapshot of one organism/agent."""

    organism_id: str
    genome_digest: str
    runtime_atp: float
    learning_atp: float
    position: tuple[int, int]
    causal_graph_digest: str | None = None
    memory_digest: str | None = None

    @classmethod
    def from_organism(cls, organism: object) -> AgentSnapshot:
        org = cast(Any, organism)
        graph = getattr(org, "causal_graph", None)
        memory = getattr(org, "episodic_memory", None)
        atp_state = org.atp_state
        genome = org.genome
        pos = tuple(org.position)
        if len(pos) != 2:
            raise ConfigurationError("organism.position must contain two coordinates")
        return cls(
            organism_id=str(org.id),
            genome_digest=str(genome.digest()),
            runtime_atp=round(float(atp_state.runtime_available), 10),
            learning_atp=round(float(atp_state.learning_available), 10),
            position=(
                _json_int_value(pos[0], "position[0]"),
                _json_int_value(pos[1], "position[1]"),
            ),
            causal_graph_digest=None if graph is None else str(graph.digest()),
            memory_digest=None if memory is None else str(memory.digest()),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "genome_digest": self.genome_digest,
            "runtime_atp": self.runtime_atp,
            "learning_atp": self.learning_atp,
            "position": [self.position[0], self.position[1]],
            "causal_graph_digest": self.causal_graph_digest,
            "memory_digest": self.memory_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> AgentSnapshot:
        return _agent_snapshot_from_dict(cls, data)


@dataclass(frozen=True, slots=True)
class PopulationSnapshot:
    """Population snapshot for replay/UI boundaries."""

    generation: int
    tick: int
    agents: tuple[AgentSnapshot, ...]
    population_digest: str
    nexus_digest: str | None = None

    @classmethod
    def from_population(
        cls, population: object, nexus_layer: object | None = None
    ) -> PopulationSnapshot:
        pop = cast(Any, population)
        nexus = cast(Any, nexus_layer)
        agents = tuple(AgentSnapshot.from_organism(item) for item in pop.organisms)
        return cls(
            generation=int(pop.generation),
            tick=int(pop.tick),
            agents=agents,
            population_digest=str(pop.digest()),
            nexus_digest=None if nexus_layer is None else str(nexus.digest()),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "generation": self.generation,
            "tick": self.tick,
            "agents": [item.to_dict() for item in self.agents],
            "population_digest": self.population_digest,
            "nexus_digest": self.nexus_digest,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> PopulationSnapshot:
        return _population_snapshot_from_dict(cls, data)

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class RawEventSchema:
    """Stable representation of one raw event bundle."""

    event_index: int
    event_digest: str
    payload: dict[str, JsonValue]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "event_index": self.event_index,
            "event_digest": self.event_digest,
            "payload": dict(self.payload),
        }


@dataclass(frozen=True, slots=True)
class ExperimentSummary:
    """Compact summary of a run for UI cards and external review."""

    run_id: str
    ticks: int
    generations: int
    final_population: int
    best_fitness: float
    mean_fitness: float
    causal_updates: int = 0
    capsules_emitted: int = 0
    capsules_adopted: int = 0
    qd_filled_bins: int = 0
    raw_best_fitness: float | None = None
    raw_mean_fitness: float | None = None
    selection_best_fitness: float | None = None
    selection_mean_fitness: float | None = None
    viable_best_fitness: float | None = None
    viable_mean_fitness: float | None = None
    viability_gate_failures: int = 0
    mean_fitness_alias: str = "raw_mean_fitness"
    best_fitness_alias: str = "raw_best_fitness"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "run_id": self.run_id,
            "ticks": self.ticks,
            "generations": self.generations,
            "final_population": self.final_population,
            "best_fitness": self.best_fitness,
            "mean_fitness": self.mean_fitness,
            "causal_updates": self.causal_updates,
            "capsules_emitted": self.capsules_emitted,
            "capsules_adopted": self.capsules_adopted,
            "qd_filled_bins": self.qd_filled_bins,
            "raw_best_fitness": self.raw_best_fitness if self.raw_best_fitness is not None else self.best_fitness,
            "raw_mean_fitness": self.raw_mean_fitness if self.raw_mean_fitness is not None else self.mean_fitness,
            "selection_best_fitness": self.selection_best_fitness if self.selection_best_fitness is not None else self.best_fitness,
            "selection_mean_fitness": self.selection_mean_fitness if self.selection_mean_fitness is not None else self.mean_fitness,
            "viable_best_fitness": self.viable_best_fitness if self.viable_best_fitness is not None else self.best_fitness,
            "viable_mean_fitness": self.viable_mean_fitness if self.viable_mean_fitness is not None else self.mean_fitness,
            "viability_gate_failures": self.viability_gate_failures,
            "mean_fitness_alias": self.mean_fitness_alias,
            "best_fitness_alias": self.best_fitness_alias,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class DiscoveryRecord:
    """Evidence-linked discovery candidate record, not a proof object."""

    candidate_id: str
    status: str
    reason: str
    manifest_digest: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "candidate_id": self.candidate_id,
            "status": self.status,
            "reason": self.reason,
            "manifest_digest": self.manifest_digest,
        }


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Deterministic run manifest for audit/replay/UI integration."""

    run_id: str
    seed: int
    config_hash: str
    codon_table_hash: str
    genome_spec_hash: str
    rule_set_hash: str
    adf_vocabulary_hash: str
    initial_population_hash: str
    tick_count: int
    replay_digest: str
    source_digest: str | None = None
    rng_backend_kind: str | None = None
    rng_namespace: str | None = None
    rng_draw_count: int | None = None
    rng_state_digest: str | None = None
    seed_schedule_digest: str | None = None
    protocol_version: str = "scientific_manifest_phase1"
    fitness_config_hash: str | None = None
    descriptor_schema_hash: str | None = None
    archive_digest: str | None = None
    qd_scheduler_digest: str | None = None
    benchmark_scenario_digest: str | None = None
    execution_source_digest: str | None = None
    claim_gate_decision_digest: str | None = None
    runtime_hashes: dict[str, str | None] = field(default_factory=dict)
    package_version: str = _PACKAGE_VERSION
    claim_level: str = "foundation_engine"
    requested_claim_level: str | None = None
    normalized_requested_claim: str | None = None
    claim_gate_allowed: bool | None = None
    claim_gate_decision: str | None = None
    final_claim_level: str | None = None
    downgraded_to: str | None = None
    failed_reasons: tuple[str, ...] = ()
    evidence_digests_used: tuple[str, ...] = ()
    claim_gate_policy_version: str | None = None
    protocol_statuses: dict[str, str] = field(default_factory=dict)
    manifest_schema_complete: bool = False
    scientific_protocol_executed: bool = False
    review_status: ReviewStatus = field(default_factory=ReviewStatus)
    started_at: str | None = None
    ended_at: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "package_version": self.package_version,
            "run_id": self.run_id,
            "seed": self.seed,
            "config_hash": self.config_hash,
            "codon_table_hash": self.codon_table_hash,
            "genome_spec_hash": self.genome_spec_hash,
            "rule_set_hash": self.rule_set_hash,
            "adf_vocabulary_hash": self.adf_vocabulary_hash,
            "initial_population_hash": self.initial_population_hash,
            "tick_count": self.tick_count,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "claim_level": self.claim_level,
            "requested_claim_level": self.requested_claim_level,
            "normalized_requested_claim": self.normalized_requested_claim,
            "claim_gate_allowed": self.claim_gate_allowed,
            "claim_gate_decision": self.claim_gate_decision,
            "final_claim_level": self.final_claim_level,
            "downgraded_to": self.downgraded_to,
            "failed_reasons": list(self.failed_reasons),
            "evidence_digests_used": list(self.evidence_digests_used),
            "claim_gate_policy_version": self.claim_gate_policy_version,
            "protocol_statuses": dict(sorted(self.protocol_statuses.items())),
            "manifest_schema_complete": self.manifest_schema_complete,
            "scientific_protocol_executed": self.scientific_protocol_executed,
            "review_status": self.review_status.to_dict(),
            "replay_digest": self.replay_digest,
            "source_digest": self.source_digest,
            "rng_backend_kind": self.rng_backend_kind,
            "rng_namespace": self.rng_namespace,
            "rng_draw_count": self.rng_draw_count,
            "rng_state_digest": self.rng_state_digest,
            "seed_schedule_digest": self.seed_schedule_digest,
            "protocol_version": self.protocol_version,
            "fitness_config_hash": self.fitness_config_hash,
            "descriptor_schema_hash": self.descriptor_schema_hash,
            "archive_digest": self.archive_digest,
            "qd_scheduler_digest": self.qd_scheduler_digest,
            "benchmark_scenario_digest": self.benchmark_scenario_digest,
            "execution_source_digest": self.execution_source_digest,
            "claim_gate_decision_digest": self.claim_gate_decision_digest,
            "runtime_hashes": dict(sorted(self.runtime_hashes.items())),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> RunManifest:
        return _run_manifest_from_dict(cls, data)


@dataclass(frozen=True, slots=True)
class RunArtifactSchema:
    """Evidence pack object returned by the engine."""

    manifest: RunManifest
    summary: ExperimentSummary
    snapshot: PopulationSnapshot
    raw_events: tuple[RawEventSchema, ...] = ()
    discovery_records: tuple[DiscoveryRecord, ...] = ()
    contribution_ledgers: tuple[dict[str, JsonValue], ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "manifest": self.manifest.to_dict(),
            "summary": self.summary.to_dict(),
            "snapshot": self.snapshot.to_dict(),
            "raw_events": [item.to_dict() for item in self.raw_events],
            "discovery_records": [item.to_dict() for item in self.discovery_records],
            "contribution_ledgers": [dict(item) for item in self.contribution_ledgers],
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ReplayBundle:
    """Self-contained replay metadata and generation/tick records."""

    manifest: RunManifest
    snapshots: tuple[PopulationSnapshot, ...]
    generation_digests: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "manifest": self.manifest.to_dict(),
            "snapshots": [item.to_dict() for item in self.snapshots],
            "generation_digests": list(self.generation_digests),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ReplayBundle:
        manifest_raw = data.get("manifest")
        if not isinstance(manifest_raw, Mapping):
            msg = "ReplayBundle.manifest must be an object."
            raise ConfigurationError(msg)
        snapshots: list[PopulationSnapshot] = []
        for item in _list(data.get("snapshots")):
            if not isinstance(item, Mapping):
                raise ConfigurationError("ReplayBundle.snapshots entries must be objects.")
            snapshots.append(PopulationSnapshot.from_dict(item))
        return cls(
            manifest=RunManifest.from_dict(manifest_raw),
            snapshots=tuple(snapshots),
            generation_digests=tuple(str(item) for item in _list(data.get("generation_digests"))),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ReplayVerificationResult:
    """Digest-level verification for ReplayBundle metadata.

    This verifies deterministic replay metadata only. It is not a full
    simulation re-execution engine.
    """

    passed: bool
    issues: tuple[str, ...] = ()
    manifest_digest: str | None = None
    bundle_digest: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "passed": self.passed,
            "issues": list(self.issues),
            "manifest_digest": self.manifest_digest,
            "bundle_digest": self.bundle_digest,
        }


def verify_replay_bundle(bundle: ReplayBundle, result: object) -> ReplayVerificationResult:
    """Verify a replay metadata bundle against a GenesisRunResult-like object."""

    issues: list[str] = []
    expected_manifest = getattr(result, "manifest", None)
    expected_bundle = getattr(result, "replay_bundle", None)
    ticks = getattr(result, "ticks", ())
    if expected_manifest is None or not hasattr(expected_manifest, "digest"):
        issues.append("missing_result_manifest")
    elif bundle.manifest.digest() != expected_manifest.digest():
        issues.append("manifest_digest_mismatch")
    if (
        expected_bundle is not None
        and hasattr(expected_bundle, "digest")
        and bundle.digest() != expected_bundle.digest()
    ):
        issues.append("bundle_digest_mismatch")
    expected_generation_digests = tuple(
        item.generation_result.digest() for item in ticks if hasattr(item, "generation_result")
    )
    if expected_generation_digests and bundle.generation_digests != expected_generation_digests:
        issues.append("generation_digests_mismatch")
    if expected_manifest is not None and bundle.manifest.tick_count != len(
        expected_generation_digests
    ):
        issues.append("tick_count_mismatch")
    return ReplayVerificationResult(
        passed=not issues,
        issues=tuple(sorted(set(issues))),
        manifest_digest=None if expected_manifest is None else expected_manifest.digest(),
        bundle_digest=bundle.digest(),
    )


class ArtifactExporterProtocol(Protocol):
    """Protocol for explicit artifact exporters."""

    def export(self, artifact: RunArtifactSchema | ReplayBundle) -> str:
        """Return serialized artifact content."""
        ...


@dataclass(frozen=True, slots=True)
class JsonArtifactExporter:
    """Explicit JSON exporter; no implicit file I/O."""

    indent: int | None = 2

    def export(self, artifact: RunArtifactSchema | ReplayBundle) -> str:
        return json.dumps(artifact.to_dict(), sort_keys=True, indent=self.indent)


def manifest_from_parts(
    *,
    run_id: str,
    seed: int,
    config: Mapping[str, JsonValue],
    codon_table_hash: str,
    genome_spec_hash: str,
    initial_population_hash: str,
    tick_count: int,
    replay_digest: str,
    rule_set_hash: str = "none",
    adf_vocabulary_hash: str = "none",
    claim_level: str = "foundation_engine",
    claim_decision: ClaimDecision | None = None,
    protocol_statuses: Mapping[str, str] | None = None,
    manifest_schema_complete: bool = False,
    scientific_protocol_executed: bool = False,
    review_status: ReviewStatus | None = None,
    runtime_hashes: Mapping[str, str | None] | None = None,
    source_digest: str | None = None,
    rng_backend_kind: str | None = None,
    rng_namespace: str | None = None,
    rng_draw_count: int | None = None,
    rng_state_digest: str | None = None,
    seed_schedule_digest: str | None = None,
    protocol_version: str = "scientific_manifest_phase1",
    fitness_config_hash: str | None = None,
    descriptor_schema_hash: str | None = None,
    archive_digest: str | None = None,
    qd_scheduler_digest: str | None = None,
    benchmark_scenario_digest: str | None = None,
    execution_source_digest: str | None = None,
    claim_gate_decision_digest: str | None = None,
) -> RunManifest:
    """Build a deterministic manifest from engine-managed pieces."""

    return RunManifest(
        run_id=run_id,
        seed=seed,
        config_hash=_digest(config),
        codon_table_hash=codon_table_hash,
        genome_spec_hash=genome_spec_hash,
        rule_set_hash=rule_set_hash,
        adf_vocabulary_hash=adf_vocabulary_hash,
        initial_population_hash=initial_population_hash,
        tick_count=tick_count,
        replay_digest=replay_digest,
        runtime_hashes=dict(runtime_hashes or {}),
        source_digest=source_digest,
        rng_backend_kind=rng_backend_kind,
        rng_namespace=rng_namespace,
        rng_draw_count=rng_draw_count,
        rng_state_digest=rng_state_digest,
        seed_schedule_digest=seed_schedule_digest,
        protocol_version=protocol_version,
        fitness_config_hash=fitness_config_hash,
        descriptor_schema_hash=descriptor_schema_hash,
        archive_digest=archive_digest,
        qd_scheduler_digest=qd_scheduler_digest,
        benchmark_scenario_digest=benchmark_scenario_digest,
        execution_source_digest=execution_source_digest,
        claim_gate_decision_digest=claim_gate_decision_digest,
        claim_level=claim_decision.final_claim if claim_decision is not None else claim_level,
        requested_claim_level=None if claim_decision is None else claim_decision.requested_claim,
        normalized_requested_claim=None
        if claim_decision is None
        else claim_decision.normalized_requested_claim,
        claim_gate_allowed=None if claim_decision is None else claim_decision.allowed,
        claim_gate_decision=None if claim_decision is None else claim_decision.decision,
        final_claim_level=None if claim_decision is None else claim_decision.final_claim,
        downgraded_to=None
        if claim_decision is None or claim_decision.allowed
        else claim_decision.final_claim,
        failed_reasons=() if claim_decision is None else claim_decision.failed_reasons,
        evidence_digests_used=()
        if claim_decision is None
        else claim_decision.evidence_digests_used,
        claim_gate_policy_version=None if claim_decision is None else claim_decision.policy_version,
        protocol_statuses=dict(protocol_statuses or {}),
        manifest_schema_complete=manifest_schema_complete,
        scientific_protocol_executed=scientific_protocol_executed,
        review_status=review_status or ReviewStatus(),
        started_at=None,
        ended_at=None,
    )


def utc_timestamp() -> str:
    """Return an ISO timestamp for optional caller-side audit metadata."""

    return datetime.now(timezone.utc).isoformat()


# Conservative from_dict helpers are attached after class creation to keep the
# dataclasses compact and make replay tests explicit.
def _run_manifest_from_dict(cls: type[RunManifest], data: Mapping[str, JsonValue]) -> RunManifest:
    review_raw = data.get("review_status")
    review = (
        ReviewStatus.from_dict(review_raw) if isinstance(review_raw, Mapping) else ReviewStatus()
    )
    return cls(
        package_version=_str(data, "package_version", _PACKAGE_VERSION),
        run_id=_str(data, "run_id"),
        seed=_int(data, "seed", 0),
        config_hash=_str(data, "config_hash"),
        codon_table_hash=_str(data, "codon_table_hash"),
        genome_spec_hash=_str(data, "genome_spec_hash"),
        rule_set_hash=_str(data, "rule_set_hash", "none"),
        adf_vocabulary_hash=_str(data, "adf_vocabulary_hash", "none"),
        initial_population_hash=_str(data, "initial_population_hash"),
        tick_count=_int(data, "tick_count", 0),
        replay_digest=_str(data, "replay_digest"),
        runtime_hashes=_string_optional_mapping(data.get("runtime_hashes")),
        source_digest=_optional_str(data.get("source_digest")),
        rng_backend_kind=_optional_str(data.get("rng_backend_kind")),
        rng_namespace=_optional_str(data.get("rng_namespace")),
        rng_draw_count=None
        if data.get("rng_draw_count") is None
        else _int(data, "rng_draw_count", 0),
        rng_state_digest=_optional_str(data.get("rng_state_digest")),
        seed_schedule_digest=_optional_str(data.get("seed_schedule_digest")),
        protocol_version=_str(data, "protocol_version", "scientific_manifest_phase1"),
        fitness_config_hash=_optional_str(data.get("fitness_config_hash")),
        descriptor_schema_hash=_optional_str(data.get("descriptor_schema_hash")),
        archive_digest=_optional_str(data.get("archive_digest")),
        qd_scheduler_digest=_optional_str(data.get("qd_scheduler_digest")),
        benchmark_scenario_digest=_optional_str(data.get("benchmark_scenario_digest")),
        execution_source_digest=_optional_str(data.get("execution_source_digest")),
        claim_gate_decision_digest=_optional_str(data.get("claim_gate_decision_digest")),
        claim_level=_str(data, "claim_level", "research_alpha_foundation_engine"),
        requested_claim_level=_optional_str(data.get("requested_claim_level")),
        normalized_requested_claim=_optional_str(data.get("normalized_requested_claim")),
        claim_gate_allowed=_optional_bool(data.get("claim_gate_allowed")),
        claim_gate_decision=_optional_str(data.get("claim_gate_decision")),
        final_claim_level=_optional_str(data.get("final_claim_level")),
        downgraded_to=_optional_str(data.get("downgraded_to")),
        failed_reasons=tuple(str(item) for item in _list(data.get("failed_reasons"))),
        evidence_digests_used=tuple(str(item) for item in _list(data.get("evidence_digests_used"))),
        claim_gate_policy_version=_optional_str(data.get("claim_gate_policy_version")),
        protocol_statuses={
            k: str(v) for k, v in _string_mapping(data.get("protocol_statuses")).items()
        },
        manifest_schema_complete=bool(data.get("manifest_schema_complete", False)),
        scientific_protocol_executed=bool(data.get("scientific_protocol_executed", False)),
        review_status=review,
        started_at=_optional_str(data.get("started_at")),
        ended_at=_optional_str(data.get("ended_at")),
    )


def _review_status_from_dict(
    cls: type[ReviewStatus], data: Mapping[str, JsonValue]
) -> ReviewStatus:
    return cls(
        status=_str(data, "status", "not_reviewed"),
        reviewer=_optional_str(data.get("reviewer")),
        decision_digest=_optional_str(data.get("decision_digest")),
    )


def _population_snapshot_from_dict(
    cls: type[PopulationSnapshot], data: Mapping[str, JsonValue]
) -> PopulationSnapshot:
    return cls(
        generation=_int(data, "generation", 0),
        tick=_int(data, "tick", 0),
        agents=tuple(
            AgentSnapshot.from_dict(item)
            for item in _list(data.get("agents"))
            if isinstance(item, Mapping)
        ),
        population_digest=_str(data, "population_digest"),
        nexus_digest=_optional_str(data.get("nexus_digest")),
    )


def _agent_snapshot_from_dict(
    cls: type[AgentSnapshot], data: Mapping[str, JsonValue]
) -> AgentSnapshot:
    pos = _list(data.get("position"))
    if len(pos) != 2:
        msg = "AgentSnapshot.position must have two integers."
        raise ConfigurationError(msg)
    return cls(
        organism_id=_str(data, "organism_id"),
        genome_digest=_str(data, "genome_digest"),
        runtime_atp=_float(data, "runtime_atp", 0.0),
        learning_atp=_float(data, "learning_atp", 0.0),
        position=(_json_int_value(pos[0], "position[0]"), _json_int_value(pos[1], "position[1]")),
        causal_graph_digest=_optional_str(data.get("causal_graph_digest")),
        memory_digest=_optional_str(data.get("memory_digest")),
    )


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _string_optional_mapping(value: object) -> dict[str, str | None]:
    if not isinstance(value, Mapping):
        return {}
    return {str(k): (None if v is None else str(v)) for k, v in value.items()}


def _string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(k): str(v) for k, v in value.items()}


def _json_int_value(value: JsonValue, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{field} must be an integer")
    return value


def _list(value: object) -> list[JsonValue]:
    if value is None:
        return []
    if not isinstance(value, list):
        msg = "expected a list."
        raise ConfigurationError(msg)
    return cast(list[JsonValue], value)


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        msg = f"{key} must be a string."
        raise ConfigurationError(msg)
    return value


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ConfigurationError("value must be a boolean or null")
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        msg = "value must be a string or null."
        raise ConfigurationError(msg)
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{key} must be an integer."
        raise ConfigurationError(msg)
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{key} must be numeric."
        raise ConfigurationError(msg)
    return float(value)


@dataclass(frozen=True, slots=True)
class ScientificManifestValidationResult:
    """Validation result for paper-grade manifest hash completeness."""

    passed: bool
    missing_hashes: tuple[str, ...]
    placeholder_hashes: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "passed": self.passed,
            "missing_hashes": list(self.missing_hashes),
            "placeholder_hashes": list(self.placeholder_hashes),
        }


def validate_scientific_manifest(manifest: RunManifest) -> ScientificManifestValidationResult:
    """Check that a run manifest contains the hashes required for scientific runs."""

    required_top = {
        "config_hash": manifest.config_hash,
        "codon_table_hash": manifest.codon_table_hash,
        "genome_spec_hash": manifest.genome_spec_hash,
        "rule_set_hash": manifest.rule_set_hash,
        "adf_vocabulary_hash": manifest.adf_vocabulary_hash,
        "initial_population_hash": manifest.initial_population_hash,
        "replay_digest": manifest.replay_digest,
    }
    required_runtime = (
        "action_registry_hash",
        "ribosome_hash",
        "engine_config_hash",
        "population_config_hash",
        "evolution_config_hash",
        "capsule_transfer_config_hash",
        "qd_archive_config_hash",
        "element_grid_hash",
        "substrate_bridge_mode",
    )
    missing: list[str] = []
    placeholders: list[str] = []
    for key, value in required_top.items():
        if value in {None, ""}:
            missing.append(key)
        elif str(value) in {"none", "genesis_v0", "default_from_ribosome", "placeholder"}:
            placeholders.append(key)
    for key in required_runtime:
        runtime_value = manifest.runtime_hashes.get(key)
        if runtime_value in {None, ""}:
            missing.append(f"runtime_hashes.{key}")
        elif str(runtime_value) in {"none", "genesis_v0", "default_from_ribosome", "placeholder"}:
            placeholders.append(f"runtime_hashes.{key}")
    return ScientificManifestValidationResult(
        not missing and not placeholders, tuple(missing), tuple(placeholders)
    )


def compute_source_digest(root: str | None = None) -> str:
    """Compute a canonical source digest when git commit metadata is unavailable."""

    env_root = os.environ.get("CODONTRACE_SOURCE_ROOT") if root is None else None
    explicit_root = root is not None or env_root is not None
    if root is not None:
        base = Path(root)
    elif env_root is not None:
        base = Path(env_root)
    else:
        source_file = Path(__file__).resolve()
        base = source_file.parents[2]
        for parent in source_file.parents:
            if (parent / "pyproject.toml").exists() and (parent / "src" / "codontrace").exists():
                base = parent
                break
    excluded_dirs = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "build",
        "dist",
        "htmlcov",
    }
    excluded_suffixes = {".pyc", ".pyo"}
    records: list[dict[str, JsonValue]] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if any(part in excluded_dirs for part in path.parts):
            continue
        if any(part.endswith((".egg-info", ".dist-info")) for part in path.parts):
            continue
        if path.suffix in excluded_suffixes or path.name in {
            ".coverage",
            "PKG-INFO",
            "SOURCES.txt",
            "dependency_links.txt",
            "top_level.txt",
        }:
            continue
        rel_candidate = path.relative_to(base).as_posix()
        if not explicit_root:
            allowed_prefixes: tuple[str, ...] = ("src/codontrace/", "docs/")
            allowed_files: set[str] = {
                "pyproject.toml",
                "README.md",
                "GENESIS_COMPATIBILITY_MATRIX.md",
            }
            # In installed-source layouts the digest root may already be src/ or codontrace/.
            if base.name == "src":
                allowed_prefixes = ("codontrace/", "docs/")
            elif base.name == "codontrace" and (base / "__init__.py").exists():
                allowed_prefixes = ("",)
                allowed_files = set()
            if (
                not rel_candidate.startswith(allowed_prefixes)
                and rel_candidate not in allowed_files
            ):
                continue
        rel = path.relative_to(base).as_posix()
        data = path.read_bytes()
        records.append(
            {
                "relative_path": rel,
                "file_size": len(data),
                "file_sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return _digest({"files": cast(JsonValue, records)})


def validate_phase1_manifest_fields(manifest: RunManifest) -> ScientificManifestValidationResult:
    """Validate Phase-1 scientific manifest additions without claiming full replay."""

    result = validate_scientific_manifest(manifest)
    missing = list(result.missing_hashes)
    placeholders = list(result.placeholder_hashes)
    fields = {
        "source_digest": manifest.source_digest,
        "rng_backend_kind": manifest.rng_backend_kind,
        "rng_namespace": manifest.rng_namespace,
        "rng_state_digest": manifest.rng_state_digest,
        "seed_schedule_digest": manifest.seed_schedule_digest,
        "protocol_version": manifest.protocol_version,
        "fitness_config_hash": manifest.fitness_config_hash,
        "descriptor_schema_hash": manifest.descriptor_schema_hash,
        "archive_digest": manifest.archive_digest,
        "claim_gate_decision_digest": manifest.claim_gate_decision_digest,
    }
    for key, value in fields.items():
        if value in {None, ""}:
            missing.append(key)
        elif str(value) in {"none", "placeholder", "genesis_v0", "default_from_ribosome"}:
            placeholders.append(key)
    if manifest.rng_draw_count is None:
        missing.append("rng_draw_count")
    return ScientificManifestValidationResult(
        not missing and not placeholders,
        tuple(sorted(set(missing))),
        tuple(sorted(set(placeholders))),
    )


# --- Strong Library Phase 2 manifest/artifact helpers ---
PHASE2_MANIFEST_FIELDS: tuple[str, ...] = (
    "genome_program_digest",
    "structural_mutation_digest",
    "structural_mutation_record_digest",
    "adf_macro_registry_digest",
    "macro_registry_digest",
    "adf_usefulness_report_digest",
    "macro_utility_digest",
    "translation_profile_digest",
    "translation_profile_hash",
    "contribution_ledger_digest",
    "micro_ablation_attribution_digest",
    "innovation_registry_digest",
    "event_graph_digest",
    "predictive_probe_digest",
    "intervention_protocol_digest",
    "intervention_result_digest",
    "causal_intervention_result_digest",
    "discovery_witness_digest",
    "benchmark_scenario_digest",
    "statistical_report_digest",
    "oee_report_digest",
    "social_generalization_digest",
    "semantic_proxy_report_digest",
    "phase2_claim_decision_digest",
    "claim_gate_decision_digest",
)


def phase2_runtime_hashes(**values: str | None) -> dict[str, str | None]:
    """Build a manifest runtime_hashes patch for Phase 2 scientific objects."""
    return {name: values.get(name) for name in PHASE2_MANIFEST_FIELDS}


_PHASE2_ACCEPTED_FEATURE_STATUSES: tuple[str, ...] = (
    "measured",
    "runtime_effective",
    "control_supported",
    "ablation_supported",
    "heldout_supported",
    "intervention_supported",
    "provisional",
    "empty_but_available",
    "unavailable",
    "not_observed",
    "not_run",
    "disabled_by_config",
    "not_configured",
    "metadata_only",
    "fixed_default",
    "not_applicable",
)


def phase2_manifest_field_statuses(manifest: RunManifest) -> dict[str, str]:
    """Return status values for every Phase 2 manifest field.

    Phase 2 artifacts are evidence-gated. A digest alone is not enough to
    promote a scientific claim because many fields intentionally carry
    deterministic ``not_run`` or ``disabled`` digests. The companion status is
    the bridge from older manifest consumers to the newer Phase 2 evidence
    contract.
    """

    return {
        field_name: str(manifest.protocol_statuses.get(f"phase2.{field_name}.status", ""))
        for field_name in PHASE2_MANIFEST_FIELDS
    }


_PHASE2_EVIDENCE_STATUSES_REQUIRING_HASH: tuple[str, ...] = (
    "measured",
    "runtime_effective",
    "control_supported",
    "ablation_supported",
    "heldout_supported",
    "intervention_supported",
    "provisional",
)

_PHASE2_CLAIM_ELIGIBLE_STATUSES: tuple[str, ...] = (
    "measured",
    "runtime_effective",
    "control_supported",
    "ablation_supported",
    "heldout_supported",
    "intervention_supported",
)

_PHASE2_PLACEHOLDER_HASH_VALUES: tuple[str, ...] = (
    "none",
    "null",
    "placeholder",
    "default",
    "not_run",
    "disabled",
    "not_configured",
    "fixed_default",
    "sha256:placeholder",
)


def validate_phase2_manifest_fields(manifest: RunManifest) -> ScientificManifestValidationResult:
    """Validate Phase 2 manifest hashes and their feature statuses.

    Measured/runtime-effective/provisional Phase 2 statuses are evidence
    surfaces, so they must carry a real deterministic runtime hash.  Statuses
    such as disabled/not-run/not-applicable may carry deterministic sentinel
    digests for replay, but they never unlock scientific claim eligibility.
    """

    missing: list[str] = []
    placeholders: list[str] = []
    statuses = phase2_manifest_field_statuses(manifest)
    accepted = set(_PHASE2_ACCEPTED_FEATURE_STATUSES)
    evidence_statuses = set(_PHASE2_EVIDENCE_STATUSES_REQUIRING_HASH)
    placeholder_values = set(_PHASE2_PLACEHOLDER_HASH_VALUES)
    for field_name in PHASE2_MANIFEST_FIELDS:
        value = manifest.runtime_hashes.get(field_name)
        status = statuses.get(field_name, "")
        text_value = "" if value is None else str(value).strip()
        if status not in accepted:
            missing.append(f"protocol_statuses.phase2.{field_name}.status")
            if not text_value:
                missing.append(field_name)
            continue

        lower_value = text_value.lower()
        if status in evidence_statuses:
            if not text_value:
                missing.append(field_name)
            elif lower_value in placeholder_values:
                placeholders.append(field_name)
            if status == "provisional":
                reason = manifest.protocol_statuses.get(f"phase2.{field_name}.status_reason")
                if not reason:
                    missing.append(f"protocol_statuses.phase2.{field_name}.status_reason")
        elif text_value and lower_value in {"none", "null", "placeholder", "default", "sha256:placeholder"}:
            # Non-evidence statuses can use explicit not-run/disabled digests,
            # but raw placeholders are still too ambiguous for replay metadata.
            placeholders.append(field_name)
    return ScientificManifestValidationResult(
        not missing and not placeholders, tuple(sorted(set(missing))), tuple(sorted(set(placeholders)))
    )
