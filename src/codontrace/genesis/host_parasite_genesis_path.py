"""HostParasiteGenesisPath — dual-clock path retired under closed-loop P1.

P1 lock (2026-09-25 specialist Pass 2 consensus):
* Both roles live as ``GenesisOrganism`` under ``step_population`` /
  ``PopulationRunner.step_generation`` via ``closed_loop_hp_life``.
* ``HostParasiteWorld.tick`` / ``_birth_role`` / ``_death_role`` are **not**
  the life authority for closed-loop accept.
* ``engine_bound=True`` alone must never green P1.
* Use ``codontrace.genesis.closed_loop_p1.ClosedLoopP1Session``.

Claim ceiling stays ``runtime_observation`` / ``candidate_evidence``.
``red_queen_proved`` remains refused.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_world import HostParasiteWorld

SCHEMA_VERSION = "host_parasite_genesis_path_v2_retired_dual"

_DUAL_PATH_MSG = (
    "P1 closed-loop: dual HostParasiteGenesisPath.tick is retired. "
    "Both roles must live as GenesisOrganism under step_population "
    "(PopulationConfigs.closed_loop_hp_life). "
    "engine_bound alone must never green P1. "
    "Use codontrace.genesis.closed_loop_p1.ClosedLoopP1Session. "
    "deprecated_dual_path fails closed — HostParasiteWorld.tick must not run."
)


@dataclass
class HostParasiteGenesisPath:
    """Retired dual orchestrator. ``tick`` / ``run`` hard-raise (fail closed)."""

    world: HostParasiteWorld
    engine: Any | None = None
    evidence_log: list[dict[str, JsonValue]] = field(default_factory=list)
    path_id: str = "hp_genesis_path"
    deprecated_dual_path: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.world, HostParasiteWorld):
            raise ConfigurationError("world must be a HostParasiteWorld.")
        if not isinstance(self.path_id, str) or not self.path_id.strip():
            raise ConfigurationError("path_id must be a non-empty string.")

    def bind_engine(self, engine: Any) -> None:
        """Attach a GenesisEngine (duck-typed). Does not authorize dual tick."""

        if engine is None:
            raise ConfigurationError("engine must not be None.")
        if not hasattr(engine, "run_ticks"):
            raise ConfigurationError("engine must expose run_ticks(ticks).")
        self.engine = engine

    def tick(self, *, deprecated_dual_path: bool | None = None) -> dict[str, JsonValue]:
        """Hard-raise: dual path is not a closed-loop life authority."""

        flag = self.deprecated_dual_path if deprecated_dual_path is None else deprecated_dual_path
        if flag:
            raise ConfigurationError(
                "deprecated_dual_path fails closed: HostParasiteWorld.tick must not "
                "run under P1 (false engine-complete adjacent). " + _DUAL_PATH_MSG
            )
        raise ConfigurationError(_DUAL_PATH_MSG)

    def run(self, ticks: int) -> dict[str, JsonValue]:
        if not isinstance(ticks, int) or isinstance(ticks, bool) or ticks < 0:
            raise ConfigurationError("ticks must be a non-negative int.")
        # Fail closed before any world demography advances.
        self.tick()
        return {}  # unreachable

    def evidence_digest_chain(self) -> str:
        raise ConfigurationError(_DUAL_PATH_MSG)


def orchestrate_hp_tick(world: HostParasiteWorld) -> Mapping[str, JsonValue]:
    """Retired entry: hard-raises (same as path.tick)."""

    return HostParasiteGenesisPath(world=world).tick()


__all__ = [
    "SCHEMA_VERSION",
    "HostParasiteGenesisPath",
    "orchestrate_hp_tick",
]
