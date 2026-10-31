"""JR5 verdict adapter: the single evidence-gated path to ``red_queen_proved``.

The adapter reads summary statistics produced by the JR5 analysis (the E1
cost gate, the E2 invasion tests, the condition (c) contrasts, the condition
(d) alternative arms and the replay checks) and returns one typed outcome
from the preregistration, plus the ``red_queen_proved`` flag.

Rules followed here, all fixed by ``docs/prereg/jr5``:

- Every threshold, margin, level and seed count is read from the hashed
  prereg constants. The prereg record is re-hashed from its files before use,
  and the evidence must name the same record digest.
- No boolean decision is taken from the input. The adapter only takes
  intervals, p-values, estimates and digests, and decides from them. An input
  that carries ``red_queen_proved``, an outcome or any unknown key is refused.
- A non-significant result never rules an alternative out. Only an
  equivalence result (90% interval inside the margin) or a 95% interval on the
  opposite side does.
- The flag is ``True`` only when conditions (a) to (e) all hold. Otherwise it
  is ``False`` and the typed outcome says why.

The E1 numbers come from the phase 3 cost gate. This module does not fit or
test anything for E1; it takes the two interval pairs per sex ratio and checks
them against the preregistered bounds, so phase 3 only has to fill
:class:`E1CostGateResult`.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest

__all__ = [
    "CLAIM",
    "Contrast",
    "E1CostGateResult",
    "Interval",
    "Jr5Evidence",
    "Jr5Verdict",
    "LoadArm",
    "ReplayCheck",
    "TimeShiftWindow",
    "assert_jr5_red_queen_claim_allowed",
    "audit_bundle_with_jr5_verdict",
    "default_prereg_dir",
    "evaluate_jr5_verdict",
    "verify_jr5_verdict",
]

CLAIM = "red_queen_proved"
_PREREG_REL = Path("docs") / "prereg" / "jr5"
_CONDITION_KEYS = ("a", "b", "c", "d", "e")
# PREREG.md section 2, load_consistent: the trend across the mutation grid is
# tested one-sided at 0.05. It is the only decision level not in the JSON.
_LOAD_TREND_ALPHA = 0.05


def default_prereg_dir() -> Path:
    """Folder of the JR5 prereg in a source checkout (src/ layout)."""

    return Path(__file__).resolve().parents[4] / _PREREG_REL


# ---------------------------------------------------------------- inputs


def _finite(value: Any, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{what} must be a number.")
    out = float(value)
    if not math.isfinite(out):
        raise ConfigurationError(f"{what} must be finite.")
    return out


def _check_keys(data: Mapping[str, Any], allowed: set[str], what: str) -> None:
    if not isinstance(data, Mapping):
        raise ConfigurationError(f"{what} must be a mapping.")
    if CLAIM in data:
        raise ConfigurationError(f"{what}: a hand-set {CLAIM!r} is refused; the adapter decides it.")
    extra = set(data) - allowed
    if extra:
        raise ConfigurationError(f"{what}: unknown keys {sorted(extra)}.")
    missing = allowed - set(data)
    if missing:
        raise ConfigurationError(f"{what}: missing keys {sorted(missing)}.")


@dataclass(frozen=True)
class Interval:
    """A closed interval [lo, hi] on the scale named by its user."""

    lo: float
    hi: float

    def __post_init__(self) -> None:
        lo = _finite(self.lo, "interval lo")
        hi = _finite(self.hi, "interval hi")
        if lo > hi:
            raise ConfigurationError("interval lo must not exceed hi.")

    @classmethod
    def parse(cls, value: Any, what: str) -> Interval:
        if not isinstance(value, Sequence) or isinstance(value, str) or len(value) != 2:
            raise ConfigurationError(f"{what} must be a [lo, hi] pair.")
        return cls(_finite(value[0], what), _finite(value[1], what))

    def inside(self, low: float, high: float) -> bool:
        return low < self.lo and self.hi < high

    def side(self, point: float = 0.0) -> int:
        """+1 if the interval is entirely above ``point``, -1 if below, else 0."""

        if self.lo > point:
            return 1
        if self.hi < point:
            return -1
        return 0

    def to_list(self) -> list[float]:
        return [self.lo, self.hi]


@dataclass(frozen=True)
class E1CostGateResult:
    """Phase 3 output for one sex ratio at N = 200, on the ratio scale.

    ``ci90`` is the TOST interval, ``ci95`` the interval that must exclude 1.
    ``n_excluded`` counts populations dropped by the early-fixation rule.
    """

    sex_ratio: float
    n_populations: int
    n_excluded: int
    ci90: Interval
    ci95: Interval

    _KEYS = frozenset({"sex_ratio", "n_populations", "n_excluded", "ci90", "ci95"})

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> E1CostGateResult:
        _check_keys(data, set(cls._KEYS), "e1")
        return cls(
            sex_ratio=_finite(data["sex_ratio"], "e1.sex_ratio"),
            n_populations=_count(data["n_populations"], "e1.n_populations"),
            n_excluded=_count(data["n_excluded"], "e1.n_excluded"),
            ci90=Interval.parse(data["ci90"], "e1.ci90"),
            ci95=Interval.parse(data["ci95"], "e1.ci95"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sex_ratio": self.sex_ratio,
            "n_populations": self.n_populations,
            "n_excluded": self.n_excluded,
            "ci90": self.ci90.to_list(),
            "ci95": self.ci95.to_list(),
        }


def _count(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigurationError(f"{what} must be a non-negative integer.")
    return value


@dataclass(frozen=True)
class Contrast:
    """A paired contrast across seeds (first arm minus second arm).

    ``p_two_sided`` is the paired t test. ``bca`` maps a confidence level
    (as written in the prereg constants) to the paired BCa interval at that
    level. ``ci90`` is the paired t interval used for equivalence.
    """

    n_seeds: int
    estimate: float
    p_two_sided: float
    ci90: Interval
    ci95: Interval
    bca: Mapping[float, Interval] = field(default_factory=dict)

    _KEYS = frozenset({"n_seeds", "estimate", "p_two_sided", "ci90", "ci95", "bca"})

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], what: str) -> Contrast:
        _check_keys(data, set(cls._KEYS), what)
        p = _finite(data["p_two_sided"], f"{what}.p_two_sided")
        if not 0.0 <= p <= 1.0:
            raise ConfigurationError(f"{what}.p_two_sided must be in [0, 1].")
        raw_bca = data["bca"]
        if not isinstance(raw_bca, Mapping):
            raise ConfigurationError(f"{what}.bca must map level to interval.")
        bca = {
            round(_finite(float(k), f"{what}.bca level"), 12): Interval.parse(v, f"{what}.bca")
            for k, v in raw_bca.items()
        }
        return cls(
            n_seeds=_count(data["n_seeds"], f"{what}.n_seeds"),
            estimate=_finite(data["estimate"], f"{what}.estimate"),
            p_two_sided=p,
            ci90=Interval.parse(data["ci90"], f"{what}.ci90"),
            ci95=Interval.parse(data["ci95"], f"{what}.ci95"),
            bca=bca,
        )

    def bca_at(self, level: float) -> Interval:
        key = round(level, 12)
        if key not in self.bca:
            raise ConfigurationError(f"no BCa interval at level {level!r}.")
        return self.bca[key]

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_seeds": self.n_seeds,
            "estimate": self.estimate,
            "p_two_sided": self.p_two_sided,
            "ci90": self.ci90.to_list(),
            "ci95": self.ci95.to_list(),
            "bca": {repr(k): v.to_list() for k, v in sorted(self.bca.items())},
        }


@dataclass(frozen=True)
class LoadArm:
    """Mutation-load arms at N = 200: outcross minus self, log fitness ratio."""

    at_mu_005: Contrast
    spearman_rho: float
    spearman_p_one_sided: float

    _KEYS = frozenset({"at_mu_005", "spearman_rho", "spearman_p_one_sided"})

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> LoadArm:
        _check_keys(data, set(cls._KEYS), "load")
        p = _finite(data["spearman_p_one_sided"], "load.spearman_p_one_sided")
        if not 0.0 <= p <= 1.0:
            raise ConfigurationError("load.spearman_p_one_sided must be in [0, 1].")
        return cls(
            at_mu_005=Contrast.from_dict(data["at_mu_005"], "load.at_mu_005"),
            spearman_rho=_finite(data["spearman_rho"], "load.spearman_rho"),
            spearman_p_one_sided=p,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "at_mu_005": self.at_mu_005.to_dict(),
            "spearman_rho": self.spearman_rho,
            "spearman_p_one_sided": self.spearman_p_one_sided,
        }


@dataclass(frozen=True)
class TimeShiftWindow:
    """One registered E4 window: its effect 95% interval and the sign cycling predicts."""

    name: str
    ci95: Interval
    expected_sign: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TimeShiftWindow:
        _check_keys(data, {"name", "ci95", "expected_sign"}, "time_shift window")
        sign = data["expected_sign"]
        if sign not in (1, -1) or isinstance(sign, bool):
            raise ConfigurationError("expected_sign must be 1 or -1.")
        name = data["name"]
        if not isinstance(name, str) or not name:
            raise ConfigurationError("window name must be a non-empty string.")
        return cls(name, Interval.parse(data["ci95"], "window.ci95"), int(sign))

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "ci95": self.ci95.to_list(), "expected_sign": self.expected_sign}


@dataclass(frozen=True)
class ReplayCheck:
    """Replay evidence for one run: digests and ledger residual, compared here."""

    run_id: str
    expected_digest: str
    replayed_digest: str
    one_shot_body_sha256: str
    resumed_body_sha256: str
    atp_ledger_residual: float

    _KEYS = frozenset(
        {
            "run_id",
            "expected_digest",
            "replayed_digest",
            "one_shot_body_sha256",
            "resumed_body_sha256",
            "atp_ledger_residual",
        }
    )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ReplayCheck:
        _check_keys(data, set(cls._KEYS), "replay")
        strings = {}
        for key in cls._KEYS - {"atp_ledger_residual"}:
            value = data[key]
            if not isinstance(value, str) or not value:
                raise ConfigurationError(f"replay.{key} must be a non-empty string.")
            strings[key] = value
        return cls(atp_ledger_residual=_finite(data["atp_ledger_residual"], "replay.residual"), **strings)

    def passes(self, max_residual: float) -> bool:
        return (
            self.expected_digest == self.replayed_digest
            and self.one_shot_body_sha256 == self.resumed_body_sha256
            and abs(self.atp_ledger_residual) <= max_residual
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "expected_digest": self.expected_digest,
            "replayed_digest": self.replayed_digest,
            "one_shot_body_sha256": self.one_shot_body_sha256,
            "resumed_body_sha256": self.resumed_body_sha256,
            "atp_ledger_residual": self.atp_ledger_residual,
        }


_E2_TESTS = ("e2_N200_high", "e2_N200_low", "e2_N50_high", "e2_N50_low")
_E2_HIGH = ("e2_N200_high", "e2_N50_high")


@dataclass(frozen=True)
class Jr5Evidence:
    """Everything the verdict is decided from. Build it with :meth:`from_dict`."""

    prereg_record_digest: str
    e1: tuple[E1CostGateResult, ...]
    e2: Mapping[str, Contrast]
    copassaged_minus_fixed: Contrast
    copassaged_minus_frozen: Contrast
    load: LoadArm
    frozen_minus_fixed: Contrast
    tax_minus_fixed: Contrast
    time_shift_windows: tuple[TimeShiftWindow, ...]
    runs: tuple[ReplayCheck, ...]
    sealed_locks: tuple[ReplayCheck, ...]

    _KEYS = frozenset(
        {
            "prereg_record_digest",
            "e1",
            "e2",
            "copassaged_minus_fixed",
            "copassaged_minus_frozen",
            "load",
            "frozen_minus_fixed",
            "tax_minus_fixed",
            "time_shift_windows",
            "runs",
            "sealed_locks",
        }
    )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Jr5Evidence:
        _check_keys(data, set(cls._KEYS), "evidence")
        digest = data["prereg_record_digest"]
        if not isinstance(digest, str):
            raise ConfigurationError("prereg_record_digest must be a string.")
        e2 = data["e2"]
        _check_keys(e2, set(_E2_TESTS), "e2")
        return cls(
            prereg_record_digest=digest,
            e1=tuple(E1CostGateResult.from_dict(x) for x in _seq(data["e1"], "e1")),
            e2={k: Contrast.from_dict(e2[k], k) for k in _E2_TESTS},
            copassaged_minus_fixed=Contrast.from_dict(data["copassaged_minus_fixed"], "c.fixed"),
            copassaged_minus_frozen=Contrast.from_dict(data["copassaged_minus_frozen"], "c.frozen"),
            load=LoadArm.from_dict(data["load"]),
            frozen_minus_fixed=Contrast.from_dict(data["frozen_minus_fixed"], "d.diversity"),
            tax_minus_fixed=Contrast.from_dict(data["tax_minus_fixed"], "d.tax"),
            time_shift_windows=tuple(TimeShiftWindow.from_dict(x) for x in _seq(data["time_shift_windows"], "windows")),
            runs=tuple(ReplayCheck.from_dict(x) for x in _seq(data["runs"], "runs")),
            sealed_locks=tuple(ReplayCheck.from_dict(x) for x in _seq(data["sealed_locks"], "sealed_locks")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "prereg_record_digest": self.prereg_record_digest,
            "e1": [x.to_dict() for x in self.e1],
            "e2": {k: self.e2[k].to_dict() for k in _E2_TESTS},
            "copassaged_minus_fixed": self.copassaged_minus_fixed.to_dict(),
            "copassaged_minus_frozen": self.copassaged_minus_frozen.to_dict(),
            "load": self.load.to_dict(),
            "frozen_minus_fixed": self.frozen_minus_fixed.to_dict(),
            "tax_minus_fixed": self.tax_minus_fixed.to_dict(),
            "time_shift_windows": [x.to_dict() for x in self.time_shift_windows],
            "runs": [x.to_dict() for x in self.runs],
            "sealed_locks": [x.to_dict() for x in self.sealed_locks],
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="jr5-evidence")


def _seq(value: Any, what: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ConfigurationError(f"{what} must be a list.")
    return value


# ---------------------------------------------------------------- prereg


@dataclass(frozen=True)
class _Prereg:
    digest: str
    constants: Mapping[str, Any]

    @property
    def outcomes(self) -> tuple[str, ...]:
        return tuple(self.constants["typed_outcomes"])


def _load_prereg(prereg_dir: Path | None) -> _Prereg:
    # Lazy import: the preregistration package is only needed on this path.
    from codontrace.preregistration import PreregistrationRecord
    from codontrace.preregistration.manifest import hash_plan

    folder = Path(prereg_dir) if prereg_dir is not None else default_prereg_dir()
    record_path = folder / "record.json"
    if not record_path.is_file():
        raise ConfigurationError(f"JR5 prereg record not found at {record_path}.")
    record = PreregistrationRecord.from_json(record_path.read_text(encoding="utf-8"))
    root = folder.parents[len(_PREREG_REL.parts) - 1]
    fresh = hash_plan([p for p, _ in record.manifest.files], root=root, title=record.manifest.title)
    if fresh.digest != record.manifest.digest or fresh.files != record.manifest.files:
        raise ConfigurationError("JR5 prereg files do not match record.json.")
    constants_path = folder / "jr5_prereg_constants.json"
    if f"{_PREREG_REL.as_posix()}/jr5_prereg_constants.json" not in {p for p, _ in record.manifest.files}:
        raise ConfigurationError("JR5 prereg record does not cover the constants file.")
    constants = json.loads(constants_path.read_text(encoding="utf-8"))
    if CLAIM not in constants.get("gated_claim_flags", {}):
        raise ConfigurationError(f"JR5 prereg does not gate {CLAIM!r}.")
    return _Prereg(record.manifest.digest, constants)


# ---------------------------------------------------------------- decisions


@dataclass(frozen=True)
class _TestCall:
    significant: bool
    direction: int
    agree: bool


def _call(t_rejects: bool, estimate: float, bca: Interval) -> _TestCall:
    """Combine the t test and the BCa interval by the prereg agreement rule.

    Significant only when both reject in the same direction. Disagreement is
    one rejecting and the other not, or both rejecting in opposite directions.
    """

    t_dir = (1 if estimate > 0 else -1 if estimate < 0 else 0) if t_rejects else 0
    b_dir = bca.side(0.0)
    if t_dir == 0 and b_dir == 0:
        return _TestCall(False, 0, True)
    if t_dir == b_dir:
        return _TestCall(True, t_dir, True)
    return _TestCall(False, 0, False)


def _holm_calls(e2: Mapping[str, Contrast], prereg: _Prereg) -> dict[str, _TestCall]:
    """Holm step-down over the four E2 tests, each paired with its BCa level.

    Tests are ordered by p (ties by name). Step k is tested at
    alpha / (m - k + 1); once a step fails, every later test is retained.
    The BCa interval of each test is read at the level registered for its step.
    """

    mult = prereg.constants["multiplicity"]
    family = list(mult["primary_family"])
    if sorted(family) != sorted(_E2_TESTS):
        raise ConfigurationError("E2 family in the prereg does not match the adapter.")
    alpha = float(mult["family_alpha"])
    levels = list(prereg.constants["e2"]["bootstrap"]["ci_level_by_holm_step"])
    order = sorted(family, key=lambda name: (e2[name].p_two_sided, name))
    calls: dict[str, _TestCall] = {}
    still_rejecting = True
    m = len(order)
    for k, name in enumerate(order):
        step_alpha = alpha / (m - k)
        t_rejects = still_rejecting and e2[name].p_two_sided < step_alpha
        if not t_rejects:
            still_rejecting = False
        calls[name] = _call(t_rejects, e2[name].estimate, e2[name].bca_at(levels[k]))
    return calls


def _one_sided_lower_call(c: Contrast, alpha: float, level: float) -> _TestCall:
    """Condition (c): one-sided t that the contrast is below 0, with the BCa check."""

    p_lower = c.p_two_sided / 2.0 if c.estimate < 0 else 1.0 - c.p_two_sided / 2.0
    return _call(p_lower < alpha, c.estimate, c.bca_at(level))


def _ruled_out(c: Contrast, margin: float, effect_sign: int) -> bool:
    """Equivalence (90% inside +-margin) or a 95% interval opposite the effect."""

    if c.ci90.inside(-margin, margin):
        return True
    return effect_sign != 0 and c.ci95.side(0.0) == -effect_sign


@dataclass(frozen=True)
class Jr5Verdict:
    """The adapter result. ``conditions`` holds (a) to (e) as decided here."""

    outcome: str
    red_queen_proved: bool
    conditions: Mapping[str, bool]
    evidence_digest: str
    prereg_record_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            CLAIM: self.red_queen_proved,
            "conditions": {k: bool(self.conditions[k]) for k in _CONDITION_KEYS},
            "evidence_digest": self.evidence_digest,
            "prereg_record_digest": self.prereg_record_digest,
        }


def evaluate_jr5_verdict(evidence: Jr5Evidence | Mapping[str, Any], *, prereg_dir: Path | None = None) -> Jr5Verdict:
    """Decide the JR5 typed outcome and the ``red_queen_proved`` flag."""

    ev = evidence if isinstance(evidence, Jr5Evidence) else Jr5Evidence.from_dict(evidence)
    prereg = _load_prereg(prereg_dir)
    if ev.prereg_record_digest != prereg.digest:
        raise ConfigurationError("evidence was produced under a different JR5 prereg record.")
    k = prereg.constants
    names = dict(zip(("rq", "load", "div", "none", "inconclusive", "fail"), prereg.outcomes, strict=True))
    _check_design(ev, k)

    # (a) cost gate, N = 200, both sex ratios.
    g = k["gate_e1"]
    cap = math.floor(float(g["exclusion_cap_fraction"]) * int(g["populations_per_cell"]))
    by_ratio = {round(r.sex_ratio, 12): r for r in ev.e1}
    cond_a = len(by_ratio) == len(ev.e1)
    for ratio in g["sex_ratios"]:
        res = by_ratio.get(round(float(ratio), 12))
        if res is None:
            cond_a = False
            continue
        lo, hi = (float(x) for x in g["equivalence_bounds"][str(ratio)])
        must_exclude = float(g["must_exclude"])
        cond_a = cond_a and res.n_excluded <= cap and res.ci90.inside(lo, hi) and res.ci95.side(must_exclude) != 0

    # (e) replay and validity.
    max_res = float(k["validity"]["atp_ledger_max_residual"])
    cond_e = bool(ev.runs) and bool(ev.sealed_locks) and all(r.passes(max_res) for r in (*ev.runs, *ev.sealed_locks))

    # (b) Holm over E2, both high-virulence tests significant with copassaged lower.
    calls = _holm_calls(ev.e2, prereg)
    high = [calls[n] for n in _E2_HIGH]
    cond_b = all(c.significant and c.direction < 0 for c in high)
    e2_any_high = any(c.significant and c.direction < 0 for c in high)

    # (c) copassaged below fixed and below frozen replay, N = 200 high.
    c_alpha = float(k["multiplicity"]["family_alpha"]) / 2.0
    c_level = float(k["e2"]["bootstrap"]["condition_c_ci_level"])
    c_fixed = _one_sided_lower_call(ev.copassaged_minus_fixed, c_alpha, c_level)
    c_frozen = _one_sided_lower_call(ev.copassaged_minus_frozen, c_alpha, c_level)
    cond_c = all(c.significant and c.direction < 0 for c in (c_fixed, c_frozen))

    # (d) alternatives ruled out; the effect side is the observed E2 N200 high sign.
    d = k["condition_d"]
    effect_sign = high[0].direction
    load_out = _ruled_out(ev.load.at_mu_005, float(d["margin_log_fitness_ratio"]), 1)
    windows_ok = any(w.ci95.side(0.0) == w.expected_sign for w in ev.time_shift_windows)
    div_out = _ruled_out(ev.frozen_minus_fixed, float(d["margin_frequency"]), effect_sign) and windows_ok
    freq_margin = float(d["margin_frequency"])
    tax_out = _ruled_out(ev.tax_minus_fixed, freq_margin, effect_sign)
    cond_d = load_out and div_out and tax_out

    conditions = {"a": cond_a, "b": cond_b, "c": cond_c, "d": cond_d, "e": cond_e}

    # Typed outcome, in the prereg order.
    if not cond_a or not cond_e:
        outcome = names["fail"]
    elif not all(c.agree for c in (*high, c_fixed, c_frozen)):
        outcome = names["inconclusive"]
    elif cond_b and tax_out and c_frozen.significant and c_frozen.direction < 0 and windows_ok:
        outcome = names["rq"]
    elif cond_b and (ev.copassaged_minus_frozen.ci90.inside(-freq_margin, freq_margin) or not windows_ok):
        outcome = names["div"]
    elif (
        not e2_any_high
        and ev.load.at_mu_005.ci95.side(0.0) > 0
        and ev.load.spearman_rho > 0
        and ev.load.spearman_p_one_sided < _LOAD_TREND_ALPHA
    ):
        outcome = names["load"]
    else:
        outcome = names["none"]

    proved = all(conditions.values()) and outcome == names["rq"]
    return Jr5Verdict(outcome, proved, conditions, ev.digest(), prereg.digest)


def _check_design(ev: Jr5Evidence, k: Mapping[str, Any]) -> None:
    """Seed and population counts must match the prereg design exactly."""

    pops = int(k["gate_e1"]["populations_per_cell"])
    for res in ev.e1:
        if res.n_populations != pops:
            raise ConfigurationError(f"E1 needs {pops} populations per sex ratio.")
    e2_seeds = int(k["e2"]["seeds_per_cell"])
    d_seeds = int(k["condition_d"]["seeds"])
    for c in (*ev.e2.values(), ev.copassaged_minus_fixed, ev.copassaged_minus_frozen):
        if c.n_seeds != e2_seeds:
            raise ConfigurationError(f"E2 contrasts need {e2_seeds} paired seeds.")
    for c in (ev.load.at_mu_005, ev.frozen_minus_fixed, ev.tax_minus_fixed):
        if c.n_seeds != d_seeds:
            raise ConfigurationError(f"condition (d) contrasts need {d_seeds} paired seeds.")


# ---------------------------------------------------------------- claim path


def verify_jr5_verdict(
    record: Mapping[str, Any],
    evidence: Jr5Evidence | Mapping[str, Any],
    *,
    prereg_dir: Path | None = None,
) -> Jr5Verdict:
    """Recompute the verdict from ``evidence`` and require ``record`` to equal it."""

    if not isinstance(record, Mapping):
        raise ConfigurationError("JR5 verdict record must be a mapping.")
    fresh = evaluate_jr5_verdict(evidence, prereg_dir=prereg_dir)
    if dict(record) != fresh.to_dict():
        raise ConfigurationError("JR5 verdict record does not match its evidence.")
    return fresh


def assert_jr5_red_queen_claim_allowed(
    record: Mapping[str, Any],
    evidence: Jr5Evidence | Mapping[str, Any],
    *,
    prereg_dir: Path | None = None,
) -> str:
    """Allow ``red_queen_proved`` only for a verified JR5 verdict with (a) to (e) true.

    ``assert_claim_allowed`` in the host_parasite adapter is not changed and
    keeps refusing the claim for every other caller.
    """

    verdict = verify_jr5_verdict(record, evidence, prereg_dir=prereg_dir)
    if not verdict.red_queen_proved:
        failed = [k for k in _CONDITION_KEYS if not verdict.conditions[k]]
        raise ConfigurationError(f"{CLAIM!r} is not supported by the JR5 verdict ({verdict.outcome}; failed {failed}).")
    return CLAIM


def audit_bundle_with_jr5_verdict(bundle: Mapping[str, Any], *, prereg_dir: Path | None = None) -> Any:
    """Run the claimgate auditor with the JR5 exemption from the Red Queen ban.

    The bundle carries ``jr5_verdict`` (the record) and ``jr5_evidence`` in its
    extra fields. The ban on ``red_queen_proved`` is lifted only when
    :func:`assert_jr5_red_queen_claim_allowed` passes on those two; any other
    bundle is graded exactly as ``audit_bundle`` grades it.
    """

    from codontrace.claimgate.auditor import audit_bundle

    def exemption(extra: Mapping[str, Any]) -> bool:
        record = extra.get("jr5_verdict")
        evidence = extra.get("jr5_evidence")
        if not isinstance(record, Mapping) or not isinstance(evidence, Mapping):
            return False
        try:
            assert_jr5_red_queen_claim_allowed(record, evidence, prereg_dir=prereg_dir)
        except (ConfigurationError, KeyError, TypeError, ValueError):
            return False
        return True

    return audit_bundle(bundle, red_queen_exemption=exemption)
