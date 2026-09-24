"""INN-12 — Split conformal risk bands with selective abstention.

Refuse-safe uncertainty intervals around point predictions using calibration
residuals. Selective abstain when interval width exceeds a budget (SCRC-lite).
Never coverage_guaranteed_proved — finite-sample exchangeability is a label.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float

SCHEMA_VERSION = "life_loop_conformal_bands_v1"


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


def _unit_interval(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0 or number > 1.0:
        raise ConfigurationError(f"{name} must be in [0, 1].")
    return number


def _quantile(sorted_vals: Sequence[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    if q <= 0.0:
        return float(sorted_vals[0])
    if q >= 1.0:
        return float(sorted_vals[-1])
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return float(sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac)


@dataclass(frozen=True, slots=True)
class ConformalBandResult:
    """Digest-stable conformal interval with optional abstention."""

    result_id: str
    point_prediction: float
    lower: float
    upper: float
    width: float
    alpha: float
    abstained: bool
    n_calibration: int
    claim_ceiling: str = "runtime_observation"
    coverage_guaranteed_proved: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        rid = _refuse_banned_fragment(_as_str(self.result_id, "result_id"), "result_id")
        object.__setattr__(self, "result_id", rid)
        for name in ("point_prediction", "lower", "upper", "width"):
            object.__setattr__(
                self, name, float(require_finite_float(name, getattr(self, name)))
            )
        if self.lower > self.upper:
            raise ConfigurationError("lower must be <= upper.")
        if abs(self.width - (self.upper - self.lower)) > 1e-9:
            raise ConfigurationError("width must equal upper - lower.")
        object.__setattr__(self, "alpha", _unit_interval(self.alpha, "alpha"))
        if not isinstance(self.abstained, bool):
            raise ConfigurationError("abstained must be a bool.")
        object.__setattr__(
            self, "n_calibration", _as_int(self.n_calibration, "n_calibration", minimum=0)
        )
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        if self.coverage_guaranteed_proved:
            raise ConfigurationError("refuses coverage_guaranteed_proved=True.")
        object.__setattr__(self, "coverage_guaranteed_proved", False)
        computed = canonical_digest(self._body(), prefix="conf_band")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "ConformalBandResult")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "result_id": self.result_id,
            "point_prediction": self.point_prediction,
            "lower": self.lower,
            "upper": self.upper,
            "width": self.width,
            "alpha": self.alpha,
            "abstained": self.abstained,
            "n_calibration": self.n_calibration,
            "claim_ceiling": self.claim_ceiling,
            "coverage_guaranteed_proved": False,
            "exchangeability_label": "finite_sample_assumption",
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def conformal_risk_band(
    *,
    result_id: str,
    point_prediction: float,
    calibration_residuals: Sequence[float],
    alpha: float = 0.1,
    max_width: float | None = None,
    claim_ceiling: str = "runtime_observation",
) -> ConformalBandResult:
    """Split conformal absolute-residual band; abstain if width > max_width."""

    pred = float(require_finite_float("point_prediction", point_prediction))
    a = _unit_interval(alpha, "alpha")
    if not isinstance(calibration_residuals, Sequence) or isinstance(
        calibration_residuals, (str, bytes)
    ):
        raise ConfigurationError("calibration_residuals must be a sequence.")
    res = sorted(
        abs(float(require_finite_float(f"residual[{i}]", r)))
        for i, r in enumerate(calibration_residuals)
    )
    n = len(res)
    if n == 0:
        raise ConfigurationError("calibration_residuals must be non-empty.")
    # standard split-conformal quantile level
    q_level = min(1.0, (1.0 - a) * (1.0 + 1.0 / n))
    q = _quantile(res, q_level)
    lower = pred - q
    upper = pred + q
    width = upper - lower
    abstain = False
    if max_width is not None:
        mw = float(require_finite_float("max_width", max_width))
        if mw < 0.0:
            raise ConfigurationError("max_width must be >= 0.")
        if width > mw:
            abstain = True
    return ConformalBandResult(
        result_id=result_id,
        point_prediction=pred,
        lower=lower,
        upper=upper,
        width=width,
        alpha=a,
        abstained=abstain,
        n_calibration=n,
        claim_ceiling=claim_ceiling,
    )
