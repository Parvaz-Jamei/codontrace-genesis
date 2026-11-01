"""JR5 phase 3: the E1 cost-of-sex equivalence gate.

Input is one fitted log per-generation odds ratio (log w) per population,
from the preregistered bias-reduced binomial fit, plus the generation at
which a population fixed or was lost, if it did. The gate does no fitting and
draws no random numbers.

Settings come only from the locked prereg constants file. ``load_e1_gate_spec``
reads ``docs/prereg/jr5/jr5_prereg_constants.json`` and refuses it unless its
sha256 equals the entry in ``record.json``. That sha travels in every gate
record, so a reader can reject a record built from other settings.

Per (sex ratio, host N) cell:
- the cell must hold exactly the preregistered seed block for that ratio
  (``seed_split``, ``populations_per_cell``), at every host N;
- populations that fixed before ``early_fixation_generation`` are excluded and
  counted; more than ``exclusion_cap_fraction`` of the cell excluded breaches
  the cap;
- the remaining log w values go into a one-sample TOST against the log of the
  preregistered ratio bounds (1 -/+ relative margin around 1 / (1 - m));
- the two-sided t interval at ``must_exclude_ci_level`` must exclude log 1.

The gate passes only when every gated cell (host N = ``host_n_gate``) passes.
``instrument_failure`` is true when the gate fails or when any E1 cell, gated
or not, breaches the exclusion cap (PREREG section 2). The result is a record
of booleans and numbers; mapping it to a typed outcome or a claim is the job
of the verdict adapter.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.statistical_protocol import (
    OneSampleTOSTResult,
    one_sample_t_interval,
    one_sample_tost,
)

__all__ = [
    "CONSTANTS_RELPATH",
    "E1CellResult",
    "E1GateResult",
    "E1GateSpec",
    "E1Population",
    "evaluate_e1_cell",
    "evaluate_e1_gate",
    "load_e1_gate_spec",
]

GATE_RECORD_SCHEMA = "jr5_e1_gate_v2"
PREREG_RELDIR = "docs/prereg/jr5"
CONSTANTS_RELPATH = f"{PREREG_RELDIR}/jr5_prereg_constants.json"
_TOL = 1e-9


def _num_item(value: object, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ConfigurationError(f"{what} must be a finite number.")
    return float(value)


def _int_item(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{what} must be an integer.")
    return value


def _mapping(value: object, what: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{what} must be a mapping.")
    return value


def _pair(value: object, what: str) -> tuple[float, float]:
    if not isinstance(value, Sequence) or isinstance(value, str) or len(value) != 2:
        raise ConfigurationError(f"{what} must be a pair.")
    return (_num_item(value[0], what), _num_item(value[1], what))


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= _TOL


@dataclass(frozen=True, slots=True)
class E1GateSpec:
    """Gate settings read from the locked prereg constants. Use ``load_e1_gate_spec``."""

    alpha: float
    relative_margin: float
    sex_ratios: tuple[float, ...]
    must_exclude: float
    must_exclude_ci_level: float
    early_fixation_generation: int
    exclusion_cap_fraction: float
    host_n_gate: int
    host_n_reported: tuple[int, ...]
    populations_per_cell: int
    seed_split: tuple[tuple[float, int, int], ...]
    constants_sha256: str

    @classmethod
    def from_prereg_constants(cls, constants: Mapping[str, object], *, constants_sha256: str) -> E1GateSpec:
        """Build the spec from the full constants mapping (``gate_e1`` must be nested).

        Every derived number stated in the file is checked against the rule
        it comes from: bounds and theoretical cost per ratio, log margins and
        the 90% level. A file whose stated numbers disagree is refused.
        """

        if not isinstance(constants_sha256, str) or len(constants_sha256) != 64:
            raise ConfigurationError("constants_sha256 must be a sha256 hex digest.")
        if "gate_e1" not in constants:
            raise ConfigurationError("constants must hold a nested gate_e1 block.")
        g = _mapping(constants["gate_e1"], "gate_e1")
        if g.get("test") != "tost_equivalence":
            raise ConfigurationError("gate_e1.test must be tost_equivalence.")
        alpha = _num_item(g.get("alpha"), "gate_e1.alpha")
        if not 0.0 < alpha < 0.5:
            raise ConfigurationError("gate_e1.alpha must lie in (0, 0.5).")
        if not _close(_num_item(g.get("ci_level"), "gate_e1.ci_level"), 1.0 - 2.0 * alpha):
            raise ConfigurationError("gate_e1.ci_level must equal 1 - 2 alpha.")
        margin = _num_item(g.get("relative_margin"), "gate_e1.relative_margin")
        if not 0.0 < margin < 1.0:
            raise ConfigurationError("gate_e1.relative_margin must lie in (0, 1).")
        raw_ratios = g.get("sex_ratios")
        if not isinstance(raw_ratios, Sequence) or isinstance(raw_ratios, str) or not raw_ratios:
            raise ConfigurationError("gate_e1.sex_ratios must be a non-empty list.")
        ratios = tuple(_num_item(m, "gate_e1.sex_ratios") for m in raw_ratios)
        if any(not 0.0 < m < 1.0 for m in ratios) or len(set(ratios)) != len(ratios):
            raise ConfigurationError("gate_e1.sex_ratios must be distinct values in (0, 1).")
        log_margin = _mapping(g.get("log_margin"), "gate_e1.log_margin")
        if not (
            _close(_num_item(log_margin.get("low"), "gate_e1.log_margin.low"), math.log(1.0 - margin))
            and _close(_num_item(log_margin.get("high"), "gate_e1.log_margin.high"), math.log(1.0 + margin))
        ):
            raise ConfigurationError("gate_e1.log_margin disagrees with relative_margin.")
        bounds = _mapping(g.get("equivalence_bounds"), "gate_e1.equivalence_bounds")
        theory = _mapping(g.get("theoretical_cost"), "gate_e1.theoretical_cost")
        split = _mapping(g.get("seed_split"), "gate_e1.seed_split")
        per_cell = _int_item(g.get("populations_per_cell"), "gate_e1.populations_per_cell")
        if per_cell < 2:
            raise ConfigurationError("gate_e1.populations_per_cell must be at least 2.")
        seed_split: list[tuple[float, int, int]] = []
        for m in ratios:
            key = str(m)
            if key not in bounds or key not in theory or key not in split:
                raise ConfigurationError(f"gate_e1 must state bounds, theoretical_cost and seed_split for m={key}.")
            centre = 1.0 / (1.0 - m)
            if not _close(_num_item(theory[key], f"theoretical_cost[{key}]"), centre):
                raise ConfigurationError(f"theoretical_cost for m={key} is not 1 / (1 - m).")
            lo, hi = _pair(bounds[key], f"equivalence_bounds[{key}]")
            if not (_close(lo, centre * (1.0 - margin)) and _close(hi, centre * (1.0 + margin))):
                raise ConfigurationError(f"equivalence_bounds for m={key} disagree with the margin rule.")
            first, last = (_int_item(x, f"seed_split[{key}]") for x in _pair_raw(split[key], f"seed_split[{key}]"))
            if last - first + 1 != per_cell:
                raise ConfigurationError(f"seed_split for m={key} does not hold populations_per_cell seeds.")
            seed_split.append((m, first, last))
        reported = g.get("host_n_reported")
        if not isinstance(reported, Sequence) or isinstance(reported, str):
            raise ConfigurationError("gate_e1.host_n_reported must be a list.")
        host_n_gate = _int_item(g.get("host_n_gate"), "gate_e1.host_n_gate")
        host_ns = tuple(_int_item(n, "gate_e1.host_n_reported") for n in reported)
        if host_n_gate not in host_ns:
            raise ConfigurationError("gate_e1.host_n_gate must be one of host_n_reported.")
        ci95 = _num_item(g.get("must_exclude_ci_level"), "gate_e1.must_exclude_ci_level")
        must_exclude = _num_item(g.get("must_exclude"), "gate_e1.must_exclude")
        cap = _num_item(g.get("exclusion_cap_fraction"), "gate_e1.exclusion_cap_fraction")
        early = _int_item(g.get("early_fixation_generation"), "gate_e1.early_fixation_generation")
        if not 0.0 < ci95 < 1.0 or must_exclude <= 0.0 or not 0.0 <= cap < 1.0 or early < 0:
            raise ConfigurationError("gate_e1 has an out-of-range setting.")
        return cls(
            alpha=alpha,
            relative_margin=margin,
            sex_ratios=ratios,
            must_exclude=must_exclude,
            must_exclude_ci_level=ci95,
            early_fixation_generation=early,
            exclusion_cap_fraction=cap,
            host_n_gate=host_n_gate,
            host_n_reported=host_ns,
            populations_per_cell=per_cell,
            seed_split=tuple(seed_split),
            constants_sha256=constants_sha256,
        )

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

    def seeds_for(self, sex_ratio: float) -> range:
        for m, first, last in self.seed_split:
            if m == sex_ratio:
                return range(first, last + 1)
        raise ConfigurationError(f"sex ratio {sex_ratio} is not preregistered.")


def _pair_raw(value: object, what: str) -> tuple[object, object]:
    if not isinstance(value, Sequence) or isinstance(value, str) or len(value) != 2:
        raise ConfigurationError(f"{what} must be a pair.")
    return (value[0], value[1])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_e1_gate_spec(root: str | Path | None = None) -> E1GateSpec:
    """Load the gate spec from the locked constants file, checked against record.json."""

    base = Path(root) if root is not None else _repo_root()
    record_path = base / PREREG_RELDIR / "record.json"
    constants_path = base / CONSTANTS_RELPATH
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        raw = constants_path.read_bytes()
    except OSError as exc:
        raise ConfigurationError(f"JR5 prereg files not readable under {base}.") from exc
    files = _mapping(record.get("manifest") if isinstance(record, Mapping) else None, "record.manifest").get("files")
    pinned = None
    if isinstance(files, Sequence):
        for entry in files:
            if isinstance(entry, Sequence) and len(entry) == 2 and entry[0] == CONSTANTS_RELPATH:
                pinned = entry[1]
    if not isinstance(pinned, str):
        raise ConfigurationError("record.json does not pin the JR5 constants file.")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != pinned:
        raise ConfigurationError("JR5 constants file does not match its record.json sha256.")
    constants = json.loads(raw.decode("utf-8"))
    return E1GateSpec.from_prereg_constants(_mapping(constants, "constants"), constants_sha256=actual)


@dataclass(frozen=True, slots=True)
class E1Population:
    """One population (one seed) of an E1 cell.

    ``log_w`` may be ``None`` or non-finite only for a population that the
    early-fixation rule excludes; the cell check refuses it otherwise.
    """

    seed: int
    log_w: float | None
    fixed_generation: int | None = None
    lost_generation: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ConfigurationError("seed must be an integer.")
        for name in ("fixed_generation", "lost_generation"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ConfigurationError(f"{name} must be a non-negative integer.")
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

    def ratio_ci90(self) -> list[JsonValue] | None:
        return None if self.tost is None else [math.exp(self.tost.ci_low), math.exp(self.tost.ci_high)]

    def ratio_ci95(self) -> list[JsonValue] | None:
        return None if self.exclusion_interval is None else [math.exp(x) for x in self.exclusion_interval]

    def to_record(self) -> dict[str, JsonValue]:
        return {
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
            "ratio_ci": self.ratio_ci90(),
            "ratio_ci95": self.ratio_ci95(),
            "exclusion_interval_log": None if self.exclusion_interval is None else list(self.exclusion_interval),
            "equivalent": self.equivalent,
            "excludes_null": self.excludes_null,
            "passed": self.passed,
        }


def evaluate_e1_cell(
    spec: E1GateSpec,
    sex_ratio: float,
    host_n: int,
    populations: Sequence[E1Population],
) -> E1CellResult:
    """Check the seed block, apply the exclusion rule, the TOST and the null check.

    A cell at a host N other than ``spec.host_n_gate`` is evaluated the same
    way and marked ``gated=False`` (report only).
    """

    if host_n not in spec.host_n_reported:
        raise ConfigurationError(f"host N {host_n} is not preregistered for E1.")
    expected = spec.seeds_for(sex_ratio)
    pops = tuple(populations)
    seeds = [p.seed for p in pops]
    if len(set(seeds)) != len(seeds) or set(seeds) != set(expected) or len(pops) != spec.populations_per_cell:
        raise ConfigurationError(
            f"cell m={sex_ratio}, N={host_n} must hold exactly seeds {expected.start}-{expected.stop - 1}."
        )
    excluded = tuple(
        p.seed for p in pops if p.fixed_generation is not None and p.fixed_generation < spec.early_fixation_generation
    )
    used: list[float] = []
    for p in pops:
        if p.seed in excluded:
            continue
        if p.log_w is None or not math.isfinite(p.log_w):
            raise ConfigurationError(f"seed {p.seed} is kept in the fit but has no finite log_w.")
        used.append(p.log_w)
    cap_exceeded = len(excluded) > spec.exclusion_cap_fraction * len(pops)
    log_bounds = spec.log_bounds(sex_ratio)
    tost = None
    interval = None
    if len(used) >= 2:
        tost = one_sample_tost(used, log_bounds[0], log_bounds[1], alpha=spec.alpha)
        interval = one_sample_t_interval(used, spec.must_exclude_ci_level)
    return E1CellResult(
        sex_ratio=sex_ratio,
        host_n=host_n,
        gated=host_n == spec.host_n_gate,
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
    constants_sha256: str

    @property
    def passed(self) -> bool:
        """Every gated (host N = host_n_gate) cell passes."""

        gated = [c for c in self.cells if c.gated]
        return bool(gated) and all(c.passed for c in gated)

    @property
    def instrument_failure(self) -> bool:
        """PREREG section 2: the gate fails, or any E1 cell breaches the exclusion cap."""

        return (not self.passed) or any(c.exclusion_cap_exceeded for c in self.cells)

    def adapter_e1(self) -> list[dict[str, JsonValue]]:
        """Gated cells in the shape the verdict adapter reads (ratio scale)."""

        rows: list[dict[str, JsonValue]] = []
        for c in self.cells:
            if not c.gated:
                continue
            ci90, ci95 = c.ratio_ci90(), c.ratio_ci95()
            if ci90 is None or ci95 is None:
                raise ConfigurationError(f"cell m={c.sex_ratio} has no interval to report.")
            rows.append(
                {
                    "sex_ratio": c.sex_ratio,
                    "n_populations": c.n_total,
                    "n_excluded": len(c.excluded_seeds),
                    "ci90": list(ci90),
                    "ci95": list(ci95),
                }
            )
        return rows

    def to_record(self) -> dict[str, JsonValue]:
        body: dict[str, JsonValue] = {
            "schema": GATE_RECORD_SCHEMA,
            "constants_sha256": self.constants_sha256,
            "cells": [c.to_record() for c in self.cells],
            "passed": self.passed,
            "instrument_failure": self.instrument_failure,
        }
        body["digest"] = canonical_digest(body)
        return body


def evaluate_e1_gate(
    spec: E1GateSpec,
    cells: Mapping[tuple[float, int], Sequence[E1Population]],
) -> E1GateResult:
    """Evaluate every cell keyed by (sex ratio, host N).

    Every preregistered sex ratio must be present at the gated host N.
    Cells at other preregistered host N are evaluated and reported; they do
    not gate, but their exclusion cap counts toward ``instrument_failure``.
    """

    missing = [m for m in spec.sex_ratios if (m, spec.host_n_gate) not in cells]
    if missing:
        raise ConfigurationError(f"gated cells missing for sex ratios {missing}.")
    ordered = sorted(cells, key=lambda key: (key[1] != spec.host_n_gate, -key[0], -key[1]))
    return E1GateResult(
        cells=tuple(evaluate_e1_cell(spec, m, n, cells[(m, n)]) for m, n in ordered),
        constants_sha256=spec.constants_sha256,
    )
