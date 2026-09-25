"""INN-11 — Granger-lite / transfer-entropy-lite on HookMeter series.

Lag-1 predictive MSE reduction (Granger-lite) and coarse-binned TE proxy.
Observation / predictive association only — never causality_proved.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float

SCHEMA_VERSION = "life_loop_transfer_entropy_v1"


def _as_str(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string.")
    text = value.strip()
    if not text and not allow_empty:
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return text


def _as_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer.")
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}.")
    return value


def _refuse_banned_fragment(text: str, name: str) -> str:
    lowered = text.casefold()
    for token in BANNED_DOMAIN_TOKENS:
        if token.casefold() in lowered:
            raise ConfigurationError(f"{name} contains a banned fragment.")
    return text


def _check_digest(existing: str, computed: str, label: str) -> str:
    if existing and existing != computed:
        raise ConfigurationError(f"{label} digest mismatch.")
    return computed


def _series(values: Sequence[float], name: str) -> tuple[float, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ConfigurationError(f"{name} must be a sequence of floats.")
    out = [float(require_finite_float(f"{name}[{i}]", v)) for i, v in enumerate(values)]
    if len(out) < 3:
        raise ConfigurationError(f"{name} must have length >= 3.")
    return tuple(out)


def _mse(pred: Sequence[float], actual: Sequence[float]) -> float:
    n = len(actual)
    if n == 0:
        return 0.0
    return sum((p - a) ** 2 for p, a in zip(pred, actual, strict=True)) / n


def granger_lite_score(x: Sequence[float], y: Sequence[float]) -> float:
    """Lag-1 MSE reduction: 1 - MSE(Y|Y_lag,X_lag)/MSE(Y|Y_lag), clipped to [0,1]."""

    xs, ys = _series(x, "x"), _series(y, "y")
    if len(xs) != len(ys):
        raise ConfigurationError("x and y must have equal length.")
    # restricted: Y_t ~ Y_{t-1}
    pred_r = list(ys[:-1])
    actual = list(ys[1:])
    mse_r = _mse(pred_r, actual)
    # unrestricted: Y_t ~ 0.5*Y_{t-1} + 0.5*X_{t-1}
    pred_u = [0.5 * ys[i] + 0.5 * xs[i] for i in range(len(ys) - 1)]
    mse_u = _mse(pred_u, actual)
    if mse_r <= 1e-15:
        return 0.0
    reduction = 1.0 - (mse_u / mse_r)
    if reduction < 0.0:
        return 0.0
    if reduction > 1.0:
        return 1.0
    return float(reduction)


def _bin_values(values: Sequence[float], n_bins: int) -> tuple[int, ...]:
    vmin, vmax = min(values), max(values)
    if vmax <= vmin:
        return tuple(0 for _ in values)
    span = vmax - vmin
    out: list[int] = []
    for v in values:
        b = int((v - vmin) / span * n_bins)
        if b >= n_bins:
            b = n_bins - 1
        if b < 0:
            b = 0
        out.append(b)
    return tuple(out)


def transfer_entropy_lite(
    x: Sequence[float], y: Sequence[float], *, n_bins: int = 3
) -> float:
    """Coarse discrete TE proxy: I(Y_t; X_{t-1} | Y_{t-1}) via plug-in counts."""

    xs, ys = _series(x, "x"), _series(y, "y")
    if len(xs) != len(ys):
        raise ConfigurationError("x and y must have equal length.")
    bins = _as_int(n_bins, "n_bins", minimum=2)
    xb = _bin_values(xs, bins)
    yb = _bin_values(ys, bins)
    # triples (y_t, y_{t-1}, x_{t-1})
    counts: dict[tuple[int, int, int], int] = {}
    for t in range(1, len(ys)):
        key = (yb[t], yb[t - 1], xb[t - 1])
        counts[key] = counts.get(key, 0) + 1
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    # marginals
    cy: dict[int, int] = {}
    cyy: dict[tuple[int, int], int] = {}
    cyx: dict[tuple[int, int], int] = {}
    cyyx = counts
    for (yt, ytm, xtm), c in counts.items():
        cy[yt] = cy.get(yt, 0) + c
        cyy[(yt, ytm)] = cyy.get((yt, ytm), 0) + c
        cyx[(ytm, xtm)] = cyx.get((ytm, xtm), 0) + c
    # also need p(y_{t-1})
    c_ytm: dict[int, int] = {}
    for (_yt, ytm, _xtm), c in counts.items():
        c_ytm[ytm] = c_ytm.get(ytm, 0) + c
    te = 0.0
    for (yt, ytm, xtm), c in cyyx.items():
        p_yyx = c / total
        p_yt_ytm = cyy[(yt, ytm)] / total
        p_ytm_xtm = cyx[(ytm, xtm)] / total
        p_ytm = c_ytm[ytm] / total
        # p(yt | ytm, xtm) / p(yt | ytm)
        # = p(yt,ytm,xtm)/p(ytm,xtm)  divided by  p(yt,ytm)/p(ytm)
        if p_ytm_xtm <= 0.0 or p_yt_ytm <= 0.0 or p_ytm <= 0.0:
            continue
        p_cond_full = p_yyx / p_ytm_xtm
        p_cond_rest = p_yt_ytm / p_ytm
        if p_cond_full <= 0.0 or p_cond_rest <= 0.0:
            continue
        te += p_yyx * math.log(p_cond_full / p_cond_rest)
    return max(0.0, float(te))


@dataclass(frozen=True, slots=True)
class TransferEntropyResult:
    """Digest-stable Granger/TE-lite contrast between two meter series."""

    result_id: str
    source_key: str
    target_key: str
    granger_lite: float
    transfer_entropy_lite: float
    n_ticks: int
    claim_ceiling: str = "runtime_observation"
    causality_proved: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        rid = _refuse_banned_fragment(_as_str(self.result_id, "result_id"), "result_id")
        object.__setattr__(self, "result_id", rid)
        object.__setattr__(
            self,
            "source_key",
            _refuse_banned_fragment(_as_str(self.source_key, "source_key"), "source_key"),
        )
        object.__setattr__(
            self,
            "target_key",
            _refuse_banned_fragment(_as_str(self.target_key, "target_key"), "target_key"),
        )
        object.__setattr__(
            self,
            "granger_lite",
            float(require_finite_float("granger_lite", self.granger_lite)),
        )
        object.__setattr__(
            self,
            "transfer_entropy_lite",
            float(
                require_finite_float("transfer_entropy_lite", self.transfer_entropy_lite)
            ),
        )
        if self.granger_lite < 0.0 or self.granger_lite > 1.0:
            raise ConfigurationError("granger_lite must be in [0, 1].")
        if self.transfer_entropy_lite < 0.0:
            raise ConfigurationError("transfer_entropy_lite must be >= 0.")
        object.__setattr__(self, "n_ticks", _as_int(self.n_ticks, "n_ticks", minimum=0))
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        if self.causality_proved:
            raise ConfigurationError("refuses causality_proved=True.")
        object.__setattr__(self, "causality_proved", False)
        computed = canonical_digest(self._body(), prefix="te_lite")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "TransferEntropyResult")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "source_key": self.source_key,
            "target_key": self.target_key,
            "granger_lite": self.granger_lite,
            "transfer_entropy_lite": self.transfer_entropy_lite,
            "n_ticks": self.n_ticks,
            "claim_ceiling": self.claim_ceiling,
            "causality_proved": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def hook_meter_transfer_entropy(
    source_series: Sequence[float],
    target_series: Sequence[float],
    *,
    result_id: str,
    source_key: str = "match_pass",
    target_key: str = "coupling_total",
    n_bins: int = 3,
    claim_ceiling: str = "runtime_observation",
) -> TransferEntropyResult:
    """Compute Granger-lite + TE-lite between two HookMeter-derived series."""

    g = granger_lite_score(source_series, target_series)
    te = transfer_entropy_lite(source_series, target_series, n_bins=n_bins)
    return TransferEntropyResult(
        result_id=result_id,
        source_key=source_key,
        target_key=target_key,
        granger_lite=g,
        transfer_entropy_lite=te,
        n_ticks=len(tuple(source_series)),
        claim_ceiling=claim_ceiling,
    )
