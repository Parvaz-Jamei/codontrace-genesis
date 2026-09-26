"""Lightweight identity / snapshot types for the unified GENESIS engine.

Extracted from ``codontrace.engine`` so tick, snapshot, and run identity
objects have a named module boundary. Digests go through
``codontrace.engine_digest._digest`` and must remain byte-stable.

``GenesisRunResult`` lives in ``codontrace.engine_run_result`` and is
re-exported from the ``codontrace.engine`` facade. See
``docs/ENGINE_REPLAY_CONTRACT.md``.
"""

from __future__ import annotations

from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.engine_digest import _digest
from codontrace.genesis.artifacts import ExperimentSummary, PopulationSnapshot
from codontrace.genesis.population import GenerationResult
from codontrace.genesis.quality_diversity import QDArchiveBatchUpdateResult


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
