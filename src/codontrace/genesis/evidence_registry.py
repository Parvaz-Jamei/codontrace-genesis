"""Public evidence registry for GENESIS scientific claim surfaces."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.artifacts import PHASE2_MANIFEST_FIELDS
from codontrace.genesis.canonical import canonical_digest


@dataclass(frozen=True, slots=True)
class EvidenceRegistryEntry:
    field_name: str
    producing_module: str
    status_source: str
    digest_source: str
    claim_labels: tuple[str, ...] = ()
    schema_version: str = "evidence_registry_entry_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "field_name": self.field_name,
            "producing_module": self.producing_module,
            "status_source": self.status_source,
            "digest_source": self.digest_source,
            "claim_labels": list(self.claim_labels),
        }


class EvidenceRegistry:
    def __init__(self, entries: Iterable[EvidenceRegistryEntry] = ()) -> None:
        mapping: dict[str, EvidenceRegistryEntry] = {}
        for entry in entries:
            if entry.field_name in mapping:
                raise ConfigurationError(f"Duplicate evidence registry field: {entry.field_name}")
            mapping[entry.field_name] = entry
        self._entries = dict(sorted(mapping.items()))

    @classmethod
    def phase2_default(cls) -> "EvidenceRegistry":
        entries = []
        for name in PHASE2_MANIFEST_FIELDS:
            module = "engine"
            if "adf" in name or "macro" in name:
                module = "adf_runtime"
            elif "mutation" in name or "genome" in name:
                module = "structural_mutation"
            elif "contribution" in name or "ablation" in name:
                module = "contribution_ledger"
            elif "event_graph" in name:
                module = "event_graph"
            elif "intervention" in name or "causal" in name:
                module = "causal_validation"
            elif "discovery" in name or "oee" in name:
                module = "discovery_gate"
            elif "social" in name:
                module = "generalization"
            elif "semantic" in name or "translation" in name:
                module = "translation_profile"
            claims = tuple(_claims_for_field(name))
            entries.append(EvidenceRegistryEntry(
                field_name=name,
                producing_module=f"codontrace.genesis.{module}",
                status_source=f"protocol_statuses.phase2.{name}.status",
                digest_source=f"runtime_hashes.{name}",
                claim_labels=claims,
            ))
        return cls(entries)

    def get(self, field_name: str) -> EvidenceRegistryEntry:
        try:
            return self._entries[field_name]
        except KeyError as exc:
            raise ConfigurationError(f"Unregistered evidence field: {field_name}") from exc

    def entries(self) -> tuple[EvidenceRegistryEntry, ...]:
        return tuple(self._entries.values())

    def claim_labels(self) -> tuple[str, ...]:
        labels = {label for entry in self._entries.values() for label in entry.claim_labels}
        return tuple(sorted(labels))

    def validate_claim_references(self, labels: Iterable[str]) -> tuple[str, ...]:
        registered = set(self.claim_labels())
        return tuple(sorted(label for label in labels if label not in registered))

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": "evidence_registry_v1", "entries": [entry.to_dict() for entry in self.entries()]}

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def _claims_for_field(name: str) -> tuple[str, ...]:
    mapping = {
        "genome_program_digest": ("variable_genome_runtime_supported",),
        "structural_mutation_digest": ("variable_genome_runtime_supported",),
        "structural_mutation_record_digest": ("variable_genome_runtime_supported",),
        "adf_macro_registry_digest": ("adf_macro_usefulness_supported",),
        "adf_usefulness_report_digest": ("adf_macro_usefulness_supported",),
        "contribution_ledger_digest": ("contribution_attribution_supported",),
        "micro_ablation_attribution_digest": ("contribution_attribution_supported",),
        "event_graph_digest": ("event_graph_evidence_supported",),
        "intervention_result_digest": ("intervention_supported_causal_evidence",),
        "causal_intervention_result_digest": ("intervention_supported_causal_evidence",),
        "discovery_witness_digest": ("discovery_witness_candidate",),
        "oee_report_digest": ("oee_candidate_evidence_supported",),
        "social_generalization_digest": ("social_partner_generalization_supported", "collective_intelligence_candidate"),
        "semantic_proxy_report_digest": ("adaptive_gp_map_proxy",),
        "phase2_claim_decision_digest": ("variable_genome_runtime_supported", "adaptive_gp_map_proxy"),
        "claim_gate_decision_digest": ("variable_genome_runtime_supported", "adaptive_gp_map_proxy"),
    }
    return mapping.get(name, ())
