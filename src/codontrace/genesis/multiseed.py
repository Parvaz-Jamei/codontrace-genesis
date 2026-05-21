"""Multi-seed scientific experiment runner for GENESIS.

This module runs ordinary :class:`GenesisEngine` experiments across explicit
seeds and aggregates descriptive, deterministic reports. It is a research-alpha
scientific protocol helper; it does not prove open-ended evolution or artificial
life.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec, GenesisRunResult


@dataclass(frozen=True, slots=True)
class MultiSeedRunConfig:
    """Configuration for deterministic multi-seed experiments."""

    seeds: tuple[int, ...]
    tick_count: int | None = None
    metrics: tuple[str, ...] = ("best_fitness", "mean_fitness", "qd_filled_bins")
    min_seeds_for_scientific_claim: int = 5
    mode: str = "reproducibility"
    mutation_rate: float = 0.0
    novelty_pressure: float = 0.0

    def __post_init__(self) -> None:
        if not self.seeds:
            raise ConfigurationError("MultiSeedRunConfig.seeds must not be empty.")
        if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in self.seeds):
            raise ConfigurationError("MultiSeedRunConfig.seeds must contain integers only.")
        if self.tick_count is not None and self.tick_count < 0:
            raise ConfigurationError("tick_count must be >= 0 or None.")
        if self.min_seeds_for_scientific_claim <= 0:
            raise ConfigurationError("min_seeds_for_scientific_claim must be > 0.")
        if self.mode not in {"reproducibility", "evolutionary_variation"}:
            raise ConfigurationError("mode must be reproducibility or evolutionary_variation.")
        if self.mutation_rate < 0 or self.novelty_pressure < 0:
            raise ConfigurationError("mutation_rate and novelty_pressure must be >= 0.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seeds": list(self.seeds),
            "tick_count": self.tick_count,
            "metrics": list(self.metrics),
            "min_seeds_for_scientific_claim": self.min_seeds_for_scientific_claim,
            "mode": self.mode,
            "mutation_rate": self.mutation_rate,
            "novelty_pressure": self.novelty_pressure,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class SeedRunRecord:
    """One seed execution record linked to manifest/replay/evidence artifacts."""

    seed: int
    run_id: str
    manifest_digest: str
    replay_digest: str
    evidence_digest: str
    qd_archive_digest: str | None
    summary_metrics: dict[str, float]
    final_population: int
    extinction: bool

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "run_id": self.run_id,
            "manifest_digest": self.manifest_digest,
            "replay_digest": self.replay_digest,
            "evidence_digest": self.evidence_digest,
            "qd_archive_digest": self.qd_archive_digest,
            "summary_metrics": dict(sorted(self.summary_metrics.items())),
            "final_population": self.final_population,
            "extinction": self.extinction,
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MultiSeedSummary:
    """Deterministic aggregate summary with descriptive statistics only."""

    seed_count: int
    metric_stats: dict[str, dict[str, float]]
    success_rate: float
    extinction_rate: float
    diversity_collapse_rate: float
    novelty_persistence_rate: float
    reproducibility_status: str
    claim_gate_status: str
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed_count": self.seed_count,
            "metric_stats": {
                key: dict(sorted(value.items())) for key, value in sorted(self.metric_stats.items())
            },
            "success_rate": self.success_rate,
            "extinction_rate": self.extinction_rate,
            "diversity_collapse_rate": self.diversity_collapse_rate,
            "novelty_persistence_rate": self.novelty_persistence_rate,
            "reproducibility_status": self.reproducibility_status,
            "claim_gate_status": self.claim_gate_status,
            "limitations": list(self.limitations),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MultiSeedStatisticalReport(MultiSeedSummary):
    """Alias-like subclass for advanced scientific reports."""


MinimumSeedPolicy = MultiSeedRunConfig
MultiSeedExperimentConfig = MultiSeedRunConfig
SeedRunResult = SeedRunRecord


@dataclass(frozen=True, slots=True)
class MultiSeedRunResult:
    """Full multi-seed run result."""

    config: MultiSeedRunConfig
    records: tuple[SeedRunRecord, ...]
    summary: MultiSeedSummary
    result_digests: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "config": self.config.to_dict(),
            "records": [item.to_dict() for item in self.records],
            "summary": self.summary.to_dict(),
            "result_digests": list(self.result_digests),
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


class MultiSeedExperimentRunner:
    """Run a GenesisExperimentSpec across explicit seeds and aggregate reports."""

    def __init__(self, spec: GenesisExperimentSpec, config: MultiSeedRunConfig) -> None:
        self.spec = spec
        self.config = config

    def run(self) -> MultiSeedRunResult:
        records: list[SeedRunRecord] = []
        result_digests: list[str] = []
        for seed in self.config.seeds:
            seed_spec = replace(
                self.spec,
                seed=seed,
                tick_count=self.spec.tick_count
                if self.config.tick_count is None
                else self.config.tick_count,
            )
            engine = GenesisEngine.from_spec(seed_spec)
            result = engine.run_ticks()
            result_digests.append(result.digest())
            records.append(_record_from_result(seed, result, engine))
        summary = _build_summary(records, self.config)
        return MultiSeedRunResult(self.config, tuple(records), summary, tuple(result_digests))


def _record_from_result(
    seed: int, result: GenesisRunResult, engine: GenesisEngine
) -> SeedRunRecord:
    summary = result.evidence_pack.summary
    metrics = {
        "best_fitness": float(summary.best_fitness),
        "mean_fitness": float(summary.mean_fitness),
        "final_population": float(summary.final_population),
        "causal_updates": float(summary.causal_updates),
        "capsules_adopted": float(summary.capsules_adopted),
        "qd_filled_bins": float(summary.qd_filled_bins),
    }
    return SeedRunRecord(
        seed=seed,
        run_id=result.run.run_id,
        manifest_digest=result.manifest.digest(),
        replay_digest=result.replay_bundle.digest(),
        evidence_digest=result.evidence_pack.digest(),
        qd_archive_digest=None if engine.qd_archive is None else engine.qd_archive.digest(),
        summary_metrics=metrics,
        final_population=summary.final_population,
        extinction=summary.final_population == 0,
    )


def _build_summary(
    records: Sequence[SeedRunRecord], config: MultiSeedRunConfig
) -> MultiSeedSummary:
    metric_stats: dict[str, dict[str, float]] = {}
    for metric in config.metrics:
        values = [float(record.summary_metrics.get(metric, 0.0)) for record in records]
        metric_stats[metric] = _stats(values)
    seed_count = len(records)
    extinction_rate = round(sum(1 for record in records if record.extinction) / seed_count, 10)
    success_rate = round(1.0 - extinction_rate, 10)
    qd_values = [record.summary_metrics.get("qd_filled_bins", 0.0) for record in records]
    diversity_collapse_rate = round(sum(1 for value in qd_values if value <= 1.0) / seed_count, 10)
    novelty_persistence_rate = round(sum(1 for value in qd_values if value > 1.0) / seed_count, 10)
    limitations: list[str] = []
    if (
        config.mode == "evolutionary_variation"
        and config.mutation_rate <= 0
        and config.novelty_pressure <= 0
    ):
        limitations.append("evolutionary_variation_mode_requires_mutation_or_novelty_pressure")
    if seed_count < config.min_seeds_for_scientific_claim:
        limitations.append("insufficient_seed_count_for_scientific_claim")
    claim_gate_status = "claim_limited" if limitations else "descriptive_multiseed_ready"
    return MultiSeedSummary(
        seed_count=seed_count,
        metric_stats=metric_stats,
        success_rate=success_rate,
        extinction_rate=extinction_rate,
        diversity_collapse_rate=diversity_collapse_rate,
        novelty_persistence_rate=novelty_persistence_rate,
        reproducibility_status=(
            "distribution_report"
            if config.mode == "evolutionary_variation"
            else (
                "deterministic_records"
                if len(set(record.digest() for record in records)) == len(records)
                else "duplicate_records_detected"
            )
        ),
        claim_gate_status=claim_gate_status,
        limitations=tuple(limitations),
    )


def _stats(values: Sequence[float]) -> dict[str, float]:
    if not values:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return {
        "mean": round(mean, 10),
        "std": round(math.sqrt(variance), 10),
        "min": round(min(values), 10),
        "max": round(max(values), 10),
    }


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
