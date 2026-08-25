"""Scientific classification of memory delayed-reward evidence.

Aligns with CLAIMS.md levels and ALife practice: temporal correlation is not
causal support. Causal claims require ablation/control digests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MemoryDelayedEvidenceClassification:
    evidence_status: str
    causal_status: str
    correct_delayed_action: bool
    claim_eligible: bool
    protocol_name: str = "memory_delayed_evidence_v1"


def classify_memory_delayed_evidence(
    *,
    memory_written: bool,
    memory_read: bool,
    reward_observed: bool,
    runtime_correct_flag: bool,
    control_digest: str | None = None,
    memory_enabled: bool = True,
) -> MemoryDelayedEvidenceClassification:
    """Classify one write/read/reward chain without inventing causal success.

    Rules:
    1. runtime_correct_flag from the world is trusted as read-linked success only
       when a memory read (or explicit flag) is present.
    2. write→later reward without read is temporal_correlation only.
    3. claim_eligible requires control_digest (ablation/paired no-memory).
    """

    if not memory_enabled:
        return MemoryDelayedEvidenceClassification(
            evidence_status="memory_disabled",
            causal_status="not_applicable",
            correct_delayed_action=False,
            claim_eligible=False,
        )
    if not memory_written and not memory_read:
        return MemoryDelayedEvidenceClassification(
            evidence_status="not_classified",
            causal_status="correlational_only",
            correct_delayed_action=False,
            claim_eligible=False,
        )

    has_control = bool(control_digest) and not str(control_digest).startswith("not_run")

    if memory_written and memory_read and reward_observed:
        status = "read_linked"
        correct = True
    elif runtime_correct_flag and memory_read:
        status = "read_linked"
        correct = True
    elif runtime_correct_flag and not memory_read:
        # Runtime flag without read is treated as provisional correlation.
        status = "temporal_correlation"
        correct = False
    elif memory_written and reward_observed and not memory_read:
        status = "temporal_correlation"
        correct = False
    elif memory_written:
        status = "observed_write"
        correct = False
    elif memory_read:
        status = "observed_read"
        correct = False
    else:
        status = "not_classified"
        correct = False

    if has_control and correct and reward_observed:
        causal = "causal_support"
        claim = True
    elif status == "read_linked":
        causal = "mechanism_candidate"
        claim = False
    else:
        causal = "correlational_only"
        claim = False

    return MemoryDelayedEvidenceClassification(
        evidence_status=status,
        causal_status=causal,
        correct_delayed_action=correct,
        claim_eligible=claim,
    )
