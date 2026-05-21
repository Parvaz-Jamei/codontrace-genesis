
"""Phase 3 scale/performance resource-budget evidence primitives."""
from __future__ import annotations
from dataclasses import dataclass
from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest, require_finite_float

@dataclass(frozen=True, slots=True)
class ResourceBudgetPolicy:
    max_organism_ticks: int
    max_seconds: float | None = None
    schema_version: str = "resource_budget_policy_v1"
    def __post_init__(self) -> None:
        if self.max_organism_ticks <= 0: raise ValueError("max_organism_ticks must be positive")
        if self.max_seconds is not None:
            object.__setattr__(self, "max_seconds", require_finite_float("max_seconds", self.max_seconds, non_negative=True))
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "max_organism_ticks": self.max_organism_ticks, "max_seconds": self.max_seconds}
    def digest(self) -> str: return canonical_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class ScaleBenchmarkSpec:
    population: int
    ticks: int
    ladder_level: str = "small"
    schema_version: str = "scale_benchmark_spec_v1"
    def __post_init__(self) -> None:
        if self.population <= 0 or self.ticks <= 0: raise ValueError("population/ticks must be positive")
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "population": self.population, "ticks": self.ticks, "ladder_level": self.ladder_level}
    def digest(self) -> str: return canonical_digest(self.to_dict())

@dataclass(frozen=True, slots=True)
class ScaleBenchmarkReport:
    spec_digest: str
    semantics_digest: str
    stop_reason: str
    schema_version: str = "scale_benchmark_report_v1"
    def to_dict(self) -> dict[str, JsonValue]:
        return {"schema_version": self.schema_version, "spec_digest": self.spec_digest, "semantics_digest": self.semantics_digest, "stop_reason": self.stop_reason}
    def digest(self) -> str: return canonical_digest(self.to_dict())

MemoryFootprintReport = ScaleBenchmarkReport
ThroughputReport = ScaleBenchmarkReport
LongRunStabilityReport = ScaleBenchmarkReport
