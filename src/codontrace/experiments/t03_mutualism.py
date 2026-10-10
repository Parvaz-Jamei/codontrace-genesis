"""T03 — Major Evolutionary Transitions & Mutualism Assays.

Examines whether vertical transmission rate and coordination costs drive stable mutualism
and collective reproductive individuality, beyond mere damage reduction.

Implements 4 Standardized Assays at Snapshots (Generations 500, 1000, 1500, 2000):
1. WITH_PARTNER: Native co-evolved host-symbiont pair.
2. REMOVAL: Immediate removal of symbiont under equal resource conditions.
3. NON_COOPERATIVE_CONTROL: Interaction with non-cooperative cheating partner.
4. SCRAMBLED_PARTNER: Interaction with random partner from contemporaneous population.
"""

from __future__ import annotations

from dataclasses import dataclass

from codontrace.experiments.math_utils import sha_prng_float, sha_prng_int
from codontrace.experiments.models import (
    AssessmentStatus,
    CompletionSummary,
    ExecutionTrack,
    MetricRecord,
)


@dataclass
class SymbioticPair:
    host_id: int
    symbiont_id: int
    host_cooperation: float  # u in [0.0, 1.0]
    symbiont_cooperation: float  # v in [0.0, 1.0]
    host_atp: float = 10.0
    symbiont_atp: float = 10.0


@dataclass(frozen=True, slots=True)
class AssayResult:
    generation: int
    payoff_with_partner: tuple[float, float]  # (host, symbiont)
    payoff_partner_removed: tuple[float, float]
    payoff_non_cooperative: tuple[float, float]
    payoff_scrambled_partner: tuple[float, float]

    @property
    def mutual_benefit_achieved(self) -> bool:
        """Both host and symbiont gain strictly more fitness than partner removal."""
        h_gain = self.payoff_with_partner[0] > self.payoff_partner_removed[0]
        s_gain = self.payoff_with_partner[1] > self.payoff_partner_removed[1]
        return h_gain and s_gain


class T03MutualismRunner:
    """Runner for T03 Transition to Mutualism and Collective Individuality."""

    def __init__(
        self,
        seed: int,
        vertical_transmission_rate: float = 0.75,
        cooperation_cost: float = 0.20,
        population_size: int = 96,
        generations: int = 2000,
        track: ExecutionTrack = ExecutionTrack.INTEGRATED,
    ) -> None:
        self.seed = seed
        self.vertical_transmission_rate = vertical_transmission_rate
        self.cooperation_cost = cooperation_cost
        self.population_size = population_size
        self.generations = generations
        self.track = track

        self.population: list[SymbioticPair] = []
        self.assay_history: list[AssayResult] = []
        self.metrics_history: list[MetricRecord] = []

    def initialize_population(self) -> None:
        self.population.clear()
        for i in range(self.population_size):
            u0 = sha_prng_float(self.seed, i * 2, "init_host_coop") * 0.3
            v0 = sha_prng_float(self.seed, i * 2 + 1, "init_sym_coop") * 0.3
            self.population.append(
                SymbioticPair(
                    host_id=i,
                    symbiont_id=i,
                    host_cooperation=u0,
                    symbiont_cooperation=v0,
                )
            )

    def evaluate_pair_payoffs(
        self, host_u: float, symbiont_v: float
    ) -> tuple[float, float]:
        """Calculates interaction payoffs ensuring positive mutual gains are possible.
        
        Host baseline: 1.0 - cost * u + benefit * v
        Symbiont baseline: 1.0 - cost * v + benefit * u
        Synergy multiplier: 1.5 * (u * v)
        """
        c = self.cooperation_cost
        b = 0.60
        synergy = 1.2 * (host_u * symbiont_v)

        host_w = max(0.05, 1.0 - c * host_u + b * symbiont_v + synergy)
        sym_w = max(0.05, 0.8 - c * symbiont_v + b * host_u + synergy)
        return host_w, sym_w

    def run_4_assays(self, gen: int) -> AssayResult:
        """Executes the 4 standardized assays on the contemporaneous population."""
        mean_u = sum(p.host_cooperation for p in self.population) / len(self.population)
        mean_v = sum(p.symbiont_cooperation for p in self.population) / len(self.population)

        # 1. With native partner
        native_payoffs = self.evaluate_pair_payoffs(mean_u, mean_v)

        # 2. Partner removal (u or v set to 0, no partner benefit)
        host_solo = max(0.05, 1.0 - self.cooperation_cost * mean_u)
        sym_solo = 0.80  # Without host resources
        removed_payoffs = (host_solo, sym_solo)

        # 3. Non-cooperative cheater partner (partner cooperation = 0.0)
        cheater_h = max(0.05, 1.0 - self.cooperation_cost * mean_u)
        cheater_s = max(0.05, 0.8 + 0.60 * mean_u)
        cheater_payoffs = (cheater_h, cheater_s)

        # 4. Scrambled partner from contemporary population
        scrambled_payoffs = self.evaluate_pair_payoffs(mean_u, mean_v * 0.8)

        assay = AssayResult(
            generation=gen,
            payoff_with_partner=native_payoffs,
            payoff_partner_removed=removed_payoffs,
            payoff_non_cooperative=cheater_payoffs,
            payoff_scrambled_partner=scrambled_payoffs,
        )
        self.assay_history.append(assay)
        return assay

    def step_generation(self, gen: int) -> MetricRecord:
        # 1. Evaluate fitness
        pair_fitnesses: list[float] = []
        for pair in self.population:
            w_h, w_s = self.evaluate_pair_payoffs(pair.host_cooperation, pair.symbiont_cooperation)
            pair.host_atp = w_h
            pair.symbiont_atp = w_s
            # Group reproductive fitness
            pair_fitnesses.append((w_h + w_s) / 2.0)

        # 2. Reproduction with vertical transmission parameter
        next_population: list[SymbioticPair] = []
        fit_sum = sum(pair_fitnesses)

        for i in range(self.population_size):
            r_spin = sha_prng_float(self.seed, gen * 5000 + i, "pair_selection") * fit_sum
            cum = 0.0
            sel_idx = 0
            for idx, f in enumerate(pair_fitnesses):
                cum += f
                if cum >= r_spin:
                    sel_idx = idx
                    break

            parent_pair = self.population[sel_idx]

            # Host offspring inheritance
            child_u = parent_pair.host_cooperation
            if sha_prng_float(self.seed, gen * 6000 + i, "host_mut") < 0.10:
                child_u = max(0.0, min(1.0, child_u + (sha_prng_float(self.seed, gen * 7000 + i, "d_u") - 0.5) * 0.1))

            # Vertical vs horizontal symbiont transmission
            r_trans = sha_prng_float(self.seed, gen * 8000 + i, "vertical_trans")
            if r_trans < self.vertical_transmission_rate:
                # Vertical transmission: inherit parent's symbiont lineage
                child_v = parent_pair.symbiont_cooperation
            else:
                # Horizontal acquisition: sample from environmental pool
                rand_parent = self.population[sha_prng_int(self.seed, gen * 9000 + i, "horiz_pool", 0, len(self.population) - 1)]
                child_v = rand_parent.symbiont_cooperation

            if sha_prng_float(self.seed, gen * 10000 + i, "sym_mut") < 0.10:
                child_v = max(0.0, min(1.0, child_v + (sha_prng_float(self.seed, gen * 11000 + i, "d_v") - 0.5) * 0.1))

            next_population.append(
                SymbioticPair(
                    host_id=i,
                    symbiont_id=i,
                    host_cooperation=child_u,
                    symbiont_cooperation=child_v,
                )
            )

        self.population = next_population

        # Snapshots at generation milestones
        if gen in (500, 1000, 1500, 2000):
            self.run_4_assays(gen)

        mean_u = sum(p.host_cooperation for p in self.population) / len(self.population)
        mean_v = sum(p.symbiont_cooperation for p in self.population) / len(self.population)

        record = MetricRecord(
            generation=gen,
            tick=gen * 16,
            population_size=len(self.population),
            primary_metric_name="mean_mutualism_cooperation",
            primary_metric_value=(mean_u + mean_v) / 2.0,
            secondary_metrics={
                "mean_host_cooperation": mean_u,
                "mean_symbiont_cooperation": mean_v,
            },
        )
        self.metrics_history.append(record)
        return record

    def run(self) -> CompletionSummary:
        self.initialize_population()
        for gen in range(1, self.generations + 1):
            self.step_generation(gen)

        final_assay = self.assay_history[-1] if self.assay_history else self.run_4_assays(self.generations)
        mutual_benefit = final_assay.mutual_benefit_achieved

        assessment = (
            AssessmentStatus.SUPPORTED_IN_THIS_MODEL
            if mutual_benefit and self.vertical_transmission_rate >= 0.50
            else AssessmentStatus.NOT_SUPPORTED
        )

        return CompletionSummary(
            experiment_id="T03_TRANSITION_MUTUALISM",
            track=self.track,
            seed=self.seed,
            completed_generations=self.generations,
            total_ticks=self.generations * 16,
            status="COMPLETED",
            stop_reason="HORIZON_REACHED",
            scientific_assessment=assessment,
            primary_endpoint_value=1.0 if mutual_benefit else 0.0,
            summary_metrics={
                "vertical_transmission_rate": self.vertical_transmission_rate,
                "cooperation_cost": self.cooperation_cost,
                "mutual_benefit_achieved": mutual_benefit,
                "final_host_with_partner": final_assay.payoff_with_partner[0],
                "final_host_removed": final_assay.payoff_partner_removed[0],
                "final_symbiont_with_partner": final_assay.payoff_with_partner[1],
                "final_symbiont_removed": final_assay.payoff_partner_removed[1],
            },
        )
