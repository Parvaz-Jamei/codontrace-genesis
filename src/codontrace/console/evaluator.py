"""Evidence evaluator and hypothesis assessment for simulation runs.

Standard library only. Does not import the evolution engine.
Evaluates empirical evidence across simulation runs into five canonical states:
- 'supported': Hypothesis empirically supported by valid data and passing controls.
- 'not_supported': Run completed validly with proper controls, but evidence does not support hypothesis.
- 'inconclusive': Sample size, statistical power, or measurement variance insufficient.
- 'invalid': Measurement errors, invariant violations, broken controls, or runtime exceptions.
- 'not_evaluated': Run is in progress, queued, or exploratory without a registered hypothesis protocol.
"""

from __future__ import annotations

import math
import time
from typing import Any, Literal

HypothesisVerdict = Literal[
    "supported",
    "not_supported",
    "inconclusive",
    "invalid",
    "not_evaluated",
]


def _is_finite(val: Any) -> bool:
    """Return True if val is an int or a finite float."""
    if not isinstance(val, bool) and isinstance(val, (int, float)):
        return math.isfinite(val)
    return False


ACTIVE_LIFECYCLE_STATES: tuple[str, ...] = (
    "STARTING",
    "QUEUED",
    "RUNNING",
    "PAUSING",
    "PAUSED",
    "RESUMING",
    "STOPPING",
)


# @audit-control C3
def evaluate_run_hypothesis(run_data: dict[str, Any] | None) -> dict[str, Any]:
    """Evaluate empirical evidence for a simulation run without boolean locking."""
    now = time.time()
    if run_data is None or not isinstance(run_data, dict):
        return {
            "verdict": "not_evaluated",
            "hypothesis_id": "none",
            "protocol": "unspecified",
            "confidence": None,
            "rationale": "No run data provided for evaluation.",
            "controls_passed": False,
            "evidence_summary": {},
            "evaluated_at": now,
        }

    status = str(run_data.get("status", "")).upper()
    if status in ACTIVE_LIFECYCLE_STATES:
        return {
            "verdict": "not_evaluated",
            "hypothesis_id": "pending_run_completion",
            "protocol": "active_run",
            "confidence": None,
            "rationale": f"Run is currently active ({status}); hypothesis assessment requires run completion.",
            "controls_passed": False,
            "evidence_summary": {"status": status},
            "evaluated_at": now,
        }

    execution = run_data.get("execution")
    if execution is None or not isinstance(execution, dict):
        if status in ("FAILED", "STOPPED", "CANCELLED"):
            return {
                "verdict": "invalid",
                "hypothesis_id": "aborted_run",
                "protocol": "lifecycle",
                "confidence": 0.0,
                "rationale": f"Run ended in state '{status}' without producing execution telemetry.",
                "controls_passed": False,
                "evidence_summary": {"status": status},
                "evaluated_at": now,
            }
        return {
            "verdict": "not_evaluated",
            "hypothesis_id": "no_execution_data",
            "protocol": "unspecified",
            "confidence": None,
            "rationale": "No execution record exists for this run.",
            "controls_passed": False,
            "evidence_summary": {},
            "evaluated_at": now,
        }

    # Validate execution integrity and control passes BEFORE candidate assessment
    validation_failures = execution.get("validation_failures") or []
    stop_reason = execution.get("stop_reason")
    replays = execution.get("replays") or []
    complete = execution.get("complete") is True
    if ("complete" in execution and not isinstance(execution["complete"], bool)) or not isinstance(validation_failures, list) or not isinstance(replays, list):
        return {"verdict": "invalid", "hypothesis_id": "execution_integrity", "protocol": "schema_validation", "confidence": None,
                "rationale": "Execution completion and integrity fields have invalid types.", "controls_passed": False, "evidence_summary": {}, "evaluated_at": now}

    if status in ("FAILED", "CANCELLED"):
        return {
            "verdict": "invalid",
            "hypothesis_id": "execution_integrity",
            "protocol": "lifecycle_validation",
            "confidence": 0.0,
            "rationale": f"Run ended in state '{status}'.",
            "controls_passed": False,
            "evidence_summary": {"status": status, "complete": complete},
            "evaluated_at": now,
        }

    if stop_reason == "EXCEPTION" or (isinstance(validation_failures, list) and len(validation_failures) > 0):
        return {
            "verdict": "invalid",
            "hypothesis_id": "execution_integrity",
            "protocol": "assay_validation",
            "confidence": 0.0,
            "rationale": f"Validation failures detected during run execution: {validation_failures}",
            "controls_passed": False,
            "evidence_summary": {"validation_failures": validation_failures, "stop_reason": stop_reason},
            "evaluated_at": now,
        }

    if replays and isinstance(replays, list):
        if any(isinstance(r, dict) and r.get("matched") is False for r in replays):
            return {
                "verdict": "invalid",
                "hypothesis_id": "replay_verification",
                "protocol": "deterministic_replay",
                "confidence": 0.0,
                "rationale": "Replay verification failed against recorded trajectory.",
                "controls_passed": False,
                "evidence_summary": {"replays": replays},
                "evaluated_at": now,
            }

    # Reference controls validation
    summary = execution.get("summary") or {}
    if not isinstance(summary, dict):
        return {"verdict": "invalid", "hypothesis_id": "execution_integrity", "protocol": "schema_validation", "confidence": None, "rationale": "Execution summary is not a mapping.", "controls_passed": False, "evidence_summary": {}, "evaluated_at": now}
    controls_flag = execution.get("controls_passed")
    if controls_flag is None:
        controls_flag = summary.get("controls_passed")
    if controls_flag is False:
        return {
            "verdict": "invalid",
            "hypothesis_id": "reference_controls",
            "protocol": "control_validation",
            "confidence": 0.0,
            "rationale": "Assay reference controls failed or unverified.",
            "controls_passed": False,
            "evidence_summary": {"controls_passed": False},
            "evaluated_at": now,
        }

    # Check for pre-computed hypothesis assessment only after integrity check
    if "hypothesis_assessment" in execution and isinstance(execution["hypothesis_assessment"], dict):
        candidate = dict(execution["hypothesis_assessment"])
        v = candidate.get("verdict")
        conf = candidate.get("confidence")
        if conf is not None:
            if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not _is_finite(conf) or conf < 0.0 or conf > 1.0:
                return {
                    "verdict": "invalid",
                    "hypothesis_id": str(candidate.get("hypothesis_id", "candidate_assessment")),
                    "protocol": str(candidate.get("protocol", "candidate_validation")),
                    "confidence": 0.0,
                    "rationale": f"Candidate assessment rejected: invalid confidence ({conf}), must be finite in [0.0, 1.0].",
                    "controls_passed": False,
                    "evidence_summary": candidate.get("evidence_summary", {}),
                    "evaluated_at": now,
                }
        if v not in ("supported", "not_supported", "inconclusive", "invalid", "not_evaluated"):
            return {
                "verdict": "invalid",
                "hypothesis_id": str(candidate.get("hypothesis_id", "candidate_assessment")),
                "protocol": str(candidate.get("protocol", "candidate_validation")),
                "confidence": 0.0,
                "rationale": f"Candidate assessment rejected: unrecognized verdict '{v}'.",
                "controls_passed": False,
                "evidence_summary": candidate.get("evidence_summary", {}),
                "evaluated_at": now,
            }
        if v in ("supported", "not_supported"):
            if candidate.get("controls_passed") is not True:
                return {
                    "verdict": "invalid",
                    "hypothesis_id": str(candidate.get("hypothesis_id", "candidate_assessment")),
                    "protocol": str(candidate.get("protocol", "candidate_validation")),
                    "confidence": 0.0,
                    "rationale": "Candidate assessment claims a confirmatory verdict without verified passing controls.",
                    "controls_passed": False,
                    "evidence_summary": candidate.get("evidence_summary", {}),
                    "evaluated_at": now,
                }
            if status != "COMPLETED" or not complete:
                return {
                    "verdict": "inconclusive" if status == "STOPPED" else "invalid",
                    "hypothesis_id": str(candidate.get("hypothesis_id", "candidate_assessment")),
                    "protocol": str(candidate.get("protocol", "candidate_validation")),
                    "confidence": 0.0,
                    "rationale": f"Candidate assessment claims a confirmatory verdict on incomplete run (status='{status}', complete={complete}).",
                    "controls_passed": False,
                    "evidence_summary": candidate.get("evidence_summary", {}),
                    "evaluated_at": now,
                }
        candidate.setdefault("evaluated_at", now)
        return candidate

    # Numeric summaries are descriptive measurements, not registered decision rules.
    # Statistical inference is accepted through the integrity-checked assessment
    # interface above; there is no inferred threshold or fabricated confidence.
    challenge = execution.get("challenge") or summary.get("challenge")
    metrics_by_challenge = {
        "OEE_NOVELTY": ("oee_unbounded_novelty", {"slope": summary.get("activity_slope"), "generations": summary.get("total_generations", execution.get("total_generations"))}),
        "MLS_PRICE": ("mls_price_partition", {"between_term": summary.get("between_deme_selection_term"), "within_term": summary.get("within_deme_selection_term")}),
        "FUNCTIONAL_INFO": ("hazen_functional_info_accretion", {"fi_bits": summary.get("hazen_functional_info_bits", summary.get("functional_info_bits")), "percolation": summary.get("neutral_percolation_rate")}),
    }
    if challenge in metrics_by_challenge:
        hypothesis_id, evidence = metrics_by_challenge[challenge]
        invalid = any(value is not None and not _is_finite(value) for value in evidence.values())
        if challenge == "FUNCTIONAL_INFO":
            percolation = evidence["percolation"]
            bits = evidence["fi_bits"]
            if _is_finite(percolation) and not 0.0 <= percolation <= 1.0:
                invalid = True
            if _is_finite(bits) and bits < 0:
                invalid = True
            zero_success = bool(summary.get("zero_success") or ("viable_count" in summary and summary.get("viable_count") == 0))
            censored = bool(zero_success or summary.get("censored") or summary.get("bound_type") in ("censored", "upper_bound", "lower_bound"))
            # With zero successes, an upper probability bound translates to a
            # lower information bound under I=-log2(F), not an upper I bound.
            evidence.update({"censored": censored, "zero_success": zero_success,
                "bound_type": "lower_bound" if zero_success else str(summary.get("bound_type") or ("censored" if censored else "point_estimate")),
                "reported_bound_type": summary.get("bound_type")})
        if challenge == "OEE_NOVELTY":
            generations = evidence["generations"]
            if _is_finite(generations) and (generations < 0 or int(generations) != generations):
                invalid = True
        return {
            "verdict": "invalid" if invalid else "inconclusive", "hypothesis_id": hypothesis_id,
            "protocol": "descriptive_metrics_without_registered_inference", "confidence": None,
            "rationale": "Invalid numeric metric or domain constraint." if invalid else (
                "Observed metrics remain exploratory without a verified preregistered assessment and replicated controls."
                + (" Zero successes imply a censored lower information bound, not a finite point estimate." if evidence.get("zero_success") else "")),
            "controls_passed": controls_flag is True, "evidence_summary": evidence, "evaluated_at": now,
        }

    diagnostics = run_data.get("diagnostics")
    if isinstance(diagnostics, dict):
        by_seed = diagnostics.get("by_seed") or []
        contrasts = []
        seeds = set()
        blocked = 0
        invalid = not isinstance(by_seed, list)
        if isinstance(by_seed, list):
            for seed_entry in by_seed:
                if not isinstance(seed_entry, dict):
                    invalid = True
                    continue
                seed = seed_entry.get("seed")
                if isinstance(seed, (int, str)) and not isinstance(seed, bool):
                    seeds.add(str(seed))
                matrices = seed_entry.get("matrices") or []
                if not isinstance(matrices, list):
                    invalid = True
                    continue
                for matrix in matrices:
                    if not isinstance(matrix, dict):
                        invalid = True
                        continue
                    if matrix.get("blocked_reason"):
                        blocked += 1
                        continue
                    value = matrix.get("mean_contrast", matrix.get("slope"))
                    if value is None:
                        continue
                    if not _is_finite(value):
                        invalid = True
                    else:
                        contrasts.append(float(value))
        return {
            "verdict": "invalid" if invalid else "inconclusive",
            "hypothesis_id": "red_queen_time_shift", "protocol": "descriptive_time_shift",
            "confidence": None, "rationale": "Invalid time-shift measurement schema or non-finite contrast." if invalid else
                "Time-shift contrasts are descriptive. Registered seed-level inference, reciprocal endpoints and matched controls are needed for a hypothesis verdict.",
            "controls_passed": controls_flag is True,
            "evidence_summary": {"independent_seeds": len(seeds), "contrasts": contrasts,
                "blocked_matrices": blocked, "diagnostics_complete": execution.get("diagnostics_complete") is True},
            "evaluated_at": now,
        }

    return {
        "verdict": "not_evaluated", "hypothesis_id": "exploratory_run" if execution.get("exploratory") else "unspecified",
        "protocol": "exploratory_sampling" if execution.get("exploratory") else "general",
        "confidence": None, "rationale": "No verified hypothesis assessment was supplied; archived telemetry remains available for analysis.",
        "controls_passed": controls_flag is True, "evidence_summary": {"complete": complete}, "evaluated_at": now,
    }
