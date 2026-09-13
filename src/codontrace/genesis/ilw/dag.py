"""Load and validate the ILW INTEGRATION_DAG.json artifact."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codontrace.errors import ConfigurationError

DAG_FILENAME = "INTEGRATION_DAG.json"
CLAIM_CEILING = "runtime_observation"
SCIENTIFIC_NAME = "integrated eco-evolutionary runtime"

REQUIRED_TELEMETRY_FIELDS: tuple[str, ...] = (
    "run_id",
    "seed",
    "tick",
    "generation",
    "world_spec_digest",
    "event_id",
    "causal_parent_ids",
    "edge_id",
    "actor_id",
    "lineage_id",
    "genome_digest",
    "source_id",
    "capsule_id",
    "capsule_parent_id",
    "payload_digest",
    "provenance_digest",
    "attempted",
    "accepted",
    "applied",
    "blocked_reason",
    "state_before_digest",
    "state_after_digest",
    "energy_delta",
    "resource_delta",
    "fitness_proxy_delta",
)


class IntegrationDAGError(ConfigurationError):
    """Raised when the integration DAG is missing, invalid, or incomplete."""


def _dag_path() -> Path:
    return Path(__file__).resolve().parent / DAG_FILENAME


@dataclass(frozen=True, slots=True)
class IntegrationEdge:
    edge_id: str
    source: str
    target: str
    required: bool
    knockout_id: str | None
    required_telemetry_fields: tuple[str, ...]
    description: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> IntegrationEdge:
        edge_id = str(raw.get("edge_id", "")).strip()
        source = str(raw.get("source", "")).strip()
        target = str(raw.get("target", "")).strip()
        if not edge_id or not source or not target:
            raise IntegrationDAGError("Each edge requires edge_id, source, and target.")
        telemetry = raw.get("required_telemetry_fields", ())
        if not isinstance(telemetry, Sequence) or isinstance(telemetry, (str, bytes)):
            raise IntegrationDAGError(f"Edge {edge_id!r} telemetry fields must be a list.")
        knockout = raw.get("knockout_id")
        return cls(
            edge_id=edge_id,
            source=source,
            target=target,
            required=bool(raw.get("required", True)),
            knockout_id=None if knockout in (None, "", "null") else str(knockout),
            required_telemetry_fields=tuple(str(item) for item in telemetry),
            description=str(raw.get("description", "")),
        )


@dataclass(frozen=True, slots=True)
class IntegrationDAG:
    schema: str
    claim_ceiling: str
    scientific_name: str
    subsystems: tuple[str, ...]
    edges: tuple[IntegrationEdge, ...]
    required_telemetry_fields: tuple[str, ...]
    knockout_ids: tuple[str, ...]
    raw: Mapping[str, Any]

    @property
    def required_edge_ids(self) -> frozenset[str]:
        return frozenset(edge.edge_id for edge in self.edges if edge.required)

    @property
    def edge_ids(self) -> frozenset[str]:
        return frozenset(edge.edge_id for edge in self.edges)

    @property
    def subsystem_ids(self) -> frozenset[str]:
        return frozenset(self.subsystems)

    def edge_by_id(self, edge_id: str) -> IntegrationEdge:
        for edge in self.edges:
            if edge.edge_id == edge_id:
                return edge
        raise IntegrationDAGError(f"Unknown edge_id {edge_id!r}.")

    def assert_required_edges_present(self, observed_edge_ids: Iterable[str]) -> None:
        observed = {str(item) for item in observed_edge_ids}
        missing = sorted(self.required_edge_ids - observed)
        if missing:
            raise IntegrationDAGError(
                "Missing required integration edges before full-world claim: "
                + ", ".join(missing)
            )
        unknown = sorted(observed - self.edge_ids)
        if unknown:
            raise IntegrationDAGError(
                "Unknown integration edge_ids (orphan edges): " + ", ".join(unknown)
            )

    def assert_claim_ceiling(self) -> None:
        if self.claim_ceiling != CLAIM_CEILING:
            raise IntegrationDAGError(
                f"ILW claim ceiling must remain {CLAIM_CEILING!r}; "
                f"got {self.claim_ceiling!r}."
            )


def load_integration_dag(path: Path | None = None) -> IntegrationDAG:
    dag_path = path if path is not None else _dag_path()
    if not dag_path.is_file():
        raise IntegrationDAGError(f"INTEGRATION_DAG.json not found at {dag_path}.")
    try:
        payload = json.loads(dag_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IntegrationDAGError(f"INTEGRATION_DAG.json is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise IntegrationDAGError("INTEGRATION_DAG.json root must be an object.")

    subsystems_raw = payload.get("subsystems", [])
    if not isinstance(subsystems_raw, list) or not subsystems_raw:
        raise IntegrationDAGError("INTEGRATION_DAG.json must declare subsystems.")
    subsystems: list[str] = []
    for item in subsystems_raw:
        if isinstance(item, Mapping):
            sid = str(item.get("id", "")).strip()
        else:
            sid = str(item).strip()
        if not sid:
            raise IntegrationDAGError("Subsystem id must be non-empty.")
        subsystems.append(sid)

    edges_raw = payload.get("edges", [])
    if not isinstance(edges_raw, list) or not edges_raw:
        raise IntegrationDAGError("INTEGRATION_DAG.json must declare edges.")
    edges = tuple(
        IntegrationEdge.from_mapping(item)
        for item in edges_raw
        if isinstance(item, Mapping)
    )
    if len(edges) != len(edges_raw):
        raise IntegrationDAGError("Every edge entry must be an object.")

    edge_ids = [edge.edge_id for edge in edges]
    if len(edge_ids) != len(set(edge_ids)):
        raise IntegrationDAGError("Duplicate edge_id values in INTEGRATION_DAG.json.")

    subsystem_set = set(subsystems)
    for edge in edges:
        if edge.source not in subsystem_set or edge.target not in subsystem_set:
            raise IntegrationDAGError(
                f"Edge {edge.edge_id!r} references unknown subsystem "
                f"{edge.source!r} -> {edge.target!r}."
            )

    telemetry = payload.get("required_telemetry_fields", REQUIRED_TELEMETRY_FIELDS)
    if not isinstance(telemetry, Sequence) or isinstance(telemetry, (str, bytes)):
        raise IntegrationDAGError("required_telemetry_fields must be a list.")
    telemetry_fields = tuple(str(item) for item in telemetry)
    missing_global = [name for name in REQUIRED_TELEMETRY_FIELDS if name not in telemetry_fields]
    if missing_global:
        raise IntegrationDAGError(
            "INTEGRATION_DAG.json missing required telemetry fields: "
            + ", ".join(missing_global)
        )

    knockouts_raw = payload.get("knockouts", [])
    if not isinstance(knockouts_raw, list):
        raise IntegrationDAGError("knockouts must be a list.")
    knockout_ids = tuple(
        str(item.get("knockout_id"))
        for item in knockouts_raw
        if isinstance(item, Mapping) and item.get("knockout_id")
    )

    claim_ceiling = str(payload.get("claim_ceiling", "")).strip()
    scientific_name = str(payload.get("scientific_name", "")).strip()
    dag = IntegrationDAG(
        schema=str(payload.get("schema", "")),
        claim_ceiling=claim_ceiling,
        scientific_name=scientific_name,
        subsystems=tuple(subsystems),
        edges=edges,
        required_telemetry_fields=telemetry_fields,
        knockout_ids=knockout_ids,
        raw=payload,
    )
    dag.assert_claim_ceiling()
    if not dag.required_edge_ids:
        raise IntegrationDAGError("INTEGRATION_DAG.json has no required edges.")
    if scientific_name != SCIENTIFIC_NAME:
        raise IntegrationDAGError(
            f"scientific_name must be {SCIENTIFIC_NAME!r}; got {scientific_name!r}."
        )
    return dag
