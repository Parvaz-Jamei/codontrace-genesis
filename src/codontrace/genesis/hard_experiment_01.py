"""Hard experiment 01: capsule source-bias vs next-generation fitness.

One measurement question, not a new Phase letter. Three paired arms:

- ``source_bias_on``: capsules on, ``min_source_fitness`` threshold +
  fitness-weighted adoption
- ``source_bias_off``: capsules on, threshold 0, threshold adoption (source
  fitness does not gate transfer)
- ``capsules_off``: transfer disabled (ablation of the capsule channel)

Outcome: last-tick mean organism fitness after a life-loop that can birth.
Default seed_count=12 is smoke / exploratory
(``StatisticalTestPolicy.tier_for_n(12) == "exploratory_only"``).
Research-grade n is 30. Claim ceiling is ``runtime_observation``.
``ScientificClaimGate`` still blocks intelligence / collective_intelligence /
AGI / tokyo_type1_passed / avida_replacement.

This module does not auto-set ClaimGate flags. A null or small effect is a
valid finding.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.capsule import CapsuleAdoptionPolicy, CapsuleShuffleMode, CapsuleTransferConfig
from codontrace.genesis.claim_gate import ClaimDecision, ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.statistical_protocol import EffectSizeResult, estimate_effect_size_lite

CLAIM_CEILING = "runtime_observation"
RESEARCH_SEED_COUNT = 12
DEFAULT_TICK_COUNT = 6
DEFAULT_POPULATION = 4
EXPERIMENT_ID = "hard_experiment_01_capsule_source_bias"
SCHEMA_VERSION = "hard_experiment_01_v1"

ArmName = Literal["source_bias_on", "source_bias_off", "capsules_off"]
ARMS: tuple[ArmName, ...] = ("source_bias_on", "source_bias_off", "capsules_off")

_FORBIDDEN = frozenset(
    {
        "collective_intelligence",
        "proved_collective_intelligence",
        "intelligence",
        "agi",
        "open_ended_intelligence",
        "tokyo_type1_passed",
        "avida_replacement",
    }
)

_QUESTION = (
    "Does source-fitness-weighted capsule transfer change last-tick / "
    "next-generation mean fitness relative to (a) the same capsule channel "
    "with source-fitness gating ablated and (b) capsules off?"
)


@dataclass(frozen=True, slots=True)
class HardExperiment01Intervention:
    """Named knob change for one arm. Observation only, not a claim unlock."""

    arm: ArmName
    role: str
    target_mechanism: str
    action: str
    knob: str
    applied_value: str
    compared_to: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "arm": self.arm,
            "role": self.role,
            "target_mechanism": self.target_mechanism,
            "action": self.action,
            "knob": self.knob,
            "applied_value": self.applied_value,
            "compared_to": self.compared_to,
            "claim_ceiling": CLAIM_CEILING,
            "collective_intelligence": False,
        }


def hard_experiment_01_interventions() -> tuple[HardExperiment01Intervention, ...]:
    """Map each arm to one explicit CapsuleTransferConfig intervention."""

    return (
        HardExperiment01Intervention(
            arm="source_bias_on",
            role="treatment",
            target_mechanism="capsule_source_fitness_bias",
            action="enable_source_fitness_weighted_capsule_transfer",
            knob="CapsuleTransferConfig.min_source_fitness+adoption_policy",
            applied_value="min_source_fitness=2.0,FITNESS_WEIGHTED",
            compared_to="life_loop_world default capsules-off overlay",
        ),
        HardExperiment01Intervention(
            arm="source_bias_off",
            role="mechanism_ablation",
            target_mechanism="capsule_source_fitness_bias",
            action="disable_source_fitness_gating_keep_capsule_channel",
            knob="CapsuleTransferConfig.min_source_fitness+adoption_policy",
            applied_value="min_source_fitness=0.0,THRESHOLD",
            compared_to="source_bias_on",
        ),
        HardExperiment01Intervention(
            arm="capsules_off",
            role="channel_off",
            target_mechanism="capsule_transfer_channel",
            action="disable_capsule_transfer",
            knob="CapsuleTransferConfig.enabled",
            applied_value="enabled=False",
            compared_to="source_bias_on",
        ),
    )


def default_research_seeds(seed_count: int = RESEARCH_SEED_COUNT) -> tuple[int, ...]:
    """Deterministic seed tuple. 12 is smoke/exploratory; research-grade n is 30."""

    count = int(seed_count)
    if count < 2:
        raise ConfigurationError("hard experiment 01 seed_count must be >= 2.")
    return tuple(range(11, 11 + count))


def _resolve_seeds(
    seeds: Sequence[int] | None,
    seed_count: int | None,
    *,
    default_count: int,
) -> tuple[int, ...]:
    if seeds is not None:
        resolved = tuple(int(item) for item in seeds)
        if len(resolved) < 2:
            raise ConfigurationError("hard experiment 01 requires at least two seeds.")
        return resolved
    return default_research_seeds(default_count if seed_count is None else seed_count)


def build_hard_experiment_01_spec(
    *,
    seed: int,
    arm: ArmName,
    tick_count: int = DEFAULT_TICK_COUNT,
    population: int = DEFAULT_POPULATION,
) -> GenesisExperimentSpec:
    """Life-loop overlay. Does not mutate default Phase A–E preset digests."""

    if arm not in ARMS:
        raise ConfigurationError(f"unknown hard experiment 01 arm: {arm!r}")
    if tick_count <= 0 or population <= 0:
        raise ConfigurationError("tick_count and population must be > 0.")
    base = GenesisRuntimeProfile.life_loop_world(
        seed=seed, tick_count=tick_count, population=population
    )
    if arm == "capsules_off":
        capsule = CapsuleTransferConfig(enabled=False)
    elif arm == "source_bias_on":
        capsule = CapsuleTransferConfig(
            enabled=True,
            min_confidence=0.1,
            min_source_fitness=2.0,
            adoption_policy=CapsuleAdoptionPolicy.FITNESS_WEIGHTED,
            shuffle_mode=CapsuleShuffleMode.OFF,
            read_radius=6,
            emission_cost_runtime_atp=0.0,
            emission_cost_learning_atp=0.0,
            read_cost_runtime_atp=0.0,
            adoption_cost_learning_atp=0.0,
            adoption_requires_atp_learning=False,
            min_atp_runtime_to_emit=0.0,
            max_adoptions_per_organism=2,
            max_capsules_read_per_tick=4,
            accept_provisional_source_fitness=True,
        )
    else:
        capsule = CapsuleTransferConfig(
            enabled=True,
            min_confidence=0.1,
            min_source_fitness=0.0,
            adoption_policy=CapsuleAdoptionPolicy.THRESHOLD,
            shuffle_mode=CapsuleShuffleMode.OFF,
            read_radius=6,
            emission_cost_runtime_atp=0.0,
            emission_cost_learning_atp=0.0,
            read_cost_runtime_atp=0.0,
            adoption_cost_learning_atp=0.0,
            adoption_requires_atp_learning=False,
            min_atp_runtime_to_emit=0.0,
            max_adoptions_per_organism=2,
            max_capsules_read_per_tick=4,
            accept_provisional_source_fitness=True,
        )
    configs = base.population_configs
    if configs is None:
        raise ConfigurationError("life_loop_world must supply population_configs.")
    configs = replace(
        configs,
        capsule_transfer=capsule,
        enable_nexus_stigmergy=capsule.enabled,
    )
    engine_config = replace(base.engine_config, enable_capsules=capsule.enabled)
    metadata = {
        **base.metadata,
        "runtime_profile": EXPERIMENT_ID,
        "hard_experiment_01_arm": arm,
        "hard_experiment_01_question": _QUESTION,
        "claim_ceiling": CLAIM_CEILING,
        "collective_intelligence": False,
        "intelligence": False,
        "agi": False,
        "tokyo_type1_passed": False,
        "avida_replacement": False,
    }
    return replace(
        base,
        population_configs=configs,
        capsule_transfer_config=capsule,
        engine_config=engine_config,
        metadata=metadata,
    )


def _mean_last_tick_fitness(result: object) -> float | None:
    """Last-tick mean fitness, or None when the tick/generation is missing.

    A missing outcome must not be coerced to 0.0 — that would bias paired
    deltas toward zero. Callers drop the pair from the analysis.
    """

    ticks = tuple(getattr(result, "ticks", ()) or ())
    if not ticks:
        return None
    generation = getattr(ticks[-1], "generation_result", None)
    if generation is None:
        return None
    selection = getattr(generation, "selection_mean_fitness", None)
    if isinstance(selection, (int, float)) and not isinstance(selection, bool):
        return round(float(selection), 10)
    population = getattr(generation, "population", None)
    scores = [
        float(getattr(item, "score", 0.0) or 0.0)
        for item in getattr(population, "fitness", ()) or ()
    ]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 10)


def _birth_count(result: object) -> int:
    total = 0
    for tick in getattr(result, "ticks", ()) or ():
        generation = getattr(tick, "generation_result", None)
        total += int(getattr(generation, "births", 0) or 0)
    return total


def _capsule_counts(result: object) -> tuple[int, int, int, int]:
    """Count source, utility, transfer, and adoption records separately.

    These surfaces are not interchangeable. A max() across them would hide
    which channel actually fired.
    """

    sources = len(tuple(getattr(result, "capsule_source_fitness_records", ()) or ()))
    utilities = len(tuple(getattr(result, "capsule_utility_records", ()) or ()))
    transfers = len(tuple(getattr(result, "capsule_transfer_metrics", ()) or ()))
    adoptions = len(tuple(getattr(result, "capsule_adoption_records", ()) or ()))
    return sources, utilities, transfers, adoptions


def _run_arm(
    *,
    seed: int,
    arm: ArmName,
    tick_count: int,
    population: int,
) -> tuple[GenesisExperimentSpec, object]:
    spec = build_hard_experiment_01_spec(
        seed=seed, arm=arm, tick_count=tick_count, population=population
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    return spec, result


@dataclass(frozen=True, slots=True)
class HardExperiment01ArmRecord:
    """One seed × one arm. Fitness is a runtime observation, not intelligence."""

    seed: int
    arm: ArmName
    terminal_mean_fitness: float | None
    births: int
    capsule_source_count: int
    capsule_utility_count: int
    capsule_transfer_count: int
    capsule_adoptions: int
    spec_digest: str
    result_digest: str
    next_generation_observed: bool
    outcome_missing: bool = False

    def __post_init__(self) -> None:
        if self.outcome_missing:
            object.__setattr__(self, "terminal_mean_fitness", None)
        elif self.terminal_mean_fitness is None:
            raise ConfigurationError("terminal_mean_fitness is required when outcome_missing is false.")
        else:
            object.__setattr__(
                self,
                "terminal_mean_fitness",
                require_finite_float("terminal_mean_fitness", self.terminal_mean_fitness),
            )
        if self.arm not in ARMS:
            raise ConfigurationError(f"unknown arm: {self.arm!r}")
        if min(
            self.births,
            self.capsule_source_count,
            self.capsule_utility_count,
            self.capsule_transfer_count,
            self.capsule_adoptions,
        ) < 0:
            raise ConfigurationError("counts must be >= 0.")
        if len(self.spec_digest) != 64 or len(self.result_digest) != 64:
            raise ConfigurationError("arm records require 64-hex spec/result digests.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "arm": self.arm,
            "terminal_mean_fitness": self.terminal_mean_fitness,
            "births": self.births,
            "capsule_source_count": self.capsule_source_count,
            "capsule_utility_count": self.capsule_utility_count,
            "capsule_transfer_count": self.capsule_transfer_count,
            "capsule_adoptions": self.capsule_adoptions,
            "spec_digest": self.spec_digest,
            "result_digest": self.result_digest,
            "next_generation_observed": self.next_generation_observed,
            "outcome_missing": self.outcome_missing,
            "claim_ceiling": CLAIM_CEILING,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01SeedRecord:
    """Paired three-arm record for one seed."""

    seed: int
    source_bias_on: HardExperiment01ArmRecord
    source_bias_off: HardExperiment01ArmRecord
    capsules_off: HardExperiment01ArmRecord
    delta_vs_source_bias_off: float | None
    delta_vs_capsules_off: float | None

    def __post_init__(self) -> None:
        if self.source_bias_on.seed != self.seed or self.source_bias_off.seed != self.seed:
            raise ConfigurationError("seed records must share one seed.")
        if self.capsules_off.seed != self.seed:
            raise ConfigurationError("seed records must share one seed.")
        if self.delta_vs_source_bias_off is not None:
            object.__setattr__(
                self,
                "delta_vs_source_bias_off",
                require_finite_float("delta_vs_source_bias_off", self.delta_vs_source_bias_off),
            )
        if self.delta_vs_capsules_off is not None:
            object.__setattr__(
                self,
                "delta_vs_capsules_off",
                require_finite_float("delta_vs_capsules_off", self.delta_vs_capsules_off),
            )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "source_bias_on": self.source_bias_on.to_dict(),
            "source_bias_off": self.source_bias_off.to_dict(),
            "capsules_off": self.capsules_off.to_dict(),
            "delta_vs_source_bias_off": self.delta_vs_source_bias_off,
            "delta_vs_capsules_off": self.delta_vs_capsules_off,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01ReplayRecord:
    """Independent re-run of one seed × arm. Digests must match the campaign."""

    seed: int
    arm: ArmName
    spec_digest: str
    result_digest: str
    matched: bool

    def __post_init__(self) -> None:
        if self.arm not in ARMS:
            raise ConfigurationError(f"unknown arm: {self.arm!r}")
        if len(self.spec_digest) != 64 or len(self.result_digest) != 64:
            raise ConfigurationError("replay records require 64-hex spec/result digests.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "arm": self.arm,
            "spec_digest": self.spec_digest,
            "result_digest": self.result_digest,
            "matched": self.matched,
            "claim_ceiling": CLAIM_CEILING,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01Campaign:
    """Multi-seed source-bias campaign. Claim ceiling stays runtime_observation."""

    seeds: tuple[int, ...]
    seed_records: tuple[HardExperiment01SeedRecord, ...]
    mean_delta_vs_source_bias_off: float
    mean_delta_vs_capsules_off: float
    effect_vs_source_bias_off: EffectSizeResult
    effect_vs_capsules_off: EffectSizeResult
    replay_verified_seed: int
    replay_verified_seeds: tuple[int, ...]
    replay_records: tuple[HardExperiment01ReplayRecord, ...]
    replay_spec_digest: str
    replay_result_digest: str
    replay_matched: bool
    missing_outcomes_per_arm: tuple[tuple[str, int], ...] = ()
    interventions: tuple[HardExperiment01Intervention, ...] = ()
    question: str = _QUESTION
    claim_ceiling: str = CLAIM_CEILING
    schema_version: str = SCHEMA_VERSION
    experiment_id: str = EXPERIMENT_ID
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2 or len(self.seeds) != len(self.seed_records):
            raise ConfigurationError("campaign requires paired seed records for every seed.")
        if self.claim_ceiling != CLAIM_CEILING or self.claim_ceiling in _FORBIDDEN:
            raise ConfigurationError("hard experiment 01 ceiling must stay runtime_observation.")
        if not self.replay_records:
            raise ConfigurationError("hard experiment 01 requires replay records for first and last seeds.")
        if not self.replay_matched or not all(item.matched for item in self.replay_records):
            raise ConfigurationError("hard experiment 01 requires a matching replay digest.")
        replay_arms = {item.arm for item in self.replay_records}
        if replay_arms != set(ARMS):
            raise ConfigurationError("hard experiment 01 must replay every arm.")
        if not self.interventions:
            object.__setattr__(self, "interventions", hard_experiment_01_interventions())
        if not self.missing_outcomes_per_arm:
            object.__setattr__(
                self,
                "missing_outcomes_per_arm",
                tuple((arm, 0) for arm in ARMS),
            )
        missing_arms = {item[0] for item in self.missing_outcomes_per_arm}
        if missing_arms != set(ARMS):
            raise ConfigurationError("missing_outcomes_per_arm must cover every arm.")
        if any(count < 0 for _, count in self.missing_outcomes_per_arm):
            raise ConfigurationError("missing outcome counts must be >= 0.")
        expected_arms = {item.arm for item in self.interventions}
        if expected_arms != set(ARMS):
            raise ConfigurationError("hard experiment 01 interventions must cover every arm.")
        object.__setattr__(
            self,
            "mean_delta_vs_source_bias_off",
            require_finite_float(
                "mean_delta_vs_source_bias_off", self.mean_delta_vs_source_bias_off
            ),
        )
        object.__setattr__(
            self,
            "mean_delta_vs_capsules_off",
            require_finite_float("mean_delta_vs_capsules_off", self.mean_delta_vs_capsules_off),
        )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("HardExperiment01Campaign digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "question": self.question,
            "seeds": list(self.seeds),
            "seed_records": [item.to_dict() for item in self.seed_records],
            "mean_delta_vs_source_bias_off": self.mean_delta_vs_source_bias_off,
            "mean_delta_vs_capsules_off": self.mean_delta_vs_capsules_off,
            "effect_vs_source_bias_off": self.effect_vs_source_bias_off.to_dict(),
            "effect_vs_capsules_off": self.effect_vs_capsules_off.to_dict(),
            "replay_verified_seed": self.replay_verified_seed,
            "replay_verified_seeds": list(self.replay_verified_seeds),
            "replay_records": [item.to_dict() for item in self.replay_records],
            "replay_spec_digest": self.replay_spec_digest,
            "replay_result_digest": self.replay_result_digest,
            "replay_matched": self.replay_matched,
            "missing_outcomes_per_arm": {
                arm: count for arm, count in self.missing_outcomes_per_arm
            },
            "interventions": [item.to_dict() for item in self.interventions],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "intelligence": False,
            "agi": False,
            "tokyo_type1_passed": False,
            "avida_replacement": False,
            "claim_gate_flags_auto_set": False,
            "limitations": [
                "life_loop_overlay_not_avida_isa",
                "source_bias_is_min_source_fitness_plus_fitness_weighted_adoption",
                "terminal_mean_fitness_is_last_tick_observation",
                "missing_last_tick_outcomes_are_dropped_not_zero_filled",
                "null_or_small_effect_is_a_valid_finding",
                "not_knowledge_transfer_proof",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _arm_record(
    *,
    seed: int,
    arm: ArmName,
    tick_count: int,
    population: int,
) -> HardExperiment01ArmRecord:
    spec, result = _run_arm(
        seed=seed, arm=arm, tick_count=tick_count, population=population
    )
    births = _birth_count(result)
    sources, utilities, transfers, adoptions = _capsule_counts(result)
    fitness = _mean_last_tick_fitness(result)
    return HardExperiment01ArmRecord(
        seed=seed,
        arm=arm,
        terminal_mean_fitness=fitness,
        births=births,
        capsule_source_count=sources,
        capsule_utility_count=utilities,
        capsule_transfer_count=transfers,
        capsule_adoptions=adoptions,
        spec_digest=spec.digest(),
        result_digest=str(result.digest()),
        next_generation_observed=births > 0,
        outcome_missing=fitness is None,
    )


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 10)


def _optional_delta(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return round(left - right, 10)


def _complete_pair_values(
    records: Sequence[HardExperiment01SeedRecord],
    *,
    treatment_arm: ArmName,
    baseline_arm: ArmName,
) -> tuple[list[float], list[float]]:
    treatment: list[float] = []
    baseline: list[float] = []
    for record in records:
        treat = getattr(record, treatment_arm)
        base = getattr(record, baseline_arm)
        if treat.outcome_missing or base.outcome_missing:
            continue
        if treat.terminal_mean_fitness is None or base.terminal_mean_fitness is None:
            continue
        treatment.append(treat.terminal_mean_fitness)
        baseline.append(base.terminal_mean_fitness)
    return baseline, treatment


def _effect_or_insufficient(
    metric_name: str, baseline: Sequence[float], treatment: Sequence[float]
) -> EffectSizeResult:
    if not baseline or not treatment:
        return EffectSizeResult(
            metric_name=metric_name,
            baseline_mean=0.0,
            treatment_mean=0.0,
            mean_delta=0.0,
            standardized_delta_lite=0.0,
            sample_count=0,
            interpretation="insufficient_paired_outcomes",
        )
    return estimate_effect_size_lite(metric_name, baseline, treatment)


def _original_arm(
    records: Sequence[HardExperiment01SeedRecord], seed: int, arm: ArmName
) -> HardExperiment01ArmRecord:
    for record in records:
        if record.seed == seed:
            return getattr(record, arm)
    raise ConfigurationError(f"no campaign record for seed {seed} arm {arm}.")


def _replay_arm(
    original: HardExperiment01ArmRecord,
    *,
    tick_count: int,
    population: int,
) -> HardExperiment01ReplayRecord:
    spec, result = _run_arm(
        seed=original.seed,
        arm=original.arm,
        tick_count=tick_count,
        population=population,
    )
    spec_digest = spec.digest()
    result_digest = str(result.digest())
    return HardExperiment01ReplayRecord(
        seed=original.seed,
        arm=original.arm,
        spec_digest=spec_digest,
        result_digest=result_digest,
        matched=spec_digest == original.spec_digest and result_digest == original.result_digest,
    )


def _missing_outcomes_per_arm(
    records: Sequence[HardExperiment01SeedRecord],
) -> tuple[tuple[str, int], ...]:
    counts = {arm: 0 for arm in ARMS}
    for record in records:
        for arm in ARMS:
            if getattr(record, arm).outcome_missing:
                counts[arm] += 1
    return tuple((arm, counts[arm]) for arm in ARMS)


def run_hard_experiment_01(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    tick_count: int = DEFAULT_TICK_COUNT,
    population: int = DEFAULT_POPULATION,
) -> HardExperiment01Campaign:
    """Paired source-bias campaign. Default seed_count=12 is exploratory; research n=30."""

    seed_tuple = _resolve_seeds(seeds, seed_count, default_count=RESEARCH_SEED_COUNT)
    records: list[HardExperiment01SeedRecord] = []
    for seed in seed_tuple:
        on_rec = _arm_record(
            seed=seed, arm="source_bias_on", tick_count=tick_count, population=population
        )
        off_rec = _arm_record(
            seed=seed, arm="source_bias_off", tick_count=tick_count, population=population
        )
        none_rec = _arm_record(
            seed=seed, arm="capsules_off", tick_count=tick_count, population=population
        )
        records.append(
            HardExperiment01SeedRecord(
                seed=seed,
                source_bias_on=on_rec,
                source_bias_off=off_rec,
                capsules_off=none_rec,
                delta_vs_source_bias_off=_optional_delta(
                    on_rec.terminal_mean_fitness, off_rec.terminal_mean_fitness
                ),
                delta_vs_capsules_off=_optional_delta(
                    on_rec.terminal_mean_fitness, none_rec.terminal_mean_fitness
                ),
            )
        )
    off_fits, on_vs_off = _complete_pair_values(
        records, treatment_arm="source_bias_on", baseline_arm="source_bias_off"
    )
    none_fits, on_vs_none = _complete_pair_values(
        records, treatment_arm="source_bias_on", baseline_arm="capsules_off"
    )
    replay_seeds = tuple(dict.fromkeys((seed_tuple[0], seed_tuple[-1])))
    replay_records = tuple(
        _replay_arm(
            _original_arm(records, seed, arm),
            tick_count=tick_count,
            population=population,
        )
        for seed in replay_seeds
        for arm in ARMS
    )
    first_replay = next(
        item
        for item in replay_records
        if item.seed == seed_tuple[0] and item.arm == "source_bias_on"
    )
    campaign = HardExperiment01Campaign(
        seeds=seed_tuple,
        seed_records=tuple(records),
        mean_delta_vs_source_bias_off=_mean(
            [item.delta_vs_source_bias_off for item in records if item.delta_vs_source_bias_off is not None]
        ),
        mean_delta_vs_capsules_off=_mean(
            [item.delta_vs_capsules_off for item in records if item.delta_vs_capsules_off is not None]
        ),
        effect_vs_source_bias_off=_effect_or_insufficient(
            "terminal_mean_fitness", off_fits, on_vs_off
        ),
        effect_vs_capsules_off=_effect_or_insufficient(
            "terminal_mean_fitness", none_fits, on_vs_none
        ),
        replay_verified_seed=seed_tuple[0],
        replay_verified_seeds=replay_seeds,
        replay_records=replay_records,
        replay_spec_digest=first_replay.spec_digest,
        replay_result_digest=first_replay.result_digest,
        replay_matched=all(item.matched for item in replay_records),
        missing_outcomes_per_arm=_missing_outcomes_per_arm(records),
    )
    _assert_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


def evaluate_hard_experiment_01_claim(
    payload: Mapping[str, JsonValue] | object,
) -> ClaimDecision:
    """Runtime observation only. Intelligence claims stay blocked."""

    gate = ScientificClaimGate()
    to_dict = getattr(payload, "to_dict", None)
    data: Mapping[str, JsonValue]
    if callable(to_dict):
        raw = to_dict()
        data = raw if isinstance(raw, Mapping) else {}
    elif isinstance(payload, Mapping):
        data = payload
    else:
        data = {}
    digest = str(data.get("digest", "") or "")
    decision = gate.decide(
        ClaimRequest(CLAIM_CEILING, {}, evidence_digests=(digest,) if digest else ())
    )
    _assert_blocked(data, gate)
    return decision


def _assert_blocked(payload: Mapping[str, JsonValue], gate: ScientificClaimGate) -> None:
    for label in (
        "collective_intelligence",
        "intelligence",
        "agi",
        "tokyo_type1_passed",
        "avida_replacement",
    ):
        if payload.get(label) is True:
            raise ConfigurationError(f"hard experiment 01 must not set {label} True.")
        if gate.decide(ClaimRequest(label, {})).allowed:
            raise ConfigurationError(f"{label} must remain blocked.")


def _cohens_d_note(value: float) -> str:
    magnitude = abs(value)
    if magnitude < 0.2:
        return "negligible"
    if magnitude < 0.5:
        return "small"
    if magnitude < 0.8:
        return "medium"
    return "large"


def format_hard_experiment_01_summary(campaign: HardExperiment01Campaign) -> str:
    """Print-friendly measurement summary. Not a claim unlock."""

    vs_off = campaign.effect_vs_source_bias_off
    vs_none = campaign.effect_vs_capsules_off
    return "\n".join(
        (
            f"experiment {campaign.experiment_id}",
            f"question {campaign.question}",
            f"seed_count {len(campaign.seeds)}",
            f"mean_delta_vs_source_bias_off {campaign.mean_delta_vs_source_bias_off}",
            f"mean_delta_vs_capsules_off {campaign.mean_delta_vs_capsules_off}",
            f"effect_vs_source_bias_off {vs_off.standardized_delta_lite} {vs_off.interpretation}",
            f"effect_vs_capsules_off {vs_none.standardized_delta_lite} {vs_none.interpretation}",
            f"replay_matched {campaign.replay_matched}",
            f"claim_ceiling {campaign.claim_ceiling}",
            "collective_intelligence False",
            "intelligence False",
            f"digest {campaign.digest}",
            f"standardized_note {_cohens_d_note(vs_off.standardized_delta_lite)}",
        )
    )
