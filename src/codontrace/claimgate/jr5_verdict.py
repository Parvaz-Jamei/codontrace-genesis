"""JR5 verdict: the single evidence-gated path to ``red_queen_proved``.

The verdict is decided from the raw per-seed run records of the JR5
confirmatory campaign, never from summary numbers. Given the records, this
module recomputes every statistic the prereg names (the E1 slope fit and its t
intervals, the paired t tests and paired BCa intervals of E2 and condition (c),
the condition (d) contrasts, the Spearman trend of the load arm and the E4
time-shift intervals) and returns one typed outcome plus the flag.

Rules, all fixed by ``docs/prereg/jr5``:

- The prereg is pinned in code. ``PREREG_RECORD_DIGEST`` is the locked record
  digest and ``PREREG_CONSTANTS_SHA256`` the sha256 of the constants file. The
  constants are read from the copy shipped with this package, checked against
  the pinned sha256 and parsed from the same bytes that were hashed. Changing
  the prereg therefore means a DEVIATIONS entry plus a reviewed bump of both
  constants; no caller can point the verdict at another prereg folder.
- The run set must equal the prereg grid exactly: every experiment, cell, host
  N and seed once, with unique run ids. Each run record is content-addressed
  (its ``sha256`` is the canonical digest of the rest of the record).
- The sealed-lock digests of PREREG section 9 and the E4 windows and signs of
  the RQ-v2 phase 6 lock are pinned here, not taken from the input.
- No decision is taken from the input. A record that carries
  ``red_queen_proved``, an outcome or an unknown key is refused.
- A non-significant result never rules an alternative out. Only equivalence
  (90% interval strictly inside the margin) or a 95% interval on the opposite
  side does. "Inside" is strict: an interval that touches a bound is not inside.
- The flag is ``True`` only when (a) to (e) all hold and the typed outcome is
  ``rq_consistent``.

Threat model. The checks above guard against analysis errors, hand-edited
summary numbers, records that were edited without being re-addressed, a
swapped or re-hashed prereg, a missing or duplicated run, replay digests that
do not match the sealed locks, and a verdict copied onto an unrelated bundle.
They do not guard against someone who fabricates the raw run records and
their replay digests consistently; only re-running the seeds detects that.
In-process code changes (monkeypatching this module) are out of scope.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest

__all__ = [
    "CLAIM",
    "E4_WINDOW_SIGNS",
    "E4_WINDOW_GENERATIONS",
    "PREREG_CONSTANTS_SHA256",
    "PREREG_RECORD_DIGEST",
    "SEALED_LOCK_DIGESTS",
    "Interval",
    "Jr5Evidence",
    "Jr5Verdict",
    "RunRecord",
    "assert_jr5_red_queen_claim_allowed",
    "evaluate_jr5_verdict",
    "jr5_constants",
    "jr5_bundle_fields",
    "jr5_run_grid",
    "red_queen_exemption_holds",
    "run_record_sha256",
    "verify_jr5_verdict",
]

CLAIM = "red_queen_proved"

# Locked prereg (docs/prereg/jr5/record.json, manifest digest) and the sha256
# of jr5_prereg_constants.json that the record lists. Bump both only together
# with a DEVIATIONS entry in docs/prereg/jr5.
PREREG_RECORD_DIGEST = "1e1fe67f176fbf4e36725f63bb8773cedf3c6d6c9585f160be14a8a05c238c1d"
PREREG_CONSTANTS_SHA256 = "e27d3d9eae739097b6fa712ba6ae4f12f568c3479197c67db27bef7439fab026"
_CONSTANTS_RESOURCE = "data/jr5_prereg_constants.json"

# PREREG section 9: every sealed lock reused by JR5, by name, with its digest.
SEALED_LOCK_DIGESTS: Mapping[str, str] = {
    "selfing_hold.design": "762e778bac175b31992fe85572b3ce7057e4727393f23d0622b295ba7a6fd298",
    "selfing_hold.campaign": "73e6a52825f92a595c0676f63f81add87f0bbddb080c657e7f42d9a274aa94e6",
    "mating_ledger.design": "f4475f69032423aa99e86cae9d4e88bc6d1cc2026aadd52f8a89b3eaa32d80dd",
    "mating_ledger.campaign": "72f59eff61ee02905efd075ba08b908c42368bb4079a96eecefc3ad53910f0a5",
    "rq_v2_phase6.summary_sha256": "948413a36d9046448f78de9cfb323207cf42852905d39329d6ba0e46d60b1344",
}

# RQ-v2 phase 6 lock (runs/rq-mechanism-v2/PHASE6_CONFIRM_LOCK.md, Estimand):
# at the horizon with the primary lag,
#   host effect     = I(H now, P past) - I(H past, P past)
#   parasite effect = I(H now, P now)  - I(H now, P past)
# Under cycling hosts resist past parasites (infectivity falls: host effect
# below 0) and parasites track current hosts (infectivity rises: parasite
# effect above 0).
E4_WINDOW_GENERATIONS = (67, 70)
E4_WINDOW_SIGNS: Mapping[str, int] = {"host_effect": -1, "parasite_effect": 1}

_CONDITION_KEYS = ("a", "b", "c", "d", "e")
_E2_TESTS = ("e2_N200_high", "e2_N200_low", "e2_N50_high", "e2_N50_low")
_E2_HIGH = ("e2_N200_high", "e2_N50_high")
_REPLAY_KEYS = frozenset(
    {"expected_digest", "replayed_digest", "one_shot_body_sha256", "resumed_body_sha256", "atp_ledger_residual"}
)
_RUN_KEYS = frozenset({"run_id", "experiment", "cell", "host_n", "seed", "data", "replay", "sha256"})
# Level names the constants give only as counts (PREREG section 4 and the
# E2/E5 text): E2 runs the mixed-invasion residents; E5 crosses the two
# obligate mating systems with fixed or copassaged parasites at two virulences.
_E2_MATING = "mixed_invasion"
_E5_PARASITE = ("fixed", "copassaged")


# ---------------------------------------------------------------- helpers


def _finite(value: Any, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{what} must be a number.")
    out = float(value)
    if not math.isfinite(out):
        raise ConfigurationError(f"{what} must be finite.")
    return out


def _int(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{what} must be an integer.")
    return value


def _mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{what} must be a mapping.")
    return value


def _seq(value: Any, what: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ConfigurationError(f"{what} must be a list.")
    return value


def _check_keys(value: Any, allowed: frozenset[str] | set[str], what: str) -> Mapping[str, Any]:
    data = _mapping(value, what)
    if CLAIM in data:
        raise ConfigurationError(f"{what}: a hand-set {CLAIM!r} is refused; the verdict decides it.")
    extra = set(data) - set(allowed)
    if extra:
        raise ConfigurationError(f"{what}: unknown keys {sorted(extra)}.")
    missing = set(allowed) - set(data)
    if missing:
        raise ConfigurationError(f"{what}: missing keys {sorted(missing)}.")
    return data


def _hex64(value: Any, what: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ConfigurationError(f"{what} must be a lowercase sha256 hex digest.")
    return value


# ---------------------------------------------------------------- prereg


def jr5_constants() -> dict[str, Any]:
    """The pinned prereg constants, parsed from the bytes that were hashed."""

    package = resources.files("codontrace.claimgate")
    record_raw = package.joinpath("data/jr5_prereg_record.json").read_bytes()
    raw = package.joinpath(_CONSTANTS_RESOURCE).read_bytes()
    return _verified_constants(raw, record_raw)


def _verified_constants(raw: bytes, record_raw: bytes) -> dict[str, Any]:
    """Verify the manifest and parse only the byte sequence whose hash was checked."""
    try:
        record = _mapping(json.loads(record_raw), "prereg record")
        manifest = _mapping(record.get("manifest"), "prereg manifest")
        files = _seq(manifest.get("files"), "prereg manifest files")
        pairs = []
        for pair in files:
            if not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(v, str) for v in pair):
                raise ConfigurationError("prereg manifest files must be path/digest pairs.")
            pairs.append((pair[0], pair[1]))
        if len({path for path, _ in pairs}) != len(pairs):
            raise ConfigurationError("prereg manifest repeats a path.")
        title = manifest.get("title")
        if not isinstance(title, str):
            raise ConfigurationError("prereg manifest title must be a string.")
        actual_manifest = canonical_digest({"schema": "codontrace_prereg_manifest_v1", "title": title,
                                            "files": [{"path": path, "sha256": sha} for path, sha in pairs]})
        if manifest.get("digest") != PREREG_RECORD_DIGEST or actual_manifest != PREREG_RECORD_DIGEST:
            raise ConfigurationError("JR5 prereg manifest does not match the code-pinned digest.")
        actual = hashlib.sha256(raw).hexdigest()
        entries = [sha for path, sha in pairs if path == "docs/prereg/jr5/jr5_prereg_constants.json"]
        if entries != [actual] or actual != PREREG_CONSTANTS_SHA256:
            raise ConfigurationError("JR5 prereg constants do not match the pinned sha256.")
        constants = _mapping(json.loads(raw), "prereg constants")
    except ConfigurationError:
        raise
    except (ValueError, UnicodeError) as exc:
        raise ConfigurationError("JR5 prereg resources must contain valid JSON.") from exc
    if CLAIM not in constants.get("gated_claim_flags", {}):
        raise ConfigurationError(f"JR5 prereg does not gate {CLAIM!r}.")
    return dict(constants)


def _inclusive(block: Sequence[Any]) -> tuple[int, ...]:
    lo, hi = int(block[0]), int(block[1])
    return tuple(range(lo, hi + 1))


Cell = tuple[tuple[str, Any], ...]
RunKey = tuple[str, Cell, int, int]


def _cell(**levels: Any) -> Cell:
    return tuple(sorted(levels.items()))


def jr5_run_grid(constants: Mapping[str, Any] | None = None) -> frozenset[RunKey]:
    """Every (experiment, cell, host N, seed) the prereg grid registers."""

    k = jr5_constants() if constants is None else constants
    g = k["gate_e1"]
    confirm = _inclusive(k["seeds"]["confirmatory_block"])
    alt = k["alternative_arms"]
    keys: set[RunKey] = set()
    for ratio in g["sex_ratios"]:
        for n in g["host_n_reported"]:
            for s in _inclusive(g["seed_split"][str(ratio)]):
                keys.add(("e1", _cell(sex_ratio=float(ratio)), int(n), s))
    cells: dict[str, list[Cell]] = {
        "e2": [_cell(mating=_E2_MATING, parasite=p) for p in k["parasite_arms"]],
        "e5": [
            _cell(mating=m, parasite=p, virulence=v)
            for m in ("obligate_outcross", "obligate_self")
            for p in _E5_PARASITE
            for v in ("low", "high")
        ],
        "mutation_load": [
            _cell(mutation=float(mu), mating=m)
            for mu in alt["mutation_load"]["host_mutation_grid"]
            for m in alt["mutation_load"]["mating"]
        ],
        "sex_ratio_0.25": [_cell(parasite=p) for p in alt["sex_ratio_0.25"]["parasite"]],
    }
    for name in ("uniform_tax", "recombination_off", "migration_on"):
        cells[name] = [_cell(virulence=v) for v in alt[name]["virulence"]]
    host_ns = [int(n) for n in k["e2"]["host_n"]]
    for exp, exp_cells in cells.items():
        for c in exp_cells:
            for n in host_ns:
                for s in confirm:
                    keys.add((exp, c, n, s))
    # The grid in the constants fixes the size of every experiment.
    for exp, dims in k["grid"].items():
        expected = math.prod(int(v) for v in dims.values())
        got = sum(1 for key in keys if key[0] == exp)
        if got != expected:
            raise ConfigurationError(f"JR5 grid for {exp} has {got} runs, prereg says {expected}.")
    if len(keys) != int(k["budget"]["runs_total"]):
        raise ConfigurationError("JR5 run grid does not match budget.runs_total.")
    return frozenset(keys)


# ---------------------------------------------------------------- inputs


@dataclass(frozen=True)
class Interval:
    """An interval [lo, hi]; :meth:`inside` is strict at both ends."""

    lo: float
    hi: float

    def inside(self, low: float, high: float) -> bool:
        return low < self.lo and self.hi < high

    def side(self, point: float = 0.0) -> int:
        """+1 if the interval is entirely above ``point``, -1 if below, else 0."""

        if self.lo > point:
            return 1
        if self.hi < point:
            return -1
        return 0


def run_record_sha256(record: Mapping[str, Any]) -> str:
    """Content address of a run record: canonical digest of all but ``sha256``."""

    return canonical_digest({k: v for k, v in record.items() if k != "sha256"})


@dataclass(frozen=True)
class RunRecord:
    """One raw per-seed run record, content-addressed by ``sha256``."""

    run_id: str
    key: RunKey
    data: Mapping[str, Any]
    replay: Mapping[str, Any]
    sha256: str
    raw: Mapping[str, Any]

    @classmethod
    def from_dict(cls, data: Any) -> RunRecord:
        d = _check_keys(data, _RUN_KEYS, "run")
        run_id = d["run_id"]
        if not isinstance(run_id, str) or not run_id:
            raise ConfigurationError("run.run_id must be a non-empty string.")
        exp = d["experiment"]
        if not isinstance(exp, str):
            raise ConfigurationError("run.experiment must be a string.")
        cell_map = _mapping(d["cell"], "run.cell")
        for level, value in cell_map.items():
            if not isinstance(level, str) or isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise ConfigurationError("run.cell levels must be strings or numbers, not booleans or containers.")
            if isinstance(value, (int, float)):
                _finite(value, f"run.cell.{level}")
        cell = tuple(
            sorted(
                (str(f), float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v)
                for f, v in cell_map.items()
            )
        )
        replay = _check_keys(d["replay"], _REPLAY_KEYS, f"run {run_id} replay")
        for name in _REPLAY_KEYS - {"atp_ledger_residual"}:
            _hex64(replay[name], f"run {run_id} replay.{name}")
        _finite(replay["atp_ledger_residual"], f"run {run_id} atp_ledger_residual")
        sha = _hex64(d["sha256"], f"run {run_id} sha256")
        if sha != run_record_sha256(d):
            raise ConfigurationError(f"run {run_id}: sha256 does not address its content.")
        key: RunKey = (exp, cell, _int(d["host_n"], "run.host_n"), _int(d["seed"], "run.seed"))
        fields = {"e1": {"uniparental_counts"}, "e2": {"terminal_uniparental_frequency"},
                  "uniform_tax": {"terminal_uniparental_frequency"}, "mutation_load": {"log_terminal_fitness"}}
        allowed = set(fields.get(exp, set()))
        if exp == "e2" and cell_map.get("parasite") == "copassaged_high" and key[2] == 200:
            allowed.update({"e4", "e4_window"})
        payload = _check_keys(d["data"], allowed, f"run {run_id} data")
        return cls(run_id, key, payload, replay, sha, d)

    def passes_replay(self, max_residual: float) -> bool:
        r = self.replay
        return (
            r["expected_digest"] == r["replayed_digest"]
            and r["one_shot_body_sha256"] == r["resumed_body_sha256"]
            and abs(float(r["atp_ledger_residual"])) <= max_residual
        )


@dataclass(frozen=True)
class Jr5Evidence:
    """Raw JR5 evidence: the run records, the sealed-lock replays, the E1 gate record."""

    prereg_record_digest: str
    runs: tuple[RunRecord, ...]
    sealed_locks: Mapping[str, str]
    e1_gate_record: Mapping[str, Any]

    _KEYS = frozenset({"prereg_record_digest", "runs", "sealed_locks", "e1_gate_record"})

    @classmethod
    def from_dict(cls, data: Any) -> Jr5Evidence:
        d = _check_keys(data, cls._KEYS, "evidence")
        if d["prereg_record_digest"] != PREREG_RECORD_DIGEST:
            raise ConfigurationError("evidence names a prereg record other than the pinned JR5 record.")
        locks = _check_keys(d["sealed_locks"], set(SEALED_LOCK_DIGESTS), "sealed_locks")
        for name, value in locks.items():
            _hex64(value, f"sealed lock {name}")
        runs = tuple(RunRecord.from_dict(r) for r in _seq(d["runs"], "runs"))
        ids = [r.run_id for r in runs]
        if len(set(ids)) != len(ids):
            raise ConfigurationError("run ids must be unique.")
        keys = [r.key for r in runs]
        if len(set(keys)) != len(keys):
            raise ConfigurationError("a grid cell and seed appear in more than one run.")
        grid = jr5_run_grid()
        if set(keys) != grid:
            missing, extra = len(grid - set(keys)), len(set(keys) - grid)
            raise ConfigurationError(f"run set must equal the prereg grid ({missing} missing, {extra} not registered).")
        return cls(PREREG_RECORD_DIGEST, runs, dict(locks), _mapping(d["e1_gate_record"], "e1_gate_record"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "prereg_record_digest": self.prereg_record_digest,
            "runs": [dict(r.raw) for r in sorted(self.runs, key=lambda r: r.run_id)],
            "sealed_locks": dict(sorted(self.sealed_locks.items())),
            "e1_gate_record": dict(self.e1_gate_record),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="jr5-evidence")

    def seeds(self) -> tuple[int, ...]:
        return tuple(sorted({r.key[3] for r in self.runs}))


# ---------------------------------------------------------------- statistics


def _mean_sd(values: Sequence[float]) -> tuple[float, float]:
    n = len(values)
    mean = math.fsum(values) / n
    var = math.fsum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, math.sqrt(var)


def _t_interval(values: Sequence[float], level: float) -> Interval:
    from codontrace.claimgate.power import t_ppf

    mean, sd = _mean_sd(values)
    half = t_ppf(0.5 + level / 2.0, len(values) - 1) * sd / math.sqrt(len(values))
    return Interval(mean - half, mean + half)


@dataclass(frozen=True)
class _Paired:
    """A paired contrast (first minus second) over the seeds of the block."""

    deltas: tuple[float, ...]
    bootstrap_seed: int
    resamples: int

    @property
    def estimate(self) -> float:
        return math.fsum(self.deltas) / len(self.deltas)

    def p_two_sided(self) -> float:
        from codontrace.claimgate.power import t_cdf

        mean, sd = _mean_sd(self.deltas)
        if sd == 0.0:
            return 1.0 if mean == 0.0 else 0.0
        t = mean / (sd / math.sqrt(len(self.deltas)))
        return min(1.0, 2.0 * t_cdf(-abs(t), len(self.deltas) - 1))

    def ci(self, level: float) -> Interval:
        return _t_interval(self.deltas, level)

    def bca(self, level: float) -> Interval:
        from codontrace.genesis.statistical_protocol import bootstrap_ci_paired

        lo, hi = bootstrap_ci_paired(
            self.deltas, method="bca", resamples=self.resamples, seed=self.bootstrap_seed, confidence=level
        )
        return Interval(lo, hi)


def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for t in range(i, j + 1):
            ranks[order[t]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def _spearman_greater(x: Sequence[float], y: Sequence[float]) -> tuple[float, float]:
    """Spearman rho (average ranks) and its one-sided p for rho > 0 (t approximation, n - 2 df)."""

    from codontrace.claimgate.power import t_cdf

    rx, ry = _ranks(x), _ranks(y)
    mx, my = math.fsum(rx) / len(rx), math.fsum(ry) / len(ry)
    sxy = math.fsum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    sxx = math.fsum((a - mx) ** 2 for a in rx)
    syy = math.fsum((b - my) ** 2 for b in ry)
    if sxx == 0.0 or syy == 0.0:
        return 0.0, 1.0
    rho = sxy / math.sqrt(sxx * syy)
    df = len(x) - 2
    if rho >= 1.0:
        return 1.0, 0.0
    if rho <= -1.0:
        return -1.0, 1.0
    t = rho * math.sqrt(df / (1.0 - rho * rho))
    return rho, t_cdf(-t, df)


def _firth_logit_slope(counts: Sequence[int], n: int, fit: Mapping[str, Any]) -> float:
    """Bias-reduced binomial logit fit of counts on generation 0..T; returns the slope.

    Maximises the log likelihood plus half the log determinant of the Fisher
    information, by Newton steps on the modified score with the Fisher
    information as the step matrix (gate_e1.fit in the prereg constants).
    """

    tol, max_iter = float(fit["tol"]), int(fit["max_iter"])
    b0, b1 = (float(v) for v in fit["start"])
    xs = [float(t) for t in range(len(counts))]
    for _ in range(max_iter):
        eta = [b0 + b1 * x for x in xs]
        if not all(math.isfinite(v) for v in eta):
            raise ConfigurationError("E1 fit: non-finite linear predictor.")
        ps = [1.0 / (1.0 + math.exp(-v)) if v >= 0 else math.exp(v) / (1.0 + math.exp(v)) for v in eta]
        ws = [n * p * (1.0 - p) for p in ps]
        i00 = math.fsum(ws)
        i01 = math.fsum(w * x for w, x in zip(ws, xs, strict=True))
        i11 = math.fsum(w * x * x for w, x in zip(ws, xs, strict=True))
        det = i00 * i11 - i01 * i01
        if det <= 0.0:
            raise ConfigurationError("E1 fit: singular information matrix.")
        v00, v01, v11 = i11 / det, -i01 / det, i00 / det
        u0 = u1 = 0.0
        for k, p, w, x in zip(counts, ps, ws, xs, strict=True):
            hat = w * (v00 + 2.0 * v01 * x + v11 * x * x)
            r = (k - n * p) + hat * (0.5 - p)
            u0 += r
            u1 += r * x
        s0, s1 = v00 * u0 + v01 * u1, v01 * u0 + v11 * u1
        b0, b1 = b0 + s0, b1 + s1
        if max(abs(s0), abs(s1)) < tol:
            return b1
    raise ConfigurationError("E1 fit did not converge.")


# ---------------------------------------------------------------- decisions


@dataclass(frozen=True)
class _TestCall:
    significant: bool
    direction: int
    agree: bool


def _call(t_rejects: bool, estimate: float, bca: Interval) -> _TestCall:
    """Significant only when the t test and the BCa interval both reject in the same direction."""

    t_dir = (1 if estimate > 0 else -1 if estimate < 0 else 0) if t_rejects else 0
    b_dir = bca.side(0.0)
    if t_dir == 0 and b_dir == 0:
        return _TestCall(False, 0, True)
    if t_dir == b_dir:
        return _TestCall(True, t_dir, True)
    return _TestCall(False, 0, False)


def _holm_calls(e2: Mapping[str, _Paired], k: Mapping[str, Any]) -> dict[str, _TestCall]:
    """Holm step-down over the four E2 tests; the BCa level follows each test's step."""

    mult = k["multiplicity"]
    family = list(mult["primary_family"])
    if sorted(family) != sorted(_E2_TESTS):
        raise ConfigurationError("E2 family in the prereg does not match the verdict code.")
    alpha = float(mult["family_alpha"])
    levels = [float(x) for x in k["e2"]["bootstrap"]["ci_level_by_holm_step"]]
    p = {name: e2[name].p_two_sided() for name in family}
    order = sorted(family, key=lambda name: (p[name], name))
    calls: dict[str, _TestCall] = {}
    still_rejecting = True
    m = len(order)
    for step, name in enumerate(order):
        t_rejects = still_rejecting and p[name] < alpha / (m - step)
        if not t_rejects:
            still_rejecting = False
        calls[name] = _call(t_rejects, e2[name].estimate, e2[name].bca(levels[step]))
    return calls


def _one_sided_lower_call(c: _Paired, alpha: float, level: float) -> _TestCall:
    """Condition (c): one-sided t that the contrast is below 0, with the 95% BCa check."""

    p2 = c.p_two_sided()
    p_lower = p2 / 2.0 if c.estimate < 0 else 1.0 - p2 / 2.0
    return _call(p_lower < alpha, c.estimate, c.bca(level))


def _ruled_out(c: _Paired, margin: float, effect_sign: int, eq_level: float, opp_level: float) -> bool:
    """Equivalence (interval strictly inside +-margin) or an interval opposite the effect."""

    if c.ci(eq_level).inside(-margin, margin):
        return True
    return effect_sign != 0 and c.ci(opp_level).side(0.0) == -effect_sign


@dataclass(frozen=True)
class Jr5Verdict:
    """The verdict. ``conditions`` holds (a) to (e) as decided here."""

    outcome: str
    red_queen_proved: bool
    conditions: Mapping[str, bool]
    evidence_digest: str
    prereg_record_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            CLAIM: self.red_queen_proved,
            "conditions": {key: bool(self.conditions[key]) for key in _CONDITION_KEYS},
            "evidence_digest": self.evidence_digest,
            "prereg_record_digest": self.prereg_record_digest,
        }


class _Values:
    """Per-seed values read from the run records, keyed by cell and host N."""

    def __init__(self, ev: Jr5Evidence) -> None:
        self._by: dict[tuple[str, Cell, int], dict[int, RunRecord]] = {}
        for r in ev.runs:
            exp, cell, n, seed = r.key
            self._by.setdefault((exp, cell, n), {})[seed] = r

    def runs(self, exp: str, n: int, **levels: Any) -> dict[int, RunRecord]:
        return self._by[(exp, _cell(**levels), n)]

    def number(
        self, exp: str, n: int, field: str, lo: float | None = None, hi: float | None = None, **levels: Any
    ) -> dict[int, float]:
        out: dict[int, float] = {}
        for seed, r in self.runs(exp, n, **levels).items():
            v = _finite(r.data.get(field), f"run {r.run_id} data.{field}")
            if (lo is not None and v < lo) or (hi is not None and v > hi):
                raise ConfigurationError(f"run {r.run_id} data.{field} is out of range.")
            out[seed] = v
        return out


def _paired(a: Mapping[int, float], b: Mapping[int, float], boot: Mapping[str, Any]) -> _Paired:
    seeds = sorted(a)
    if sorted(b) != seeds:
        raise ConfigurationError("paired arms do not share the seed block.")
    return _Paired(tuple(a[s] - b[s] for s in seeds), int(boot["seed"]), int(boot["resamples"]))


def _e1(values: _Values, k: Mapping[str, Any]) -> tuple[bool, bool, list[dict[str, Any]]]:
    """Return (every gated N = 200 cell passes the TOST and the null check, any E1 cell breaches the cap)."""

    g = k["gate_e1"]
    cap = float(g["exclusion_cap_fraction"])
    early = int(g["early_fixation_generation"])
    log_null = math.log(float(g["must_exclude"]))
    gated_pass = True
    breach = False
    cells = []
    for ratio in g["sex_ratios"]:
        gens = int(g["generations"][str(ratio)])
        lo, hi = (math.log(float(x)) for x in g["equivalence_bounds"][str(ratio)])
        for n in g["host_n_reported"]:
            n = int(n)
            log_w: list[float] = []
            excluded_seeds = []
            fixed_seeds = []
            lost_seeds = []
            runs = values.runs("e1", n, sex_ratio=float(ratio))
            for seed in sorted(runs):
                r = runs[seed]
                counts = _seq(r.data.get("uniparental_counts"), f"run {r.run_id} uniparental_counts")
                if len(counts) != gens + 1:
                    raise ConfigurationError(f"run {r.run_id}: E1 needs counts for generations 0 to {gens}.")
                cs = [_int(c, f"run {r.run_id} count") for c in counts]
                if any(c < 0 or c > n for c in cs):
                    raise ConfigurationError(f"run {r.run_id}: counts must lie in [0, {n}].")
                fixed = next((t for t, c in enumerate(cs) if c == n), None)
                if fixed is not None:
                    fixed_seeds.append(seed)
                if 0 in cs:
                    lost_seeds.append(seed)
                if fixed is not None and 0 in cs:
                    raise ConfigurationError(f"run {r.run_id}: a population cannot fix and be lost.")
                if fixed is not None and fixed < early:
                    excluded_seeds.append(seed)
                    continue
                log_w.append(_firth_logit_slope(cs, n, g["fit"]))
            exceeded = len(excluded_seeds) > cap * len(runs)
            breach = breach or exceeded
            ci90 = _t_interval(log_w, float(g["ci_level"])) if len(log_w) >= 2 else None
            ci95 = _t_interval(log_w, float(g["must_exclude_ci_level"])) if len(log_w) >= 2 else None
            equivalent = ci90 is not None and ci90.inside(lo, hi)
            excludes = ci95 is not None and ci95.side(log_null) != 0
            passed = equivalent and excludes and not exceeded
            gated = n == int(g["host_n_gate"])
            if gated:
                gated_pass = gated_pass and passed
            cells.append({
                "sex_ratio": float(ratio), "host_n": n, "gated": gated,
                "n_total": len(runs), "n_used": len(log_w), "seeds": sorted(runs),
                "excluded_seeds": excluded_seeds, "fixed_seeds": fixed_seeds, "lost_seeds": lost_seeds,
                "exclusion_cap_exceeded": exceeded, "log_bounds": [lo, hi],
                "ratio_bounds": list(g["equivalence_bounds"][str(ratio)]),
                "ratio_ci": None if ci90 is None else [math.exp(ci90.lo), math.exp(ci90.hi)],
                "ratio_ci95": None if ci95 is None else [math.exp(ci95.lo), math.exp(ci95.hi)],
                "exclusion_interval_log": None if ci95 is None else [ci95.lo, ci95.hi],
                "equivalent": equivalent, "excludes_null": excludes, "passed": passed,
                "tost": _tost_record(log_w, lo, hi, float(g["alpha"])) if ci90 is not None else None,
            })
    return gated_pass, breach, cells


def _tost_record(values: Sequence[float], lo: float, hi: float, alpha: float) -> dict[str, Any]:
    from codontrace.claimgate.power import t_cdf

    n = len(values)
    mean, sd = _mean_sd(values)
    se = sd / math.sqrt(n)
    tl = (mean - lo) / se if se else math.copysign(math.inf, mean - lo) if mean != lo else 0.0
    tu = (mean - hi) / se if se else math.copysign(math.inf, mean - hi) if mean != hi else 0.0
    pl, pu = t_cdf(-tl, n - 1), t_cdf(tu, n - 1)
    ci = _t_interval(values, 1.0 - 2.0 * alpha)
    return {"test": "one_sample_tost", "n": n, "df": n - 1, "mean": mean, "sd": sd,
            "standard_error": se, "lower_bound": lo, "upper_bound": hi, "alpha": alpha,
            "t_lower": tl, "t_upper": tu, "p_lower": pl, "p_upper": pu, "p_value": max(pl, pu),
            "ci_level": 1.0 - 2.0 * alpha, "ci_low": ci.lo, "ci_high": ci.hi,
            "equivalent": pl < alpha and pu < alpha}


def _same_analysis(actual: Any, expected: Any) -> bool:
    """Exact provenance and decisions; tolerate only floating evaluation roundoff."""
    if isinstance(expected, dict):
        return isinstance(actual, Mapping) and set(actual) == set(expected) and all(
            _same_analysis(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _same_analysis(a, e) for a, e in zip(actual, expected, strict=True))
    if isinstance(expected, float):
        return not isinstance(actual, bool) and isinstance(actual, (int, float)) and math.isclose(
            actual, expected, rel_tol=1e-9, abs_tol=1e-11)
    return type(actual) is type(expected) and actual == expected


def _check_e1_gate_record(rec: Mapping[str, Any], gated_pass: bool, instrument_failure: bool,
                          cells: list[dict[str, Any]], k: Mapping[str, Any]) -> None:
    """Verify the complete v3 provenance and recomputed per-cell record."""
    _check_keys(rec, {"schema", "constants_sha256", "prereg_manifest_digest", "spec", "cells",
                      "passed", "instrument_failure", "digest"}, "E1 gate record")
    if rec["schema"] != "jr5_e1_gate_v3":
        raise ConfigurationError("E1 gate record must use schema jr5_e1_gate_v3.")
    if rec["constants_sha256"] != PREREG_CONSTANTS_SHA256:
        raise ConfigurationError("E1 gate record has a missing or wrong constants_sha256.")
    if rec["prereg_manifest_digest"] != PREREG_RECORD_DIGEST:
        raise ConfigurationError("E1 gate record has the wrong prereg manifest digest.")
    g = k["gate_e1"]
    spec_keys = ("test", "alpha", "ci_level", "relative_margin", "must_exclude", "must_exclude_ci_level",
                 "exclusion_cap_fraction", "early_fixation_generation", "host_n_gate", "populations_per_cell",
                 "sex_ratios", "host_n_reported", "seed_split")
    expected_spec = {key: g[key] for key in spec_keys}
    expected_spec.update(constants_sha256=PREREG_CONSTANTS_SHA256, prereg_manifest_digest=PREREG_RECORD_DIGEST)
    if not _same_analysis(rec["spec"], expected_spec) or dict(rec["spec"]) != expected_spec:
        raise ConfigurationError("E1 gate spec does not match the trusted prereg settings.")
    body = {key: v for key, v in rec.items() if key != "digest"}
    if rec["digest"] != canonical_digest(body):
        raise ConfigurationError("E1 gate record digest does not match its body.")
    actual_cells = _seq(rec["cells"], "E1 gate cells")
    keyed = {}
    for cell in actual_cells:
        c = dict(_mapping(cell, "E1 gate cell"))
        for name in ("excluded_seeds", "fixed_seeds", "lost_seeds"):
            if name in c:
                c[name] = sorted(_int(seed, f"E1 {name}") for seed in _seq(c[name], f"E1 {name}"))
        key = (_finite(c.get("sex_ratio"), "E1 sex ratio"), _int(c.get("host_n"), "E1 host N"))
        if key in keyed:
            raise ConfigurationError("E1 gate cells must be unique.")
        keyed[key] = c
    expected = {(c["sex_ratio"], c["host_n"]): c for c in cells}
    if not _same_analysis(keyed, expected):
        raise ConfigurationError("E1 gate cells disagree with the registered seeds or raw analysis.")
    if rec["passed"] is not gated_pass or rec["instrument_failure"] is not instrument_failure:
        raise ConfigurationError("E1 gate record disagrees with the E1 fit recomputed from the raw records.")


def evaluate_jr5_verdict(evidence: Jr5Evidence | Mapping[str, Any]) -> Jr5Verdict:
    """Decide the JR5 typed outcome and the ``red_queen_proved`` flag from raw records."""

    ev = Jr5Evidence.from_dict(evidence.to_dict() if isinstance(evidence, Jr5Evidence) else evidence)
    k = jr5_constants()
    names = dict(zip(("rq", "load", "div", "none", "inconclusive", "fail"), k["typed_outcomes"], strict=True))
    vals = _Values(ev)
    boot = k["e2"]["bootstrap"]
    big, small = (int(n) for n in k["e2"]["host_n"])

    # (a) cost gate from the raw E1 counts; the cap applies to every E1 cell.
    gated_pass, breach, cells = _e1(vals, k)
    cond_a = gated_pass and not breach
    _check_e1_gate_record(ev.e1_gate_record, gated_pass, not cond_a, cells, k)

    # (e) every grid run replays, and every sealed lock replays to its pinned digest.
    max_res = float(k["validity"]["atp_ledger_max_residual"])
    cond_e = all(r.passes_replay(max_res) for r in ev.runs) and all(
        ev.sealed_locks[name] == digest for name, digest in SEALED_LOCK_DIGESTS.items()
    )

    def freq(exp: str, n: int, **levels: Any) -> dict[int, float]:
        return vals.number(exp, n, "terminal_uniparental_frequency", 0.0, 1.0, **levels)

    def e2(arm: str, n: int) -> dict[int, float]:
        return freq("e2", n, mating=_E2_MATING, parasite=arm)

    # (b) Holm over E2: copassaged minus fixed, by host N and virulence.
    e2_contrasts = {
        f"e2_N{n}_{v}": _paired(e2(f"copassaged_{v}", n), e2(f"fixed_{v}", n), boot)
        for n in (big, small)
        for v in ("high", "low")
    }
    calls = _holm_calls(e2_contrasts, k)
    high = [calls[name] for name in _E2_HIGH]
    cond_b = all(c.significant and c.direction < 0 for c in high)
    e2_any = any(c.significant for c in calls.values())

    # (c) copassaged below fixed and below frozen replay, N = 200 high.
    c_alpha = float(k["multiplicity"]["family_alpha"]) / 2.0
    c_level = float(boot["condition_c_ci_level"])
    co_fixed = e2_contrasts[f"e2_N{big}_high"]
    co_frozen = _paired(e2("copassaged_high", big), e2("frozen_replay_high", big), boot)
    c_fixed = _one_sided_lower_call(co_fixed, c_alpha, c_level)
    c_frozen = _one_sided_lower_call(co_frozen, c_alpha, c_level)
    cond_c = all(c.significant and c.direction < 0 for c in (c_fixed, c_frozen))

    # (d) alternatives; the effect side is the observed E2 N200 high sign.
    d = k["condition_d"]
    eq_level, opp_level = float(d["equivalence_ci_level"]), float(d["opposite_sign_ci_level"])
    d_n = int(d["host_n"])
    effect_sign = high[0].direction
    mus = [float(mu) for mu in k["alternative_arms"]["mutation_load"]["host_mutation_grid"]]
    load_diffs: dict[float, _Paired] = {}
    for mu in mus:
        out = vals.number("mutation_load", d_n, "log_terminal_fitness", mutation=mu, mating="obligate_outcross")
        self_ = vals.number("mutation_load", d_n, "log_terminal_fitness", mutation=mu, mating="obligate_self")
        load_diffs[mu] = _paired(out, self_, boot)
    load_at = load_diffs[max(mus)]
    load_out = _ruled_out(load_at, float(d["margin_log_fitness_ratio"]), 1, eq_level, opp_level)
    freq_margin = float(d["margin_frequency"])
    diversity = _paired(e2("frozen_replay_high", d_n), e2("fixed_high", d_n), boot)
    tax = _paired(freq("uniform_tax", d_n, virulence="high"), e2("fixed_high", d_n), boot)
    windows: list[Interval] = []
    window_ok: list[bool] = []
    co_runs = vals.runs("e2", d_n, mating=_E2_MATING, parasite="copassaged_high")
    for name, sign in sorted(E4_WINDOW_SIGNS.items()):
        per_seed = []
        for seed in sorted(co_runs):
            r = co_runs[seed]
            if not _same_analysis(r.data.get("e4_window"), list(E4_WINDOW_GENERATIONS)):
                raise ConfigurationError(f"run {r.run_id}: E4 must use the registered primary window.")
            e4 = _check_keys(r.data.get("e4"), set(E4_WINDOW_SIGNS), f"run {r.run_id} e4")
            per_seed.append(_finite(e4[name], f"run {r.run_id} e4.{name}"))
        iv = _t_interval(per_seed, opp_level)
        windows.append(iv)
        window_ok.append(iv.side(0.0) == sign)
    windows_ok = any(window_ok)
    windows_any_excl = any(iv.side(0.0) != 0 for iv in windows)
    div_out = _ruled_out(diversity, freq_margin, effect_sign, eq_level, opp_level) and windows_ok
    tax_out = _ruled_out(tax, freq_margin, effect_sign, eq_level, opp_level)
    cond_d = load_out and div_out and tax_out

    conditions = {"a": cond_a, "b": cond_b, "c": cond_c, "d": cond_d, "e": cond_e}

    # Typed outcome, in the prereg order (PREREG section 2).
    if not cond_a or not cond_e:
        outcome = names["fail"]
    elif not all(c.agree for c in (*high, c_fixed, c_frozen)):
        outcome = names["inconclusive"]
    elif cond_b and tax_out and c_frozen.significant and c_frozen.direction < 0 and windows_ok:
        outcome = names["rq"]
    elif cond_b and (co_frozen.ci(eq_level).inside(-freq_margin, freq_margin) or not windows_any_excl):
        outcome = names["div"]
    elif not e2_any and _load_trend(load_at, load_diffs, mus, k, opp_level):
        outcome = names["load"]
    else:
        outcome = names["none"]

    proved = all(conditions.values()) and outcome == names["rq"]
    return Jr5Verdict(outcome, proved, conditions, ev.digest(), PREREG_RECORD_DIGEST)


def _load_trend(
    load_at: _Paired, diffs: Mapping[float, _Paired], mus: Sequence[float], k: Mapping[str, Any], level: float
) -> bool:
    """load_consistent: 95% interval above 0 at the top mutation rate and a rising Spearman trend.

    PREREG section 2 fixes the trend test one-sided at 0.05, which is the
    family alpha of the constants; it is read from there.
    """

    xs = [mu for mu in mus for _ in diffs[mu].deltas]
    ys = [v for mu in mus for v in diffs[mu].deltas]
    rho, p = _spearman_greater(xs, ys)
    alpha = float(k["multiplicity"]["family_alpha"])
    return load_at.ci(level).side(0.0) > 0 and rho > 0 and p < alpha


# ---------------------------------------------------------------- claim path


def verify_jr5_verdict(record: Mapping[str, Any], evidence: Jr5Evidence | Mapping[str, Any]) -> Jr5Verdict:
    """Recompute the verdict from ``evidence`` and require ``record`` to equal it."""

    if not isinstance(record, Mapping):
        raise ConfigurationError("JR5 verdict record must be a mapping.")
    fresh = evaluate_jr5_verdict(evidence)
    if dict(record) != fresh.to_dict():
        raise ConfigurationError("JR5 verdict record does not match its evidence.")
    return fresh


def assert_jr5_red_queen_claim_allowed(record: Mapping[str, Any], evidence: Jr5Evidence | Mapping[str, Any]) -> str:
    """Allow ``red_queen_proved`` only for a verified JR5 verdict with (a) to (e) true."""

    verdict = verify_jr5_verdict(record, evidence)
    if not verdict.red_queen_proved:
        failed = [key for key in _CONDITION_KEYS if not verdict.conditions[key]]
        raise ConfigurationError(f"{CLAIM!r} is not supported by the JR5 verdict ({verdict.outcome}; failed {failed}).")
    return CLAIM


def jr5_bundle_fields(evidence: Jr5Evidence | Mapping[str, Any]) -> dict[str, Any]:
    """Project the addressed run set into the only bundle body eligible for the exemption.

    Arm names address their complete per-seed records; vectors and displayed
    comparisons are reconstructed, not supplied summary statistics. Displayed
    intervals are unadjusted 95% paired intervals; the verdict alone applies
    the registered step-down and resampling decisions.
    """
    ev = Jr5Evidence.from_dict(evidence.to_dict() if isinstance(evidence, Jr5Evidence) else evidence)
    k = jr5_constants()
    return _bundle_fields(ev, k)


def _bundle_fields(ev: Jr5Evidence, k: Mapping[str, Any]) -> dict[str, Any]:
    grouped: dict[tuple[str, Cell, int], list[RunRecord]] = {}
    for run in ev.runs:
        grouped.setdefault(run.key[:3], []).append(run)
    arms = []
    names = {}
    vectors: dict[str, list[float]] = {}
    for key in sorted(grouped, key=repr):
        runs = sorted(grouped[key], key=lambda r: r.key[3])
        name = "jr5-arm:" + canonical_digest([r.sha256 for r in runs])
        names[key] = name
        exp, cell, _n = key
        levels = dict(cell)
        role = "channel_off" if exp == "uniform_tax" else "negative_control" if str(levels.get("parasite", "")).startswith("fixed") else "treatment"
        arms.append({"name": name, "role": role, "n": len(runs)})
        if exp == "e2":
            vectors[name] = [_finite(r.data["terminal_uniparental_frequency"], "bundle frequency") for r in runs]
    values = _Values(ev)
    boot = k["e2"]["bootstrap"]
    comparisons = []
    for n in k["e2"]["host_n"]:
        for virulence in ("high", "low"):
            a_cell = _cell(mating=_E2_MATING, parasite=f"copassaged_{virulence}")
            b_cell = _cell(mating=_E2_MATING, parasite=f"fixed_{virulence}")
            a = values.number("e2", n, "terminal_uniparental_frequency", mating=_E2_MATING, parasite=f"copassaged_{virulence}")
            b = values.number("e2", n, "terminal_uniparental_frequency", mating=_E2_MATING, parasite=f"fixed_{virulence}")
            paired = _paired(a, b, boot)
            interval = paired.ci(0.95)
            comparisons.append({"a": names[("e2", a_cell, n)], "b": names[("e2", b_cell, n)],
                                "effect_size": paired.estimate, "ci_low": interval.lo, "ci_high": interval.hi,
                                "p": paired.p_two_sided(), "test": "paired_t_two_sided", "correction": "none"})
    ordered_runs = sorted(ev.runs, key=lambda r: r.run_id)
    return {
        "config_digest": canonical_digest({"prereg": PREREG_RECORD_DIGEST, "runs": [r.sha256 for r in ordered_runs]}),
        "seeds": list(ev.seeds()), "preregistration_digest": PREREG_RECORD_DIGEST,
        "arms": arms, "outcomes": [{"metric": "terminal_uniparental_frequency", "values_by_arm": vectors}],
        "comparisons": comparisons,
        "replay": {"verified": all(r.passes_replay(float(k["validity"]["atp_ledger_max_residual"])) for r in ev.runs),
                   "digests": [r.replay["replayed_digest"] for r in ordered_runs]},
        "artifacts": [{"path": "jr5_evidence.json", "sha256": ev.digest().split(":", 1)[1]}]
                     + [{"path": f"jr5/runs/{r.run_id}.json", "sha256": r.sha256} for r in ordered_runs],
    }


def red_queen_exemption_holds(bundle: Any) -> bool:
    """The auditor rechecks the verdict and the complete run-addressed bundle projection."""
    extra = getattr(bundle, "extra", None) or {}
    record, evidence = extra.get("jr5_verdict"), extra.get("jr5_evidence")
    if not isinstance(record, Mapping) or not isinstance(evidence, Mapping):
        return False
    try:
        ev = Jr5Evidence.from_dict(evidence)
        assert_jr5_red_queen_claim_allowed(record, ev)
        expected = _bundle_fields(ev, jr5_constants())
        actual = bundle.to_dict()
        return all(actual.get(key) == value for key, value in expected.items())
    except (ConfigurationError, KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError):
        return False


# Register public digest fields from this layer, without an engine dependency
# on any campaign-specific class name. Replay body hashes are checked within
# each addressed run envelope rather than separate summary dataclasses.
def _register_digest_contracts() -> None:
    from codontrace.genesis.replay_integrity import register_noncritical_digest_class

    for cls in (Jr5Evidence, Jr5Verdict):
        register_noncritical_digest_class(cls)


_register_digest_contracts()
