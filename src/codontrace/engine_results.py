"""Lightweight identity / snapshot types for the unified GENESIS engine.

Extracted from ``codontrace.engine`` so tick, snapshot, and run identity
objects have a named module boundary. Digests go through
``codontrace.engine_digest._digest`` and must remain byte-stable.

``GenesisRunResult`` lives in ``codontrace.engine_run_result`` and is
re-exported from the ``codontrace.engine`` facade. See
``docs/ENGINE_REPLAY_CONTRACT.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from codontrace._types import JsonValue
from codontrace.engine_digest import _digest
from codontrace.genesis.artifacts import ExperimentSummary, PopulationSnapshot
from codontrace.genesis.population import GenerationResult
from codontrace.genesis.quality_diversity import QDArchiveBatchUpdateResult
from codontrace.trace import WorldEvent


@dataclass(frozen=True, slots=True)
class GenesisTickResult:
    """One logical GENESIS tick/generation result."""

    index: int
    generation_result: GenerationResult
    qd_update: QDArchiveBatchUpdateResult | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "index": self.index,
            "generation_result": self.generation_result.to_dict(),
            "qd_update": None if self.qd_update is None else self.qd_update.to_dict(),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ExogenousInputRecord:
    """World events a ``GenerationInputProvider`` supplied before one generation.

    ``world_digest_before`` / ``world_digest_after`` bracket the application,
    so a replay can check it starts from the same world and lands on the same
    one. Records exist only for generations that received at least one event.
    """

    tick_index: int
    generation_index: int
    events: tuple[WorldEvent, ...]
    world_digest_before: str
    world_digest_after: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick_index": self.tick_index,
            "generation_index": self.generation_index,
            "events": [event.to_dict() for event in self.events],
            "world_digest_before": self.world_digest_before,
            "world_digest_after": self.world_digest_after,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ExogenousInputRecord:
        events = data.get("events")
        if not isinstance(events, list):
            msg = "ExogenousInputRecord.events must be a list."
            raise ValueError(msg)
        ints = {}
        for key in ("tick_index", "generation_index"):
            value = data.get(key)
            if type(value) is not int or value < 0:
                msg = f"ExogenousInputRecord.{key} must be an integer >= 0."
                raise ValueError(msg)
            ints[key] = value
        digests = {}
        for key in ("world_digest_before", "world_digest_after"):
            value = data.get(key)
            if not isinstance(value, str) or not value:
                msg = f"ExogenousInputRecord.{key} must be a non-empty string."
                raise ValueError(msg)
            digests[key] = value
        return cls(
            tick_index=ints["tick_index"],
            generation_index=ints["generation_index"],
            events=tuple(WorldEvent.from_dict(cast(dict[str, JsonValue], dict(item))) for item in events),
            world_digest_before=digests["world_digest_before"],
            world_digest_after=digests["world_digest_after"],
        )


@dataclass(frozen=True, slots=True)
class GenesisSnapshot:
    """Engine snapshot for UI/API/replay."""

    run_id: str
    population: PopulationSnapshot
    world_digest: str
    qd_archive_digest: str | None = None
    element_grid_digest: str | None = None
    substrate_bridge_mode: str = "world2d_mirror"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "run_id": self.run_id,
            "population": self.population.to_dict(),
            "world_digest": self.world_digest,
            "qd_archive_digest": self.qd_archive_digest,
            "element_grid_digest": self.element_grid_digest,
            "substrate_bridge_mode": self.substrate_bridge_mode,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class GenesisRunSummary:
    """Summary across multiple engine ticks."""

    experiment: ExperimentSummary
    tick_digests: tuple[str, ...]
    manifest_digest: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "experiment": self.experiment.to_dict(),
            "tick_digests": list(self.tick_digests),
            "manifest_digest": self.manifest_digest,
        }


@dataclass(frozen=True, slots=True)
class GenesisRun:
    """Identity object for one engine-managed run."""

    run_id: str
    spec_digest: str
    seed: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {"run_id": self.run_id, "spec_digest": self.spec_digest, "seed": self.seed}


@dataclass(frozen=True, slots=True)
class ConsistencyValidationResult:
    """Self-check result for engine outputs and manifest/evidence wiring."""

    passed: bool
    issues: tuple[str, ...] = ()
    schema_version: str = "genesis_result_consistency_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "passed": self.passed,
            "issues": list(self.issues),
        }
