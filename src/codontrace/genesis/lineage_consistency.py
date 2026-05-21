"""Integration EvidenceLineageDAG path consistency checks."""

from __future__ import annotations

from collections.abc import Mapping
from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest, is_real_evidence_digest


def validate_evidence_lineage_dag_payload(payload: Mapping[str, object]) -> dict[str, JsonValue]:
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    issues: list[str] = []
    node_ids: set[str] = set()
    if isinstance(nodes, list):
        for node in nodes:
            if isinstance(node, Mapping):
                node_id = str(node.get("node_id", node.get("id", "")))
                digest = node.get("digest", node.get("record_digest", ""))
                if not node_id:
                    issues.append("node_without_id")
                else:
                    node_ids.add(node_id)
                if not is_real_evidence_digest(digest):
                    issues.append(f"node_without_real_digest:{node_id}")
    if isinstance(edges, list):
        for edge in edges:
            if isinstance(edge, Mapping):
                source = str(edge.get("source", edge.get("from", "")))
                target = str(edge.get("target", edge.get("to", "")))
                if source not in node_ids or target not in node_ids:
                    issues.append(f"broken_edge:{source}->{target}")
    out: dict[str, JsonValue] = {"schema_version": "integration_lineage_consistency_v1", "passed": not issues, "issues": sorted(set(issues))}
    out["audit_digest"] = canonical_digest(out, prefix="integration_lineage")
    return out
