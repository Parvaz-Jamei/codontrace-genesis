"""Single orchestrated path: HostParasiteWorld + PopulationRegistry + GenesisEngine.

Architecture lock
-----------------
* ``HostParasiteWorld.tick`` is the **only** demographic / attachment / energy /
  inherit stepper for HP populations.
* ``PopulationRegistry`` is the membership book advanced *inside* that tick —
  not a parallel second engine.
* ``GenesisEngine`` remains the organism / world-physics spine. Infection /
  attachment physics must **not** land in ``engine.py``.
* This module is the documented bridge: run HP ticks alongside (or without)
  GenesisEngine, and mirror opaque registry digests into evidence payloads.

Claim ceiling stays ``runtime_observation`` / ``candidate_evidence``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.host_parasite_world import HostParasiteWorld

SCHEMA_VERSION = "host_parasite_genesis_path_v1"


@dataclass
class HostParasiteGenesisPath:
    """Orchestrate HP life-loop ticks; optionally lockstep with GenesisEngine.

    Passing an engine is optional. When present, each ``tick`` advances the HP
    world then asks the engine for one tick — without injecting infection into
    the engine. Registry digests are recorded on this path's evidence log.
    """

    world: HostParasiteWorld
    engine: Any | None = None
    evidence_log: list[dict[str, JsonValue]] = field(default_factory=list)
    path_id: str = "hp_genesis_path"

    def __post_init__(self) -> None:
        if not isinstance(self.world, HostParasiteWorld):
            raise ConfigurationError("world must be a HostParasiteWorld.")
        if not isinstance(self.path_id, str) or not self.path_id.strip():
            raise ConfigurationError("path_id must be a non-empty string.")

    def bind_engine(self, engine: Any) -> None:
        """Attach a GenesisEngine (duck-typed: must expose ``run_ticks``)."""

        if engine is None:
            raise ConfigurationError("engine must not be None.")
        if not hasattr(engine, "run_ticks"):
            raise ConfigurationError("engine must expose run_ticks(ticks).")
        self.engine = engine

    def tick(self) -> dict[str, JsonValue]:
        """Advance HP world one tick; optionally advance bound GenesisEngine."""

        self.world.tick()
        engine_tick: int | None = None
        if self.engine is not None:
            result = self.engine.run_ticks(1)
            engine_tick = int(getattr(result, "ticks_executed", 1) or 1)
        snap = self.world.life_loop_snapshot()
        record: dict[str, JsonValue] = {
            "schema_version": SCHEMA_VERSION,
            "path_id": self.path_id,
            "hp_tick": snap["tick"],
            "registry_digest": snap["registry_digest"],
            "book_digest": snap["book_digest"],
            "census": dict(snap["census"]),  # type: ignore[arg-type]
            "coexistence": snap["coexistence"],
            "extinct_primary": snap["extinct_primary"],
            "extinct_secondary": snap["extinct_secondary"],
            "engine_bound": self.engine is not None,
            "engine_ticks_advanced": engine_tick,
        }
        record["evidence_digest"] = canonical_digest(
            {k: record[k] for k in record if k != "evidence_digest"},
            prefix="hp_path",
        )
        self.evidence_log.append(record)
        return record

    def run(self, ticks: int) -> dict[str, JsonValue]:
        if not isinstance(ticks, int) or isinstance(ticks, bool) or ticks < 0:
            raise ConfigurationError("ticks must be a non-negative int.")
        last: dict[str, JsonValue] = {}
        for _ in range(ticks):
            last = self.tick()
        return {
            "schema_version": SCHEMA_VERSION,
            "path_id": self.path_id,
            "ticks": ticks,
            "final": last,
            "evidence_count": len(self.evidence_log),
            "world_summary": self.world.summary(),
            "claim_ceiling": "runtime_observation",
            "red_queen_proved": False,
            "raises_claim_ladder": False,
            "note": (
                "PopulationRegistry participates via HostParasiteWorld.tick; "
                "GenesisEngine is the organism spine; no infection in engine.py."
            ),
        }

    def evidence_digest_chain(self) -> str:
        return canonical_digest(
            {"entries": list(self.evidence_log)}, prefix="hp_path_chain"
        )


def orchestrate_hp_tick(world: HostParasiteWorld) -> Mapping[str, JsonValue]:
    """Module-level single-path entry: one HP tick through the orchestrator."""

    return HostParasiteGenesisPath(world=world).tick()


__all__ = [
    "SCHEMA_VERSION",
    "HostParasiteGenesisPath",
    "orchestrate_hp_tick",
]
