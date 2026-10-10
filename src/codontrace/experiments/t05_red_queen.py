"""Bounded, standalone antagonistic coevolution with archived time-shift assays.

This REFERENCE model measures temporal adaptation; inference about a Red Queen
mechanism additionally requires replicated, preregistered arm comparisons.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from codontrace.experiments.math_utils import sha_prng_float
from codontrace.experiments.math_utils import sha_prng_int_unbiased as sha_prng_int
from codontrace.experiments.models import (
    RED_QUEEN_PROVED,
    AssessmentStatus,
    CompletionSummary,
    ExecutionTrack,
    MetricRecord,
    validate_reference_run,
)


@dataclass
class OrganismState:
    genome: int
    atp: float
    age: int

class T05RedQueenRunner:
    experiment_id = "T05_RED_QUEEN"

    def __init__(self, seed: int, arm: str = "COEVOLUTION", population_size: int = 96,
                 generations: int = 4000, track: ExecutionTrack = ExecutionTrack.REFERENCE) -> None:
        validate_reference_run(population_size, generations, track)
        if arm not in {"COEVOLUTION", "NO_SELECTION", "FIXED_HOST", "FIXED_PARASITE"}:
            raise ValueError("Unknown T05 arm")
        self.seed, self.arm = seed, arm
        self.population_size, self.generations, self.track = population_size, generations, track
        self.hosts: list[OrganismState] = []
        self.parasites: list[OrganismState] = []
        self.metrics_history: list[MetricRecord] = []
        self.time_shift_matrix: list[list[float | None]] = []
        self.archive: dict[int, tuple[tuple[int, ...], tuple[int, ...]]] = {}
        self.archive_stride = max(1, (generations + 30) // 31)
        self.completed_generations = 0

    def initialize_populations(self) -> None:
        self.hosts = [OrganismState(sha_prng_int(self.seed, i, "t05_host", 0, 0xFFFFFFFF), 10.0, 0) for i in range(self.population_size)]
        self.parasites = [OrganismState(sha_prng_int(self.seed, i, "t05_parasite", 0, 0xFFFFFFFF), 10.0, 0) for i in range(self.population_size)]

    def evaluate_interaction(self, host_genome: int, parasite_genome: int) -> tuple[float, float]:
        infection = ((~(host_genome ^ parasite_genome)) & 0xFFFFFFFF).bit_count() / 32.0
        return 1.0 - infection, infection

    def _snapshot(self, generation: int) -> None:
        # Deterministic dispersed sample, maximum 16 per species and 33 snapshots.
        def sample(population: list[OrganismState]) -> tuple[int, ...]:
            n = min(16, len(population))
            return tuple(population[i * len(population) // n].genome for i in range(n)) if n else ()
        self.archive[generation] = (sample(self.hosts), sample(self.parasites))

    def _reproduce(self, survivors: list[OrganismState], gen: int, species: str) -> list[OrganismState]:
        if not survivors:
            return []  # Extinction is observable, never silently rescue or reset founders.
        offspring: list[OrganismState] = []
        for i in range(self.population_size - len(survivors)):
            parent = survivors[sha_prng_int(self.seed, gen * self.population_size + i, species + "_parent", 0, len(survivors) - 1)]
            genome = parent.genome
            if sha_prng_float(self.seed, gen * self.population_size + i, species + "_mutation") < 0.18:
                genome ^= 1 << sha_prng_int(self.seed, gen * self.population_size + i, species + "_locus", 0, 31)
            offspring.append(OrganismState(genome, 10.0, 0))
        return survivors + offspring

    def step_generation(self, gen: int) -> MetricRecord:
        host_survivors: list[OrganismState] = []
        parasite_survivors: list[OrganismState] = []
        for idx, (host, parasite) in enumerate(zip(self.hosts, self.parasites, strict=True)):
            resistance, infection = self.evaluate_interaction(host.genome, parasite.genome)
            if self.arm == "NO_SELECTION":
                resistance, infection = 0.5, 0.5
            if self.arm == "FIXED_HOST" or sha_prng_float(self.seed, gen * self.population_size + idx, "h_surv") < resistance:
                host_survivors.append(host)
            if self.arm == "FIXED_PARASITE" or sha_prng_float(self.seed, gen * self.population_size + idx, "p_surv") < infection:
                parasite_survivors.append(parasite)
        if self.arm != "FIXED_HOST":
            self.hosts = self._reproduce(host_survivors, gen, "host")
        if self.arm != "FIXED_PARASITE":
            self.parasites = self._reproduce(parasite_survivors, gen, "parasite")
        self.completed_generations = gen
        if gen % self.archive_stride == 0 or gen == self.generations or not self.hosts or not self.parasites:
            self._snapshot(gen)
        record = MetricRecord(gen, 0, min(len(self.hosts), len(self.parasites)), "host_survival_rate",
            len(host_survivors) / self.population_size,
            {"parasite_survival_rate": len(parasite_survivors) / self.population_size,
             "host_population_size": float(len(self.hosts)), "parasite_population_size": float(len(self.parasites))})
        self.metrics_history.append(record)
        return record

    def _assay_time_shifts(self) -> dict[str, object]:
        generations = sorted(self.archive)
        # Rows: host sample generation; columns: parasite sample generation.
        # Value: mean parasite infection probability across all sampled pairs.
        matrix = []
        valid = True
        for h_gen in generations:
            row = []
            for p_gen in generations:
                hosts, parasites = self.archive[h_gen][0], self.archive[p_gen][1]
                if not hosts or not parasites:
                    row.append(None)
                    valid = False
                else:
                    row.append(sum(self.evaluate_interaction(h, p)[1] for h in hosts for p in parasites) / (len(hosts) * len(parasites)))
            matrix.append(row)
        self.time_shift_matrix = matrix
        host_margin = parasite_margin = None
        if valid and len(matrix) >= 2:
            # Current hosts resist past parasites relative to past hosts;
            # current parasites infect past hosts relative to past parasites.
            host_margin = matrix[-2][-2] - matrix[-1][-2]
            parasite_margin = matrix[-2][-1] - matrix[-2][-2]
        return {"matrix": matrix, "row_labels": generations, "column_labels": generations,
                "host_generations": generations, "parasite_generations": generations,
                "value": "mean_infection_probability", "archive_stride": self.archive_stride,
                "sample_limit_per_species": 16, "valid": valid,
                "host_recent_margin": host_margin, "parasite_recent_margin": parasite_margin}

    def run(self, on_generation: Callable[[MetricRecord], None] | None = None) -> CompletionSummary:
        self.metrics_history.clear()
        self.archive.clear()
        self.initialize_populations()
        self._snapshot(0)
        for gen in range(1, self.generations + 1):
            record = self.step_generation(gen)
            if on_generation is not None:
                on_generation(record)
            if not self.hosts or not self.parasites:
                break
        evidence = self._assay_time_shifts()
        extinct = not self.hosts or not self.parasites
        return CompletionSummary(self.experiment_id, self.track, self.seed, self.completed_generations,
            0, "EXTINCT" if extinct else "COMPLETED", "EXTINCTION" if extinct else "HORIZON_REACHED",
            AssessmentStatus.INCONCLUSIVE, float(record.primary_metric_value),
            {"arm": self.arm, "time_shift": evidence,
             "assessed_claim": "descriptive_temporal_adaptation", "requires_replicated_control_comparison": True,
             "prng_int_stream_version": "sha256-rejection-v2", "engine_ticks_executed": 0}, red_queen_proved=RED_QUEEN_PROVED)
