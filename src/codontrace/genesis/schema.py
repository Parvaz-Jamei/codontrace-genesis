"""Execution and artifact schema definitions for Genesis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError

SCHEMA_VERSION = "genesis_execution_v1"


@dataclass(frozen=True, slots=True)
class RunState:
    run_id: str
    status: str
    start_time: str
    end_time: str | None
    
    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass(frozen=True, slots=True)
class FeatureExecutionRecord:
    feature_name: str
    executed: bool
    result: str | None
    
    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "feature_name": self.feature_name,
            "executed": self.executed,
            "result": self.result,
        }


@dataclass(frozen=True, slots=True)
class MetricRecord:
    metric_name: str
    value: float
    unit: str | None
    
    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
        }


@dataclass(frozen=True, slots=True)
class HypothesisAssessment:
    hypothesis_id: str
    conclusion: str
    confidence: float
    evidence_digests: tuple[str, ...]
    
    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "evidence_digests": list(self.evidence_digests),
        }


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    artifacts: tuple[Mapping[str, Any], ...]
    version: str = SCHEMA_VERSION
    
    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "version": self.version,
            "artifacts": list(self.artifacts),
        }
