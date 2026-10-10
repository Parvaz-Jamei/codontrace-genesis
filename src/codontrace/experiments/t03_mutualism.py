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

from collections.abc import Callable
from dataclasses import dataclass

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
    payoff_partner_removed_constitutive: tuple[float, float] | None = None

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
        track: ExecutionTrack = ExecutionTrack.REFERENCE,
    ) -> None:
        if not 0.0 <= vertical_transmission_rate <= 1.0:
            raise ValueError("vertical_transmission_rate must be in [0, 1]")
        if not 0.0 <= cooperation_cost < float("inf"):
            raise ValueError("cooperation_cost must be finite and nonnegative")
        self.seed = seed
        self.vertical_transmission_rate = vertical_transmission_rate
        self.cooperation_cost = cooperation_cost
        self.population_size = population_size
        self.generations = generations
        self.track = track
        validate_reference_run(self.population_size, generations, track)

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
        Symbiont baseline: 0.8 - cost * v + benefit * u
        Synergy multiplier: 1.2 * (u * v)
        """
        c = self.cooperation_cost
        b = 0.60
        synergy = 1.2 * (host_u * symbiont_v)

        host_w = max(0.05, 1.0 - c * host_u + b * symbiont_v + synergy)
        sym_w = max(0.05, 0.8 - c * symbiont_v + b * host_u + synergy)
        return host_w, sym_w

    def run_4_assays(self, gen: int) -> AssayResult:
        """Executes the 4 standardized assays on the contemporaneous population."""
        if not self.population:
            raise ValueError("Cannot assay an empty population")
        n = len(self.population)
        def average(values: list[tuple[float, float]]) -> tuple[float, float]:
            return sum(v[0] for v in values) / n, sum(v[1] for v in values) / n
        native_payoffs = average([self.evaluate_pair_payoffs(p.host_cooperation, p.symbiont_cooperation) for p in self.population])
        # Interaction investment is inducible: isolated individuals neither pay
        # cooperation costs nor receive partner benefits. Equal external resources.
        # This estimates NET interaction benefit; the previous persistent-cost
        # counterfactual estimated only gross benefit and could not detect harm.
        removed_payoffs = (1.0, 0.8)
        # Preserve the old persistent-cost measurement as a separate diagnostic;
        # it measures gross partner benefit and does not establish net mutualism.
        constitutive_removed = average([
            (max(0.05, 1.0 - self.cooperation_cost * p.host_cooperation),
             max(0.05, 0.8 - self.cooperation_cost * p.symbiont_cooperation))
            for p in self.population
        ])
        cheater_payoffs = average([self.evaluate_pair_payoffs(p.host_cooperation, 0.0) for p in self.population])
        indices = list(range(n))
        for i in range(n - 1, 0, -1):
            j = sha_prng_int(self.seed, gen * n + i, "assay_shuffle", 0, i)
            indices[i], indices[j] = indices[j], indices[i]
        scrambled_payoffs = average([self.evaluate_pair_payoffs(p.host_cooperation, self.population[indices[i]].symbiont_cooperation) for i, p in enumerate(self.population)])

        assay = AssayResult(
            generation=gen,
            payoff_with_partner=native_payoffs,
            payoff_partner_removed=removed_payoffs,
            payoff_non_cooperative=cheater_payoffs,
            payoff_scrambled_partner=scrambled_payoffs,
            payoff_partner_removed_constitutive=constitutive_removed,
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
            tick=0,
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

    def run(self, on_generation: Callable[[MetricRecord], None] | None = None) -> CompletionSummary:
        self.assay_history.clear()
        self.metrics_history.clear()
        self.initialize_population()
        for gen in range(1, self.generations + 1):
            record = self.step_generation(gen)
            if on_generation is not None:
                on_generation(record)

        final_assay = self.assay_history[-1] if self.assay_history and self.assay_history[-1].generation == self.generations else self.run_4_assays(self.generations)
        mutual_benefit = final_assay.mutual_benefit_achieved

        assessment = (
            AssessmentStatus.SUPPORTED_IN_THIS_MODEL
            if mutual_benefit
            else AssessmentStatus.NOT_SUPPORTED
        )

        return CompletionSummary(
            experiment_id="T03_TRANSITION_MUTUALISM",
            track=self.track,
            seed=self.seed,
            completed_generations=self.generations,
            total_ticks=0,
            status="COMPLETED",
            stop_reason="HORIZON_REACHED",
            scientific_assessment=assessment,
            primary_endpoint_value=1.0 if mutual_benefit else 0.0,
            summary_metrics={
                "assessed_claim": "immediate_net_partner_removal_benefit_only",
                "assay_counterfactual_version": "inducible-investment-removal-v2",
                "removal_cost_policy": "interaction_costs_absent_in_isolation",
                "collective_individuality_assessed": False,
                "final_assay_generation": final_assay.generation,
                "prng_int_stream_version": "sha256-rejection-v2", "engine_ticks_executed": 0,
                "vertical_transmission_rate": self.vertical_transmission_rate,
                "cooperation_cost": self.cooperation_cost,
                "mutual_benefit_achieved": mutual_benefit,
                "final_host_with_partner": final_assay.payoff_with_partner[0],
                "final_host_removed": final_assay.payoff_partner_removed[0],
                "final_symbiont_with_partner": final_assay.payoff_with_partner[1],
                "final_symbiont_removed": final_assay.payoff_partner_removed[1],
                "constitutive_cost_removal_diagnostic": final_assay.payoff_partner_removed_constitutive,
                "interpretation_notice": "Net benefit assumes inducible interaction investment; constitutive costs are reported separately. Neither assay establishes collective individuality.",
            },
        )
