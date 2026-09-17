"""E1 food-patch signal knob for HARD_EXPERIMENT_02 (Floreano 2007).

Default-off. When enabled, hidden food patches give selective value to
capsule payloads that encode patch coordinates, and receivers can execute
``MOVE_TOWARD_CAPSULE_TARGET``. Mutual information between payload and true
patch location is the manipulation check (≈0 under capsules_shuffled).

Claim ceiling remains runtime_observation until ClaimGate grants more.
Pins A–E are unchanged when this knob is disabled.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import log2
from typing import Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float

MOVE_TOWARD_CAPSULE_TARGET = "MOVE_TOWARD_CAPSULE_TARGET"
_PAYLOAD_PREFIX = "PATCH"


def encode_patch_payload(x: int, y: int) -> str:
    """Encode integer patch coordinates into a capsule payload token."""

    return f"{_PAYLOAD_PREFIX}:{int(x)}:{int(y)}"


def decode_patch_payload(payload: str | None) -> tuple[int, int] | None:
    """Decode a patch payload token; return None when malformed."""

    if payload is None:
        return None
    text = str(payload)
    if not text.startswith(f"{_PAYLOAD_PREFIX}:"):
        return None
    parts = text.split(":")
    if len(parts) != 3:
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class FoodPatchSignalConfig:
    """Opt-in food-location signalling substrate (Floreano-style)."""

    enabled: bool = False
    patch_spawn_period_ticks: int = 8
    patch_lifetime_ticks: int = 16
    visibility_radius: int = 1
    patch_atp: float = 2.0
    patch_count: int = 1

    def __post_init__(self) -> None:
        if self.patch_spawn_period_ticks <= 0:
            raise ConfigurationError("patch_spawn_period_ticks must be > 0.")
        if self.patch_lifetime_ticks <= 0:
            raise ConfigurationError("patch_lifetime_ticks must be > 0.")
        if self.visibility_radius < 0:
            raise ConfigurationError("visibility_radius must be >= 0.")
        if self.patch_count <= 0:
            raise ConfigurationError("patch_count must be > 0.")
        object.__setattr__(
            self,
            "patch_atp",
            require_finite_float("patch_atp", self.patch_atp, non_negative=True),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize; callers omit this key when disabled (digest stability)."""

        return {
            "enabled": self.enabled,
            "patch_spawn_period_ticks": self.patch_spawn_period_ticks,
            "patch_lifetime_ticks": self.patch_lifetime_ticks,
            "visibility_radius": self.visibility_radius,
            "patch_atp": self.patch_atp,
            "patch_count": self.patch_count,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> FoodPatchSignalConfig:
        return cls(
            enabled=bool(data.get("enabled", False)),
            patch_spawn_period_ticks=int(data.get("patch_spawn_period_ticks", 8)),
            patch_lifetime_ticks=int(data.get("patch_lifetime_ticks", 16)),
            visibility_radius=int(data.get("visibility_radius", 1)),
            patch_atp=float(data.get("patch_atp", 2.0)),
            patch_count=int(data.get("patch_count", 1)),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FoodPatchState:
    """One active food patch in world coordinates."""

    patch_id: str
    x: int
    y: int
    spawn_tick: int
    expire_tick: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "patch_id": self.patch_id,
            "x": self.x,
            "y": self.y,
            "spawn_tick": self.spawn_tick,
            "expire_tick": self.expire_tick,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> FoodPatchState:
        return cls(
            patch_id=str(data.get("patch_id", "")),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            spawn_tick=int(data.get("spawn_tick", 0)),
            expire_tick=int(data.get("expire_tick", 0)),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FoodPatchSignalRecord:
    """Digest-backed observation for one emit/adopt/move/eat event."""

    tick: int
    emitter_id: str
    receiver_id: str
    payload_digest: str
    target_true: tuple[int, int]
    moved: bool
    ate_at_target: bool
    payload_token: str = ""

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "emitter_id": self.emitter_id,
            "receiver_id": self.receiver_id,
            "payload_digest": self.payload_digest,
            "target_true": [self.target_true[0], self.target_true[1]],
            "moved": self.moved,
            "ate_at_target": self.ate_at_target,
            "payload_token": self.payload_token,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def patch_visible_to(
    organism_position: tuple[int, int],
    patch: FoodPatchState,
    *,
    visibility_radius: int,
) -> bool:
    dx = abs(int(organism_position[0]) - int(patch.x))
    dy = abs(int(organism_position[1]) - int(patch.y))
    return max(dx, dy) <= int(visibility_radius)


def discrete_mutual_information(
    pairs: Sequence[tuple[str, str]],
) -> float:
    """Plugin MI estimate I(X;Y) over discrete string pairs (bits).

    Returns 0.0 when undefined (empty or single-outcome). Stdlib only.
    """

    if not pairs:
        return 0.0
    n = float(len(pairs))
    joint: dict[tuple[str, str], int] = {}
    mx: dict[str, int] = {}
    my: dict[str, int] = {}
    for x, y in pairs:
        joint[(x, y)] = joint.get((x, y), 0) + 1
        mx[x] = mx.get(x, 0) + 1
        my[y] = my.get(y, 0) + 1
    if len(mx) <= 1 or len(my) <= 1:
        return 0.0
    mi = 0.0
    for (x, y), count in joint.items():
        pxy = count / n
        px = mx[x] / n
        py = my[y] / n
        mi += pxy * log2(pxy / (px * py))
    return round(mi, 10)


def payload_patch_mutual_information(
    records: Sequence[FoodPatchSignalRecord],
) -> float:
    """I(payload_token; true_patch) over HE02 signal records."""

    pairs = [
        (item.payload_token or item.payload_digest, f"{item.target_true[0]}:{item.target_true[1]}")
        for item in records
    ]
    return discrete_mutual_information(pairs)


def spawn_patches_for_tick(
    *,
    tick: int,
    width: int,
    height: int,
    config: FoodPatchSignalConfig,
    rng_draw: Sequence[float],
    active: Sequence[FoodPatchState] = (),
) -> tuple[FoodPatchState, ...]:
    """Deterministic patch spawn/expiry. ``rng_draw`` supplies [0,1) floats."""

    if not config.enabled:
        return ()
    surviving = tuple(
        item for item in active if int(tick) < int(item.expire_tick)
    )
    if tick % config.patch_spawn_period_ticks != 0:
        return surviving
    if width <= 0 or height <= 0:
        raise ConfigurationError("world width/height must be > 0 for food patches.")
    draws = list(rng_draw)
    needed = config.patch_count * 2
    if len(draws) < needed:
        raise ConfigurationError(
            f"food patch spawn requires {needed} rng draws; got {len(draws)}."
        )
    spawned: list[FoodPatchState] = []
    for index in range(config.patch_count):
        x = int(draws[index * 2] * width) % width
        y = int(draws[index * 2 + 1] * height) % height
        spawned.append(
            FoodPatchState(
                patch_id=f"patch-{tick}-{index}-{x}-{y}",
                x=x,
                y=y,
                spawn_tick=int(tick),
                expire_tick=int(tick) + int(config.patch_lifetime_ticks),
            )
        )
    return surviving + tuple(spawned)


SelectionCell = Literal[
    "GERMLINE_CLONAL",
    "GERMLINE_MIXED",
    "INDIVIDUAL_CLONAL",
    "INDIVIDUAL_MIXED",
]
