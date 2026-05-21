"""Schema-versioned evidence manifest helpers for GENESIS artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from codontrace._types import JsonValue

_ALLOWED_FEATURE_STATUS = {
    "measured",
    "empty_but_available",
    "unavailable",
    "disabled_by_config",
    "not_applicable",
    "provisional",
    # Phase-1 runtime maturity / claim-safety states. These are allowed
    # manifest statuses, but ClaimGate still decides whether any claim is
    # actually allowed. They prevent fake/placeholder/no-output cases from
    # being hidden behind missing fields.
    "allowed",
    "limited",
    "downgraded",
    "descriptive_only",
    "blocked",
    "rejected",
    "skipped_by_resource_budget",
    "not_claim_relevant",
}


def canonical_digest(payload: object) -> str:
    """Return a process-stable digest for JSON-like evidence payloads."""

    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("evidence digest payload must be finite canonical JSON.") from exc
    forbidden_fragments = ("object at 0x", "<function", "<bound method")
    if any(fragment in encoded for fragment in forbidden_fragments):
        raise ValueError("unstable runtime object representation entered evidence digest payload.")
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class EvidenceManifest:
    schema_version: str
    producer_version: str
    library_version: str
    config_digest: str
    source_digest: str
    protocol_digest: str
    artifact_digests: tuple[str, ...] = ()
    artifact_digest_map: dict[str, str] | None = None
    determinism_policy: str = "canonical_json_sha256_no_time_no_object_id"
    feature_status: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = (
            ("schema_version", self.schema_version),
            ("producer_version", self.producer_version),
            ("library_version", self.library_version),
            ("config_digest", self.config_digest),
            ("source_digest", self.source_digest),
            ("protocol_digest", self.protocol_digest),
            ("determinism_policy", self.determinism_policy),
        )
        missing = tuple(name for name, value in required if not value)
        if missing:
            raise ValueError(f"EvidenceManifest missing required fields: {missing!r}.")
        statuses = dict(self.feature_status)
        bad = tuple(sorted(key for key, value in statuses.items() if value not in _ALLOWED_FEATURE_STATUS))
        if bad:
            raise ValueError(f"EvidenceManifest feature_status has invalid entries: {bad!r}.")
        object.__setattr__(self, "artifact_digests", tuple(sorted(str(item) for item in self.artifact_digests)))
        object.__setattr__(self, "artifact_digest_map", dict(sorted((self.artifact_digest_map or {}).items())))
        object.__setattr__(self, "feature_status", dict(sorted(statuses.items())))

    @property
    def artifact_digest(self) -> str:
        """Aggregate artifact digest for manifest-level claim gates."""

        return canonical_digest({
            "artifact_digests": list(self.artifact_digests),
            "artifact_digest_map": dict(self.artifact_digest_map or {}),
        })

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "producer_version": self.producer_version,
            "library_version": self.library_version,
            "config_digest": self.config_digest,
            "source_digest": self.source_digest,
            "protocol_digest": self.protocol_digest,
            "artifact_digests": list(self.artifact_digests),
            "artifact_digest_map": dict(sorted((self.artifact_digest_map or {}).items())),
            "artifact_digest": self.artifact_digest,
            "determinism_policy": self.determinism_policy,
            "feature_status": dict(sorted(self.feature_status.items())),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def validate_claim_ready_schema(self) -> tuple[str, ...]:
        """Return missing/invalid manifest fields; empty tuple means schema-safe."""

        data = self.to_dict()
        required = (
            "schema_version",
            "producer_version",
            "library_version",
            "config_digest",
            "source_digest",
            "protocol_digest",
            "artifact_digest",
            "determinism_policy",
            "feature_status",
        )
        missing = [name for name in required if not data.get(name)]
        if self.determinism_policy != "canonical_json_sha256_no_time_no_object_id":
            missing.append("determinism_policy_not_canonical")
        return tuple(missing)
