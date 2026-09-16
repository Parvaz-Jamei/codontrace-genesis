"""E5 stepping-stone reward knob for HARD_EXPERIMENT_02 (Lenski 2003).

Default-off intermediate rewards for emit-correct → move-to-target →
eat-at-target. Does not invent claims; records only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float

DEFAULT_COMPONENT_REWARDS: tuple[float, ...] = (0.25, 0.5, 1.0)
COMPONENT_NAMES: tuple[str, ...] = (
    "emit_correct_patch",
    "move_toward_target",
    "eat_at_target",
)


@dataclass(frozen=True, slots=True)
class SteppingStoneRewardConfig:
    """Opt-in intermediate rewards for HE02 collective task components."""

    enabled: bool = False
    component_rewards: tuple[float, ...] = DEFAULT_COMPONENT_REWARDS

    def __post_init__(self) -> None:
        if len(self.component_rewards) != 3:
            raise ConfigurationError(
                "SteppingStoneRewardConfig.component_rewards must have length 3 "
                "(emit, move, eat)."
            )
        cleaned = tuple(
            require_finite_float(f"component_rewards[{index}]", value, non_negative=True)
            for index, value in enumerate(self.component_rewards)
        )
        object.__setattr__(self, "component_rewards", cleaned)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "component_rewards": list(self.component_rewards),
            "component_names": list(COMPONENT_NAMES),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> SteppingStoneRewardConfig:
        raw = data.get("component_rewards", list(DEFAULT_COMPONENT_REWARDS))
        if not isinstance(raw, (list, tuple)):
            raise ConfigurationError("component_rewards must be a sequence of floats.")
        return cls(
            enabled=bool(data.get("enabled", False)),
            component_rewards=tuple(float(item) for item in raw),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def reward_for(self, component: str) -> float:
        if not self.enabled:
            return 0.0
        try:
            index = COMPONENT_NAMES.index(component)
        except ValueError as exc:
            raise ConfigurationError(f"unknown stepping-stone component: {component!r}") from exc
        return float(self.component_rewards[index])


@dataclass(frozen=True, slots=True)
class SteppingStoneRewardRecord:
    """Digest-backed intermediate reward event."""

    tick: int
    organism_id: str
    component: str
    reward_atp: float
    cumulative_components: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "organism_id": self.organism_id,
            "component": self.component,
            "reward_atp": self.reward_atp,
            "cumulative_components": list(self.cumulative_components),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def apply_stepping_stone_rewards(
    *,
    tick: int,
    organism_id: str,
    achieved: Sequence[str],
    previously_achieved: Sequence[str],
    config: SteppingStoneRewardConfig,
) -> tuple[SteppingStoneRewardRecord, ...]:
    """Emit records (and implied ATP amounts) for newly achieved components."""

    if not config.enabled:
        return ()
    prior = set(previously_achieved)
    records: list[SteppingStoneRewardRecord] = []
    cumulative = list(previously_achieved)
    for component in COMPONENT_NAMES:
        if component in achieved and component not in prior:
            reward = config.reward_for(component)
            cumulative.append(component)
            records.append(
                SteppingStoneRewardRecord(
                    tick=int(tick),
                    organism_id=str(organism_id),
                    component=component,
                    reward_atp=reward,
                    cumulative_components=tuple(cumulative),
                )
            )
    return tuple(records)
