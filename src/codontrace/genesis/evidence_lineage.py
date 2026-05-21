"""Evidence-lineage and mature-alpha readiness objects for GENESIS.

These helpers are dependency-free object models. They summarize caller-provided
evidence metadata only; they do not run experiments, write files, generate
reports, or claim proof.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.api_audit import APIAuditResult
from codontrace.genesis.claim_audit import ClaimAuditResult
from codontrace.genesis.evidence_bundle import EvidenceBundle
from codontrace.genesis.limitations import LimitationRecord, LimitationSeverity
from codontrace.genesis.release_candidate import ReleaseCandidateDecision
from codontrace.genesis.scientific_evidence import (
    ScientificEvidencePack,
    ScientificEvidenceValidationResult,
)


@dataclass(frozen=True, slots=True)
class EvidenceDependency:
    source_evidence_id: str
    target_evidence_id: str
    relation: str
    required: bool = True
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.source_evidence_id or not self.target_evidence_id or not self.relation:
            raise ConfigurationError("EvidenceDependency source/target/relation must not be empty.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "source_evidence_id": self.source_evidence_id,
            "target_evidence_id": self.target_evidence_id,
            "relation": self.relation,
            "required": self.required,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EvidenceDependency:
        return cls(
            _str(data, "source_evidence_id"),
            _str(data, "target_evidence_id"),
            _str(data, "relation"),
            _bool(data, "required", True),
            _str(data, "reason", ""),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EvidenceLineageGraph:
    graph_id: str
    dependencies: tuple[EvidenceDependency, ...]
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.graph_id:
            raise ConfigurationError("EvidenceLineageGraph.graph_id must not be empty.")
        object.__setattr__(self, "evidence_ids", tuple(sorted(self.evidence_ids)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "graph_id": self.graph_id,
            "dependencies": [item.to_dict() for item in self.dependencies],
            "evidence_ids": list(self.evidence_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EvidenceLineageGraph:
        raw = data.get("dependencies", [])
        if not isinstance(raw, list):
            raise ConfigurationError("EvidenceLineageGraph.dependencies must be a list.")
        return cls(
            _str(data, "graph_id"),
            tuple(EvidenceDependency.from_dict(_mapping(item, "dependency")) for item in raw),
            _str_tuple(data, "evidence_ids"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class EvidenceLineageValidationResult:
    attempted: bool
    succeeded: bool
    missing_evidence_ids: tuple[str, ...]
    dangling_dependencies: tuple[str, ...]
    circular_dependencies: tuple[str, ...]
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "missing_evidence_ids": list(self.missing_evidence_ids),
            "dangling_dependencies": list(self.dangling_dependencies),
            "circular_dependencies": list(self.circular_dependencies),
            "reasons": list(self.reasons),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EvidenceLineageValidationResult:
        return cls(
            _bool(data, "attempted", False),
            _bool(data, "succeeded", False),
            _str_tuple(data, "missing_evidence_ids"),
            _str_tuple(data, "dangling_dependencies"),
            _str_tuple(data, "circular_dependencies"),
            _str_tuple(data, "reasons"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def validate_evidence_lineage(graph: EvidenceLineageGraph) -> EvidenceLineageValidationResult:
    ids = set(graph.evidence_ids)
    dangling: list[str] = []
    missing: set[str] = set()
    adjacency: dict[str, list[str]] = defaultdict(list)
    for dep in graph.dependencies:
        if dep.source_evidence_id not in ids:
            missing.add(dep.source_evidence_id)
            dangling.append(f"{dep.source_evidence_id}->{dep.target_evidence_id}")
        if dep.target_evidence_id not in ids:
            missing.add(dep.target_evidence_id)
            dangling.append(f"{dep.source_evidence_id}->{dep.target_evidence_id}")
        adjacency[dep.source_evidence_id].append(dep.target_evidence_id)
    cycles = _cycles(adjacency)
    reasons: list[str] = []
    if missing:
        reasons.append("missing_evidence_ids")
    if dangling:
        reasons.append("dangling_dependencies")
    if cycles:
        reasons.append("circular_dependencies")
    return EvidenceLineageValidationResult(
        True,
        not reasons,
        tuple(sorted(missing)),
        tuple(sorted(set(dangling))),
        cycles,
        tuple(reasons) if reasons else ("evidence_lineage_validated",),
    )


@dataclass(frozen=True, slots=True)
class ReproducibilitySummary:
    seed_count: int
    unique_seed_count: int
    config_digest_count: int
    trace_digest_count: int
    replay_digest_count: int
    deterministic_replay_available: bool
    duplicate_seed_count: int
    missing_digest_count: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed_count": self.seed_count,
            "unique_seed_count": self.unique_seed_count,
            "config_digest_count": self.config_digest_count,
            "trace_digest_count": self.trace_digest_count,
            "replay_digest_count": self.replay_digest_count,
            "deterministic_replay_available": self.deterministic_replay_available,
            "duplicate_seed_count": self.duplicate_seed_count,
            "missing_digest_count": self.missing_digest_count,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> ReproducibilitySummary:
        return cls(
            _int(data, "seed_count", 0),
            _int(data, "unique_seed_count", 0),
            _int(data, "config_digest_count", 0),
            _int(data, "trace_digest_count", 0),
            _int(data, "replay_digest_count", 0),
            _bool(data, "deterministic_replay_available", False),
            _int(data, "duplicate_seed_count", 0),
            _int(data, "missing_digest_count", 0),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def summarize_reproducibility(bundle: EvidenceBundle) -> ReproducibilitySummary:
    seeds = tuple(record.seed for record in bundle.records)
    duplicate_seed_count = sum(1 for seed in set(seeds) if seeds.count(seed) > 1)
    config_count = sum(1 for record in bundle.records if record.config_digest)
    trace_count = sum(1 for record in bundle.records if record.trace_digest)
    replay_count = sum(1 for record in bundle.records if record.replay_digest)
    missing = sum(
        1
        for record in bundle.records
        for digest in (record.config_digest, record.trace_digest)
        if not digest
    )
    return ReproducibilitySummary(
        len(seeds),
        len(set(seeds)),
        config_count,
        trace_count,
        replay_count,
        replay_count > 0,
        duplicate_seed_count,
        missing,
    )


@dataclass(frozen=True, slots=True)
class EvidenceQualityScore:
    score_0_to_1: float
    completeness_score: float
    reproducibility_score: float
    limitation_penalty: float
    claim_safety_score: float
    missing_items: tuple[str, ...]
    critical_limitations: tuple[str, ...]
    warnings: tuple[str, ...] = ("quality_score_is_not_proof",)

    def __post_init__(self) -> None:
        for name, value in (
            ("score_0_to_1", self.score_0_to_1),
            ("completeness_score", self.completeness_score),
            ("reproducibility_score", self.reproducibility_score),
            ("limitation_penalty", self.limitation_penalty),
            ("claim_safety_score", self.claim_safety_score),
        ):
            if not 0.0 <= value <= 1.0:
                raise ConfigurationError(f"EvidenceQualityScore.{name} must be in [0, 1].")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "score_0_to_1": self.score_0_to_1,
            "completeness_score": self.completeness_score,
            "reproducibility_score": self.reproducibility_score,
            "limitation_penalty": self.limitation_penalty,
            "claim_safety_score": self.claim_safety_score,
            "missing_items": list(self.missing_items),
            "critical_limitations": list(self.critical_limitations),
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> EvidenceQualityScore:
        return cls(
            _float(data, "score_0_to_1", 0.0),
            _float(data, "completeness_score", 0.0),
            _float(data, "reproducibility_score", 0.0),
            _float(data, "limitation_penalty", 0.0),
            _float(data, "claim_safety_score", 0.0),
            _str_tuple(data, "missing_items"),
            _str_tuple(data, "critical_limitations"),
            _str_tuple(data, "warnings"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def score_evidence_quality(
    pack: ScientificEvidencePack,
    bundle: EvidenceBundle,
    limitations: tuple[LimitationRecord, ...],
    claim_audit: ClaimAuditResult,
) -> EvidenceQualityScore:
    missing = []
    if pack.d0_summary is None:
        missing.append("d0")
    if pack.qd_summary is None:
        missing.append("qd")
    if pack.ablation_summary is None:
        missing.append("ablation")
    if pack.witness_summary is None:
        missing.append("witness")
    completeness = max(0.0, 1.0 - len(missing) / 4.0)
    repro = summarize_reproducibility(bundle)
    reproducibility = (
        0.0
        if repro.seed_count == 0
        else min(1.0, repro.unique_seed_count / max(1, repro.seed_count))
    )
    critical = tuple(
        sorted(
            item.limitation_id
            for item in limitations
            if item.severity == LimitationSeverity.CRITICAL
        )
    )
    limitation_penalty = min(1.0, len(critical) * 0.25)
    claim_safety = (
        0.0 if claim_audit.blocked_claims else max(0.0, 1.0 - len(claim_audit.warnings) * 0.1)
    )
    score = max(
        0.0, min(1.0, (completeness + reproducibility + claim_safety) / 3.0 - limitation_penalty)
    )
    warnings_list = ["quality_score_is_not_proof"]
    if critical:
        warnings_list.append("critical_limitations_reduce_score")
    if claim_audit.blocked_claims:
        warnings_list.append("claim_audit_blockers_reduce_score")
    return EvidenceQualityScore(
        score,
        completeness,
        reproducibility,
        limitation_penalty,
        claim_safety,
        tuple(missing),
        critical,
        tuple(warnings_list),
    )


@dataclass(frozen=True, slots=True)
class MatureAlphaReadinessResult:
    attempted: bool
    accepted: bool
    version: str
    release_decision_digest: str
    scientific_evidence_validation_digest: str
    evidence_quality_digest: str
    claim_audit_digest: str
    api_audit_digest: str
    blocking_issues: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    accepted_for_testpypi: bool = False
    accepted_for_public_release: bool = False
    accepted_for_mature_alpha: bool = False
    requires_owner_approval: bool = False
    missing_external_evidence: tuple[str, ...] = ()
    exception_gate_names: tuple[str, ...] = ()
    final_claim_ceiling: str = "CANDIDATE"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "attempted": self.attempted,
            "accepted": self.accepted,
            "version": self.version,
            "release_decision_digest": self.release_decision_digest,
            "scientific_evidence_validation_digest": self.scientific_evidence_validation_digest,
            "evidence_quality_digest": self.evidence_quality_digest,
            "claim_audit_digest": self.claim_audit_digest,
            "api_audit_digest": self.api_audit_digest,
            "blocking_issues": list(self.blocking_issues),
            "warnings": list(self.warnings),
            "accepted_for_testpypi": self.accepted_for_testpypi,
            "accepted_for_public_release": self.accepted_for_public_release,
            "accepted_for_mature_alpha": self.accepted_for_mature_alpha,
            "requires_owner_approval": self.requires_owner_approval,
            "missing_external_evidence": list(self.missing_external_evidence),
            "exception_gate_names": list(self.exception_gate_names),
            "final_claim_ceiling": self.final_claim_ceiling,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> MatureAlphaReadinessResult:
        return cls(
            _bool(data, "attempted", False),
            _bool(data, "accepted", False),
            _str(data, "version"),
            _str(data, "release_decision_digest", ""),
            _str(data, "scientific_evidence_validation_digest", ""),
            _str(data, "evidence_quality_digest", ""),
            _str(data, "claim_audit_digest", ""),
            _str(data, "api_audit_digest", ""),
            _str_tuple(data, "blocking_issues"),
            _str_tuple(data, "warnings"),
            _bool(data, "accepted_for_testpypi", False),
            _bool(data, "accepted_for_public_release", False),
            _bool(data, "accepted_for_mature_alpha", False),
            _bool(data, "requires_owner_approval", False),
            _str_tuple(data, "missing_external_evidence"),
            _str_tuple(data, "exception_gate_names"),
            _str(data, "final_claim_ceiling", "CANDIDATE"),
        )

    def digest(self) -> str:
        return _digest(self.to_dict())


def evaluate_mature_alpha_readiness(
    version: str,
    release_decision: ReleaseCandidateDecision,
    scientific_validation: ScientificEvidenceValidationResult,
    evidence_quality: EvidenceQualityScore,
    claim_audit: ClaimAuditResult,
    api_audit: APIAuditResult,
    limitations: tuple[LimitationRecord, ...] = (),
) -> MatureAlphaReadinessResult:
    blockers: list[str] = []
    warnings: list[str] = []
    if not release_decision.accepted_for_mature_alpha:
        blockers.append("release_candidate_not_mature_alpha_ready")
    if scientific_validation.profile_name != "mature_alpha":
        blockers.append("scientific_evidence_not_mature_alpha_profile")
    if not scientific_validation.succeeded:
        blockers.append("scientific_evidence_validation_failed")
    if claim_audit.blocked_claims:
        blockers.append("claim_audit_blockers")
    if not api_audit.succeeded:
        blockers.append("api_audit_failed")
    critical = tuple(item for item in limitations if item.severity == LimitationSeverity.CRITICAL)
    if critical:
        blockers.append("critical_limitations")
    if evidence_quality.score_0_to_1 < 0.75:
        warnings.append("evidence_quality_below_mature_alpha_target")
    missing_external: list[str] = []
    if not release_decision.accepted_for_pypi:
        for gate in ("hosted_ci", "pip_audit"):
            if (
                gate in release_decision.required_missing_gates
                or gate in release_decision.blocked_reasons
            ):
                missing_external.append(gate)
    requires_owner = bool(release_decision.accepted_with_exceptions or missing_external)
    return MatureAlphaReadinessResult(
        True,
        not blockers,
        version,
        release_decision.digest(),
        scientific_validation.digest(),
        evidence_quality.digest(),
        claim_audit.digest(),
        api_audit.digest(),
        tuple(sorted(set(blockers))),
        tuple(sorted(set(warnings))),
        release_decision.accepted_for_testpypi,
        release_decision.accepted_for_pypi,
        not blockers,
        requires_owner,
        tuple(sorted(set(missing_external))),
        release_decision.exception_gate_names,
        scientific_validation.claim_ceiling,
    )


def _cycles(adjacency: Mapping[str, list[str]]) -> tuple[str, ...]:
    cycles: set[str] = set()
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, path: tuple[str, ...]) -> None:
        if node in visiting:
            try:
                idx = path.index(node)
            except ValueError:
                idx = 0
            cycles.add("->".join(path[idx:] + (node,)))
            return
        if node in visited:
            return
        visiting.add(node)
        for nxt in adjacency.get(node, []):
            visit(nxt, path + (nxt,))
        visiting.remove(node)
        visited.add(node)

    for key in sorted(adjacency):
        visit(key, (key,))
    return tuple(sorted(cycles))


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _mapping(value: object, name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{name} must be an object.")
    return value


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        raise ConfigurationError(f"{key} must be a string.")
    return value


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be a boolean.")
    return value


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError(f"{key} must be numeric.")
    return float(value)


def _str_tuple(data: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ConfigurationError(f"{key} must be a list of strings.")
    return tuple(str(item) for item in raw)

# Phase 3 evidence-lineage DAG: config -> run -> artifact/statistic -> claim.
from codontrace.genesis.canonical import canonical_digest as _phase3_digest

_PHASE3_NODE_TYPES = {"config", "world_snapshot", "organism_snapshot", "run_record", "artifact", "statistical_result", "ablation_result", "control_result", "claim_decision", "release_manifest"}

@dataclass(frozen=True, slots=True)
class EvidenceLineageNode:
    node_id: str
    node_type: str
    digest_value: str
    schema_version: str = "evidence_lineage_node_v1"
    def __post_init__(self) -> None:
        if not self.node_id or self.node_type not in _PHASE3_NODE_TYPES or not self.digest_value:
            raise ConfigurationError("EvidenceLineageNode requires id, supported type, and digest")
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "node_id": self.node_id, "node_type": self.node_type, "digest": self.digest_value}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class EvidenceLineageEdge:
    source_node_id: str
    target_node_id: str
    relation: str
    schema_version: str = "evidence_lineage_edge_v1"
    def __post_init__(self) -> None:
        if not self.source_node_id or not self.target_node_id or not self.relation:
            raise ConfigurationError("EvidenceLineageEdge requires source/target/relation")
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "source_node_id": self.source_node_id, "target_node_id": self.target_node_id, "relation": self.relation}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class EvidenceLineageDAG:
    nodes: tuple[EvidenceLineageNode, ...]
    edges: tuple[EvidenceLineageEdge, ...]
    schema_version: str = "evidence_lineage_dag_v1"
    def __post_init__(self) -> None:
        ids = [n.node_id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise ConfigurationError("EvidenceLineageDAG node ids must be unique")
        known=set(ids)
        for e in self.edges:
            if e.source_node_id not in known or e.target_node_id not in known:
                raise ConfigurationError("EvidenceLineageDAG edge references unknown node")
        if _phase3_has_cycle(tuple(ids), self.edges):
            raise ConfigurationError("EvidenceLineageDAG must be acyclic")
    def has_path(self, source_type: str, target_type: str) -> bool:
        ids_by_type={t:{n.node_id for n in self.nodes if n.node_type==t} for t in (source_type,target_type)}
        targets=ids_by_type[target_type]
        adj: dict[str, list[str]]={}
        for e in self.edges:
            adj.setdefault(e.source_node_id, []).append(e.target_node_id)
        for start in ids_by_type[source_type]:
            stack=[start]; seen=set()
            while stack:
                cur=stack.pop()
                if cur in targets:
                    return True
                if cur in seen: continue
                seen.add(cur); stack.extend(adj.get(cur,()))
        return False
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "nodes": [n.to_dict() for n in self.nodes], "edges": [e.to_dict() for e in self.edges]}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class EvidenceLineageValidator:
    require_config_to_claim_path: bool = True
    schema_version: str = "evidence_lineage_validator_v1"
    def validate(self, dag: EvidenceLineageDAG) -> EvidenceLineageValidationResult:
        reasons=[]
        if self.require_config_to_claim_path and not dag.has_path("config", "claim_decision"):
            reasons.append("missing_config_to_claim_path")
        return EvidenceLineageValidationResult(True, not reasons, (), (), (), tuple(reasons) if reasons else ("evidence_lineage_validated",))

def _phase3_has_cycle(ids: tuple[str, ...], edges: tuple[EvidenceLineageEdge, ...]) -> bool:
    adj={i: [] for i in ids}
    for e in edges:
        adj[e.source_node_id].append(e.target_node_id)
    visiting=set(); visited=set()
    def dfs(n: str) -> bool:
        if n in visiting: return True
        if n in visited: return False
        visiting.add(n)
        for m in adj.get(n,()):
            if dfs(m): return True
        visiting.remove(n); visited.add(n); return False
    return any(dfs(i) for i in ids)
