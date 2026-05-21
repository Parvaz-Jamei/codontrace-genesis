"""Provider-neutral LLM review contract for GENESIS evidence and rule APIs.

This module defines schemas/protocols only. It does not call external LLM
providers and must not run inside the simulation hot loop.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, cast

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.claim_gate import default_claim_gate_policy, normalize_claim_label


class ReviewArtifactType(str, Enum):
    EVIDENCE_PACK = "evidence_pack"
    RUN_MANIFEST = "run_manifest"
    REPLAY_BUNDLE = "replay_bundle"
    RULE_PROPOSAL = "rule_proposal"
    CLAIM_TEXT = "claim_text"


class ReviewSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class ReviewArtifact:
    artifact_type: ReviewArtifactType
    payload: dict[str, JsonValue]
    digest: str = ""

    def __post_init__(self) -> None:
        if not self.digest:
            object.__setattr__(self, "digest", _digest(self.payload))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "artifact_type": self.artifact_type.value,
            "payload": self.payload,
            "digest": self.digest,
        }


@dataclass(frozen=True, slots=True)
class ReviewerInstructionSet:
    """Stable instruction metadata for an external reviewer."""

    goal: str = "review_evidence_without_overclaim"
    forbidden_claims: tuple[str, ...] = (
        "AGI",
        "consciousness",
        "proof of artificial life",
        "full GENESIS Engine",
    )
    require_structured_output: bool = True

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "goal": self.goal,
            "forbidden_claims": list(self.forbidden_claims),
            "require_structured_output": self.require_structured_output,
        }


@dataclass(frozen=True, slots=True)
class AllowedOutputSchema:
    required_fields: tuple[str, ...] = ("findings", "claim_review", "reviewer_id")
    max_findings: int = 64

    def to_dict(self) -> dict[str, JsonValue]:
        return {"required_fields": list(self.required_fields), "max_findings": self.max_findings}


@dataclass(frozen=True, slots=True)
class ForbiddenClaimPolicy:
    forbidden_terms: tuple[str, ...] | None = None
    action: str = "flag"

    def __post_init__(self) -> None:
        if self.forbidden_terms is None:
            aliases = default_claim_gate_policy().forbidden_aliases
            object.__setattr__(self, "forbidden_terms", aliases)
        else:
            normalized = tuple(
                sorted({normalize_claim_label(item) for item in self.forbidden_terms})
            )
            object.__setattr__(self, "forbidden_terms", normalized)

    def check_text(self, text: str) -> tuple[str, ...]:
        normalized_text = normalize_claim_label(text)
        assert self.forbidden_terms is not None
        display = {
            "agi": "AGI",
            "consciousness": "consciousness",
            "proof_of_artificial_life": "proof of artificial life",
        }
        return tuple(
            display.get(term, term) for term in self.forbidden_terms if term in normalized_text
        )

    def to_dict(self) -> dict[str, JsonValue]:
        assert self.forbidden_terms is not None
        return {
            "forbidden_terms": list(self.forbidden_terms),
            "action": self.action,
            "derived_from": "ClaimGatePolicy",
        }


@dataclass(frozen=True, slots=True)
class LLMReviewRequest:
    request_id: str
    artifacts: tuple[ReviewArtifact, ...]
    instruction_set: ReviewerInstructionSet = field(default_factory=ReviewerInstructionSet)
    allowed_output_schema: AllowedOutputSchema = field(default_factory=AllowedOutputSchema)

    @classmethod
    def from_evidence_pack(
        cls, evidence_pack: object, *, request_id: str = "review:default"
    ) -> LLMReviewRequest:
        if hasattr(evidence_pack, "to_dict"):
            payload = cast(dict[str, JsonValue], cast(Any, evidence_pack).to_dict())
        elif isinstance(evidence_pack, Mapping):
            payload = {str(k): cast(JsonValue, v) for k, v in evidence_pack.items()}
        else:
            raise TypeError("evidence_pack must be mapping-like or expose to_dict().")
        return cls(
            request_id=request_id,
            artifacts=(ReviewArtifact(ReviewArtifactType.EVIDENCE_PACK, payload),),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "request_id": self.request_id,
            "artifacts": [item.to_dict() for item in self.artifacts],
            "instruction_set": self.instruction_set.to_dict(),
            "allowed_output_schema": self.allowed_output_schema.to_dict(),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    severity: ReviewSeverity
    message: str
    artifact_digest: str | None = None
    path: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "severity": self.severity.value,
            "message": self.message,
            "artifact_digest": self.artifact_digest,
            "path": self.path,
        }


@dataclass(frozen=True, slots=True)
class ClaimReview:
    allowed: bool
    flagged_claims: tuple[str, ...] = ()
    reason: str = ""

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "allowed": self.allowed,
            "flagged_claims": list(self.flagged_claims),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryReview:
    status: str = "review_needed"
    reason: str = "candidate_not_proof"

    def to_dict(self) -> dict[str, JsonValue]:
        return {"status": self.status, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class RuleProposalReview:
    accepted_for_validation: bool
    reason: str = "schema_only_review"

    def to_dict(self) -> dict[str, JsonValue]:
        return {"accepted_for_validation": self.accepted_for_validation, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class LLMReviewResult:
    request_digest: str
    reviewer_id: str
    findings: tuple[ReviewFinding, ...]
    claim_review: ClaimReview
    discovery_review: DiscoveryReview = field(default_factory=DiscoveryReview)
    rule_proposal_review: RuleProposalReview | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "request_digest": self.request_digest,
            "reviewer_id": self.reviewer_id,
            "findings": [item.to_dict() for item in self.findings],
            "claim_review": self.claim_review.to_dict(),
            "discovery_review": self.discovery_review.to_dict(),
            "rule_proposal_review": None
            if self.rule_proposal_review is None
            else self.rule_proposal_review.to_dict(),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


class ReviewerProtocol(Protocol):
    """External reviewer protocol. Implementations live outside core."""

    def review(self, request: LLMReviewRequest) -> LLMReviewResult:
        """Return a structured review result."""
        ...


@dataclass(frozen=True, slots=True)
class HumanReviewDecision:
    reviewer: str
    decision: str
    reason: str
    review_result_digest: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "reviewer": self.reviewer,
            "decision": self.decision,
            "reason": self.reason,
            "review_result_digest": self.review_result_digest,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ExternalReviewRecord:
    request_digest: str
    result_digest: str
    validated: bool
    human_decision: HumanReviewDecision | None = None

    @classmethod
    def from_result(
        cls,
        result: LLMReviewResult,
        *,
        validated: bool = True,
        human_decision: HumanReviewDecision | None = None,
    ) -> ExternalReviewRecord:
        return cls(
            request_digest=result.request_digest,
            result_digest=result.digest(),
            validated=validated,
            human_decision=human_decision,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "request_digest": self.request_digest,
            "result_digest": self.result_digest,
            "validated": self.validated,
            "human_decision": None
            if self.human_decision is None
            else self.human_decision.to_dict(),
        }


def validate_review_result(
    result: LLMReviewResult,
    *,
    request: LLMReviewRequest | None = None,
    forbidden_policy: ForbiddenClaimPolicy | None = None,
) -> LLMReviewResult:
    """Validate provider-neutral review output and flag forbidden claims."""

    if request is not None and result.request_digest != request.digest():
        msg = "review result request_digest does not match request."
        raise ConfigurationError(msg)
    forbidden_policy = forbidden_policy or ForbiddenClaimPolicy()
    flagged = list(result.claim_review.flagged_claims)
    for finding in result.findings:
        flagged.extend(forbidden_policy.check_text(finding.message))
    unique_flagged = tuple(sorted(set(flagged)))
    claim_review = ClaimReview(
        allowed=not unique_flagged and result.claim_review.allowed,
        flagged_claims=unique_flagged,
        reason=result.claim_review.reason
        or ("forbidden_claims_flagged" if unique_flagged else "ok"),
    )
    return LLMReviewResult(
        request_digest=result.request_digest,
        reviewer_id=result.reviewer_id,
        findings=result.findings,
        claim_review=claim_review,
        discovery_review=result.discovery_review,
        rule_proposal_review=result.rule_proposal_review,
    )


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
