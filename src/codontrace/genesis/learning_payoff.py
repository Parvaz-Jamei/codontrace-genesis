"""Cue → action → ATP/task-reward protocol (Am Nat 2020 / odometry analog).

Clune 2007, Lalejini & Ofria 2016, and Frontiers 2021 Adaptive Phenotypic
Plasticity treat subsequent action under a sensory cue, with ablation, as the
experimental design. Am Nat 2020 associative learning and the PLOS One
odometry case study map here to capsule/memory slots that change later action
and ATP/task eligibility.

This protocol records that chain, requires an ablation contrast, and can
aggregate ≥2 seeds. ``instinct_improved`` stays ClaimGate-gated (multi-seed +
ablation on the Phase D pack). This module never upgrades to associative
learning proved, instinct evolution, or intelligence.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.claim_gate import ClaimDecision, ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec, GenesisRunResult
from codontrace.genesis.multi_generation import (
    InstinctAblationControl,
    build_multi_generation_evidence_pack,
    evaluate_instinct_improvement_claim,
)
from codontrace.genesis.phase_e import build_phase_e_evidence_pack
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.statistical_protocol import StatisticalProtocolConfig

_PACK_SCHEMA = "learning_causal_payoff_v1"
_CLAIM_CEILING = "runtime_observation"
_FORBIDDEN = frozenset(
    {
        "associative_learning_proved",
        "instinct_evolution_proved",
        "evolved_plasticity",
        "agi",
        "open_ended_intelligence",
        "tokyo_type1_passed",
    }
)

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "am_nat_2020_associative_learning",
        "American Naturalist 2020 associative learning in Avida: cue-conditioned "
        "subsequent action with a payoff. Protocol instrumentation only.",
    ),
    (
        "plos_one_odometry",
        "PLOS One odometry case study: navigation/memory mapped to capsule slots "
        "that change later action/ATP/task eligibility.",
    ),
    (
        "clune_lalejini_frontiers_2021_plasticity",
        "Clune 2007; Lalejini & Ofria 2016; Frontiers 2021 Adaptive Phenotypic "
        "Plasticity: subsequent-action effect under a sensory cue, with ablation.",
    ),
)


@dataclass(frozen=True, slots=True)
class CueActionPayoffRecord:
    """One seed's cue → action → ATP/task observation."""

    seed: int
    run_digest: str
    cue_source: str
    substitutions: int
    capsule_reads: int
    capsule_writes: int
    mean_runtime_atp: float
    ablation_run_digest: str = ""
    ablation_substitutions: int = 0
    payoff_delta_atp: float = 0.0
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "mean_runtime_atp",
            require_finite_float("mean_runtime_atp", self.mean_runtime_atp, non_negative=True),
        )
        object.__setattr__(
            self,
            "payoff_delta_atp",
            require_finite_float("payoff_delta_atp", self.payoff_delta_atp),
        )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("CueActionPayoffRecord digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "run_digest": self.run_digest,
            "cue_source": self.cue_source,
            "substitutions": self.substitutions,
            "capsule_reads": self.capsule_reads,
            "capsule_writes": self.capsule_writes,
            "mean_runtime_atp": self.mean_runtime_atp,
            "ablation_run_digest": self.ablation_run_digest,
            "ablation_substitutions": self.ablation_substitutions,
            "payoff_delta_atp": self.payoff_delta_atp,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class LearningCausalPayoffPack:
    """Multi-seed cue→action→payoff protocol. instinct_improved stays gated."""

    records: tuple[CueActionPayoffRecord, ...]
    seed_count: int
    ablation_present: bool
    substitutions_on: int
    substitutions_off: int
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    instinct_improved_status: str = "gated_requires_phase_d_claim_gate"
    schema_version: str = _PACK_SCHEMA
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_ceiling in _FORBIDDEN or self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError(
                "LearningCausalPayoffPack claim_ceiling must stay runtime_observation."
            )
        if self.instinct_improved_status in _FORBIDDEN:
            raise ConfigurationError("LearningCausalPayoffPack must not claim instinct proved.")
        if self.seed_count < 1:
            raise ConfigurationError("seed_count must be >= 1.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("LearningCausalPayoffPack digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "records": [item.to_dict() for item in self.records],
            "seed_count": self.seed_count,
            "ablation_present": self.ablation_present,
            "substitutions_on": self.substitutions_on,
            "substitutions_off": self.substitutions_off,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "instinct_improved_status": self.instinct_improved_status,
            "associative_learning_proved": False,
            "limitations": [
                "protocol_instrumentation_not_associative_learning_proof",
                "instinct_improved_remains_claim_gate_gated",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _mean_runtime_atp(result: GenesisRunResult) -> float:
    totals: list[float] = []
    for tick in result.ticks:
        generation = tick.generation_result
        population = generation.population
        for organism in population.organisms:
            totals.append(float(organism.atp_state.runtime_available))
    if not totals:
        return 0.0
    return round(sum(totals) / len(totals), 10)


def _record_for_seed(
    seed: int,
    *,
    tick_count: int,
    population: int,
) -> CueActionPayoffRecord:
    on_spec = GenesisRuntimeProfile.phase_e_substrate_world(
        seed=seed,
        tick_count=tick_count,
        population=population,
        enable_capsule_memory=True,
        enable_demes=False,
        seed_preferred_action="EAT_LUMEN",
    )
    off_spec = GenesisRuntimeProfile.phase_e_substrate_world(
        seed=seed,
        tick_count=tick_count,
        population=population,
        enable_capsule_memory=False,
        enable_demes=False,
        seed_preferred_action="",
    )
    on_result = GenesisEngine.from_spec(on_spec).run_ticks()
    off_result = GenesisEngine.from_spec(off_spec).run_ticks()
    on_pack = build_phase_e_evidence_pack(on_result)
    off_pack = build_phase_e_evidence_pack(off_result)
    on_atp = _mean_runtime_atp(on_result)
    off_atp = _mean_runtime_atp(off_result)
    return CueActionPayoffRecord(
        seed=seed,
        run_digest=on_result.digest(),
        cue_source="phase_c_env_and_local_patches",
        substitutions=on_pack.observation.capsule_substitutions,
        capsule_reads=on_pack.observation.capsule_reads,
        capsule_writes=on_pack.observation.capsule_writes,
        mean_runtime_atp=on_atp,
        ablation_run_digest=off_result.digest(),
        ablation_substitutions=off_pack.observation.capsule_substitutions,
        payoff_delta_atp=round(on_atp - off_atp, 10),
    )


def build_learning_causal_payoff_pack(
    *,
    seeds: Sequence[int] = (7, 11),
    tick_count: int = 8,
    population: int = 4,
    treatment: GenesisRunResult | None = None,
    ablation: GenesisRunResult | None = None,
    treatment_spec: GenesisExperimentSpec | None = None,
) -> LearningCausalPayoffPack:
    """Build the cue→action→payoff protocol with ablation.

    Pass ``seeds`` with length ≥ 2 for the multi-seed path, or pass an already
    executed treatment/ablation pair (single-seed protocol record).
    """

    records: list[CueActionPayoffRecord]
    if treatment is not None and ablation is not None:
        on_pack = build_phase_e_evidence_pack(treatment)
        off_pack = build_phase_e_evidence_pack(ablation)
        seed = int(getattr(treatment_spec, "seed", getattr(treatment, "seed", 0)) or 0)
        on_atp = _mean_runtime_atp(treatment)
        off_atp = _mean_runtime_atp(ablation)
        records = [
            CueActionPayoffRecord(
                seed=seed,
                run_digest=treatment.digest(),
                cue_source="phase_c_env_and_local_patches",
                substitutions=on_pack.observation.capsule_substitutions,
                capsule_reads=on_pack.observation.capsule_reads,
                capsule_writes=on_pack.observation.capsule_writes,
                mean_runtime_atp=on_atp,
                ablation_run_digest=ablation.digest(),
                ablation_substitutions=off_pack.observation.capsule_substitutions,
                payoff_delta_atp=round(on_atp - off_atp, 10),
            )
        ]
    else:
        if len(tuple(seeds)) < 1:
            raise ConfigurationError("build_learning_causal_payoff_pack requires at least one seed.")
        records = [
            _record_for_seed(int(seed), tick_count=tick_count, population=population)
            for seed in seeds
        ]
    substitutions_on = sum(item.substitutions for item in records)
    substitutions_off = sum(item.ablation_substitutions for item in records)
    return LearningCausalPayoffPack(
        records=tuple(records),
        seed_count=len(records),
        ablation_present=all(item.ablation_run_digest for item in records),
        substitutions_on=substitutions_on,
        substitutions_off=substitutions_off,
    )


def evaluate_learning_causal_payoff_claim(
    pack: LearningCausalPayoffPack,
    gate: ScientificClaimGate | None = None,
) -> ClaimDecision:
    """Runtime observation only. Associative-learning-proved stays blocked."""

    resolved = gate or ScientificClaimGate()
    decision = resolved.decide(ClaimRequest(_CLAIM_CEILING, {}, evidence_digests=(pack.digest,)))
    blocked = resolved.decide(ClaimRequest("associative_learning_proved", {}))
    if blocked.allowed:
        raise ConfigurationError("associative_learning_proved must remain blocked.")
    instinct = resolved.decide(ClaimRequest("instinct_improved", {}))
    if instinct.allowed and not (
        pack.seed_count >= 2 and pack.ablation_present
    ):
        raise ConfigurationError("instinct_improved must stay gated without Phase D evidence.")
    return decision


def instinct_improved_remains_gated(
    treatment: GenesisRunResult,
    ablation: GenesisRunResult,
    *,
    spec: GenesisExperimentSpec,
    multi_seed: bool = False,
) -> ClaimDecision:
    """Show that this protocol does not unlock instinct_improved by itself."""

    control = InstinctAblationControl(
        control_kind="capsules_off_ablation",
        treatment_fitness_delta=0.0,
        control_fitness_delta=0.0,
        treatment_exceeds_control=False,
        treatment_run_digest=treatment.digest(),
        control_run_digest=ablation.digest(),
    )
    protocol = (
        StatisticalProtocolConfig(min_seeds=2) if multi_seed else None
    )
    pack = build_multi_generation_evidence_pack(
        treatment,
        spec=spec,
        ablation_control=control,
        multi_seed_protocol=protocol,
    )
    return evaluate_instinct_improvement_claim(pack)
