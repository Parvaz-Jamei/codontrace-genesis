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
    if isinstance(val, (int, float)):
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
    complete = bool(execution.get("complete", False))

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
        if v == "supported":
            if candidate.get("controls_passed") is not True:
                return {
                    "verdict": "invalid",
                    "hypothesis_id": str(candidate.get("hypothesis_id", "candidate_assessment")),
                    "protocol": str(candidate.get("protocol", "candidate_validation")),
                    "confidence": 0.0,
                    "rationale": "Candidate assessment claims 'supported' without verified passing controls.",
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
                    "rationale": f"Candidate assessment claims 'supported' on incomplete run (status='{status}', complete={complete}).",
                    "controls_passed": False,
                    "evidence_summary": candidate.get("evidence_summary", {}),
                    "evaluated_at": now,
                }
        candidate.setdefault("evaluated_at", now)
        return candidate

    # Frontier Challenge evaluations
    challenge = execution.get("challenge") or summary.get("challenge")

    if challenge == "OEE_NOVELTY":
        raw_slope = summary.get("activity_slope", 0.0)
        raw_gens = summary.get("total_generations", execution.get("total_generations", 0))
        if isinstance(raw_slope, bool) or isinstance(raw_gens, bool) or not _is_finite(raw_slope) or not _is_finite(raw_gens):
            return {
                "verdict": "invalid",
                "hypothesis_id": "oee_unbounded_novelty",
                "protocol": "bedau_channon_oee",
                "confidence": 0.0,
                "rationale": f"Non-finite evolutionary activity metric detected: slope={raw_slope}, gens={raw_gens}.",
                "controls_passed": False,
                "evidence_summary": {"slope": raw_slope, "generations": raw_gens},
                "evaluated_at": now,
            }
        slope = float(raw_slope)
        gens = int(raw_gens or 0)
        if not complete and gens < 1000:
            return {
                "verdict": "inconclusive",
                "hypothesis_id": "oee_unbounded_novelty",
                "protocol": "bedau_channon_oee",
                "confidence": 0.4,
                "rationale": f"Run halted before sufficient generational depth (gens={gens} < 1000).",
                "controls_passed": False,
                "evidence_summary": {"slope": slope, "generations": gens},
                "evaluated_at": now,
            }
        if gens < 100:
            return {
                "verdict": "inconclusive",
                "hypothesis_id": "oee_unbounded_novelty",
                "protocol": "bedau_channon_oee",
                "confidence": 0.4,
                "rationale": f"Generational depth insufficient for evolutionary activity trend evaluation (gens={gens} < 100).",
                "controls_passed": False,
                "evidence_summary": {"slope": slope, "generations": gens},
                "evaluated_at": now,
            }
        if slope >= 0.1:
            return {
                "verdict": "supported",
                "hypothesis_id": "oee_unbounded_novelty",
                "protocol": "bedau_channon_oee",
                "confidence": 0.95,
                "rationale": f"Positive evolutionary activity trend confirmed across observed window (activity_slope={slope:.4f} >= 0.10).",
                "controls_passed": True,
                "evidence_summary": {"slope": slope, "generations": gens},
                "evaluated_at": now,
            }
        return {
            "verdict": "not_supported",
            "hypothesis_id": "oee_unbounded_novelty",
            "protocol": "bedau_channon_oee",
            "confidence": 0.90,
            "rationale": f"Evolutionary activity bounded into finite cycling (activity_slope={slope:.4f} < 0.10).",
            "controls_passed": True,
            "evidence_summary": {"slope": slope, "generations": gens},
            "evaluated_at": now,
        }

    if challenge == "MLS_PRICE":
        raw_between = summary.get("between_deme_selection_term", 0.0)
        raw_within = summary.get("within_deme_selection_term", 0.0)
        if isinstance(raw_between, bool) or isinstance(raw_within, bool) or not _is_finite(raw_between) or not _is_finite(raw_within):
            return {
                "verdict": "invalid",
                "hypothesis_id": "mls_price_partition",
                "protocol": "price_1972_mls",
                "confidence": 0.0,
                "rationale": f"Non-finite selection metric detected in MLS Price partition (between={raw_between}, within={raw_within}).",
                "controls_passed": False,
                "evidence_summary": {"between_term": raw_between, "within_term": raw_within},
                "evaluated_at": now,
            }
        between = float(raw_between)
        within = float(raw_within)
        if not complete or status != "COMPLETED":
            return {
                "verdict": "inconclusive",
                "hypothesis_id": "mls_price_partition",
                "protocol": "price_1972_mls",
                "confidence": 0.5,
                "rationale": "Multilevel selection run terminated prematurely or incomplete.",
                "controls_passed": False,
                "evidence_summary": {"between_term": between, "within_term": within},
                "evaluated_at": now,
            }
        if between > 0.0:
            return {
                "verdict": "supported",
                "hypothesis_id": "mls_price_partition",
                "protocol": "price_1972_mls",
                "confidence": 0.92,
                "rationale": f"Positive between-group selection confirmed under Price partition (between_term={between:.4f} > 0).",
                "controls_passed": True,
                "evidence_summary": {"between_term": between, "within_term": within},
                "evaluated_at": now,
            }
        return {
            "verdict": "not_supported",
            "hypothesis_id": "mls_price_partition",
            "protocol": "price_1972_mls",
            "confidence": 0.88,
            "rationale": f"Between-group selection term did not exceed zero (between_term={between:.4f} <= 0).",
            "controls_passed": True,
            "evidence_summary": {"between_term": between, "within_term": within},
            "evaluated_at": now,
        }

    if challenge == "FUNCTIONAL_INFO":
        raw_fi = summary.get("hazen_functional_info_bits", summary.get("functional_info_bits", 0.0))
        raw_perc = summary.get("neutral_percolation_rate", 0.0)
        if (
            isinstance(raw_fi, bool)
            or isinstance(raw_perc, bool)
            or not _is_finite(raw_fi)
            or not _is_finite(raw_perc)
        ):
            return {
                "verdict": "invalid",
                "hypothesis_id": "hazen_functional_info_accretion",
                "protocol": "hazen_2007_functional_information",
                "confidence": 0.0,
                "rationale": f"Non-finite functional information metric detected (fi_bits={raw_fi}, percolation={raw_perc}).",
                "controls_passed": False,
                "evidence_summary": {"fi_bits": raw_fi, "percolation": raw_perc},
                "evaluated_at": now,
            }
        fi_bits = float(raw_fi)
        percolation = float(raw_perc)
        if percolation < 0.0 or percolation > 1.0:
            return {
                "verdict": "invalid",
                "hypothesis_id": "hazen_functional_info_accretion",
                "protocol": "hazen_2007_functional_information",
                "confidence": 0.0,
                "rationale": f"Invalid neutral percolation rate ({percolation}), must be bounded in [0.0, 1.0].",
                "controls_passed": False,
                "evidence_summary": {"fi_bits": fi_bits, "percolation": percolation},
                "evaluated_at": now,
            }
        if not complete or status != "COMPLETED":
            return {
                "verdict": "inconclusive",
                "hypothesis_id": "hazen_functional_info_accretion",
                "protocol": "hazen_2007_functional_information",
                "confidence": 0.5,
                "rationale": f"Functional information assessment requires completed run (status='{status}', complete={complete}).",
                "controls_passed": False,
                "evidence_summary": {"fi_bits": fi_bits, "percolation": percolation},
                "evaluated_at": now,
            }
        if fi_bits > 0.0 and percolation > 0.0:
            return {
                "verdict": "supported",
                "hypothesis_id": "hazen_functional_info_accretion",
                "protocol": "hazen_2007_functional_information",
                "confidence": 0.95,
                "rationale": f"Functional information accretion ({fi_bits:.2f} bits) and neutral network percolation ({percolation*100:.1f}%) observed.",
                "controls_passed": True,
                "evidence_summary": {"fi_bits": fi_bits, "percolation": percolation},
                "evaluated_at": now,
            }
        return {
            "verdict": "not_supported",
            "hypothesis_id": "hazen_functional_info_accretion",
            "protocol": "hazen_2007_functional_information",
            "confidence": 0.70,
            "rationale": "Functional information threshold not exceeded in sampled sequence space.",
            "controls_passed": True,
            "evidence_summary": {"fi_bits": fi_bits, "percolation": percolation},
            "evaluated_at": now,
        }

    # Red Queen reciprocal time-shift evaluations
    diagnostics = run_data.get("diagnostics")
    if diagnostics and isinstance(diagnostics, dict):
        diag_complete = execution.get("diagnostics_complete", False)
        if not diag_complete:
            return {
                "verdict": "inconclusive",
                "hypothesis_id": "red_queen_time_shift",
                "protocol": "papkou_timeshift_v2",
                "confidence": 0.5,
                "rationale": "Time-shift diagnostics incomplete or sample size too small for confirmatory inference.",
                "controls_passed": True,
                "evidence_summary": {"diagnostics_complete": False},
                "evaluated_at": now,
            }

        # Check empirical outcomes from diagnostics
        by_seed = diagnostics.get("by_seed") or []
        if isinstance(by_seed, list) and len(by_seed) >= 2:
            # Check if any seed exhibits confirmed reciprocal adaptation
            positive_signals = 0
            negative_signals = 0
            for s_entry in by_seed:
                if not isinstance(s_entry, dict):
                    continue
                matrices = s_entry.get("matrices") or []
                for m in matrices:
                    if not isinstance(m, dict):
                        continue
                    if m.get("blocked_reason"):
                        continue
                    stat = m.get("mean_contrast") or m.get("slope")
                    if isinstance(stat, (int, float)):
                        if stat > 0.05:
                            positive_signals += 1
                        elif stat < -0.05:
                            negative_signals += 1

            total_signals = positive_signals + negative_signals
            if total_signals == 0:
                return {
                    "verdict": "inconclusive",
                    "hypothesis_id": "red_queen_time_shift",
                    "protocol": "papkou_timeshift_v2",
                    "confidence": 0.6,
                    "rationale": "Time-shift matrices show neutral variance without directional or cyclical bias.",
                    "controls_passed": True,
                    "evidence_summary": {"seeds": len(by_seed), "positive_signals": positive_signals},
                    "evaluated_at": now,
                }
            if positive_signals > negative_signals and (positive_signals / total_signals) >= 0.70:
                return {
                    "verdict": "supported",
                    "hypothesis_id": "red_queen_time_shift",
                    "protocol": "papkou_timeshift_v2",
                    "confidence": 0.90,
                    "rationale": "Empirical reciprocal time-shift confirms antagonistic coevolutionary lag and adaptation.",
                    "controls_passed": True,
                    "evidence_summary": {"seeds": len(by_seed), "positive_signals": positive_signals, "negative_signals": negative_signals},
                    "evaluated_at": now,
                }
            return {
                "verdict": "not_supported",
                "hypothesis_id": "red_queen_time_shift",
                "protocol": "papkou_timeshift_v2",
                "confidence": 0.85,
                "rationale": "Reciprocal time-shift does not show significant coevolutionary lag or parasite advantage.",
                "controls_passed": True,
                "evidence_summary": {"seeds": len(by_seed), "positive_signals": positive_signals, "negative_signals": negative_signals},
                "evaluated_at": now,
            }

    # Fallback: check if execution outcome has a generic exploratory flag
    if execution.get("exploratory"):
        return {
            "verdict": "not_evaluated",
            "hypothesis_id": "exploratory_run",
            "protocol": "exploratory_sampling",
            "confidence": None,
            "rationale": "Exploratory simulation run completed without a registered hypothesis protocol.",
            "controls_passed": True,
            "evidence_summary": {"complete": complete},
            "evaluated_at": now,
        }

    return {
        "verdict": "not_evaluated",
        "hypothesis_id": "unspecified",
        "protocol": "general",
        "confidence": None,
        "rationale": "Simulation run completed; no active hypothesis evaluation rule triggered.",
        "controls_passed": True,
        "evidence_summary": {"complete": complete},
        "evaluated_at": now,
    }
