"""GENESIS replay metadata verification helpers.

ReplayBundle is currently a deterministic replay metadata bundle. The verifier
checks digests against a run result; it does not re-execute the simulation yet.
"""

from codontrace.genesis.artifacts import (
    ReplayBundle,
    ReplayVerificationResult,
    verify_replay_bundle,
)

__all__ = ["ReplayBundle", "ReplayVerificationResult", "verify_replay_bundle"]

from dataclasses import dataclass
from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest as _phase3_digest

@dataclass(frozen=True, slots=True)
class ReplayBundleManifest:
    config_digest: str
    seed_digest: str
    source_digest: str
    artifact_digests: tuple[str, ...]
    environment_digest: str
    schema_version: str = "replay_bundle_manifest_v1"
    def __post_init__(self) -> None:
        if not self.config_digest or not self.seed_digest or not self.source_digest or not self.environment_digest:
            raise ValueError("ReplayBundleManifest requires config/seed/source/environment digests")
        if any(not d for d in self.artifact_digests):
            raise ValueError("ReplayBundleManifest rejects missing artifact digest")
        object.__setattr__(self, "artifact_digests", tuple(sorted(self.artifact_digests)))
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "config_digest": self.config_digest, "seed_digest": self.seed_digest, "source_digest": self.source_digest, "artifact_digests": list(self.artifact_digests), "environment_digest": self.environment_digest}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class ReplayBundleV2:
    manifest: ReplayBundleManifest
    partial_failure_status: str = "none"
    schema_version: str = "replay_bundle_v2"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "manifest": self.manifest.to_dict(), "partial_failure_status": self.partial_failure_status}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class ReplayEquivalenceReport:
    continuous_digest: str
    resumed_digest: str
    equivalent: bool
    mismatch_field_path: str | None = None
    schema_version: str = "replay_equivalence_report_v1"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "continuous_digest": self.continuous_digest, "resumed_digest": self.resumed_digest, "equivalent": self.equivalent, "mismatch_field_path": self.mismatch_field_path}
    def digest(self) -> str:
        return _phase3_digest(self.to_dict())
