"""Collective-intelligence evidence protocol primitives for GENESIS.

These objects separate observed social interaction from stronger collective
coordination claims.  A claim requires multi-agent dependency, role
complementarity, heldout partner evidence, ablation sensitivity, and a stable
digest.  No success is hard-coded: reports downgrade when evidence is missing.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.social import SocialInteractionEvent, score_social_interactions


@dataclass(frozen=True, slots=True)
class CollectiveTaskSpec:
    task_id: str
    requires_multiple_agents: bool
    required_roles: tuple[str, ...]
    heldout_partner_protocol_digest: str | None = None
    schema_version: str = "collective_task_spec_v1"

    def __post_init__(self) -> None:
        if not self.task_id:
            raise ValueError("task_id must not be empty")
        object.__setattr__(self, "required_roles", tuple(sorted(str(x) for x in self.required_roles)))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "requires_multiple_agents": self.requires_multiple_agents,
            "required_roles": list(self.required_roles),
            "heldout_partner_protocol_digest": self.heldout_partner_protocol_digest,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CollectiveCoordinationRecord:
    task_id: str
    tick: int
    participating_agents: tuple[str, ...]
    coordinated_progress_delta: float
    non_capsule: bool = True
    schema_version: str = "collective_coordination_record_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "participating_agents", tuple(sorted(str(x) for x in self.participating_agents)))
        object.__setattr__(self, "coordinated_progress_delta", round(require_finite_float("coordinated_progress_delta", self.coordinated_progress_delta), 10))
        if self.tick < 0:
            raise ValueError("tick must be non-negative")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "tick": self.tick,
            "participating_agents": list(self.participating_agents),
            "coordinated_progress_delta": self.coordinated_progress_delta,
            "non_capsule": self.non_capsule,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class RoleComplementarityRecord:
    task_id: str
    role_a: str
    role_b: str
    complementarity_delta: float
    evidence_digest: str
    schema_version: str = "role_complementarity_record_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "complementarity_delta", round(require_finite_float("complementarity_delta", self.complementarity_delta), 10))
        if not self.evidence_digest:
            raise ValueError("evidence_digest must not be empty")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "role_a": self.role_a,
            "role_b": self.role_b,
            "complementarity_delta": self.complementarity_delta,
            "evidence_digest": self.evidence_digest,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CollectiveAblationRecord:
    ablation_id: str
    baseline_digest: str
    ablated_digest: str
    performance_drop: float
    isolated_factor: str
    schema_version: str = "collective_ablation_record_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "performance_drop", round(require_finite_float("performance_drop", self.performance_drop), 10))
        if not self.baseline_digest or not self.ablated_digest or not self.isolated_factor:
            raise ValueError("collective ablation requires baseline, ablated digest, and isolated_factor")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "ablation_id": self.ablation_id,
            "baseline_digest": self.baseline_digest,
            "ablated_digest": self.ablated_digest,
            "performance_drop": self.performance_drop,
            "isolated_factor": self.isolated_factor,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CollectiveIntelligenceEvidenceReport:
    task: CollectiveTaskSpec
    coordination_records: tuple[CollectiveCoordinationRecord, ...]
    role_records: tuple[RoleComplementarityRecord, ...]
    ablation_records: tuple[CollectiveAblationRecord, ...]
    familiar_partner_digest: str | None
    unfamiliar_partner_digest: str | None
    non_capsule_cooperation_score: float
    capsule_transfer_score: float
    heldout_distinct: bool
    replay_digest: str | None
    schema_version: str = "collective_intelligence_evidence_report_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "non_capsule_cooperation_score", round(require_finite_float("non_capsule_cooperation_score", self.non_capsule_cooperation_score, non_negative=True), 10))
        object.__setattr__(self, "capsule_transfer_score", round(require_finite_float("capsule_transfer_score", self.capsule_transfer_score, non_negative=True), 10))
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ValueError("CollectiveIntelligenceEvidenceReport digest mismatch")
        object.__setattr__(self, "digest", computed)

    @property
    def claim_eligible(self) -> bool:
        return (
            self.task.requires_multiple_agents
            and len(self.task.required_roles) >= 2
            and bool(self.coordination_records)
            and bool(self.role_records)
            and bool(self.ablation_records)
            and self.non_capsule_cooperation_score > 0.0
            and self.heldout_distinct
            and bool(self.familiar_partner_digest)
            and bool(self.unfamiliar_partner_digest)
            and self.familiar_partner_digest != self.unfamiliar_partner_digest
            and bool(self.replay_digest)
        )

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "task": self.task.to_dict(),
            "coordination_records": [r.to_dict() for r in self.coordination_records],
            "role_records": [r.to_dict() for r in self.role_records],
            "ablation_records": [r.to_dict() for r in self.ablation_records],
            "familiar_partner_digest": self.familiar_partner_digest,
            "unfamiliar_partner_digest": self.unfamiliar_partner_digest,
            "non_capsule_cooperation_score": self.non_capsule_cooperation_score,
            "capsule_transfer_score": self.capsule_transfer_score,
            "heldout_distinct": self.heldout_distinct,
            "replay_digest": self.replay_digest,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "claim_eligible": self.claim_eligible, "digest": self.digest}


def build_collective_evidence_report(
    task: CollectiveTaskSpec,
    events: Sequence[SocialInteractionEvent],
    *,
    coordination_records: Sequence[CollectiveCoordinationRecord] = (),
    role_records: Sequence[RoleComplementarityRecord] = (),
    ablation_records: Sequence[CollectiveAblationRecord] = (),
    familiar_partner_digest: str | None = None,
    unfamiliar_partner_digest: str | None = None,
    replay_digest: str | None = None,
) -> CollectiveIntelligenceEvidenceReport:
    scores = score_social_interactions(events)
    return CollectiveIntelligenceEvidenceReport(
        task=task,
        coordination_records=tuple(coordination_records),
        role_records=tuple(role_records),
        ablation_records=tuple(ablation_records),
        familiar_partner_digest=familiar_partner_digest,
        unfamiliar_partner_digest=unfamiliar_partner_digest,
        non_capsule_cooperation_score=scores.non_capsule_cooperation_score,
        capsule_transfer_score=scores.capsule_social_transfer_score,
        heldout_distinct=bool(familiar_partner_digest and unfamiliar_partner_digest and familiar_partner_digest != unfamiliar_partner_digest),
        replay_digest=replay_digest,
    )

CollectiveEvidenceReport = CollectiveIntelligenceEvidenceReport
RoleComplementarityReport = RoleComplementarityRecord

@dataclass(frozen=True, slots=True)
class DivisionOfLaborReport:
    role_count: int
    stable_role_digest: str
    heldout_digest: str
    ablation_loss: float
    schema_version: str = "division_of_labor_report_v1"
    def __post_init__(self) -> None:
        object.__setattr__(self, "ablation_loss", require_finite_float("ablation_loss", self.ablation_loss, non_negative=True))
    @property
    def claim_eligible(self) -> bool:
        return self.role_count >= 2 and bool(self.stable_role_digest) and bool(self.heldout_digest) and self.ablation_loss > 0.0
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "role_count": self.role_count, "stable_role_digest": self.stable_role_digest, "heldout_digest": self.heldout_digest, "ablation_loss": self.ablation_loss, "claim_eligible": self.claim_eligible}
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

JointTaskProgressReport = DivisionOfLaborReport
PartnerHeldoutReport = DivisionOfLaborReport

@dataclass(frozen=True, slots=True)
class SocialClaimLadder:
    capsule_transfer: bool = False
    non_capsule_cooperation: bool = False
    heldout_partner: bool = False
    role_complementarity: bool = False
    ablation_loss: bool = False
    swarm_resilience: bool = False
    schema_version: str = "social_claim_ladder_v1"
    @property
    def level(self) -> str:
        if self.swarm_resilience and self.role_complementarity and self.ablation_loss and self.heldout_partner:
            return "swarm_intelligence_candidate"
        if self.role_complementarity and self.ablation_loss and self.heldout_partner:
            return "collective_coordination_candidate"
        if self.non_capsule_cooperation and self.heldout_partner:
            return "social_intelligence_candidate"
        if self.capsule_transfer or self.non_capsule_cooperation:
            return "social_interaction_observed"
        return "metadata_only"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "capsule_transfer": self.capsule_transfer, "non_capsule_cooperation": self.non_capsule_cooperation, "heldout_partner": self.heldout_partner, "role_complementarity": self.role_complementarity, "ablation_loss": self.ablation_loss, "swarm_resilience": self.swarm_resilience, "level": self.level}
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

# ---------------------------------------------------------------------------
# Collective task graphs and role-ablation protocols (P1)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CollectiveTaskNode:
    node_id: str
    required_role: str
    success_metric: str = "task_progress"
    schema_version: str = "collective_task_node_v1"

    def __post_init__(self) -> None:
        if not self.node_id or not self.required_role:
            raise ValueError("node_id and required_role are required")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "node_id": self.node_id, "required_role": self.required_role, "success_metric": self.success_metric}

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="collective_node")


@dataclass(frozen=True, slots=True)
class RoleDependencyEdge:
    source_node_id: str
    target_node_id: str
    dependency_kind: str = "enables"
    schema_version: str = "role_dependency_edge_v1"

    def __post_init__(self) -> None:
        if not self.source_node_id or not self.target_node_id:
            raise ValueError("role dependency requires source and target nodes")
        if self.source_node_id == self.target_node_id:
            raise ValueError("role dependency cannot point to itself")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "source_node_id": self.source_node_id, "target_node_id": self.target_node_id, "dependency_kind": self.dependency_kind}

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="role_dependency")


@dataclass(frozen=True, slots=True)
class CollectiveTaskGraph:
    task_spec: CollectiveTaskSpec
    nodes: tuple[CollectiveTaskNode, ...]
    edges: tuple[RoleDependencyEdge, ...] = ()
    single_agent_baseline_digest: str | None = None
    role_ablation_required: bool = True
    schema_version: str = "collective_task_graph_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(sorted(self.nodes, key=lambda node: node.node_id)))
        object.__setattr__(self, "edges", tuple(sorted(self.edges, key=lambda edge: (edge.source_node_id, edge.target_node_id, edge.dependency_kind))))
        node_ids = {node.node_id for node in self.nodes}
        for edge in self.edges:
            if edge.source_node_id not in node_ids or edge.target_node_id not in node_ids:
                raise ValueError("all dependency edges must reference graph nodes")

    @property
    def required_roles(self) -> tuple[str, ...]:
        return tuple(sorted({node.required_role for node in self.nodes}))

    @property
    def supports_collective_claim(self) -> bool:
        return self.task_spec.requires_multiple_agents and len(self.required_roles) >= 2 and bool(self.single_agent_baseline_digest)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "task_spec": self.task_spec.to_dict(),
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "required_roles": list(self.required_roles),
            "single_agent_baseline_digest": self.single_agent_baseline_digest,
            "role_ablation_required": self.role_ablation_required,
            "supports_collective_claim": self.supports_collective_claim,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="collective_task_graph")


@dataclass(frozen=True, slots=True)
class JointTaskProgressRecord:
    graph_digest: str
    tick: int
    contributing_agents: tuple[str, ...]
    completed_node_ids: tuple[str, ...]
    progress_delta: float
    evidence_digest: str | None = None
    schema_version: str = "joint_task_progress_record_v1"

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ValueError("tick must be non-negative")
        object.__setattr__(self, "contributing_agents", tuple(sorted(str(x) for x in self.contributing_agents)))
        object.__setattr__(self, "completed_node_ids", tuple(sorted(str(x) for x in self.completed_node_ids)))
        object.__setattr__(self, "progress_delta", round(require_finite_float("progress_delta", self.progress_delta), 10))

    @property
    def claim_eligible(self) -> bool:
        return len(self.contributing_agents) >= 2 and self.progress_delta > 0.0 and bool(self.evidence_digest)

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "graph_digest": self.graph_digest, "tick": self.tick, "contributing_agents": list(self.contributing_agents), "completed_node_ids": list(self.completed_node_ids), "progress_delta": self.progress_delta, "evidence_digest": self.evidence_digest, "claim_eligible": self.claim_eligible}

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="joint_task_progress")


@dataclass(frozen=True, slots=True)
class RoleAblationProtocol:
    ablate_roles: tuple[str, ...]
    preserve_population_size: bool = True
    replay_matched_seed: bool = True
    protocol_id: str = "role_ablation_protocol"
    schema_version: str = "role_ablation_protocol_v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "ablate_roles", tuple(sorted(str(role) for role in self.ablate_roles)))
        if not self.ablate_roles:
            raise ValueError("RoleAblationProtocol requires at least one role")

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "protocol_id": self.protocol_id, "ablate_roles": list(self.ablate_roles), "preserve_population_size": self.preserve_population_size, "replay_matched_seed": self.replay_matched_seed}

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="role_ablation_protocol")
