"""E3 task-switch cost knob for HARD_EXPERIMENT_03 (Goldsby et al. 2012 PNAS).

Default-off. When enabled, consecutive switches between dual-resource tasks A/B
incur ``switch_cost_atp`` (Goldsby 0 / ~25 / ~50 cycle analogues mapped to ATP).

Pins A–E unchanged when disabled. Claim ceiling stays runtime_observation until
ClaimGate grants more. Not a collective-intelligence claim.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float

TASK_A = "TASK_A"
TASK_B = "TASK_B"

# Goldsby 2012 CPU-cycle delay analogues → ATP (1 ATP ≈ 100 cycles).
SWITCH_COST_ATP_COST_0 = 0.0
SWITCH_COST_ATP_MODERATE = 0.25  # ≈ 25-cycle analogue
SWITCH_COST_ATP_HIGH = 0.50  # ≈ 50-cycle analogue
GOLDSBY_CYCLE_ANALOGUE_PER_ATP = 100.0

DEFAULT_TASK_A_ACTIONS: tuple[str, ...] = (
    "EAT_LUMEN",
    "COLLECT_FOOD",
    "COLLECT_RESOURCE",
    "COLLECT_RESOURCE_OBJECT",
    "SENSE_FOOD",
    "SENSE_RESOURCE",
)
DEFAULT_TASK_B_ACTIONS: tuple[str, ...] = (
    "EMIT_NEXUS",
    "DEPOSIT_RESOURCE",
    "CRAFT_ITEM",
    "CRAFT_TOOL",
    "RETURN_HOME",
    "RETURN_TO_TARGET",
)


@dataclass(frozen=True, slots=True)
class TaskSwitchCostConfig:
    """Opt-in Goldsby-style task-switch ATP cost (HE03 E3)."""

    enabled: bool = False
    switch_cost_atp: float = SWITCH_COST_ATP_COST_0
    task_a_actions: tuple[str, ...] = DEFAULT_TASK_A_ACTIONS
    task_b_actions: tuple[str, ...] = DEFAULT_TASK_B_ACTIONS

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "switch_cost_atp",
            require_finite_float("switch_cost_atp", self.switch_cost_atp, non_negative=True),
        )
        if not self.task_a_actions:
            raise ConfigurationError("task_a_actions must be non-empty.")
        if not self.task_b_actions:
            raise ConfigurationError("task_b_actions must be non-empty.")
        overlap = set(self.task_a_actions) & set(self.task_b_actions)
        if overlap:
            raise ConfigurationError(
                f"task_a_actions and task_b_actions overlap: {sorted(overlap)}"
            )
        object.__setattr__(self, "task_a_actions", tuple(str(item) for item in self.task_a_actions))
        object.__setattr__(self, "task_b_actions", tuple(str(item) for item in self.task_b_actions))

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize; callers omit this key when disabled (digest stability)."""

        return {
            "enabled": self.enabled,
            "switch_cost_atp": self.switch_cost_atp,
            "task_a_actions": list(self.task_a_actions),
            "task_b_actions": list(self.task_b_actions),
            "goldsby_cycle_analogue": round(
                self.switch_cost_atp * GOLDSBY_CYCLE_ANALOGUE_PER_ATP, 10
            ),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> TaskSwitchCostConfig:
        raw_a = data.get("task_a_actions", list(DEFAULT_TASK_A_ACTIONS))
        raw_b = data.get("task_b_actions", list(DEFAULT_TASK_B_ACTIONS))
        if not isinstance(raw_a, (list, tuple)) or not isinstance(raw_b, (list, tuple)):
            raise ConfigurationError("task_a_actions/task_b_actions must be sequences.")
        return cls(
            enabled=bool(data.get("enabled", False)),
            switch_cost_atp=float(data.get("switch_cost_atp", SWITCH_COST_ATP_COST_0)),
            task_a_actions=tuple(str(item) for item in raw_a),
            task_b_actions=tuple(str(item) for item in raw_b),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def classify_task(self, action: str) -> str | None:
        name = str(action)
        if name in self.task_a_actions:
            return TASK_A
        if name in self.task_b_actions:
            return TASK_B
        return None


@dataclass(frozen=True, slots=True)
class TaskSwitchCostRecord:
    """Digest-backed observation of one task switch (and optional ATP debit)."""

    tick: int
    organism_id: str
    from_task: str
    to_task: str
    action: str
    switch_cost_atp: float
    charged: bool
    runtime_atp_after: float

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "organism_id": self.organism_id,
            "from_task": self.from_task,
            "to_task": self.to_task,
            "action": self.action,
            "switch_cost_atp": self.switch_cost_atp,
            "charged": self.charged,
            "runtime_atp_after": self.runtime_atp_after,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> TaskSwitchCostRecord:
        return cls(
            tick=int(data.get("tick", 0)),
            organism_id=str(data.get("organism_id", "")),
            from_task=str(data.get("from_task", "")),
            to_task=str(data.get("to_task", "")),
            action=str(data.get("action", "")),
            switch_cost_atp=float(data.get("switch_cost_atp", 0.0)),
            charged=bool(data.get("charged", False)),
            runtime_atp_after=float(data.get("runtime_atp_after", 0.0)),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def apply_task_switch_cost(
    *,
    tick: int,
    organism_id: str,
    action: str,
    previous_task: str | None,
    config: TaskSwitchCostConfig,
    atp_state: object,
) -> tuple[str | None, TaskSwitchCostRecord | None]:
    """Classify action; if a switch occurs under an enabled config, debit ATP.

    Returns ``(current_task_or_None, record_or_None)``. When the knob is off,
    returns ``(None, None)`` without mutating ATP (pin stability).
    """

    if not config.enabled:
        return None, None
    current = config.classify_task(action)
    if current is None:
        return previous_task, None
    if previous_task is None or previous_task == current:
        return current, None
    cost = float(config.switch_cost_atp)
    charged = False
    if cost > 0.0:
        debit = getattr(atp_state, "debit_runtime", None)
        if callable(debit):
            ledger_id = debit(
                cost,
                tick=int(tick),
                organism_id=str(organism_id),
                codon="he03",
                action=str(action),
                reason="task_switch_cost",
            )
            charged = ledger_id is not None
    runtime_after = float(getattr(atp_state, "runtime_available", 0.0) or 0.0)
    record = TaskSwitchCostRecord(
        tick=int(tick),
        organism_id=str(organism_id),
        from_task=str(previous_task),
        to_task=str(current),
        action=str(action),
        switch_cost_atp=cost,
        charged=charged if cost > 0.0 else True,  # cost_0 arm: switch observed, 0 ATP
        runtime_atp_after=runtime_after,
    )
    return current, record


def collect_individual_task_samples(
    records: Sequence[TaskSwitchCostRecord],
    *,
    activity: Sequence[tuple[str, str]] = (),
) -> tuple[tuple[str, str], ...]:
    """Build (individual, task) samples for Gorelick NMI.

    Prefers explicit activity samples; falls back to switch endpoints.
    """

    if activity:
        return tuple((str(i), str(t)) for i, t in activity)
    samples: list[tuple[str, str]] = []
    for item in records:
        samples.append((item.organism_id, item.from_task))
        samples.append((item.organism_id, item.to_task))
    return tuple(samples)


def update_task_activity(
    activity: MutableMapping[tuple[str, str], int],
    *,
    organism_id: str,
    task: str | None,
) -> None:
    if task is None:
        return
    key = (str(organism_id), str(task))
    activity[key] = int(activity.get(key, 0)) + 1
