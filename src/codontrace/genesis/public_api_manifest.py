"""Public integration API manifest helpers.

The manifest makes the public research surface explicit. CodonTrace keeps the
scientific evidence APIs under ``codontrace.genesis``; root-level ``codontrace``
may re-export core convenience symbols, but integration/release hardening does
not require private imports for normal GENESIS research use.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload

ROOT_PUBLIC_API_POLICY = "genesis_scientific_api_under_codontrace.genesis"

_STABLE_SYMBOLS: tuple[tuple[str, str, str, bool], ...] = (
    ("GenesisEngine", "codontrace.genesis", "0.3.0a1", True),
    ("GenesisExperimentSpec", "codontrace.genesis", "0.3.0a1", True),
    ("GenesisRunResult", "codontrace.genesis", "0.3.0a1", True),
    ("Phase1RuntimeMaturityReport", "codontrace.genesis", "0.3.0a1-phase1", True),
    ("PhaseBScientificMaturityReport", "codontrace.genesis", "0.3.0a1-phaseB", True),
    ("ReleaseEvidencePackSample", "codontrace.genesis", "0.3.0a1-phaseB", True),
    ("FinalClaimManifest", "codontrace.genesis", "0.3.0a1-phase3", True),
    ("EvidenceLineageDAG", "codontrace.genesis", "0.3.0a1-phase3", True),
    ("PluginManifest", "codontrace.genesis", "0.3.0a1", True),
    # Explicit Phase-B aliases prevent hidden shadowing between mature runtime
    # primitives and Phase-B evidence schema records.
    ("PhaseBDiscoveryEvent", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBDiscoveryCandidate", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBDiscoveryWitness", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBDistanceToD0Result", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBAblationWitness", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBInterventionResult", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBHeldoutEvaluationResult", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBTaskGeneratorSpec", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBEnvironmentMutationSpec", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBScaleBenchmarkSpec", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBScaleBenchmarkReport", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBResourceBudgetPolicy", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBPluginValidationResult", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBReleaseEvidencePack", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBFinalClaimManifest", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("PhaseBEvidenceLineageDAG", "codontrace.genesis", "0.3.0a1-phaseB", False),
    # Backward-compatible legacy aliases are intentionally explicit and not
    # claim-ready; users can migrate to PhaseB* names for Phase-B evidence.
    ("LegacyDiscoveryWitness", "codontrace.genesis", "pre-phaseB", False),
    ("LegacyDistanceToD0Result", "codontrace.genesis", "pre-phaseB", False),
    ("LegacyInterventionResult", "codontrace.genesis", "pre-phaseB", False),
    ("LegacyHeldoutEvaluationResult", "codontrace.genesis", "pre-phaseB", False),
    ("LegacyScaleBenchmarkReport", "codontrace.genesis", "pre-phaseB", False),
    ("LegacyPluginValidationResult", "codontrace.genesis", "pre-phaseB", False),
    ("LegacyReleaseEvidencePack", "codontrace.genesis", "pre-phaseB", False),
    ("LegacyFinalClaimManifest", "codontrace.genesis", "pre-phaseB", False),
    ("LegacyEvidenceLineageDAG", "codontrace.genesis", "pre-phaseB", False),
    ("FinalClaimManifestSample", "codontrace.genesis", "0.3.0a1-phaseB", False),
    ("EvidenceLineageDAGSample", "codontrace.genesis", "0.3.0a1-phaseB", False),
)

_PROVISIONAL_SYMBOLS: tuple[tuple[str, str, str], ...] = ()

_DEPRECATED_SYMBOLS: tuple[tuple[str, str, str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class IntegrationPublicAPISymbol:
    symbol_name: str
    module_path: str
    stability_status: str
    introduced_in: str
    replacement_if_deprecated: str | None
    claim_ready_allowed: bool
    schema_digest: str

    def __post_init__(self) -> None:
        if self.stability_status not in {"stable", "provisional", "deprecated", "internal"}:
            raise ConfigurationError("Unsupported public API stability status")
        if self.stability_status == "provisional" and self.claim_ready_allowed:
            raise ConfigurationError("provisional symbols cannot be claim-ready by default")
        if self.stability_status == "deprecated" and not self.replacement_if_deprecated:
            raise ConfigurationError("deprecated symbols require a replacement or note")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "symbol_name": self.symbol_name,
            "module_path": self.module_path,
            "stability_status": self.stability_status,
            "introduced_in": self.introduced_in,
            "replacement_if_deprecated": self.replacement_if_deprecated,
            "claim_ready_allowed": self.claim_ready_allowed,
            "schema_digest": self.schema_digest,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="integration_api")


def _schema_digest(symbol_name: str, module_path: str, stability: str) -> str:
    return canonical_digest({"symbol_name": symbol_name, "module_path": module_path, "stability": stability}, prefix="api_schema")


def build_public_api_manifest() -> tuple[IntegrationPublicAPISymbol, ...]:
    rows: list[IntegrationPublicAPISymbol] = []
    for symbol, module, introduced, claim_ready in _STABLE_SYMBOLS:
        rows.append(IntegrationPublicAPISymbol(symbol, module, "stable", introduced, None, claim_ready, _schema_digest(symbol, module, "stable")))
    for symbol, module, introduced in _PROVISIONAL_SYMBOLS:
        rows.append(IntegrationPublicAPISymbol(symbol, module, "provisional", introduced, None, False, _schema_digest(symbol, module, "provisional")))
    for symbol, module, note, replacement in _DEPRECATED_SYMBOLS:
        rows.append(IntegrationPublicAPISymbol(symbol, module, "deprecated", "pre-phaseB", replacement or note, False, _schema_digest(symbol, module, "deprecated")))
    return tuple(rows)


def import_public_symbol(row: IntegrationPublicAPISymbol) -> Any:
    module = import_module(row.module_path)
    try:
        return getattr(module, row.symbol_name)
    except AttributeError as exc:  # pragma: no cover - exercised through audit/tests
        raise ConfigurationError(f"documented public symbol is not importable: {row.module_path}.{row.symbol_name}") from exc


def validate_public_api_manifest(rows: tuple[IntegrationPublicAPISymbol, ...] | None = None) -> dict[str, JsonValue]:
    manifest = rows or build_public_api_manifest()
    issues: list[str] = []
    seen: set[str] = set()
    for row in manifest:
        key = f"{row.module_path}.{row.symbol_name}"
        if key in seen:
            issues.append(f"duplicate_public_symbol:{key}")
        seen.add(key)
        if row.module_path.startswith("codontrace.genesis._") or ".__" in row.module_path:
            issues.append(f"private_public_symbol_path:{key}")
        if row.stability_status == "provisional" and row.claim_ready_allowed:
            issues.append(f"provisional_claim_ready:{key}")
        if row.stability_status == "stable":
            try:
                import_public_symbol(row)
            except Exception as exc:
                issues.append(f"import_failed:{key}:{type(exc).__name__}")
    return {
        "schema_version": "integration_public_api_manifest_audit_v1",
        "root_public_api_policy": ROOT_PUBLIC_API_POLICY,
        "passed": not issues,
        "feature_status": "complete_limited_claim" if not issues else "blocked_by_public_api_issue",
        "claim_gate_reason": "public API surface is importable and provisional symbols are not claim-ready" if not issues else "public API manifest has blocking issues",
        "issues": issues,
        "symbols": [row.to_dict() for row in manifest],
        "manifest_digest": canonical_digest([row.to_dict() for row in manifest], prefix="integration_public_api"),
    }


def public_api_manifest_payload() -> dict[str, JsonValue]:
    return validate_public_api_manifest()
