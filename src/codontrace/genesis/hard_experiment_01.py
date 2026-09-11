"""Hard experiment 01: capsule source-bias vs next-generation fitness.

One measurement question, not a new Phase letter. Three paired arms:

- ``source_bias_on``: capsules on, ``min_source_fitness`` threshold +
  fitness-weighted adoption
- ``source_bias_off``: capsules on, threshold 0, threshold adoption (source
  fitness does not gate transfer)
- ``capsules_off``: transfer disabled (ablation of the capsule channel)

Outcome: last-tick mean organism fitness after a life-loop that can birth.
Research default is 12 paired seeds. Claim ceiling is ``runtime_observation``.
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


def default_research_seeds(seed_count: int = RESEARCH_SEED_COUNT) -> tuple[int, ...]:
    """Deterministic seed tuple. Research default is 12."""

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


def _mean_last_tick_fitness(result: object) -> float:
    ticks = tuple(getattr(result, "ticks", ()) or ())
    if not ticks:
        return 0.0
    generation = getattr(ticks[-1], "generation_result", None)
    if generation is None:
        return 0.0
    selection = getattr(generation, "selection_mean_fitness", None)
    if isinstance(selection, (int, float)) and not isinstance(selection, bool):
        return round(float(selection), 10)
    population = getattr(generation, "population", None)
    scores = [
        float(getattr(item, "score", 0.0) or 0.0)
        for item in getattr(population, "fitness", ()) or ()
    ]
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 10)


def _birth_count(result: object) -> int:
    total = 0
    for tick in getattr(result, "ticks", ()) or ():
        generation = getattr(tick, "generation_result", None)
        total += int(getattr(generation, "births", 0) or 0)
    return total


def _capsule_counts(result: object) -> tuple[int, int]:
    adoptions = len(tuple(getattr(result, "capsule_adoption_records", ()) or ()))
    sources = len(tuple(getattr(result, "capsule_source_fitness_records", ()) or ()))
    utilities = len(tuple(getattr(result, "capsule_utility_records", ()) or ()))
    transfers = len(tuple(getattr(result, "capsule_transfer_metrics", ()) or ()))
    return max(sources, utilities, transfers), adoptions


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
    terminal_mean_fitness: float
    births: int
    capsule_emissions: int
    capsule_adoptions: int
    spec_digest: str
    result_digest: str
    next_generation_observed: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "terminal_mean_fitness",
            require_finite_float("terminal_mean_fitness", self.terminal_mean_fitness),
        )
        if self.arm not in ARMS:
            raise ConfigurationError(f"unknown arm: {self.arm!r}")
        if self.births < 0 or self.capsule_emissions < 0 or self.capsule_adoptions < 0:
            raise ConfigurationError("counts must be >= 0.")
        if len(self.spec_digest) != 64 or len(self.result_digest) != 64:
            raise ConfigurationError("arm records require 64-hex spec/result digests.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "arm": self.arm,
            "terminal_mean_fitness": self.terminal_mean_fitness,
            "births": self.births,
            "capsule_emissions": self.capsule_emissions,
            "capsule_adoptions": self.capsule_adoptions,
            "spec_digest": self.spec_digest,
            "result_digest": self.result_digest,
            "next_generation_observed": self.next_generation_observed,
            "claim_ceiling": CLAIM_CEILING,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01SeedRecord:
    """Paired three-arm record for one seed."""

    seed: int
    source_bias_on: HardExperiment01ArmRecord
    source_bias_off: HardExperiment01ArmRecord
    capsules_off: HardExperiment01ArmRecord
    delta_vs_source_bias_off: float
    delta_vs_capsules_off: float

    def __post_init__(self) -> None:
        if self.source_bias_on.seed != self.seed or self.source_bias_off.seed != self.seed:
            raise ConfigurationError("seed records must share one seed.")
        if self.capsules_off.seed != self.seed:
            raise ConfigurationError("seed records must share one seed.")
        object.__setattr__(
            self,
            "delta_vs_source_bias_off",
            require_finite_float("delta_vs_source_bias_off", self.delta_vs_source_bias_off),
        )
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
class HardExperiment01Campaign:
    """Multi-seed source-bias campaign. Claim ceiling stays runtime_observation."""

    seeds: tuple[int, ...]
    seed_records: tuple[HardExperiment01SeedRecord, ...]
    mean_delta_vs_source_bias_off: float
    mean_delta_vs_capsules_off: float
    effect_vs_source_bias_off: EffectSizeResult
    effect_vs_capsules_off: EffectSizeResult
    replay_verified_seed: int
    replay_spec_digest: str
    replay_result_digest: str
    replay_matched: bool
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
        if not self.replay_matched:
            raise ConfigurationError("hard experiment 01 requires a matching replay digest.")
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
            "replay_spec_digest": self.replay_spec_digest,
            "replay_result_digest": self.replay_result_digest,
            "replay_matched": self.replay_matched,
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
    emissions, adoptions = _capsule_counts(result)
    return HardExperiment01ArmRecord(
        seed=seed,
        arm=arm,
        terminal_mean_fitness=_mean_last_tick_fitness(result),
        births=births,
        capsule_emissions=emissions,
        capsule_adoptions=adoptions,
        spec_digest=spec.digest(),
        result_digest=str(result.digest()),
        next_generation_observed=births > 0,
    )


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 10)


def run_hard_experiment_01(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    tick_count: int = DEFAULT_TICK_COUNT,
    population: int = DEFAULT_POPULATION,
) -> HardExperiment01Campaign:
    """Paired 12-seed source-bias campaign. Research default seed_count=12."""

    seed_tuple = _resolve_seeds(seeds, seed_count, default_count=RESEARCH_SEED_COUNT)
    records: list[HardExperiment01SeedRecord] = []
    on_fits: list[float] = []
    off_fits: list[float] = []
    none_fits: list[float] = []
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
        on_fits.append(on_rec.terminal_mean_fitness)
        off_fits.append(off_rec.terminal_mean_fitness)
        none_fits.append(none_rec.terminal_mean_fitness)
        records.append(
            HardExperiment01SeedRecord(
                seed=seed,
                source_bias_on=on_rec,
                source_bias_off=off_rec,
                capsules_off=none_rec,
                delta_vs_source_bias_off=round(
                    on_rec.terminal_mean_fitness - off_rec.terminal_mean_fitness, 10
                ),
                delta_vs_capsules_off=round(
                    on_rec.terminal_mean_fitness - none_rec.terminal_mean_fitness, 10
                ),
            )
        )
    replay_seed = seed_tuple[0]
    replay_spec, replay_result = _run_arm(
        seed=replay_seed,
        arm="source_bias_on",
        tick_count=tick_count,
        population=population,
    )
    first = records[0].source_bias_on
    replay_matched = (
        replay_spec.digest() == first.spec_digest
        and str(replay_result.digest()) == first.result_digest
    )
    campaign = HardExperiment01Campaign(
        seeds=seed_tuple,
        seed_records=tuple(records),
        mean_delta_vs_source_bias_off=_mean([item.delta_vs_source_bias_off for item in records]),
        mean_delta_vs_capsules_off=_mean([item.delta_vs_capsules_off for item in records]),
        effect_vs_source_bias_off=estimate_effect_size_lite(
            "terminal_mean_fitness", off_fits, on_fits
        ),
        effect_vs_capsules_off=estimate_effect_size_lite(
            "terminal_mean_fitness", none_fits, on_fits
        ),
        replay_verified_seed=replay_seed,
        replay_spec_digest=replay_spec.digest(),
        replay_result_digest=str(replay_result.digest()),
        replay_matched=replay_matched,
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
