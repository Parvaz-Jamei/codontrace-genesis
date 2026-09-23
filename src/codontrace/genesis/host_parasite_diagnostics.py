"""Infectivity / resistance range diagnostics for host–parasite campaigns.

Maps time-series range summaries onto ARD-like / FSD-like / mixed *labels*
(Hall et al. 2011; Lopez Pascua et al. 2014 analogies). These are digital
diagnostic enums only: ``red_queen_proved`` is always False. No clinical,
CRISPR-identity, phage-therapy, vaccine, epidemic, or BSL claim is granted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, canonical_payload

_DIAGNOSTIC_LABELS = frozenset(
    {"undeclared", "ard_like", "fsd_like", "mixed_like"}
)


@dataclass(frozen=True, slots=True)
class RangeObservation:
    """One time-point infectivity / resistance range summary."""

    time_index: int
    infectivity_range: float
    resistance_range: float

    def to_dict(self) -> dict[str, object]:
        return {
            "time_index": self.time_index,
            "infectivity_range": self.infectivity_range,
            "resistance_range": self.resistance_range,
        }


@dataclass(frozen=True, slots=True)
class CoevolutionDiagnostics:
    """ARD/FSD-like diagnostic label with Red Queen always unproved."""

    label: str
    red_queen_proved: bool
    infectivity_trend: float
    resistance_trend: float
    infectivity_fluctuation: float
    resistance_fluctuation: float
    note: str
    observations: tuple[RangeObservation, ...]

    def to_dict(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": "host_parasite_coevolution_diagnostics_v1",
            "label": self.label,
            "red_queen_proved": self.red_queen_proved,
            "infectivity_trend": self.infectivity_trend,
            "resistance_trend": self.resistance_trend,
            "infectivity_fluctuation": self.infectivity_fluctuation,
            "resistance_fluctuation": self.resistance_fluctuation,
            "note": self.note,
            "observations": [item.to_dict() for item in self.observations],
            "raises_claim_ladder": False,
        }
        body["digest"] = canonical_digest(
            canonical_payload({k: body[k] for k in body if k != "digest"})
        )
        return body


def _finite_nonneg(name: str, value: float) -> float:
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ConfigurationError(f"{name} must be finite.")
    if number < 0.0:
        raise ConfigurationError(f"{name} must be >= 0.")
    return number


def _trend(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return round(values[-1] - values[0], 10)


def _fluctuation(values: Sequence[float]) -> float:
    """Residual fluctuation after removing the end-start linear trend.

    Raw stdev on a monotonic escalation series is large even without oscillation.
    Detrended residuals distinguish FSD-like wobble from ARD-like climb.
    """

    if len(values) < 2:
        return 0.0
    n = len(values)
    start = values[0]
    end = values[-1]
    residuals: list[float] = []
    for index, value in enumerate(values):
        expected = start + (end - start) * (index / (n - 1))
        residuals.append(value - expected)
    mean = sum(residuals) / n
    var = sum((item - mean) ** 2 for item in residuals) / (n - 1)
    return float(round(var**0.5, 10))


def diagnose_coevolution_ranges(
    observations: Sequence[Mapping[str, object] | RangeObservation],
    *,
    escalation_threshold: float = 0.05,
    fluctuation_threshold: float = 0.05,
) -> CoevolutionDiagnostics:
    """Classify ARD-like / FSD-like / mixed diagnostics from range trajectories.

    ARD-like: infectivity and resistance ranges escalate (positive end-start
    trend above threshold). FSD-like: ranges fluctuate (stdev above threshold)
    without strong net escalation. Mixed: both signals. Always
    ``red_queen_proved=False``.
    """

    if not observations:
        raise ConfigurationError("diagnose_coevolution_ranges needs observations.")
    rows_list: list[RangeObservation] = []
    for index, raw in enumerate(observations):
        if isinstance(raw, RangeObservation):
            rows_list.append(raw)
            continue
        if not isinstance(raw, dict) and not hasattr(raw, "get"):
            raise ConfigurationError(f"observations[{index}] must be a mapping.")
        mapping = dict(raw)
        t = mapping.get("time_index", index)
        if isinstance(t, bool) or not isinstance(t, int):
            raise ConfigurationError(f"observations[{index}].time_index must be an int.")
        inf = _finite_nonneg(
            f"observations[{index}].infectivity_range",
            float(mapping["infectivity_range"]),
        )
        res = _finite_nonneg(
            f"observations[{index}].resistance_range",
            float(mapping["resistance_range"]),
        )
        rows_list.append(RangeObservation(t, inf, res))
    rows = tuple(sorted(rows_list, key=lambda item: item.time_index))
    inf_vals = [item.infectivity_range for item in rows]
    res_vals = [item.resistance_range for item in rows]
    inf_trend = _trend(inf_vals)
    res_trend = _trend(res_vals)
    inf_fluc = _fluctuation(inf_vals)
    res_fluc = _fluctuation(res_vals)
    esc = float(escalation_threshold)
    fluc = float(fluctuation_threshold)
    if esc < 0.0 or fluc < 0.0:
        raise ConfigurationError("thresholds must be >= 0.")
    escalating = inf_trend >= esc and res_trend >= esc
    fluctuating = inf_fluc >= fluc or res_fluc >= fluc
    if escalating and fluctuating:
        label = "mixed_like"
        note = (
            "Range escalation and fluctuation both present; mixed diagnostic only. "
            "Red Queen dynamics are not proved."
        )
    elif escalating:
        label = "ard_like"
        note = (
            "Infectivity and resistance ranges escalate (ARD-like digital label). "
            "Red Queen dynamics are not proved."
        )
    elif fluctuating:
        label = "fsd_like"
        note = (
            "Infectivity/resistance ranges fluctuate without strong net escalation "
            "(FSD-like digital label). Red Queen dynamics are not proved."
        )
    else:
        label = "undeclared"
        note = "Insufficient range signal for ARD/FSD-like diagnostics."
    return CoevolutionDiagnostics(
        label=label,
        red_queen_proved=False,
        infectivity_trend=inf_trend,
        resistance_trend=res_trend,
        infectivity_fluctuation=inf_fluc,
        resistance_fluctuation=res_fluc,
        note=note,
        observations=rows,
    )


__all__ = [
    "CoevolutionDiagnostics",
    "RangeObservation",
    "diagnose_coevolution_ranges",
]
