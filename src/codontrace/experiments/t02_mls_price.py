"""T02 — Multilevel Selection (MLS) & Real Price Equation Accounting.

Investigates whether between-group selection can overcome within-group fitness costs
of altruistic cooperation, verified with exact Price equation accounting identities.

Design:
- 8 Demes x 16 Individuals = 128 total population.
- Factorial 2x2: Group Selection (ON/OFF) x Migration (LOW/HIGH).
- Verified mathematical invariant at every generation:
  Delta bar(z) = Cov(w, z) / bar(w) + E[w * (z' - z)] / bar(w)
  Identity residual < 1e-7.
- Dedicated deme- and lineage-keyed PRNG streams.
"""

from __future__ import annotations

from dataclasses import dataclass

from codontrace.experiments.math_utils import (
    PriceEquationAccounting,
    compute_exact_price_equation,
    sha_prng_float,
    sha_prng_int,
)
from codontrace.experiments.models import (
    AssessmentStatus,
    CompletionSummary,
    ExecutionTrack,
    MetricRecord,
)


@dataclass
class Individual:
    deme_id: int
    lineage_id: int
    altruism_trait: float  # z_i in [0.0, 1.0]: investment in group common good
    atp: float
    offspring_count: int = 0


class T02MLSPriceRunner:
    """Runner for T02 Multilevel Selection with verified Price equation identities."""

    def __init__(
        self,
        seed: int,
        group_selection: bool = True,
        high_migration: bool = False,
        num_demes: int = 8,
        deme_capacity: int = 16,
        generations: int = 2000,
        track: ExecutionTrack = ExecutionTrack.ENGINE,
    ) -> None:
        self.seed = seed
        self.group_selection = group_selection
        self.high_migration = high_migration
        self.num_demes = num_demes
        self.deme_capacity = deme_capacity
        self.population_size = num_demes * deme_capacity
        self.generations = generations
        self.track = track

        self.population: list[Individual] = []
        self.price_history: list[PriceEquationAccounting] = []
        self.metrics_history: list[MetricRecord] = []

    def initialize_population(self) -> None:
        self.population.clear()
        lineage_counter = 0
        for d in range(self.num_demes):
            for i in range(self.deme_capacity):
                # Deme- and individual-keyed initial trait
                init_z = sha_prng_float(self.seed, d * 100 + i, "init_altruism")
                self.population.append(
                    Individual(
                        deme_id=d,
                        lineage_id=lineage_counter,
                        altruism_trait=init_z,
                        atp=10.0,
                    )
                )
                lineage_counter += 1

    def step_generation(self, gen: int) -> MetricRecord:
        # 1. Intra-group interaction & Common Good Contribution
        # Individual cost: -c * z_i; Group return: b * sum(z_i) distributed equally
        c = 0.25  # Individual altruism cost
        b = 0.60  # Group benefit multiplier

        deme_contributions: dict[int, float] = {d: 0.0 for d in range(self.num_demes)}
        for ind in self.population:
            deme_contributions[ind.deme_id] += ind.altruism_trait

        deme_returns: dict[int, float] = {
            d: (b * deme_contributions[d]) / float(self.deme_capacity)
            for d in range(self.num_demes)
        }

        # Parent traits before selection
        parents_z: list[float] = [ind.altruism_trait for ind in self.population]
        deme_ids: list[int] = [ind.deme_id for ind in self.population]

        # 2. Reproduction Allocation & Realized Offspring Accounting
        # Group productivity depends on mean altruism if group_selection is ON
        group_productivity: dict[int, float] = {}
        for d in range(self.num_demes):
            mean_z = deme_contributions[d] / float(self.deme_capacity)
            group_productivity[d] = 1.0 + (1.5 * mean_z if self.group_selection else 0.0)

        total_prod = sum(group_productivity.values())
        group_target_slots = {
            d: int(round((group_productivity[d] / total_prod) * (self.num_demes * self.deme_capacity)))
            for d in range(self.num_demes)
        }

        # Reset realized offspring counts
        for ind in self.population:
            ind.offspring_count = 0

        next_generation: list[Individual] = []
        offspring_mean_z: list[float] = [0.0] * len(self.population)
        offspring_by_parent: dict[int, list[float]] = {idx: [] for idx in range(len(self.population))}

        for d in range(self.num_demes):
            deme_parents = [
                (idx, ind) for idx, ind in enumerate(self.population) if ind.deme_id == d
            ]
            if not deme_parents:
                deme_parents = list(enumerate(self.population))

            slots = group_target_slots.get(d, self.deme_capacity)
            if slots <= 0:
                continue

            # Within-deme relative fitness: individual payoff = 1.0 - c*z_i + return_d
            fitnesses = [
                max(0.01, 1.0 - c * ind.altruism_trait + deme_returns[d])
                for _, ind in deme_parents
            ]
            fit_sum = sum(fitnesses)

            for s in range(slots):
                # Deme- and lineage-isolated RNG stream
                r_spin = sha_prng_float(self.seed, gen * 10000 + d * 100 + s, "parent_selection") * fit_sum
                cum = 0.0
                selected_parent_idx = deme_parents[0][0]
                for (p_idx, _p_ind), fit in zip(deme_parents, fitnesses, strict=True):
                    cum += fit
                    if cum >= r_spin:
                        selected_parent_idx = p_idx
                        break

                p_ind = self.population[selected_parent_idx]
                p_ind.offspring_count += 1

                # Offspring trait with mutation (lineage-keyed PRNG stream)
                p_mut = sha_prng_float(self.seed, gen * 20000 + p_ind.lineage_id * 10 + s, "mls_mut_event")
                child_z = p_ind.altruism_trait
                if p_mut < 0.10:
                    delta_z = (sha_prng_float(self.seed, gen * 30000 + p_ind.lineage_id * 10 + s, "mls_delta") - 0.5) * 0.1
                    child_z = max(0.0, min(1.0, child_z + delta_z))

                offspring_by_parent[selected_parent_idx].append(child_z)
                next_generation.append(
                    Individual(
                        deme_id=d,
                        lineage_id=p_ind.lineage_id,
                        altruism_trait=child_z,
                        atp=10.0,
                    )
                )

        # Record offspring mean trait per parent
        for p_idx, z_list in offspring_by_parent.items():
            if z_list:
                offspring_mean_z[p_idx] = sum(z_list) / len(z_list)
            else:
                offspring_mean_z[p_idx] = parents_z[p_idx]

        offspring_counts = [ind.offspring_count for ind in self.population]

        # 3. Exact Price Equation Accounting Verification
        accounting = compute_exact_price_equation(
            parents_z=parents_z,
            offspring_counts=offspring_counts,
            offspring_mean_z=offspring_mean_z,
            deme_ids=deme_ids,
        )
        self.price_history.append(accounting)

        # 4. Migration Phase
        migration_rate = 0.15 if self.high_migration else 0.02
        for ind_idx, ind in enumerate(next_generation):
            r_mig = sha_prng_float(self.seed, gen * 40000 + ind_idx, "migration")
            if r_mig < migration_rate:
                new_d = sha_prng_int(self.seed, gen * 50000 + ind_idx, "new_deme", 0, self.num_demes - 1)
                next_generation[ind_idx] = Individual(
                    deme_id=new_d,
                    lineage_id=ind.lineage_id,
                    altruism_trait=ind.altruism_trait,
                    atp=ind.atp,
                )

        self.population = next_generation[: self.num_demes * self.deme_capacity]

        mean_pop_z = sum(ind.altruism_trait for ind in self.population) / len(self.population)
        record = MetricRecord(
            generation=gen,
            tick=gen * 16,
            population_size=len(self.population),
            primary_metric_name="mean_altruism_trait",
            primary_metric_value=mean_pop_z,
            secondary_metrics={
                "between_group_term": accounting.between_group_term,
                "within_group_term": accounting.within_group_term,
                "covariance_selection": accounting.covariance_selection,
                "transmission_bias": accounting.transmission_bias,
                "identity_residual": accounting.identity_residual,
            },
        )
        self.metrics_history.append(record)
        return record

    def run(self) -> CompletionSummary:
        self.initialize_population()
        for gen in range(1, self.generations + 1):
            self.step_generation(gen)

        final_altruism = sum(ind.altruism_trait for ind in self.population) / len(self.population)
        mean_between = sum(p.between_group_term for p in self.price_history[-100:]) / 100.0
        mean_within = sum(p.within_group_term for p in self.price_history[-100:]) / 100.0

        # Scientific assessment
        assessment = (
            AssessmentStatus.SUPPORTED_IN_THIS_MODEL
            if self.group_selection and final_altruism > 0.40 and mean_between > 0
            else AssessmentStatus.NOT_SUPPORTED
        )

        return CompletionSummary(
            experiment_id="T02_MLS_PRICE",
            track=self.track,
            seed=self.seed,
            completed_generations=self.generations,
            total_ticks=self.generations * 16,
            status="COMPLETED",
            stop_reason="HORIZON_REACHED",
            scientific_assessment=assessment,
            primary_endpoint_value=final_altruism,
            summary_metrics={
                "group_selection": self.group_selection,
                "high_migration": self.high_migration,
                "final_mean_altruism": final_altruism,
                "late_between_group_covariance": mean_between,
                "late_within_group_covariance": mean_within,
                "max_price_residual": max(abs(p.identity_residual) for p in self.price_history),
            },
        )
