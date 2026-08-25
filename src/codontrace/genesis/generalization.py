"""Held-out and partner-generalization records for GENESIS campaigns."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from codontrace._types import JsonValue


@dataclass(frozen=True, slots=True)
class LineageGroup:
    group_id: str
    organism_ids: tuple[str, ...]
    source: str = "train"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "group_id": self.group_id,
            "organism_ids": list(self.organism_ids),
            "source": self.source,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class PartnerGroup(LineageGroup):
    source: str = "partner"


@dataclass(frozen=True, slots=True)
class MixedPopulationSpec:
    mode: str
    lineage_groups: tuple[LineageGroup, ...]
    heldout: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "mode": self.mode,
            "lineage_groups": [item.to_dict() for item in self.lineage_groups],
            "heldout": self.heldout,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class HeldoutWorldSpec:
    world_id: str
    world_digest: str
    relation_to_train: str = "heldout"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "world_id": self.world_id,
            "world_digest": self.world_digest,
            "relation_to_train": self.relation_to_train,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class GeneralizationResult:
    """Heldout generalization evaluation record.

    Status ladder (claim-strict):
    - protocol_not_run: no explicit heldout protocol executed
    - provisional: partial protocol without leakage-clean heldout
    - measured: real train/heldout digests from an explicit protocol
    - unavailable: cannot evaluate

    First-vs-last tick proxies are forbidden. claim_eligible requires
    measured status, distinct digests, and a non-not_run heldout digest.
    """

    evaluation_id: str
    train_digest: str
    heldout_digest: str
    score: float
    claim_eligible: bool = False
    status: str = "protocol_not_run"
    schema_version: str = "generalization_result_v2"

    def __post_init__(self) -> None:
        allowed = {"protocol_not_run", "provisional", "measured", "unavailable"}
        if self.status not in allowed:
            raise ValueError(f"invalid generalization status: {self.status}")
        # Hard gate: never claim-eligible on not_run digests or non-measured status.
        if (
            self.claim_eligible
            and (
                self.status != "measured"
                or str(self.train_digest).startswith("not_run")
                or str(self.heldout_digest).startswith("not_run")
                or self.train_digest == self.heldout_digest
            )
        ):
            object.__setattr__(self, "claim_eligible", False)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "evaluation_id": self.evaluation_id,
            "train_digest": self.train_digest,
            "heldout_digest": self.heldout_digest,
            "score": self.score,
            "claim_eligible": self.claim_eligible,
            "status": self.status,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


def _digest(payload: dict[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

# ---------------------------------------------------------------------------
# Heldout partner generalization protocol (P1)
# ---------------------------------------------------------------------------
from codontrace.genesis.canonical import canonical_digest as _generalization_canonical_digest, require_finite_float as _generalization_require_finite_float


@dataclass(frozen=True, slots=True)
class HeldoutPartnerEvaluationProtocol:
    enabled: bool = True
    train_partner_pool: str = "A"
    test_partner_pool: str = "B"
    prevent_lineage_overlap: bool = True
    compare_familiar_vs_unfamiliar: bool = True
    schema_version: str = "heldout_partner_evaluation_protocol_v1"

    def __post_init__(self) -> None:
        if not self.train_partner_pool or not self.test_partner_pool:
            raise ValueError("partner pool identifiers are required")
        if self.enabled and self.prevent_lineage_overlap and self.train_partner_pool == self.test_partner_pool:
            raise ValueError("heldout partner protocol requires distinct pools when lineage overlap is prevented")

    @property
    def claim_eligible_by_design(self) -> bool:
        return self.enabled and self.prevent_lineage_overlap and self.compare_familiar_vs_unfamiliar and self.train_partner_pool != self.test_partner_pool

    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "enabled": self.enabled, "train_partner_pool": self.train_partner_pool, "test_partner_pool": self.test_partner_pool, "prevent_lineage_overlap": self.prevent_lineage_overlap, "compare_familiar_vs_unfamiliar": self.compare_familiar_vs_unfamiliar, "claim_eligible_by_design": self.claim_eligible_by_design}

    def digest(self) -> str:
        return _generalization_canonical_digest(self.to_dict(), prefix="heldout_partner_protocol")


@dataclass(frozen=True, slots=True)
class HeldoutPartnerEvaluationRecord:
    protocol_digest: str
    familiar_partner_digest: str
    unfamiliar_partner_digest: str
    familiar_score: float
    unfamiliar_score: float
    leakage_status: str = "clean"
    schema_version: str = "heldout_partner_evaluation_record_v1"
    record_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "familiar_score", round(_generalization_require_finite_float("familiar_score", self.familiar_score), 10))
        object.__setattr__(self, "unfamiliar_score", round(_generalization_require_finite_float("unfamiliar_score", self.unfamiliar_score), 10))
        if not self.record_digest:
            object.__setattr__(self, "record_digest", _generalization_canonical_digest(self._payload(), prefix="heldout_partner_eval"))

    @property
    def generalization_delta(self) -> float:
        return round(self.unfamiliar_score - self.familiar_score, 10)

    @property
    def claim_eligible(self) -> bool:
        return self.leakage_status == "clean" and self.familiar_partner_digest != self.unfamiliar_partner_digest and self.unfamiliar_score > 0.0

    def _payload(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "protocol_digest": self.protocol_digest, "familiar_partner_digest": self.familiar_partner_digest, "unfamiliar_partner_digest": self.unfamiliar_partner_digest, "familiar_score": self.familiar_score, "unfamiliar_score": self.unfamiliar_score, "generalization_delta": self.generalization_delta, "leakage_status": self.leakage_status, "claim_eligible": self.claim_eligible}

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "record_digest": self.record_digest}

    def digest(self) -> str:
        return self.record_digest
