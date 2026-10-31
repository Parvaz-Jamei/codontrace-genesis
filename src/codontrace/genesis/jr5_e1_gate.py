"""JR5 phase 3: the E1 cost-of-sex equivalence gate.

Input is one fitted log per-generation odds ratio (log w) per population,
from the preregistered bias-reduced binomial fit, plus the generation at
which a population fixed, if it did. The gate does no fitting and draws no
random numbers.

Per sex-ratio cell at the gated host N:
- populations that fixed before ``early_fixation_generation`` are excluded
  and counted; more than ``exclusion_cap_fraction`` of the cell excluded is
  an instrument failure of the cell;
- the remaining log w values go into a one-sample TOST against the log of the
  preregistered ratio bounds (1 -/+ relative margin around 1 / (1 - m));
- the two-sided t interval at ``must_exclude_ci_level`` must exclude log 1.

The gate passes only when every gated cell passes. The result is a plain
record of booleans and numbers; mapping it to a typed outcome or a claim is
the job of the verdict adapter, not of this module.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.statistical_protocol import (
    OneSampleTOSTResult,
    one_sample_t_interval,
    one_sample_tost,
)

__all__ = [
    "E1CellResult",
    "E1GateResult",
    "E1GateSpec",
    "E1Population",
    "evaluate_e1_cell",
    "evaluate_e1_gate",
]

GATE_RECORD_SCHEMA = "jr5_e1_gate_v1"


def _num_item(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError("gate_e1 values must be numbers.")
    return float(value)


def _num(block: Mapping[str, object], key: str) -> float:
    return _num_item(block.get(key))


def _int(block: Mapping[str, object], key: str) -> int:
    value = block.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"gate_e1.{key} must be an integer.")
    return value


def _list(block: Mapping[str, object], key: str) -> Sequence[object]:
    value = block.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise ConfigurationError(f"gate_e1.{key} must be a list.")
    return value


@dataclass(frozen=True, slots=True)
class E1GateSpec:
    """Preregistered gate settings. Build it from the prereg constants."""

    alpha: float
    relative_margin: float
    sex_ratios: tuple[float, ...]
    must_exclude: float
    must_exclude_ci_level: float
    early_fixation_generation: int
    exclusion_cap_fraction: float
    host_n_gate: int

    def __post_init__(self) -> None:
        if not 0.0 < self.alpha < 0.5:
            raise ConfigurationError("alpha must lie in (0, 0.5).")
        if not 0.0 < self.relative_margin < 1.0:
            raise ConfigurationError("relative_margin must lie in (0, 1).")
        if not self.sex_ratios or any(not 0.0 < m < 1.0 for m in self.sex_ratios):
            raise ConfigurationError("sex ratios must lie in (0, 1).")
        if self.must_exclude <= 0.0:
            raise ConfigurationError("must_exclude is a ratio and must be positive.")
        if not 0.0 < self.must_exclude_ci_level < 1.0:
            raise ConfigurationError("must_exclude_ci_level must lie in (0, 1).")
        if self.early_fixation_generation < 0 or not 0.0 <= self.exclusion_cap_fraction < 1.0:
            raise ConfigurationError("bad exclusion settings.")
        if self.host_n_gate < 1:
            raise ConfigurationError("host_n_gate must be positive.")

    @classmethod
    def from_prereg_constants(cls, constants: Mapping[str, object]) -> E1GateSpec:
        """Read the ``gate_e1`` block of ``jr5_prereg_constants.json``."""

        block = constants.get("gate_e1", constants)
        if not isinstance(block, Mapping):
            raise ConfigurationError("gate_e1 must be a mapping.")
        if block.get("test") != "tost_equivalence":
            raise ConfigurationError("gate_e1.test must be tost_equivalence.")
        if abs(_num(block, "ci_level") - (1.0 - 2.0 * _num(block, "alpha"))) > 1e-12:
            raise ConfigurationError("gate_e1.ci_level must equal 1 - 2 alpha.")
        spec = cls(
            alpha=_num(block, "alpha"),
            relative_margin=_num(block, "relative_margin"),
            sex_ratios=tuple(_num_item(m) for m in _list(block, "sex_ratios")),
            must_exclude=_num(block, "must_exclude"),
            must_exclude_ci_level=_num(block, "must_exclude_ci_level"),
            early_fixation_generation=_int(block, "early_fixation_generation"),
            exclusion_cap_fraction=_num(block, "exclusion_cap_fraction"),
            host_n_gate=_int(block, "host_n_gate"),
        )
        bounds = block.get("equivalence_bounds")
        if isinstance(bounds, Mapping):
            for m in spec.sex_ratios:
                stated = bounds.get(str(m))
                if stated is None:
                    continue
                derived = spec.ratio_bounds(m)
                if not isinstance(stated, Sequence) or any(
                    abs(_num_item(s) - d) > 1e-9 for s, d in zip(stated, derived, strict=True)
                ):
                    raise ConfigurationError(f"stated bounds for m={m} disagree with the margin rule.")
        return spec

    @staticmethod
    def theoretical_cost(sex_ratio: float) -> float:
        """Per-generation advantage of an all-female asexual line: 1 / (1 - m)."""

        return 1.0 / (1.0 - sex_ratio)

    def ratio_bounds(self, sex_ratio: float) -> tuple[float, float]:
        centre = self.theoretical_cost(sex_ratio)
        return (centre * (1.0 - self.relative_margin), centre * (1.0 + self.relative_margin))

    def log_bounds(self, sex_ratio: float) -> tuple[float, float]:
        low, high = self.ratio_bounds(sex_ratio)
        return (math.log(low), math.log(high))


@dataclass(frozen=True, slots=True)
class E1Population:
    """One population (one seed) of an E1 cell."""

    seed: int
    log_w: float
    fixed_generation: int | None = None
    lost_generation: int | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.log_w):
            raise ConfigurationError("log_w must be finite.")
        for name in ("fixed_generation", "lost_generation"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ConfigurationError(f"{name} must be non-negative.")
        if self.fixed_generation is not None and self.lost_generation is not None:
            raise ConfigurationError("a population cannot both fix and be lost.")


@dataclass(frozen=True, slots=True)
class E1CellResult:
    sex_ratio: float
    host_n: int
    gated: bool
    n_total: int
    excluded_seeds: tuple[int, ...]
    fixed_seeds: tuple[int, ...]
    lost_seeds: tuple[int, ...]
    exclusion_cap_exceeded: bool
    log_bounds: tuple[float, float]
    ratio_bounds: tuple[float, float]
    tost: OneSampleTOSTResult | None
    exclusion_interval: tuple[float, float] | None
    log_must_exclude: float

    @property
    def equivalent(self) -> bool:
        return self.tost is not None and self.tost.equivalent

    @property
    def excludes_null(self) -> bool:
        if self.exclusion_interval is None:
            return False
        low, high = self.exclusion_interval
        return low > self.log_must_exclude or high < self.log_must_exclude

    @property
    def passed(self) -> bool:
        return (not self.exclusion_cap_exceeded) and self.equivalent and self.excludes_null

    def to_record(self) -> dict[str, JsonValue]:
        record: dict[str, JsonValue] = {
            "sex_ratio": self.sex_ratio,
            "host_n": self.host_n,
            "gated": self.gated,
            "n_total": self.n_total,
            "n_used": self.n_total - len(self.excluded_seeds),
            "excluded_seeds": list(self.excluded_seeds),
            "fixed_seeds": list(self.fixed_seeds),
            "lost_seeds": list(self.lost_seeds),
            "exclusion_cap_exceeded": self.exclusion_cap_exceeded,
            "log_bounds": list(self.log_bounds),
            "ratio_bounds": list(self.ratio_bounds),
            "tost": None if self.tost is None else self.tost.to_record(),
            "ratio_ci": None
            if self.tost is None
            else [math.exp(self.tost.ci_low), math.exp(self.tost.ci_high)],
            "exclusion_interval_log": None if self.exclusion_interval is None else list(self.exclusion_interval),
            "equivalent": self.equivalent,
            "excludes_null": self.excludes_null,
            "passed": self.passed,
        }
        return record


def evaluate_e1_cell(
    spec: E1GateSpec,
    sex_ratio: float,
    host_n: int,
    populations: Sequence[E1Population],
) -> E1CellResult:
    """Apply the exclusion rule, the TOST and the null-exclusion check to one cell.

    A cell at a host N other than ``spec.host_n_gate`` is evaluated the same
    way and marked ``gated=False`` (report only).
    """

    if sex_ratio not in spec.sex_ratios:
        raise ConfigurationError(f"sex ratio {sex_ratio} is not preregistered.")
    pops = tuple(populations)
    seeds = [p.seed for p in pops]
    if len(set(seeds)) != len(seeds):
        raise ConfigurationError("each population must have its own seed.")
    excluded = tuple(
        p.seed for p in pops if p.fixed_generation is not None and p.fixed_generation < spec.early_fixation_generation
    )
    cap_exceeded = len(excluded) > spec.exclusion_cap_fraction * len(pops)
    used = [p.log_w for p in pops if p.seed not in excluded]
    log_bounds = spec.log_bounds(sex_ratio)
    tost = None
    interval = None
    if len(used) >= 2:
        tost = one_sample_tost(used, log_bounds[0], log_bounds[1], alpha=spec.alpha)
        interval = one_sample_t_interval(used, spec.must_exclude_ci_level)
    return E1CellResult(
        sex_ratio=sex_ratio,
        host_n=int(host_n),
        gated=int(host_n) == spec.host_n_gate,
        n_total=len(pops),
        excluded_seeds=excluded,
        fixed_seeds=tuple(p.seed for p in pops if p.fixed_generation is not None),
        lost_seeds=tuple(p.seed for p in pops if p.lost_generation is not None),
        exclusion_cap_exceeded=cap_exceeded,
        log_bounds=log_bounds,
        ratio_bounds=spec.ratio_bounds(sex_ratio),
        tost=tost,
        exclusion_interval=interval,
        log_must_exclude=math.log(spec.must_exclude),
    )


@dataclass(frozen=True, slots=True)
class E1GateResult:
    cells: tuple[E1CellResult, ...]

    @property
    def passed(self) -> bool:
        gated = [c for c in self.cells if c.gated]
        return bool(gated) and all(c.passed for c in gated)

    def to_record(self) -> dict[str, JsonValue]:
        body: dict[str, JsonValue] = {
            "schema": GATE_RECORD_SCHEMA,
            "cells": [c.to_record() for c in self.cells],
            "passed": self.passed,
        }
        body["digest"] = canonical_digest(body)
        return body


def evaluate_e1_gate(
    spec: E1GateSpec,
    cells: Mapping[tuple[float, int], Sequence[E1Population]],
) -> E1GateResult:
    """Evaluate every cell keyed by (sex ratio, host N).

    Every preregistered sex ratio must be present at the gated host N.
    Cells at other host N are evaluated and reported but do not gate.
    """

    missing = [m for m in spec.sex_ratios if (m, spec.host_n_gate) not in cells]
    if missing:
        raise ConfigurationError(f"gated cells missing for sex ratios {missing}.")
    ordered = sorted(cells, key=lambda key: (key[1] != spec.host_n_gate, -key[0], -key[1]))
    return E1GateResult(cells=tuple(evaluate_e1_cell(spec, m, n, cells[(m, n)]) for m, n in ordered))
