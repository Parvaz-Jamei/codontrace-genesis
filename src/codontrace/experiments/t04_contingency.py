"""T04 — Historical Contingency and Replay.

Evaluates whether the past state of the agent changes the probability of reaching
a functional innovation when the future environment is identical.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, replace

from codontrace.experiments.math_utils import sha_prng_float
from codontrace.experiments.math_utils import sha_prng_int_unbiased as sha_prng_int
from codontrace.experiments.models import (
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


@dataclass(frozen=True)
class HistorySnapshot:
    history_seed: int
    generation: int
    population: tuple[tuple[int, float, int], ...]
    discoveries: tuple[int, ...]

    def digest(self) -> str:
        payload = {"population": self.population, "discoveries": self.discoveries}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class T04ContingencyRunner:
    """Runner for T04 Historical Contingency."""

    def __init__(
        self,
        seed: int,
        arm: str = "CONTINGENCY_REPLAY",
        population_size: int = 96,
        generations: int = 1500,
        track: ExecutionTrack = ExecutionTrack.REFERENCE,
        replay_branches: int = 8,
        replay_generations: int | None = None,
        history_count: int = 2,
        snapshot_generations: tuple[int, ...] | None = None,
    ) -> None:
        validate_reference_run(population_size, generations, track)
        if arm != "CONTINGENCY_REPLAY":
            raise ValueError("Unknown T04 arm")
        for name, value, bound in (("replay_branches", replay_branches, 32), ("history_count", history_count, 8)):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= bound:
                raise ValueError(f"{name} must be in [1, {bound}]")
        self.replay_branches = replay_branches
        self.history_count = history_count
        self.replay_generations = min(64, max(1, generations // 4)) if replay_generations is None else replay_generations
        if isinstance(self.replay_generations, bool) or not isinstance(self.replay_generations, int) or self.replay_generations <= 0:
            raise ValueError("replay_generations must be a positive integer")
        self.snapshot_generations = tuple(sorted(set((0, generations) if snapshot_generations is None else snapshot_generations)))
        if not self.snapshot_generations or len(self.snapshot_generations) > 16 or any(isinstance(g, bool) or not isinstance(g, int) or g < 0 or g > generations for g in self.snapshot_generations):
            raise ValueError("snapshot_generations must contain 1..16 history generations in the requested horizon")
        self.planned_work_units = history_count * generations + history_count * len(self.snapshot_generations) * (replay_branches + 1) * self.replay_generations
        self.seed = seed
        self.arm = arm
        self.population_size = population_size
        self.generations = generations
        self.track = track

        self.population: list[OrganismState] = []
        self.metrics_history: list[MetricRecord] = []
        self.completed_generations = 0
        self.discovered_phenotypes: set[int] = set()

    def initialize_population(self, branch_seed: int) -> None:
        self.population.clear()
        for i in range(self.population_size):
            g0 = sha_prng_int(branch_seed, i, "t04_founder", 0, 0xFFFFFFFF)
            self.population.append(OrganismState(genome=g0, atp=10.0, age=0))

    def evaluate_functional_phenotype(self, genome: int) -> int:
        phenotype = 0
        for task_idx in range(8):
            nibble = (genome >> (task_idx * 4)) & 0x0F
            target_mask = (task_idx * 3 + 5) & 0x0F
            if nibble == target_mask:
                phenotype |= (1 << task_idx)
        return phenotype

    def step_generation(self, gen: int, branch_seed: int) -> MetricRecord:
        survivors: list[OrganismState] = []

        for idx, org in enumerate(self.population):
            org.age += 1
            phenotype = self.evaluate_functional_phenotype(org.genome)
            
            if phenotype > 0:
                self.discovered_phenotypes.add(phenotype)

            match_count = bin(phenotype).count("1")
            survival_prob = min(0.95, 0.20 + 0.15 * match_count)
            r_surv = sha_prng_float(branch_seed, gen * 1000 + idx, "survival")
            
            if r_surv < survival_prob:
                org.atp += match_count * 1.5 - 0.5
                survivors.append(org)

        if not survivors:
            self.population = []

        offspring: list[OrganismState] = []
        needed = self.population_size - len(survivors)
        for i in range(max(0, needed)):
            if not survivors:
                break
            parent_idx = sha_prng_int(branch_seed, gen * 2000 + i, "parent", 0, len(survivors) - 1)
            parent = survivors[parent_idx]

            child_genome = parent.genome
            p_mut = sha_prng_float(branch_seed, gen * 3000 + i, "mut_event")
            if p_mut < 0.18:
                # Bug fix: Uniform distribution across 32 bits
                locus = sha_prng_int(branch_seed, gen * 4000 + i, "mut_locus", 0, 31)
                child_genome ^= (1 << locus)

            offspring.append(OrganismState(genome=child_genome, atp=10.0, age=0))

        self.population = (survivors + offspring)[: self.population_size]

        record = MetricRecord(
            generation=gen,
            tick=0,
            population_size=len(self.population),
            primary_metric_name="discovered_phenotypes",
            primary_metric_value=float(len(self.discovered_phenotypes)),
            secondary_metrics={},
        )
        self.completed_generations = gen
        self.metrics_history.append(record)
        return record

    def run_branch(self, start_gen: int, branch_seed: int, on_generation: Callable[[MetricRecord], None] | None = None) -> None:
        for gen in range(start_gen + 1, start_gen + self.generations + 1):
            record = self.step_generation(gen, branch_seed)
            if on_generation is not None:
                on_generation(record)
            if not self.population:
                break

    def snapshot(self, history_seed: int, generation: int) -> HistorySnapshot:
        return HistorySnapshot(history_seed, generation,
            tuple((o.genome, o.atp, o.age) for o in self.population),
            tuple(sorted(self.discovered_phenotypes)))

    def restore_snapshot(self, snapshot: HistorySnapshot) -> None:
        self.population = [OrganismState(*state) for state in snapshot.population]
        self.discovered_phenotypes = set(snapshot.discoveries)
        self.completed_generations = snapshot.generation
        self.metrics_history.clear()

    def run(self, on_generation: Callable[[MetricRecord], None] | None = None) -> CompletionSummary:
        self.metrics_history.clear()
        self.discovered_phenotypes.clear()
        self.completed_generations = 0
        work_units = 0
        snapshots: list[HistorySnapshot] = []
        branches: list[dict[str, object]] = []
        history_hashes: list[dict[str, object]] = []

        def publish(record: MetricRecord, history_index: int, phase: str, branch_index: int | None = None) -> None:
            nonlocal work_units
            work_units += 1
            global_record = replace(record, generation=work_units,
                details={**record.details, "phase": phase, "history_index": history_index,
                         "history_generation": record.generation, "branch_index": branch_index})
            if on_generation is not None:
                on_generation(global_record)

        for history_index in range(self.history_count):
            history_seed = self.seed if history_index == 0 else sha_prng_int(self.seed, history_index, "history_seed", 0, 0xFFFFFFFF)
            self.initialize_population(history_seed)
            self.discovered_phenotypes.clear()
            if 0 in self.snapshot_generations:
                snapshots.append(self.snapshot(history_seed, 0))
            for generation in range(1, self.generations + 1):
                if not self.population:
                    break
                record = self.step_generation(generation, history_seed)
                publish(record, history_index, "history")
                self.metrics_history.clear()
                if generation in self.snapshot_generations:
                    snapshots.append(self.snapshot(history_seed, generation))
            history_hashes.append({"history_index": history_index, "history_seed": history_seed,
                "state_sha256": self.snapshot(history_seed, self.completed_generations).digest(),
                "extinct": not self.population, "completed_generations": self.completed_generations,
                "stop_reason": "EXTINCTION" if not self.population else "HORIZON_REACHED",
                "skipped_snapshot_generations": [g for g in self.snapshot_generations if g > self.completed_generations]})

        for snapshot_index, snapshot in enumerate(snapshots):
            for branch_index in range(self.replay_branches + 1):
                # The last branch exactly repeats branch0 as a replay calibration.
                future_index = 0 if branch_index == self.replay_branches else branch_index
                future_seed = sha_prng_int(self.seed, future_index, "matched_future_seed", 0, 0xFFFFFFFF)
                self.restore_snapshot(snapshot)
                branch_work = 0
                for offset in range(1, self.replay_generations + 1):
                    if not self.population:
                        break
                    record = self.step_generation(snapshot.generation + offset, future_seed)
                    record = replace(record, details={"snapshot_index": snapshot_index, "future_seed": future_seed, "history_seed": snapshot.history_seed})
                    source_history_index = next(int(h["history_index"]) for h in history_hashes if h["history_seed"] == snapshot.history_seed)
                    publish(record, source_history_index, "replay", branch_index)
                    branch_work += 1
                    self.metrics_history.clear()
                final_state = self.snapshot(snapshot.history_seed, snapshot.generation + branch_work)
                branches.append({"snapshot_index": snapshot_index,
                    "history_seed": snapshot.history_seed, "snapshot_generation": snapshot.generation,
                    "snapshot_sha256": snapshot.digest(), "future_seed": future_seed,
                    "branch_index": branch_index, "replay_of": 0 if branch_index == self.replay_branches else None,
                    "completed_generations": branch_work, "extinct": not self.population,
                    "stop_reason": "EXTINCTION" if not self.population else "HORIZON_REACHED",
                    "skipped_generations": self.replay_generations - branch_work,
                    "endpoint": len(self.discovered_phenotypes - set(snapshot.discoveries)),
                    "final_state_sha256": final_state.digest()})
        exact_replay = bool(snapshots) and all(
            branches[i * (self.replay_branches + 1)]["final_state_sha256"] == branches[(i + 1) * (self.replay_branches + 1) - 1]["final_state_sha256"]
            for i in range(len(snapshots)))
        differences = []
        for generation in self.snapshot_generations:
            matched = [b for b in branches if b["snapshot_generation"] == generation and b["branch_index"] == 0]
            if len(matched) > 1:
                differences.append({"snapshot_generation": generation,
                    "matched_future_seed": matched[0]["future_seed"],
                    "endpoint_difference": float(matched[1]["endpoint"]) - float(matched[0]["endpoint"])})
        self.completed_generations = work_units
        return CompletionSummary(
            experiment_id="T04_CONTINGENCY_REPLAY", track=self.track, seed=self.seed,
            completed_generations=work_units, total_ticks=0, status="COMPLETED",
            stop_reason="ENSEMBLE_FINISHED", scientific_assessment=AssessmentStatus.INCONCLUSIVE if exact_replay else AssessmentStatus.INVALID_MEASUREMENT,
            primary_endpoint_value=sum(float(b["endpoint"]) for b in branches) / len(branches) if branches else None,
            summary_metrics={"arm": self.arm, "replay_ensemble_implemented": True,
                "history_horizon": self.generations, "replay_horizon": self.replay_generations,
                "planned_work_units": self.planned_work_units, "completed_work_units": work_units,
                "history_hashes": history_hashes, "snapshots": [{"history_seed": s.history_seed,
                    "generation": s.generation, "state_sha256": s.digest()} for s in snapshots],
                "branches": branches, "matched_future_endpoint_differences": differences,
                "exact_replay_passed": exact_replay, "prng_int_stream_version": "sha256-rejection-v2", "engine_ticks_executed": 0,
                "assessed_claim": "reference_historical_fork_replay",
                "requires_replicated_history_inference": True})
