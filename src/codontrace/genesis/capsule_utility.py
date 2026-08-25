"""Outcome-based capsule utility evaluation for GENESIS evidence surfaces.

Scientific design (aligned with ALife / multi-agent communication literature):

* Utility is a *task-specific outcome delta*, not a synthetic reward for a
  behavior-digest change alone.
* Behavioral adoption is instrumented separately from usefulness.
* Claim eligibility requires a measured numeric outcome and a trusted
  (non-provisional) source-fitness status.
* Synthetic fixed rewards such as ``task_delta = 1.0`` are forbidden so
  ClaimGate cannot treat invented evidence as positive.

Extensibility for artificial-world research:
* Default measured axis is selection fitness before/after adoption.
* Future protocols may supply additional measured axes (survival, resource,
  reproduction, partner-task scores) without inventing fixed rewards.
* ``utility_task_delta`` remains ``None`` until a real task protocol provides
  a measured task score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CapsuleUtilityEvaluation:
    """Deterministic evaluation result for one capsule adoption event."""

    source_fitness_status: str
    state_changed: bool
    adoption_success: bool
    allowed_source: bool
    selection_delta_measured: bool
    utility_selection_delta: float | None
    utility_raw_fitness_delta: float | None
    utility_task_delta: float | None
    utility_delta: float | None
    utility_status: str
    claim_eligible: bool
    protocol_name: str = "capsule_outcome_utility_v2"

    def protocol_payload(
        self,
        *,
        capsule_id: str,
        target_organism_id: str,
        behavior_digest_before: str | None,
        behavior_digest_after: str | None,
        selection_fitness_before: float | None,
        selection_fitness_after: float | None,
    ) -> dict[str, Any]:
        return {
            "protocol": self.protocol_name,
            "capsule_id": str(capsule_id),
            "target_organism_id": str(target_organism_id),
            "behavior_digest_before": behavior_digest_before,
            "behavior_digest_after": behavior_digest_after,
            "source_fitness_status": self.source_fitness_status,
            "selection_fitness_before": selection_fitness_before,
            "selection_fitness_after": selection_fitness_after,
            "selection_delta_measured": self.selection_delta_measured,
        }


def evaluate_capsule_utility(
    *,
    raw_source_status: str,
    adoption_success: bool,
    target_behavior_before: str | None,
    target_behavior_after: str | None,
    selection_delta: float | None,
) -> CapsuleUtilityEvaluation:
    """Evaluate capsule usefulness from measured outcomes only.

    Rules:
    1. Never invent a synthetic task reward.
    2. Never upgrade provisional source status to measured solely because a
       behavior digest changed.
    3. claim_eligible requires adoption + measured positive outcome + trusted
       source status.
    """

    status = raw_source_status
    state_changed = (
        target_behavior_before is not None
        and target_behavior_after is not None
        and target_behavior_before != target_behavior_after
    )
    allowed_source = status in {"measured", "last_known"}
    selection_delta_measured = selection_delta is not None
    utility_selection_delta = selection_delta
    utility_raw_fitness_delta = selection_delta
    utility_task_delta = None  # reserved for future measured task protocols
    utility_delta = selection_delta

    if not adoption_success:
        utility_status = "blocked"
    elif selection_delta_measured and utility_delta is not None and utility_delta > 0.0:
        utility_status = "positive_utility_measured"
    elif selection_delta_measured and utility_delta is not None and utility_delta < 0.0:
        utility_status = "negative_utility_measured"
    elif selection_delta_measured and utility_delta is not None:
        utility_status = "zero_utility_measured"
    elif state_changed:
        utility_status = "state_change_only_not_measured"
    else:
        utility_status = "adoption_without_measured_outcome"

    claim_eligible = bool(
        adoption_success
        and selection_delta_measured
        and utility_delta is not None
        and utility_delta > 0.0
        and allowed_source
    )
    return CapsuleUtilityEvaluation(
        source_fitness_status=status,
        state_changed=state_changed,
        adoption_success=adoption_success,
        allowed_source=allowed_source,
        selection_delta_measured=selection_delta_measured,
        utility_selection_delta=utility_selection_delta,
        utility_raw_fitness_delta=utility_raw_fitness_delta,
        utility_task_delta=utility_task_delta,
        utility_delta=utility_delta,
        utility_status=utility_status,
        claim_eligible=claim_eligible,
    )
