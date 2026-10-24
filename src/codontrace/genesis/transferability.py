"""Sim-to-real transferability records (STR disparity and the stop rule).

Moved verbatim from the ClaimGate device adapter module; that module and
``claimgate.adapters`` re-export these names. Domain-free: the record compares
two named metric maps, it does not talk to a device.

The record follows the transferability approach to the reality gap in
evolutionary robotics. Digests identify the comparison record; they do not grant a physical
campaign claim.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError

__all__ = ["STRDisparityResult", "compute_str_disparity", "str_stop_criterion_met"]


@dataclass(frozen=True, slots=True)
class STRDisparityResult:
    """Honest sim-vs-physical disparity (transferability approach).

    ``disparity`` is mean absolute relative error across paired metrics.
    Digests identify the comparison record; they do **not** grant a hardware
    campaign claim. Stop criterion (goal §11): after 20 real tests, if STR is
    not better than the no-transfer baseline, stop / redesign.
    """

    metric_names: tuple[str, ...]
    sim_values: tuple[float, ...]
    physical_values: tuple[float, ...]
    per_metric_abs_rel_error: tuple[float, ...]
    mean_abs_rel_error: float
    n_pairs: int
    transfer_method: str
    notes: tuple[str, ...] = ()
    record_digest: str = ""

    def __post_init__(self) -> None:
        payload = self._payload()
        computed = _digest(payload)
        if self.record_digest and self.record_digest != computed:
            raise ConfigurationError("STRDisparityResult record_digest mismatch.")
        object.__setattr__(self, "record_digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "metric_names": list(self.metric_names),
            "sim_values": list(self.sim_values),
            "physical_values": list(self.physical_values),
            "per_metric_abs_rel_error": list(self.per_metric_abs_rel_error),
            "mean_abs_rel_error": self.mean_abs_rel_error,
            "n_pairs": self.n_pairs,
            "transfer_method": self.transfer_method,
            "notes": list(self.notes),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "record_digest": self.record_digest}

    def digest(self) -> str:
        return self.record_digest


def compute_str_disparity(
    sim_metrics: Mapping[str, float],
    physical_metrics: Mapping[str, float],
    *,
    transfer_method: str = "none",
    notes: Sequence[str] = (),
    epsilon: float = 1e-9,
) -> STRDisparityResult:
    """Compare sim vs reported physical metrics (synthetic or real).

    Relative error uses ``|sim - phys| / max(|sim|, |phys|, epsilon)``.
    Does not fabricate hardware results — callers supply both sides.
    """

    if isinstance(epsilon, bool) or not isinstance(epsilon, int | float) or epsilon <= 0:
        raise ConfigurationError("epsilon must be a positive finite number.")
    names = tuple(sorted(set(sim_metrics) & set(physical_metrics)))
    if not names:
        raise ConfigurationError(
            "compute_str_disparity requires at least one shared metric name."
        )
    sim_vals: list[float] = []
    phys_vals: list[float] = []
    errors: list[float] = []
    for name in names:
        sim_v = float(sim_metrics[name])
        phys_v = float(physical_metrics[name])
        if not math.isfinite(sim_v) or not math.isfinite(phys_v):
            raise ConfigurationError(f"metric {name!r} must be finite.")
        denom = max(abs(sim_v), abs(phys_v), float(epsilon))
        err = abs(sim_v - phys_v) / denom
        sim_vals.append(sim_v)
        phys_vals.append(phys_v)
        errors.append(round(err, 12))
    mean_err = round(sum(errors) / len(errors), 12)
    return STRDisparityResult(
        metric_names=names,
        sim_values=tuple(sim_vals),
        physical_values=tuple(phys_vals),
        per_metric_abs_rel_error=tuple(errors),
        mean_abs_rel_error=mean_err,
        n_pairs=len(names),
        transfer_method=str(transfer_method),
        notes=tuple(str(item) for item in notes),
    )


def str_stop_criterion_met(
    *,
    n_real_tests: int,
    disparity_with_transfer: float,
    disparity_without_transfer: float,
    real_test_budget: int = 20,
) -> bool:
    """Goal §11: after ``real_test_budget`` real tests, stop if STR not better.

    Returns True when the program should stop/redesign (honesty gate).
    """

    if n_real_tests < real_test_budget:
        return False
    if not math.isfinite(disparity_with_transfer) or not math.isfinite(
        disparity_without_transfer
    ):
        raise ConfigurationError("disparity values must be finite.")
    # "Not better" = transfer disparity is not strictly lower than baseline.
    return disparity_with_transfer >= disparity_without_transfer


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
