"""INN-04 — Phylodynamics-inspired skyline Ne proxy from HookMeter windows.

Piecewise effective-size proxy from birth/death/attach tallies. Shape
inspired by MASCOT-Skyline Ne series — no MCMC, no epidemic forecast claim.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float

SCHEMA_VERSION = "life_loop_skyline_proxy_v1"


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


def _nonneg(value: object, name: str) -> float:
    number = float(require_finite_float(name, value))
    if number < 0.0:
        raise ConfigurationError(f"{name} must be >= 0.")
    return number


@dataclass(frozen=True, slots=True)
class SkylineWindow:
    """One piecewise window of meter tallies → Ne proxy."""

    window_id: str
    tick_start: int
    tick_end: int
    birth_count: float
    death_count: float
    attach_occupancy: float
    ne_proxy: float
    digest: str = ""

    def __post_init__(self) -> None:
        wid = _refuse_banned_fragment(_as_str(self.window_id, "window_id"), "window_id")
        object.__setattr__(self, "window_id", wid)
        ts = _as_int(self.tick_start, "tick_start", minimum=0)
        te = _as_int(self.tick_end, "tick_end", minimum=0)
        if te < ts:
            raise ConfigurationError("tick_end must be >= tick_start.")
        object.__setattr__(self, "tick_start", ts)
        object.__setattr__(self, "tick_end", te)
        object.__setattr__(self, "birth_count", _nonneg(self.birth_count, "birth_count"))
        object.__setattr__(self, "death_count", _nonneg(self.death_count, "death_count"))
        object.__setattr__(
            self, "attach_occupancy", _nonneg(self.attach_occupancy, "attach_occupancy")
        )
        object.__setattr__(self, "ne_proxy", _nonneg(self.ne_proxy, "ne_proxy"))
        computed = canonical_digest(self._body(), prefix="sky_win")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "SkylineWindow")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "window_id": self.window_id,
            "tick_start": self.tick_start,
            "tick_end": self.tick_end,
            "birth_count": self.birth_count,
            "death_count": self.death_count,
            "attach_occupancy": self.attach_occupancy,
            "ne_proxy": self.ne_proxy,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class SkylineSeries:
    """Digest-stable piecewise Ne proxy series."""

    series_id: str
    windows: tuple[SkylineWindow, ...]
    claim_ceiling: str = "runtime_observation"
    epidemic_forecast_certified: bool = False
    red_queen_proved: bool = False
    digest: str = ""

    def __post_init__(self) -> None:
        sid = _refuse_banned_fragment(_as_str(self.series_id, "series_id"), "series_id")
        object.__setattr__(self, "series_id", sid)
        if not self.windows:
            raise ConfigurationError("windows must be non-empty.")
        object.__setattr__(self, "windows", tuple(self.windows))
        ceiling = _as_str(self.claim_ceiling, "claim_ceiling").casefold()
        if ceiling not in {"runtime_observation", "candidate_evidence"}:
            raise ConfigurationError(
                "claim_ceiling must be runtime_observation or candidate_evidence."
            )
        object.__setattr__(self, "claim_ceiling", ceiling)
        if self.epidemic_forecast_certified:
            raise ConfigurationError("refuses epidemic_forecast_certified=True.")
        if self.red_queen_proved:
            raise ConfigurationError("refuses red_queen_proved=True.")
        object.__setattr__(self, "epidemic_forecast_certified", False)
        object.__setattr__(self, "red_queen_proved", False)
        computed = canonical_digest(self._body(), prefix="sky_ser")
        object.__setattr__(
            self, "digest", _check_digest(self.digest, computed, "SkylineSeries")
        )

    def _body(self) -> dict[str, JsonValue]:
        return {
            "schema_version": SCHEMA_VERSION,
            "series_id": self.series_id,
            "windows": [w.to_dict() for w in self.windows],
            "claim_ceiling": self.claim_ceiling,
            "epidemic_forecast_certified": False,
            "red_queen_proved": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._body(), "digest": self.digest}


def _ne_from_tallies(birth: float, death: float, attach: float) -> float:
    """Simple refuse-safe proxy: surviving mass + attach occupancy.

    ne = max(0, birth - death) + attach; avoids division-by-zero coalescent formulas.
    """

    return max(0.0, birth - death) + max(0.0, attach)


def skyline_ne_proxy(
    windows: Sequence[Mapping[str, object]],
    *,
    series_id: str,
    claim_ceiling: str = "runtime_observation",
) -> SkylineSeries:
    """Build SkylineSeries from raw window mappings.

    Each window mapping requires:
      window_id, tick_start, tick_end, birth_count, death_count, attach_occupancy
    """

    built: list[SkylineWindow] = []
    for raw in windows:
        if not isinstance(raw, Mapping):
            raise ConfigurationError("each window must be a mapping.")
        birth = _nonneg(raw.get("birth_count", 0.0), "birth_count")
        death = _nonneg(raw.get("death_count", 0.0), "death_count")
        attach = _nonneg(raw.get("attach_occupancy", 0.0), "attach_occupancy")
        built.append(
            SkylineWindow(
                window_id=_as_str(raw.get("window_id"), "window_id"),
                tick_start=_as_int(raw.get("tick_start"), "tick_start", minimum=0),
                tick_end=_as_int(raw.get("tick_end"), "tick_end", minimum=0),
                birth_count=birth,
                death_count=death,
                attach_occupancy=attach,
                ne_proxy=_ne_from_tallies(birth, death, attach),
            )
        )
    return SkylineSeries(
        series_id=series_id,
        windows=tuple(built),
        claim_ceiling=claim_ceiling,
    )
