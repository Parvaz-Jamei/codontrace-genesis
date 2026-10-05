"""Stage-0 instrument for the 2026-09-29 discovery program.

The eight named population tests are not run here. Hand arithmetic and
pre-specified fixtures check the meter. A fixture match is not a result
about the live model, and this module never sets a discovery flag.
"""

from __future__ import annotations

from collections.abc import Mapping

from codontrace.dynvalues import same_float, same_mapping
from codontrace.genesis.campaigns.discovery_q_20260928_measurement import (
    RQ_ACCEPT_THRESHOLD,
    RQ_SYNTHETIC_SCORE,
    rq_barrier_holds,
    rq_model_decision,
    rq_preregistered_direction_reaches_threshold,
)
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.measurements.rq_frequency_clocks import (
    frequency_swap_signal,
    realised_conditional_host_pressure,
    reference_graded_affinity,
)

PROGRAM_ID = "GENESIS-DISCOVERY-PROGRAM-20260929"
STAGE_ID = "STAGE0-INSTRUMENT-V1"
STAGE_DATE = "2026-09-29"
KAPPA = 1.2
CLAIM_CEILING = "phase2_design"
TIMES: tuple[str, ...] = ("past", "now", "future")
SUPPORT_PATTERNS = frozenset({"contemporary_match", "lagged_match"})
DECISION_CODES = (
    "SUPPORTED_IN_MODEL",
    "FALSIFIED_IN_MODEL",
    "INCONCLUSIVE",
    "BLOCKED_MEASUREMENT",
)

# Named tests in the program. None of them is a population run at this stage.
PROGRAM_TESTS: tuple[str, ...] = (
    "RQ-1",
    "RQ-2",
    "RQ-3",
    "RQ-4",
    "D-1",
    "D-2",
    "D-3",
    "D-4",
)
STAGE0_PILOTS: tuple[str, ...] = ("RQ-1", "RQ-3", "D-2")


def _r(value: float) -> float:
    """Ten decimal places, the pressure-report convention. Not a new threshold."""

    return round(float(value), 10)


def _debit(affinity: float, available: float | None = None) -> float:
    raw = float(KAPPA) * float(affinity)
    if available is None:
        return raw
    return min(raw, float(available))


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("pressure mean needs at least one contact")
    return float(sum(values) / len(values))


def example_histogram_blind() -> dict[str, float]:
    """Corrected MEASUREMENT_VALIDATION example 1. The rule is 3×2 agreement.

    ``111100`` against ``000011`` has affinity 0, not 1/6. The difference is
    0.800 ATP per opportunity. The withdrawn figure 0.700 is not used.
    """

    pi_a = _mean(
        [
            _debit(reference_graded_affinity("000000", "000001")),
            _debit(reference_graded_affinity("000000", "000011")),
        ]
    )
    pi_b = _mean(
        [
            _debit(reference_graded_affinity("111100", "000001")),
            _debit(reference_graded_affinity("111100", "000011")),
        ]
    )
    return {
        "pi_a": _r(pi_a),
        "pi_b": _r(pi_b),
        "difference": _r(pi_a - pi_b),
        "histogram_difference": 0.0,
        "affinity_b_against_000011": _r(
            reference_graded_affinity("111100", "000011")
        ),
    }


def example_flat_affinity() -> dict[str, float]:
    """Example 2. Affinity is set to 0.5. A histogram shift does not move pressure."""

    pi = _mean([_debit(0.5), _debit(0.5)])
    return {"pi": _r(pi), "difference": 0.0, "histogram_shift": 0.25}


def example_truncation() -> dict[str, float]:
    """Example 2b. Intended attack is symmetric. Realised damage is not."""

    intended = _debit(0.5)
    paid_a = min(intended, 10.0)
    paid_b = min(intended, 0.5)
    return {
        "intended": _r(intended),
        "pi_realised_a": _r(paid_a),
        "pi_realised_b": _r(paid_b),
        "intended_difference": 0.0,
        "realised_difference": _r(paid_a - paid_b),
        "paid_does_not_exceed_available_b": float(paid_b <= 0.5),
    }


def classify_time_shift_matrix(matrix: Mapping[str, Mapping[str, float]]) -> str:
    """Label a 3×3 pressure matrix. This is not a population result."""

    values = [float(matrix[host][ant]) for host in TIMES for ant in TIMES]
    if max(values) - min(values) <= 1e-9:
        return "flat"
    directional = all(
        float(matrix[host]["past"])
        < float(matrix[host]["now"])
        < float(matrix[host]["future"])
        for host in TIMES
    )
    if directional:
        return "directional_increase"
    contemporary = all(
        float(matrix[ant][ant]) > float(matrix[host][ant])
        for ant in TIMES
        for host in TIMES
        if host != ant
    )
    if contemporary:
        return "contemporary_match"
    lagged = (
        float(matrix["now"]["past"]) > float(matrix["past"]["past"])
        and float(matrix["now"]["past"]) > float(matrix["future"]["past"])
        and float(matrix["future"]["now"]) > float(matrix["past"]["now"])
        and float(matrix["future"]["now"]) > float(matrix["now"]["now"])
        and float(matrix["future"]["future"]) > float(matrix["past"]["future"])
        and float(matrix["future"]["future"]) > float(matrix["now"]["future"])
    )
    if lagged:
        return "lagged_match"
    return "other"


def rotate_antagonist_labels(
    matrix: Mapping[str, Mapping[str, float]],
) -> dict[str, dict[str, float]]:
    """One deterministic time-label rotation. Not a draw."""

    source = {"past": "future", "now": "past", "future": "now"}
    return {
        host: {ant: float(matrix[host][source[ant]]) for ant in TIMES}
        for host in TIMES
    }


def rq1_hand_instrument() -> dict[str, object]:
    """Pre-specified matrices. The live model does not produce them."""

    coevolve = {
        "past": {"past": 0.70, "now": 0.20, "future": 0.15},
        "now": {"past": 0.25, "now": 0.80, "future": 0.30},
        "future": {"past": 0.20, "now": 0.35, "future": 0.60},
    }
    lagged = {
        "past": {"past": 0.20, "now": 0.30, "future": 0.15},
        "now": {"past": 0.70, "now": 0.25, "future": 0.20},
        "future": {"past": 0.30, "now": 0.75, "future": 0.55},
    }
    directional = {
        "past": {"past": 0.20, "now": 0.40, "future": 0.60},
        "now": {"past": 0.30, "now": 0.50, "future": 0.70},
        "future": {"past": 0.40, "now": 0.60, "future": 0.90},
    }
    frozen = {host: {ant: 0.40 for ant in TIMES} for host in TIMES}
    co_label = classify_time_shift_matrix(coevolve)
    lag_label = classify_time_shift_matrix(lagged)
    shuffled = classify_time_shift_matrix(rotate_antagonist_labels(coevolve))
    frozen_label = classify_time_shift_matrix(frozen)
    directional_label = classify_time_shift_matrix(directional)
    instrument_ok = (
        co_label == "contemporary_match"
        and lag_label == "lagged_match"
        and frozen_label not in SUPPORT_PATTERNS
        and shuffled not in SUPPORT_PATTERNS
        and directional_label == "directional_increase"
    )
    return {
        "instrument_positive_case": bool(instrument_ok),
        "coevolve_label": co_label,
        "lagged_label": lag_label,
        "frozen_label": frozen_label,
        "shuffled_label": shuffled,
        "directional_label": directional_label,
        "decision": "BLOCKED_MEASUREMENT",
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "population_run": False,
    }


def rq3_hand_channel() -> dict[str, object]:
    """Hand contact matrices for the delayed channel. Frozen pairing gives S = 0.

    This is the same arithmetic as the measurement kernel's hand check.
    It is not a run of the live census.
    """

    host = {"A": "000000"}
    antagonist = {"P_A": "000000", "P_B": "111111"}
    adapted = {"A": {"P_A": 3.0, "P_B": 1.0}}
    swapped = {"A": {"P_A": 1.0, "P_B": 3.0}}
    common = realised_conditional_host_pressure(
        host, antagonist, contact_matrix=adapted
    )
    rare = realised_conditional_host_pressure(
        host, antagonist, contact_matrix=swapped
    )
    signal = frequency_swap_signal(
        {0: float(rare["pressure"]["A"])},  # type: ignore[index]
        {0: float(common["pressure"]["A"])},  # type: ignore[index]
        window=[0],
    )
    frozen_signal = frequency_swap_signal(
        {0: float(common["pressure"]["A"])},  # type: ignore[index]
        {0: float(common["pressure"]["A"])},  # type: ignore[index]
        window=[0],
    )
    score = _r(same_float(signal["s"]))
    frozen = _r(same_float(frozen_signal["s"]))
    return {
        "pi_common": _r(float(common["pressure"]["A"])),  # type: ignore[index]
        "pi_rare": _r(float(rare["pressure"]["A"])),  # type: ignore[index]
        "s": score,
        "frozen_s": frozen,
        "preregistered_direction": bool(
            rq_preregistered_direction_reaches_threshold(score)
        ),
        "frozen_reaches_floor": bool(
            rq_preregistered_direction_reaches_threshold(frozen)
        ),
        "instrument_positive_case": bool(
            abs(score - (-0.6)) < 1e-9 and abs(frozen) < 1e-12
        ),
        "decision": "BLOCKED_MEASUREMENT",
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "population_run": False,
    }


def live_program_decisions(
    idea2: Mapping[str, object],
    idea4: Mapping[str, object],
) -> dict[str, object]:
    """Label the live model. Stage 0 cannot return ``SUPPORTED_IN_MODEL``."""

    has_population = idea2.get("parasite_is_genotype_population") is True
    contact_ready = (
        idea4.get("checkpoint_fork_complete") is True
        and idea4.get("parent_child_ids_recorded") is True
        and idea4.get("topology_effect_identified") is True
        and idea4.get("endpoint_map_is_contact_physics") is True
    )
    # A real roster removes the instrument block. It does not confirm the
    # hypothesis. A missing roster stays blocked. Stage 0 never supports.
    blocked_antagonist = "INCONCLUSIVE" if has_population else "BLOCKED_MEASUREMENT"
    blocked_contact = "BLOCKED_MEASUREMENT" if not contact_ready else "INCONCLUSIVE"
    decisions = {
        "RQ-1": blocked_antagonist,
        "RQ-2": blocked_antagonist,
        "RQ-3": blocked_antagonist,
        "RQ-4": blocked_antagonist,
        "D-1": blocked_antagonist,
        "D-2": blocked_contact,
        "D-3": "BLOCKED_MEASUREMENT",
        "D-4": "BLOCKED_MEASUREMENT",
    }
    if any(code == "SUPPORTED_IN_MODEL" for code in decisions.values()):
        raise RuntimeError("stage 0 must not support a model claim")
    model = rq_model_decision(RQ_SYNTHETIC_SCORE)
    return {
        "program_id": PROGRAM_ID,
        "stage_id": STAGE_ID,
        "stage_date": STAGE_DATE,
        "claim_ceiling": CLAIM_CEILING,
        "n_program_tests": len(PROGRAM_TESTS),
        "pilots_named": list(STAGE0_PILOTS),
        "population_runs": 0,
        "decisions": decisions,
        "hypothesis_supported": False,
        "red_queen_proved": False,
        "synthetic_score": RQ_SYNTHETIC_SCORE,
        "synthetic_barrier_holds": bool(rq_barrier_holds(RQ_SYNTHETIC_SCORE)),
        "accept_threshold": RQ_ACCEPT_THRESHOLD,
        "model_claim_inputs_sufficient": bool(model["claim_inputs_sufficient"]),
        "confirmatory_run": False,
    }


def stage0_report(
    idea2: Mapping[str, object],
    idea4: Mapping[str, object],
) -> dict[str, object]:
    """One stage-0 pack. Replay is the digest of the hand section only."""

    hand = {
        "histogram_blind": example_histogram_blind(),
        "flat_affinity": example_flat_affinity(),
        "truncation": example_truncation(),
        "rq1": {
            "coevolve_label": rq1_hand_instrument()["coevolve_label"],
            "lagged_label": rq1_hand_instrument()["lagged_label"],
            "shuffled_label": rq1_hand_instrument()["shuffled_label"],
            "frozen_label": rq1_hand_instrument()["frozen_label"],
        },
        "rq3": {
            "s": rq3_hand_channel()["s"],
            "frozen_s": rq3_hand_channel()["frozen_s"],
        },
    }
    digest = canonical_digest(hand)
    live = live_program_decisions(idea2, idea4)
    rq1 = rq1_hand_instrument()
    rq3 = rq3_hand_channel()
    return {
        **live,
        "instrument_positive_case": bool(
            rq1["instrument_positive_case"] and rq3["instrument_positive_case"]
        ),
        "hand_digest": digest,
        "hand_digest_replay": canonical_digest(hand),
        "histogram_difference": same_mapping(hand["histogram_blind"])["difference"],
        "withdrawn_difference": 0.700,
    }
