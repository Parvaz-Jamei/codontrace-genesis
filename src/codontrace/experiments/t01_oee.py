"""T01 — Bounded descriptor novelty and Quality-Diversity reference experiment.

Evaluates whether ecological selection with Quality-Diversity archives generates
bounded descriptor novelty evaluated on held-out bit patterns, beyond neutral genetic turnover.

Four experimental arms:
1. REAL_SELECTION_WITH_QD: Full ecological selection with functional QD archive.
2. REAL_SELECTION_NO_QD: Real ecological selection without QD archive.
3. NEUTRAL_DRIFT_CONTROL: Equal-budget neutral drift without fitness-dependent survival.
4. QD_RANDOM_DESCRIPTOR: QD archive using random descriptor control.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from codontrace.experiments.math_utils import sha_prng_float
from codontrace.experiments.math_utils import sha_prng_int_unbiased as sha_prng_int
from codontrace.experiments.models import (
    AssessmentStatus,
    CompletionSummary,
    ExecutionTrack,
    MetricRecord,
    validate_reference_run,
)

TASKS: tuple[str, ...] = tuple(f"nibble_target_{i}" for i in range(8))
HELDOUT_TASKS: tuple[str, ...] = tuple(f"heldout_bit_pattern_{i}" for i in range(4))


@dataclass
class OrganismState:
    genome: int  # 32-bit integer representation
    atp: float
    age: int
    phenotype_history: set[int] = field(default_factory=set)


class T01OEERunner:
    """Runner for T01 bounded descriptor matching, not executed Boolean programs."""

    def __init__(
        self,
        seed: int,
        arm: str = "REAL_SELECTION_WITH_QD",
        population_size: int = 96,
        generations: int = 2000,
        track: ExecutionTrack = ExecutionTrack.REFERENCE,
    ) -> None:
        self.seed = seed
        self.arm = arm
        self.population_size = population_size
        self.generations = generations
        self.track = track
        validate_reference_run(self.population_size, generations, track)

        self.population: list[OrganismState] = []
        self.discovered_phenotypes: set[int] = set()
        self.heldout_innovations: set[int] = set()
        self.component_activity: dict[int, int] = {}
        self.cumulative_activity: int = 0
        self.metrics_history: list[MetricRecord] = []
        self.qd_archive: dict[int, tuple[int, int]] = {}
        if arm not in {"REAL_SELECTION_WITH_QD", "REAL_SELECTION_NO_QD", "NEUTRAL_DRIFT_CONTROL", "QD_RANDOM_DESCRIPTOR"}:
            raise ValueError("Unknown T01 arm")

    def initialize_population(self) -> None:
        self.population.clear()
        for i in range(self.population_size):
            # Deterministic founder generation
            g0 = sha_prng_int(self.seed, i, "t01_founder", 0, 0xFFFFFFFF)
            self.population.append(OrganismState(genome=g0, atp=10.0, age=0))

    def evaluate_functional_phenotype(self, genome: int) -> int:
        """Returns a bounded nibble-match descriptor, not executed Boolean tasks."""
        phenotype = 0
        for task_idx in range(len(TASKS)):
            # Task target matching logic based on 4-bit nibbles
            nibble = (genome >> (task_idx * 4)) & 0x0F
            target_mask = (task_idx * 3 + 5) & 0x0F
            if nibble == target_mask:
                phenotype |= (1 << task_idx)
        return phenotype

    def evaluate_heldout_task(self, genome: int) -> int:
        """Evaluates held-out bit-pattern descriptors, not actual task execution."""
        heldout_bits = 0
        for h_idx in range(len(HELDOUT_TASKS)):
            sub_key = ((genome >> (h_idx * 7)) ^ (genome >> 13)) & 0x1F
            if sub_key == ((h_idx * 7 + 11) & 0x1F):
                heldout_bits |= (1 << h_idx)
        return heldout_bits

    def step_generation(self, gen: int) -> MetricRecord:
        new_innovations = 0
        survivors: list[OrganismState] = []

        # 1. Action, Evaluation & Survival Selection
        for idx, org in enumerate(self.population):
            org.age += 1
            phenotype = self.evaluate_functional_phenotype(org.genome)
            heldout = self.evaluate_heldout_task(org.genome)

            match_count = bin(phenotype).count("1")
            if self.arm in ("REAL_SELECTION_WITH_QD", "QD_RANDOM_DESCRIPTOR"):
                descriptor = phenotype if self.arm == "REAL_SELECTION_WITH_QD" else sha_prng_int(self.seed, org.genome, "random_descriptor", 0, 255)
                old = self.qd_archive.get(descriptor)
                if old is None or match_count > old[1]:
                    self.qd_archive[descriptor] = (org.genome, match_count)

            # Tracking novel discoveries
            if phenotype not in self.discovered_phenotypes:
                self.discovered_phenotypes.add(phenotype)
                new_innovations += 1

            if heldout > 0 and heldout not in self.heldout_innovations:
                self.heldout_innovations.add(heldout)

            # Bedau activity: record presence of components actively selected
            if phenotype > 0:
                self.component_activity[phenotype] = self.component_activity.get(phenotype, 0) + 1
                self.cumulative_activity += 1

            # Survival / ATP accounting based on Arm
            if self.arm in ("REAL_SELECTION_WITH_QD", "REAL_SELECTION_NO_QD", "QD_RANDOM_DESCRIPTOR"):
                survival_prob = min(0.95, 0.20 + 0.15 * match_count)
            else:  # NEUTRAL_DRIFT_CONTROL
                survival_prob = 0.50

            r_surv = sha_prng_float(self.seed, gen * 1000 + idx, "survival")
            if r_surv < survival_prob:
                org.atp += match_count * 1.5 - 0.5
                survivors.append(org)

        # 2. Reproduction to restore population capacity
        if not survivors:
            self.population = []

        offspring: list[OrganismState] = []
        needed = self.population_size - len(survivors)
        for i in range(max(0, needed)):
            if not survivors:
                break
            parent_idx = sha_prng_int(self.seed, gen * 2000 + i, "parent", 0, len(survivors) - 1)
            child_genome = survivors[parent_idx].genome
            if self.qd_archive and sha_prng_float(self.seed, gen * 2000 + i, "archive_parent") < 0.25:
                cells = sorted(self.qd_archive)
                cell = cells[sha_prng_int(self.seed, gen * 2000 + i, "archive_cell", 0, len(cells) - 1)]
                child_genome = self.qd_archive[cell][0]
            # Decoupled mutation: event probability vs uniform locus selection across all 32 bits
            p_mut = sha_prng_float(self.seed, gen * 3000 + i, "mut_event")
            if p_mut < 0.18:
                locus = sha_prng_int(self.seed, gen * 4000 + i, "mut_locus", 0, 31)
                child_genome ^= (1 << locus)

            offspring.append(OrganismState(genome=child_genome, atp=10.0, age=0))

        self.population = (survivors + offspring)[: self.population_size]

        record = MetricRecord(
            generation=gen,
            tick=0,
            population_size=len(self.population),
            primary_metric_name="cumulative_activity",
            primary_metric_value=float(self.cumulative_activity),
            secondary_metrics={
                "discovered_phenotypes_total": float(len(self.discovered_phenotypes)),
                "heldout_innovations_total": float(len(self.heldout_innovations)),
                "new_innovations_this_gen": float(new_innovations),
            },
        )
        self.metrics_history.append(record)
        return record

    def run(self, on_generation: Callable[[MetricRecord], None] | None = None) -> CompletionSummary:
        self.discovered_phenotypes.clear()
        self.heldout_innovations.clear()
        self.component_activity.clear()
        self.qd_archive.clear()
        self.metrics_history.clear()
        self.cumulative_activity = 0
        self.initialize_population()
        for gen in range(1, self.generations + 1):
            record = self.step_generation(gen)
            if on_generation is not None:
                on_generation(record)
            if not self.population:
                break

        heldout_count = len(self.heldout_innovations)
        assessment = AssessmentStatus.INCONCLUSIVE

        return CompletionSummary(
            experiment_id="T01_OEE_NOVELTY",
            track=self.track,
            seed=self.seed,
            completed_generations=gen,
            total_ticks=0,
            status="COMPLETED" if self.population else "EXTINCT",
            stop_reason="HORIZON_REACHED" if self.population else "EXTINCTION",
            scientific_assessment=assessment,
            primary_endpoint_value=float(heldout_count),
            summary_metrics={
                "arm": self.arm,
                "assessed_claim": "bounded_descriptor_novelty",
                "requires_between_arm_seed_comparison": True,
                "qd_archive_cells": len(self.qd_archive),
                "prng_int_stream_version": "sha256-rejection-v2", "engine_ticks_executed": 0,
                "cumulative_activity": self.cumulative_activity,
                "total_discovered_phenotypes": len(self.discovered_phenotypes),
                "total_heldout_innovations": heldout_count,
            },
        )
