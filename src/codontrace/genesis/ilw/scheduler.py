"""ILW tick scheduler bound to a single run_id (ILW-1).

Advances discrete ticks under one WorldSpec / run_id. Does not execute the
full eco-evolutionary chain (that is ILW-2+).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from codontrace.errors import ConfigurationError
from codontrace.genesis.ilw.seed_namespace import SeedNamespace
from codontrace.genesis.ilw.world_spec import WorldSpec


class IlwSchedulerError(ConfigurationError):
    """Raised when the ILW scheduler is used incorrectly."""


@dataclass(slots=True)
class IlwScheduler:
    """Sequential tick scheduler locked to one ``run_id``."""

    run_id: str
    world_spec: WorldSpec
    seed_namespace: SeedNamespace
    tick: int = 0
    _advanced_ticks: list[int] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        rid = str(self.run_id).strip()
        if not rid:
            raise IlwSchedulerError("IlwScheduler.run_id must be non-empty.")
        if self.seed_namespace.run_id != rid:
            raise IlwSchedulerError(
                "IlwScheduler seed_namespace.run_id must match scheduler run_id "
                f"({self.seed_namespace.run_id!r} != {rid!r})."
            )
        if self.tick < 0:
            raise IlwSchedulerError("IlwScheduler.tick must be non-negative.")
        object.__setattr__(self, "run_id", rid)

    @classmethod
    def for_run(cls, run_id: str, world_spec: WorldSpec) -> IlwScheduler:
        ns = SeedNamespace(run_id=run_id, seed=world_spec.seed)
        return cls(run_id=run_id, world_spec=world_spec, seed_namespace=ns, tick=0)

    def assert_run_id(self, run_id: str) -> None:
        if str(run_id).strip() != self.run_id:
            raise IlwSchedulerError(
                f"Scheduler is bound to run_id {self.run_id!r}; "
                f"refusing operation for {run_id!r}."
            )

    def advance(self, *, run_id: str | None = None) -> int:
        """Advance one tick under the bound run_id; return the new tick index."""

        if run_id is not None:
            self.assert_run_id(run_id)
        if self.tick >= self.world_spec.tick_horizon:
            raise IlwSchedulerError(
                f"Cannot advance past tick_horizon={self.world_spec.tick_horizon} "
                f"(current tick={self.tick})."
            )
        self.tick += 1
        self._advanced_ticks.append(self.tick)
        return self.tick

    def advance_many(self, steps: int, *, run_id: str | None = None) -> int:
        if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
            raise IlwSchedulerError("steps must be a non-negative integer.")
        for _ in range(steps):
            self.advance(run_id=run_id)
        return self.tick

    @property
    def advanced_ticks(self) -> tuple[int, ...]:
        return tuple(self._advanced_ticks)

    def scheduler_rng(self):
        return self.seed_namespace.fork_rng("scheduler", f"tick-{self.tick}")
