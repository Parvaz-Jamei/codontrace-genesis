"""Innovation protection guard rails for young genome/macro innovations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError


def _digest(payload: Mapping[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class InnovationProtectionConfig:
    protection_generations: int = 10
    minimum_trials: int = 20
    max_protected_fraction: float = 0.25
    novelty_bonus: float = 0.1
    protection_scope: str = "niche"

    def __post_init__(self) -> None:
        if self.protection_generations < 0 or self.minimum_trials < 0:
            raise ConfigurationError("protection_generations/minimum_trials must be non-negative.")
        if self.max_protected_fraction < 0 or self.max_protected_fraction > 1:
            raise ConfigurationError("max_protected_fraction must be in [0, 1].")
        if self.protection_scope not in {"global", "niche", "lineage"}:
            raise ConfigurationError("protection_scope must be global, niche, or lineage.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "protection_generations": self.protection_generations,
            "minimum_trials": self.minimum_trials,
            "max_protected_fraction": self.max_protected_fraction,
            "novelty_bonus": self.novelty_bonus,
            "protection_scope": self.protection_scope,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class InnovationRecord:
    innovation_id: str
    kind: str
    first_seen_generation: int
    protected_until_generation: int
    lineage_id: str
    contribution_digest: str | None
    status: str
    digest: str = ""
    novelty_score: float = 0.0
    safety_score: float = 1.0
    niche_id: str | None = None

    def __post_init__(self) -> None:
        computed = _digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("InnovationRecord digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "innovation_id": self.innovation_id,
            "kind": self.kind,
            "first_seen_generation": self.first_seen_generation,
            "protected_until_generation": self.protected_until_generation,
            "lineage_id": self.lineage_id,
            "contribution_digest": self.contribution_digest,
            "status": self.status,
            "novelty_score": self.novelty_score,
            "safety_score": self.safety_score,
            "niche_id": self.niche_id,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def build_innovation_record(
    innovation_id: str,
    kind: str,
    first_seen_generation: int,
    lineage_id: str,
    config: InnovationProtectionConfig | None = None,
    *,
    contribution_digest: str | None = None,
    novelty_score: float = 0.0,
    safety_score: float = 1.0,
    niche_id: str | None = None,
) -> InnovationRecord:
    cfg = config or InnovationProtectionConfig()
    payload: dict[str, JsonValue] = {
        "innovation_id": innovation_id,
        "kind": kind,
        "first_seen_generation": first_seen_generation,
        "protected_until_generation": first_seen_generation + cfg.protection_generations,
        "lineage_id": lineage_id,
        "contribution_digest": contribution_digest,
        "status": "protected",
        "novelty_score": novelty_score,
        "safety_score": safety_score,
        "niche_id": niche_id,
    }
    return InnovationRecord(
        innovation_id=innovation_id,
        kind=kind,
        first_seen_generation=first_seen_generation,
        protected_until_generation=first_seen_generation + cfg.protection_generations,
        lineage_id=lineage_id,
        contribution_digest=contribution_digest,
        status="protected",
        novelty_score=novelty_score,
        safety_score=safety_score,
        niche_id=niche_id,
        digest=_digest(payload),
    )


def enforce_innovation_protection_limit(
    records: Sequence[InnovationRecord],
    population_size: int,
    config: InnovationProtectionConfig | None = None,
    *,
    scope_id: str | None = None,
) -> tuple[InnovationRecord, ...]:
    cfg = config or InnovationProtectionConfig()
    if population_size <= 0:
        return ()
    candidates = [record for record in records if record.status == "protected"]
    if scope_id is not None:
        if cfg.protection_scope == "niche":
            candidates = [r for r in candidates if r.niche_id == scope_id]
        elif cfg.protection_scope == "lineage":
            candidates = [r for r in candidates if r.lineage_id == scope_id]
    max_count = max(0, int(population_size * cfg.max_protected_fraction))
    keep_ids = {
        record.innovation_id
        for record in sorted(
            candidates,
            key=lambda r: (-r.novelty_score, -r.safety_score, r.lineage_id, r.innovation_id),
        )[:max_count]
    }
    updated = []
    for record in records:
        if record.status == "protected" and record.innovation_id not in keep_ids:
            updated.append(_replace_status(record, "active"))
        else:
            updated.append(record)
    return tuple(updated)


def is_innovation_protected(record: InnovationRecord, generation: int) -> bool:
    return record.status == "protected" and generation <= record.protected_until_generation


def _replace_status(record: InnovationRecord, status: str) -> InnovationRecord:
    payload: dict[str, JsonValue] = {k: v for k, v in record.to_dict().items() if k != "digest"}
    payload["status"] = status
    return InnovationRecord(
        innovation_id=record.innovation_id,
        kind=record.kind,
        first_seen_generation=record.first_seen_generation,
        protected_until_generation=record.protected_until_generation,
        lineage_id=record.lineage_id,
        contribution_digest=record.contribution_digest,
        status=status,
        novelty_score=record.novelty_score,
        safety_score=record.safety_score,
        niche_id=record.niche_id,
        digest=_digest(payload),
    )
