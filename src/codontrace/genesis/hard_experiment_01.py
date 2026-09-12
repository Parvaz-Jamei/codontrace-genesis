"""Hard experiment 01: capsule source-bias vs next-generation fitness.

One measurement question, not a new Phase letter. Four paired arms:

- ``source_bias_on``: capsules on, ``min_source_fitness`` threshold +
  fitness-weighted adoption (treatment)
- ``source_bias_off``: capsules on, threshold 0, threshold adoption (source
  fitness does not gate transfer; mechanism ablation)
- ``capsules_off``: transfer disabled (channel-off ablation)
- ``capsules_shuffled``: capsules on, same fitness-weighted knobs as treatment,
  ``CapsuleShuffleMode.SOURCE`` permutes source identities/weights so content
  is not causally tied to source fitness (negative / specificity control)

Dose-response: ``min_source_fitness`` ladder on the treatment channel
(FITNESS_WEIGHTED, shuffle off) with at least three levels.

Outcome: last-tick mean organism fitness after a life-loop that can birth.
Default seed_count=12 is smoke / exploratory
(``StatisticalTestPolicy.tier_for_n(12) == "exploratory_only"``).
Research-grade n is 30
(``StatisticalTestPolicy.tier_for_n(30) == "research_grade_benchmark_candidate"``).
Claim ceiling stays ``runtime_observation`` until a dated digest-backed
campaign artifact is archived. The design *may* later support
``intervention_supported``; this module never auto-sets that flag.
``ScientificClaimGate`` still blocks intelligence / collective_intelligence /
AGI / tokyo_type1_passed / avida_replacement.

Price-equation terms are a statistical identity, not automatic causation
(Okasha & Otsuka 2020; van Veelen 2020). Causal reading requires the explicit
DAG and do()-style arms below. A null or small effect is a valid finding.
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
from codontrace.genesis.statistical_protocol import (
    EffectSizeResult,
    StatisticalTestPolicy,
    bootstrap_ci_paired,
    estimate_effect_size_lite,
    exact_sign_flip_permutation_p,
    holm_correction,
    paired_effect_size,
)

CLAIM_CEILING = "runtime_observation"
DESIGN_CLAIM_CEILING = "intervention_supported"
RESEARCH_SEED_COUNT = 12
RESEARCH_GRADE_SEED_COUNT = 30
DEFAULT_TICK_COUNT = 6
DEFAULT_POPULATION = 4
EXPERIMENT_ID = "hard_experiment_01_capsule_source_bias"
SCHEMA_VERSION = "hard_experiment_01_v2"
DOSE_KNOB = "CapsuleTransferConfig.min_source_fitness"
DEFAULT_DOSE_LEVELS: tuple[float, ...] = (0.0, 1.0, 2.0)
SHUFFLED_CONTROL_MODE = CapsuleShuffleMode.SOURCE
TREATMENT_MIN_SOURCE_FITNESS = 2.0

ArmName = Literal["source_bias_on", "source_bias_off", "capsules_off", "capsules_shuffled"]
ARMS: tuple[ArmName, ...] = (
    "source_bias_on",
    "source_bias_off",
    "capsules_off",
    "capsules_shuffled",
)
PLANNED_CONTRASTS: tuple[tuple[str, ArmName], ...] = (
    ("vs_source_bias_off", "source_bias_off"),
    ("vs_capsules_off", "capsules_off"),
    ("vs_capsules_shuffled", "capsules_shuffled"),
)

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
    "with source-fitness gating ablated, (b) capsules off, and (c) a "
    "digest-reproducible shuffled-source negative control that preserves "
    "capsule traffic while destroying source→recipient fitness coupling? "
    "Does the outcome change monotonically across a min_source_fitness dose "
    "ladder? Price-equation terms are a statistical identity, not automatic "
    "causation; causal reading requires the explicit DAG and do()-style arms."
)

_SHUFFLED_RATIONALE = (
    "Negative control / specificity control: keep capsule traffic, "
    "FITNESS_WEIGHTED adoption, and min_source_fitness=2.0, but permute "
    "source identities and source-fitness weights via CapsuleShuffleMode.SOURCE "
    "so capsule content is not causally tied to the emitting source's fitness. "
    "The shuffle is payload-level and digest-reproducible. Goldsby-style "
    "isolation is the ablation pattern (channel off / shuffled), not a second "
    "product story."
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
    cuts_dag_edge: str
    do_intervention: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "arm": self.arm,
            "role": self.role,
            "target_mechanism": self.target_mechanism,
            "action": self.action,
            "knob": self.knob,
            "applied_value": self.applied_value,
            "compared_to": self.compared_to,
            "cuts_dag_edge": self.cuts_dag_edge,
            "do_intervention": self.do_intervention,
            "claim_ceiling": CLAIM_CEILING,
            "design_claim_ceiling": DESIGN_CLAIM_CEILING,
            "collective_intelligence": False,
        }


def hard_experiment_01_interventions() -> tuple[HardExperiment01Intervention, ...]:
    """Map each arm to one explicit CapsuleTransferConfig / do() intervention."""

    return (
        HardExperiment01Intervention(
            arm="source_bias_on",
            role="treatment",
            target_mechanism="capsule_source_fitness_bias",
            action="enable_source_fitness_weighted_capsule_transfer",
            knob="CapsuleTransferConfig.min_source_fitness+adoption_policy",
            applied_value="min_source_fitness=2.0,FITNESS_WEIGHTED,shuffle=off",
            compared_to="life_loop_world default capsules-off overlay",
            cuts_dag_edge="none",
            do_intervention="do(channel=on, source_fitness_bias=on, source_identity_coupling=intact)",
        ),
        HardExperiment01Intervention(
            arm="source_bias_off",
            role="mechanism_ablation",
            target_mechanism="capsule_source_fitness_bias",
            action="disable_source_fitness_gating_keep_capsule_channel",
            knob="CapsuleTransferConfig.min_source_fitness+adoption_policy",
            applied_value="min_source_fitness=0.0,THRESHOLD,shuffle=off",
            compared_to="source_bias_on",
            cuts_dag_edge="source_fitness -> source_fitness_bias",
            do_intervention="do(source_fitness_bias=off)",
        ),
        HardExperiment01Intervention(
            arm="capsules_off",
            role="channel_off",
            target_mechanism="capsule_transfer_channel",
            action="disable_capsule_transfer",
            knob="CapsuleTransferConfig.enabled",
            applied_value="enabled=False",
            compared_to="source_bias_on",
            cuts_dag_edge="channel_enabled -> recipient_fitness",
            do_intervention="do(channel_enabled=off)",
        ),
        HardExperiment01Intervention(
            arm="capsules_shuffled",
            role="negative_control",
            target_mechanism="source_identity_to_content_coupling",
            action="permute_source_identities_and_fitness_weights",
            knob="CapsuleTransferConfig.shuffle_mode",
            applied_value="SOURCE (identities/weights permuted; traffic preserved)",
            compared_to="source_bias_on",
            cuts_dag_edge="source_identity_coupling -> capsule_content",
            do_intervention="do(source_identity_coupling=permuted)",
        ),
    )


@dataclass(frozen=True, slots=True)
class HardExperiment01DagNode:
    """One DAG node. Not a Price-term label and not a claim unlock."""

    node_id: str
    label: str
    role: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {"node_id": self.node_id, "label": self.label, "role": self.role}


@dataclass(frozen=True, slots=True)
class HardExperiment01DagEdge:
    """One DAG edge plus which arm's do() cuts it."""

    source: str
    target: str
    justification: str
    cut_by_arms: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "source": self.source,
            "target": self.target,
            "justification": self.justification,
            "cut_by_arms": list(self.cut_by_arms),
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01CausalDag:
    """Explicit causal model for HARD_EXPERIMENT_01.

    Price-equation decomposition is a statistical identity (Okasha & Otsuka
    2020; van Veelen 2020). Multilevel Price vs contextual analysis encode
    non-equivalent causal assumptions (Fronhofer et al. 2021). This DAG plus
    the four do()-style arms is the causal model; Price terms alone do not
    prove mechanism.
    """

    nodes: tuple[HardExperiment01DagNode, ...]
    edges: tuple[HardExperiment01DagEdge, ...]
    literature: tuple[str, ...]
    schema_version: str = "hard_experiment_01_dag_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("HardExperiment01CausalDag digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "nodes": [item.to_dict() for item in self.nodes],
            "edges": [item.to_dict() for item in self.edges],
            "literature": list(self.literature),
            "price_equation_is_automatic_causation": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def hard_experiment_01_dag() -> HardExperiment01CausalDag:
    """Preregistered DAG. Nodes and cut-edges are part of the design, not results."""

    return HardExperiment01CausalDag(
        nodes=(
            HardExperiment01DagNode("source_fitness", "Source organism fitness at emission", "exposure"),
            HardExperiment01DagNode("source_identity_coupling", "Binding of capsule payload to emitting source", "coupling"),
            HardExperiment01DagNode("capsule_content", "Capsule payload (pattern, prediction, graph digest)", "mediator"),
            HardExperiment01DagNode("source_fitness_bias", "FITNESS_WEIGHTED adoption + min_source_fitness gate", "mechanism"),
            HardExperiment01DagNode("channel_enabled", "CapsuleTransferConfig.enabled", "gate"),
            HardExperiment01DagNode("recipient_fitness", "Last-tick / next-generation mean fitness", "outcome"),
        ),
        edges=(
            HardExperiment01DagEdge(
                source="source_fitness",
                target="source_fitness_bias",
                justification=(
                    "Source fitness is the numeric input to FITNESS_WEIGHTED "
                    "adoption and the min_source_fitness gate."
                ),
                cut_by_arms=("source_bias_off",),
            ),
            HardExperiment01DagEdge(
                source="source_identity_coupling",
                target="capsule_content",
                justification=(
                    "Emitted content and attached source-fitness weights remain "
                    "tied to the emitting organism unless SOURCE shuffle permutes them."
                ),
                cut_by_arms=("capsules_shuffled",),
            ),
            HardExperiment01DagEdge(
                source="source_fitness",
                target="capsule_content",
                justification=(
                    "Fitter sources may emit different content. This edge is an "
                    "observational association until an intervention cuts identity "
                    "coupling; it is not proved by a Price transmission term."
                ),
                cut_by_arms=("capsules_shuffled",),
            ),
            HardExperiment01DagEdge(
                source="source_fitness_bias",
                target="recipient_fitness",
                justification=(
                    "Weighting / gating changes which capsules are adopted and "
                    "can therefore change recipient last-tick fitness."
                ),
                cut_by_arms=("source_bias_off", "capsules_off"),
            ),
            HardExperiment01DagEdge(
                source="capsule_content",
                target="recipient_fitness",
                justification=(
                    "Adopted payload can change recipient behavior or fitness, "
                    "but only if the channel is on."
                ),
                cut_by_arms=("capsules_off",),
            ),
            HardExperiment01DagEdge(
                source="channel_enabled",
                target="recipient_fitness",
                justification="Channel-off severs every capsule-mediated path to the outcome.",
                cut_by_arms=("capsules_off",),
            ),
        ),
        literature=(
            "Okasha & Otsuka 2020 Phil Trans B: Price identity vs causal decomposition",
            "van Veelen 2020: selection/transmission terms need a causal model",
            "Fronhofer et al. 2021 Front Ecol Evol: multilevel Price vs contextual analysis",
            "Glymour 2026 preprint comments: interventions, not fiat, choose the causal reading",
            "Goldsby et al. 2012 PNAS: isolation / knockout as mechanism ablation pattern",
        ),
    )


def hard_experiment_01_shuffled_control_properties() -> dict[str, JsonValue]:
    """Documented properties of the capsules_shuffled specificity control."""

    return {
        "arm": "capsules_shuffled",
        "role": "negative_control",
        "shuffle_mode": SHUFFLED_CONTROL_MODE.value,
        "preserves_capsule_traffic": True,
        "preserves_fitness_weighted_adoption": True,
        "preserves_min_source_fitness": True,
        "destroys_source_to_content_fitness_coupling": True,
        "digest_reproducible": True,
        "goldsby_isolation_pattern": "channel_off_or_shuffled",
        "is_goldsby_2012_pnas_experiment": False,
        "rationale": _SHUFFLED_RATIONALE,
        "cuts_dag_edge": "source_identity_coupling -> capsule_content",
        "claim_ceiling": CLAIM_CEILING,
    }


def hard_experiment_01_statistical_tier(n: int) -> str:
    """StatisticalTestPolicy language tier for a seed count."""

    return StatisticalTestPolicy().tier_for_n(int(n))


def default_research_seeds(seed_count: int = RESEARCH_SEED_COUNT) -> tuple[int, ...]:
    """Deterministic seed tuple. 12 is smoke/exploratory; research-grade n is 30."""

    count = int(seed_count)
    if count < 2:
        raise ConfigurationError("hard experiment 01 seed_count must be >= 2.")
    return tuple(range(11, 11 + count))


def default_research_grade_seeds() -> tuple[int, ...]:
    """Thirty paired seeds for research-grade claim language."""

    return default_research_seeds(RESEARCH_GRADE_SEED_COUNT)


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


def _treatment_capsule_config(
    *,
    enabled: bool = True,
    min_source_fitness: float = TREATMENT_MIN_SOURCE_FITNESS,
    adoption_policy: CapsuleAdoptionPolicy = CapsuleAdoptionPolicy.FITNESS_WEIGHTED,
    shuffle_mode: CapsuleShuffleMode = CapsuleShuffleMode.OFF,
) -> CapsuleTransferConfig:
    return CapsuleTransferConfig(
        enabled=enabled,
        min_confidence=0.1,
        min_source_fitness=min_source_fitness,
        adoption_policy=adoption_policy,
        shuffle_mode=shuffle_mode,
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


def _capsule_config_for_arm(arm: ArmName) -> CapsuleTransferConfig:
    if arm == "capsules_off":
        return CapsuleTransferConfig(enabled=False)
    if arm == "source_bias_on":
        return _treatment_capsule_config()
    if arm == "source_bias_off":
        return _treatment_capsule_config(
            min_source_fitness=0.0,
            adoption_policy=CapsuleAdoptionPolicy.THRESHOLD,
        )
    if arm == "capsules_shuffled":
        return _treatment_capsule_config(shuffle_mode=SHUFFLED_CONTROL_MODE)
    raise ConfigurationError(f"unknown hard experiment 01 arm: {arm!r}")


def _spec_from_capsule(
    *,
    seed: int,
    tick_count: int,
    population: int,
    capsule: CapsuleTransferConfig,
    metadata_extra: Mapping[str, JsonValue],
) -> GenesisExperimentSpec:
    if tick_count <= 0 or population <= 0:
        raise ConfigurationError("tick_count and population must be > 0.")
    base = GenesisRuntimeProfile.life_loop_world(
        seed=seed, tick_count=tick_count, population=population
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
        "hard_experiment_01_question": _QUESTION,
        "claim_ceiling": CLAIM_CEILING,
        "design_claim_ceiling": DESIGN_CLAIM_CEILING,
        "collective_intelligence": False,
        "intelligence": False,
        "agi": False,
        "tokyo_type1_passed": False,
        "avida_replacement": False,
        **dict(metadata_extra),
    }
    return replace(
        base,
        population_configs=configs,
        capsule_transfer_config=capsule,
        engine_config=engine_config,
        metadata=metadata,
    )


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
    capsule = _capsule_config_for_arm(arm)
    extra: dict[str, JsonValue] = {
        "hard_experiment_01_arm": arm,
        "hard_experiment_01_shuffle_mode": (
            SHUFFLED_CONTROL_MODE.value if arm == "capsules_shuffled" else CapsuleShuffleMode.OFF.value
        ),
    }
    return _spec_from_capsule(
        seed=seed,
        tick_count=tick_count,
        population=population,
        capsule=capsule,
        metadata_extra=extra,
    )


def build_hard_experiment_01_dose_spec(
    *,
    seed: int,
    min_source_fitness: float,
    tick_count: int = DEFAULT_TICK_COUNT,
    population: int = DEFAULT_POPULATION,
) -> GenesisExperimentSpec:
    """Treatment-channel overlay at one min_source_fitness dose. Not a new arm letter."""

    dose = require_finite_float("min_source_fitness", min_source_fitness)
    if dose < 0.0:
        raise ConfigurationError("min_source_fitness dose must be >= 0.")
    capsule = _treatment_capsule_config(min_source_fitness=dose)
    extra: dict[str, JsonValue] = {
        "hard_experiment_01_arm": "source_bias_on",
        "hard_experiment_01_dose_knob": DOSE_KNOB,
        "hard_experiment_01_dose_level": dose,
    }
    return _spec_from_capsule(
        seed=seed,
        tick_count=tick_count,
        population=population,
        capsule=capsule,
        metadata_extra=extra,
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


def _run_spec(spec: GenesisExperimentSpec) -> object:
    return GenesisEngine.from_spec(spec).run_ticks()


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
    return spec, _run_spec(spec)


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
    """Paired four-arm record for one seed."""

    seed: int
    source_bias_on: HardExperiment01ArmRecord
    source_bias_off: HardExperiment01ArmRecord
    capsules_off: HardExperiment01ArmRecord
    capsules_shuffled: HardExperiment01ArmRecord
    delta_vs_source_bias_off: float | None
    delta_vs_capsules_off: float | None
    delta_vs_capsules_shuffled: float | None

    def __post_init__(self) -> None:
        arms = (
            self.source_bias_on,
            self.source_bias_off,
            self.capsules_off,
            self.capsules_shuffled,
        )
        if any(item.seed != self.seed for item in arms):
            raise ConfigurationError("seed records must share one seed.")
        for name in (
            "delta_vs_source_bias_off",
            "delta_vs_capsules_off",
            "delta_vs_capsules_shuffled",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, require_finite_float(name, value))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "source_bias_on": self.source_bias_on.to_dict(),
            "source_bias_off": self.source_bias_off.to_dict(),
            "capsules_off": self.capsules_off.to_dict(),
            "capsules_shuffled": self.capsules_shuffled.to_dict(),
            "delta_vs_source_bias_off": self.delta_vs_source_bias_off,
            "delta_vs_capsules_off": self.delta_vs_capsules_off,
            "delta_vs_capsules_shuffled": self.delta_vs_capsules_shuffled,
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
class HardExperiment01InferentialContrast:
    """Paired d_z / BCa / sign-flip contrast. Measurement, not a claim unlock."""

    contrast_name: str
    treatment_arm: str
    baseline_arm: str
    pair_count: int
    missing_pairs: int
    mean_delta: float
    paired_dz: float | None
    bca_ci_low: float | None
    bca_ci_high: float | None
    sign_flip_p: float | None
    holm_adjusted_p: float | None
    interpretation: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "contrast_name": self.contrast_name,
            "treatment_arm": self.treatment_arm,
            "baseline_arm": self.baseline_arm,
            "pair_count": self.pair_count,
            "missing_pairs": self.missing_pairs,
            "mean_delta": self.mean_delta,
            "paired_dz": self.paired_dz,
            "bca_ci_low": self.bca_ci_low,
            "bca_ci_high": self.bca_ci_high,
            "sign_flip_p": self.sign_flip_p,
            "holm_adjusted_p": self.holm_adjusted_p,
            "interpretation": self.interpretation,
            "claim_ceiling": CLAIM_CEILING,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01Campaign:
    """Multi-seed source-bias campaign. Claim ceiling stays runtime_observation."""

    seeds: tuple[int, ...]
    seed_records: tuple[HardExperiment01SeedRecord, ...]
    mean_delta_vs_source_bias_off: float
    mean_delta_vs_capsules_off: float
    mean_delta_vs_capsules_shuffled: float
    effect_vs_source_bias_off: EffectSizeResult
    effect_vs_capsules_off: EffectSizeResult
    effect_vs_capsules_shuffled: EffectSizeResult
    inferential_contrasts: tuple[HardExperiment01InferentialContrast, ...]
    statistical_tier: str
    statistical_policy: StatisticalTestPolicy
    replay_verified_seed: int
    replay_verified_seeds: tuple[int, ...]
    replay_records: tuple[HardExperiment01ReplayRecord, ...]
    replay_spec_digest: str
    replay_result_digest: str
    replay_matched: bool
    missing_outcomes_per_arm: tuple[tuple[str, int], ...] = ()
    interventions: tuple[HardExperiment01Intervention, ...] = ()
    causal_dag: HardExperiment01CausalDag | None = None
    question: str = _QUESTION
    claim_ceiling: str = CLAIM_CEILING
    design_claim_ceiling: str = DESIGN_CLAIM_CEILING
    schema_version: str = SCHEMA_VERSION
    experiment_id: str = EXPERIMENT_ID
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2 or len(self.seeds) != len(self.seed_records):
            raise ConfigurationError("campaign requires paired seed records for every seed.")
        if self.claim_ceiling != CLAIM_CEILING or self.claim_ceiling in _FORBIDDEN:
            raise ConfigurationError("hard experiment 01 ceiling must stay runtime_observation.")
        if self.design_claim_ceiling != DESIGN_CLAIM_CEILING:
            raise ConfigurationError("hard experiment 01 design ceiling is intervention_supported only.")
        if self.statistical_tier != hard_experiment_01_statistical_tier(len(self.seeds)):
            raise ConfigurationError("statistical_tier must match StatisticalTestPolicy.tier_for_n(n).")
        if not self.replay_records:
            raise ConfigurationError("hard experiment 01 requires replay records for first and last seeds.")
        if not self.replay_matched or not all(item.matched for item in self.replay_records):
            raise ConfigurationError("hard experiment 01 requires a matching replay digest.")
        replay_arms = {item.arm for item in self.replay_records}
        if replay_arms != set(ARMS):
            raise ConfigurationError("hard experiment 01 must replay every arm.")
        if not self.interventions:
            object.__setattr__(self, "interventions", hard_experiment_01_interventions())
        if self.causal_dag is None:
            object.__setattr__(self, "causal_dag", hard_experiment_01_dag())
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
        if {item.contrast_name for item in self.inferential_contrasts} != {
            name for name, _ in PLANNED_CONTRASTS
        }:
            raise ConfigurationError("inferential_contrasts must cover the three planned comparisons.")
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
        object.__setattr__(
            self,
            "mean_delta_vs_capsules_shuffled",
            require_finite_float(
                "mean_delta_vs_capsules_shuffled", self.mean_delta_vs_capsules_shuffled
            ),
        )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("HardExperiment01Campaign digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        dag = self.causal_dag or hard_experiment_01_dag()
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "question": self.question,
            "seeds": list(self.seeds),
            "seed_records": [item.to_dict() for item in self.seed_records],
            "mean_delta_vs_source_bias_off": self.mean_delta_vs_source_bias_off,
            "mean_delta_vs_capsules_off": self.mean_delta_vs_capsules_off,
            "mean_delta_vs_capsules_shuffled": self.mean_delta_vs_capsules_shuffled,
            "effect_vs_source_bias_off": self.effect_vs_source_bias_off.to_dict(),
            "effect_vs_capsules_off": self.effect_vs_capsules_off.to_dict(),
            "effect_vs_capsules_shuffled": self.effect_vs_capsules_shuffled.to_dict(),
            "inferential_contrasts": [item.to_dict() for item in self.inferential_contrasts],
            "statistical_tier": self.statistical_tier,
            "statistical_policy": self.statistical_policy.to_dict(),
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
            "causal_dag": dag.to_dict(),
            "shuffled_control": hard_experiment_01_shuffled_control_properties(),
            "claim_ceiling": self.claim_ceiling,
            "design_claim_ceiling": self.design_claim_ceiling,
            "results_archived": False,
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
                "price_equation_is_statistical_identity_not_automatic_causation",
                "causal_reading_requires_explicit_dag_and_interventions",
                "capsules_shuffled_is_specificity_control_not_intelligence",
                "goldsby_isolation_is_ablation_pattern_not_pnas_replication",
                "intervention_supported_requires_archived_digest_backed_results",
                "statistical_tier_must_match_n",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class HardExperiment01DoseRecord:
    """One seed × one min_source_fitness dose. Not a silent zero fill."""

    seed: int
    min_source_fitness: float
    terminal_mean_fitness: float | None
    births: int
    spec_digest: str
    result_digest: str
    outcome_missing: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "min_source_fitness",
            require_finite_float("min_source_fitness", self.min_source_fitness),
        )
        if self.outcome_missing:
            object.__setattr__(self, "terminal_mean_fitness", None)
        elif self.terminal_mean_fitness is None:
            raise ConfigurationError("dose terminal_mean_fitness required when outcome_missing is false.")
        else:
            object.__setattr__(
                self,
                "terminal_mean_fitness",
                require_finite_float("terminal_mean_fitness", self.terminal_mean_fitness),
            )
        if len(self.spec_digest) != 64 or len(self.result_digest) != 64:
            raise ConfigurationError("dose records require 64-hex spec/result digests.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "min_source_fitness": self.min_source_fitness,
            "terminal_mean_fitness": self.terminal_mean_fitness,
            "births": self.births,
            "spec_digest": self.spec_digest,
            "result_digest": self.result_digest,
            "outcome_missing": self.outcome_missing,
            "claim_ceiling": CLAIM_CEILING,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01DoseReplayRecord:
    """Independent re-run of one seed × dose. Digests must match."""

    seed: int
    min_source_fitness: float
    spec_digest: str
    result_digest: str
    matched: bool

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "min_source_fitness": self.min_source_fitness,
            "spec_digest": self.spec_digest,
            "result_digest": self.result_digest,
            "matched": self.matched,
            "claim_ceiling": CLAIM_CEILING,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01DoseResponse:
    """min_source_fitness ladder. Report monotone or null honestly."""

    knob: str
    levels: tuple[float, ...]
    seeds: tuple[int, ...]
    records: tuple[HardExperiment01DoseRecord, ...]
    mean_fitness_by_level: tuple[tuple[float, float], ...]
    missing_outcomes_by_level: tuple[tuple[float, int], ...]
    monotone_report: str
    statistical_tier: str
    replay_records: tuple[HardExperiment01DoseReplayRecord, ...]
    replay_matched: bool
    question: str = (
        "Does last-tick mean fitness change monotonically across a "
        "min_source_fitness dose ladder on the FITNESS_WEIGHTED channel?"
    )
    claim_ceiling: str = CLAIM_CEILING
    schema_version: str = "hard_experiment_01_dose_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.levels) < 3:
            raise ConfigurationError("dose-response requires at least three levels.")
        if len(self.seeds) < 2:
            raise ConfigurationError("dose-response requires at least two seeds.")
        if self.claim_ceiling != CLAIM_CEILING:
            raise ConfigurationError("dose-response ceiling must stay runtime_observation.")
        if self.statistical_tier != hard_experiment_01_statistical_tier(len(self.seeds)):
            raise ConfigurationError("dose-response statistical_tier must match n.")
        if self.monotone_report not in {"increasing", "decreasing", "null", "insufficient"}:
            raise ConfigurationError("monotone_report must be increasing, decreasing, null, or insufficient.")
        if not self.replay_matched or not self.replay_records:
            raise ConfigurationError("dose-response requires a matching replay digest.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("HardExperiment01DoseResponse digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "knob": self.knob,
            "levels": [float(item) for item in self.levels],
            "seeds": list(self.seeds),
            "records": [item.to_dict() for item in self.records],
            "mean_fitness_by_level": [[level, mean] for level, mean in self.mean_fitness_by_level],
            "missing_outcomes_by_level": [
                [level, count] for level, count in self.missing_outcomes_by_level
            ],
            "monotone_report": self.monotone_report,
            "statistical_tier": self.statistical_tier,
            "replay_records": [item.to_dict() for item in self.replay_records],
            "replay_matched": self.replay_matched,
            "question": self.question,
            "claim_ceiling": self.claim_ceiling,
            "results_archived": False,
            "collective_intelligence": False,
            "is_goldsby_2012_pnas_experiment": False,
            "limitations": [
                "dose_is_min_source_fitness_not_goldsby_task_switching_cost",
                "null_or_nonmonotone_curve_is_a_valid_finding",
                "missing_outcomes_are_dropped_not_zero_filled",
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


def _inferential_contrast(
    *,
    contrast_name: str,
    baseline_arm: ArmName,
    records: Sequence[HardExperiment01SeedRecord],
) -> HardExperiment01InferentialContrast:
    baseline, treatment = _complete_pair_values(
        records, treatment_arm="source_bias_on", baseline_arm=baseline_arm
    )
    missing = len(records) - len(baseline)
    if len(baseline) < 2:
        return HardExperiment01InferentialContrast(
            contrast_name=contrast_name,
            treatment_arm="source_bias_on",
            baseline_arm=baseline_arm,
            pair_count=len(baseline),
            missing_pairs=missing,
            mean_delta=0.0,
            paired_dz=None,
            bca_ci_low=None,
            bca_ci_high=None,
            sign_flip_p=None,
            holm_adjusted_p=None,
            interpretation="insufficient_paired_outcomes",
        )
    deltas = [treat - base for treat, base in zip(treatment, baseline, strict=True)]
    mean_delta = _mean(deltas)
    try:
        paired_dz: float | None = round(paired_effect_size(deltas), 10)
        dz_note = "paired_dz"
    except ConfigurationError:
        paired_dz = None
        dz_note = "undefined_paired_dz"
    ci_low, ci_high = bootstrap_ci_paired(deltas, method="bca")
    sign_p = exact_sign_flip_permutation_p(deltas)
    return HardExperiment01InferentialContrast(
        contrast_name=contrast_name,
        treatment_arm="source_bias_on",
        baseline_arm=baseline_arm,
        pair_count=len(deltas),
        missing_pairs=missing,
        mean_delta=mean_delta,
        paired_dz=paired_dz,
        bca_ci_low=round(ci_low, 10),
        bca_ci_high=round(ci_high, 10),
        sign_flip_p=round(sign_p, 10),
        holm_adjusted_p=None,
        interpretation=dz_note,
    )


def _with_holm(
    contrasts: Sequence[HardExperiment01InferentialContrast],
) -> tuple[HardExperiment01InferentialContrast, ...]:
    indexed = [(index, item) for index, item in enumerate(contrasts) if item.sign_flip_p is not None]
    if not indexed:
        return tuple(contrasts)
    adjusted = holm_correction([item.sign_flip_p or 0.0 for _, item in indexed])
    by_index = {index: value for (index, _), value in zip(indexed, adjusted, strict=True)}
    updated: list[HardExperiment01InferentialContrast] = []
    for index, item in enumerate(contrasts):
        if index not in by_index:
            updated.append(item)
            continue
        updated.append(
            replace(item, holm_adjusted_p=round(by_index[index], 10))
        )
    return tuple(updated)


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


def _monotone_report(means: Sequence[float]) -> str:
    if len(means) < 2:
        return "insufficient"
    ups = all(means[index] <= means[index + 1] + 1e-12 for index in range(len(means) - 1))
    downs = all(means[index] >= means[index + 1] - 1e-12 for index in range(len(means) - 1))
    if ups and downs:
        return "null"
    if ups:
        return "increasing"
    if downs:
        return "decreasing"
    return "null"


def run_hard_experiment_01(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    tick_count: int = DEFAULT_TICK_COUNT,
    population: int = DEFAULT_POPULATION,
) -> HardExperiment01Campaign:
    """Paired four-arm campaign. Default seed_count=12 is exploratory; research n=30."""

    seed_tuple = _resolve_seeds(seeds, seed_count, default_count=RESEARCH_SEED_COUNT)
    records: list[HardExperiment01SeedRecord] = []
    for seed in seed_tuple:
        by_arm = {
            arm: _arm_record(seed=seed, arm=arm, tick_count=tick_count, population=population)
            for arm in ARMS
        }
        on_rec = by_arm["source_bias_on"]
        records.append(
            HardExperiment01SeedRecord(
                seed=seed,
                source_bias_on=on_rec,
                source_bias_off=by_arm["source_bias_off"],
                capsules_off=by_arm["capsules_off"],
                capsules_shuffled=by_arm["capsules_shuffled"],
                delta_vs_source_bias_off=_optional_delta(
                    on_rec.terminal_mean_fitness,
                    by_arm["source_bias_off"].terminal_mean_fitness,
                ),
                delta_vs_capsules_off=_optional_delta(
                    on_rec.terminal_mean_fitness,
                    by_arm["capsules_off"].terminal_mean_fitness,
                ),
                delta_vs_capsules_shuffled=_optional_delta(
                    on_rec.terminal_mean_fitness,
                    by_arm["capsules_shuffled"].terminal_mean_fitness,
                ),
            )
        )
    off_fits, on_vs_off = _complete_pair_values(
        records, treatment_arm="source_bias_on", baseline_arm="source_bias_off"
    )
    none_fits, on_vs_none = _complete_pair_values(
        records, treatment_arm="source_bias_on", baseline_arm="capsules_off"
    )
    shuffled_fits, on_vs_shuffled = _complete_pair_values(
        records, treatment_arm="source_bias_on", baseline_arm="capsules_shuffled"
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
    contrasts = _with_holm(
        tuple(
            _inferential_contrast(
                contrast_name=name, baseline_arm=baseline, records=records
            )
            for name, baseline in PLANNED_CONTRASTS
        )
    )
    policy = StatisticalTestPolicy()
    campaign = HardExperiment01Campaign(
        seeds=seed_tuple,
        seed_records=tuple(records),
        mean_delta_vs_source_bias_off=_mean(
            [item.delta_vs_source_bias_off for item in records if item.delta_vs_source_bias_off is not None]
        ),
        mean_delta_vs_capsules_off=_mean(
            [item.delta_vs_capsules_off for item in records if item.delta_vs_capsules_off is not None]
        ),
        mean_delta_vs_capsules_shuffled=_mean(
            [
                item.delta_vs_capsules_shuffled
                for item in records
                if item.delta_vs_capsules_shuffled is not None
            ]
        ),
        effect_vs_source_bias_off=_effect_or_insufficient(
            "terminal_mean_fitness", off_fits, on_vs_off
        ),
        effect_vs_capsules_off=_effect_or_insufficient(
            "terminal_mean_fitness", none_fits, on_vs_none
        ),
        effect_vs_capsules_shuffled=_effect_or_insufficient(
            "terminal_mean_fitness", shuffled_fits, on_vs_shuffled
        ),
        inferential_contrasts=contrasts,
        statistical_tier=policy.tier_for_n(len(seed_tuple)),
        statistical_policy=policy,
        replay_verified_seed=seed_tuple[0],
        replay_verified_seeds=replay_seeds,
        replay_records=replay_records,
        replay_spec_digest=first_replay.spec_digest,
        replay_result_digest=first_replay.result_digest,
        replay_matched=all(item.matched for item in replay_records),
        missing_outcomes_per_arm=_missing_outcomes_per_arm(records),
        causal_dag=hard_experiment_01_dag(),
    )
    _assert_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


def run_hard_experiment_01_dose_response(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    levels: Sequence[float] = DEFAULT_DOSE_LEVELS,
    tick_count: int = DEFAULT_TICK_COUNT,
    population: int = DEFAULT_POPULATION,
) -> HardExperiment01DoseResponse:
    """min_source_fitness ladder on the treatment channel. Honest null is valid."""

    seed_tuple = _resolve_seeds(seeds, seed_count, default_count=RESEARCH_SEED_COUNT)
    dose_levels = tuple(require_finite_float("dose_level", item) for item in levels)
    if len(dose_levels) < 3:
        raise ConfigurationError("dose-response requires at least three levels.")
    if len(set(dose_levels)) != len(dose_levels):
        raise ConfigurationError("dose-response levels must be unique.")
    records: list[HardExperiment01DoseRecord] = []
    for seed in seed_tuple:
        for level in dose_levels:
            spec = build_hard_experiment_01_dose_spec(
                seed=seed,
                min_source_fitness=level,
                tick_count=tick_count,
                population=population,
            )
            result = _run_spec(spec)
            fitness = _mean_last_tick_fitness(result)
            records.append(
                HardExperiment01DoseRecord(
                    seed=seed,
                    min_source_fitness=level,
                    terminal_mean_fitness=fitness,
                    births=_birth_count(result),
                    spec_digest=spec.digest(),
                    result_digest=str(result.digest()),
                    outcome_missing=fitness is None,
                )
            )
    means: list[tuple[float, float]] = []
    missing: list[tuple[float, int]] = []
    monotone_means: list[float] = []
    for level in dose_levels:
        values = [
            item.terminal_mean_fitness
            for item in records
            if item.min_source_fitness == level and not item.outcome_missing
            and item.terminal_mean_fitness is not None
        ]
        dropped = sum(
            1
            for item in records
            if item.min_source_fitness == level and item.outcome_missing
        )
        missing.append((level, dropped))
        means.append((level, _mean([float(item) for item in values])))
        if values:
            monotone_means.append(_mean([float(item) for item in values]))
        else:
            monotone_means = []
            break
    replay_levels = (dose_levels[0], dose_levels[-1])
    replay_seed = seed_tuple[0]
    replay_records: list[HardExperiment01DoseReplayRecord] = []
    for level in replay_levels:
        original = next(
            item
            for item in records
            if item.seed == replay_seed and item.min_source_fitness == level
        )
        spec = build_hard_experiment_01_dose_spec(
            seed=replay_seed,
            min_source_fitness=level,
            tick_count=tick_count,
            population=population,
        )
        result = _run_spec(spec)
        spec_digest = spec.digest()
        result_digest = str(result.digest())
        replay_records.append(
            HardExperiment01DoseReplayRecord(
                seed=replay_seed,
                min_source_fitness=level,
                spec_digest=spec_digest,
                result_digest=result_digest,
                matched=spec_digest == original.spec_digest
                and result_digest == original.result_digest,
            )
        )
    policy = StatisticalTestPolicy()
    dose = HardExperiment01DoseResponse(
        knob=DOSE_KNOB,
        levels=dose_levels,
        seeds=seed_tuple,
        records=tuple(records),
        mean_fitness_by_level=tuple(means),
        missing_outcomes_by_level=tuple(missing),
        monotone_report=_monotone_report(monotone_means),
        statistical_tier=policy.tier_for_n(len(seed_tuple)),
        replay_records=tuple(replay_records),
        replay_matched=all(item.matched for item in replay_records),
    )
    _assert_blocked(dose.to_dict(), ScientificClaimGate())
    return dose


def evaluate_hard_experiment_01_claim(
    payload: Mapping[str, JsonValue] | object,
) -> ClaimDecision:
    """Runtime observation only. Intelligence claims stay blocked.

    ``intervention_supported`` is the design ceiling, not an auto-granted
    claim. Until a dated digest-backed campaign is archived with the
    ClaimGate evidence flags, this evaluator requests ``runtime_observation``.
    """

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
    if gate.decide(ClaimRequest(DESIGN_CLAIM_CEILING, dict(data))).allowed:
        raise ConfigurationError(
            "hard experiment 01 must not auto-grant intervention_supported "
            "without an archived digest-backed evidence pack."
        )
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
    vs_shuffled = campaign.effect_vs_capsules_shuffled
    holm = ", ".join(
        f"{item.contrast_name}={item.holm_adjusted_p}"
        for item in campaign.inferential_contrasts
    )
    return "\n".join(
        (
            f"experiment {campaign.experiment_id}",
            f"question {campaign.question}",
            f"seed_count {len(campaign.seeds)}",
            f"statistical_tier {campaign.statistical_tier}",
            f"mean_delta_vs_source_bias_off {campaign.mean_delta_vs_source_bias_off}",
            f"mean_delta_vs_capsules_off {campaign.mean_delta_vs_capsules_off}",
            f"mean_delta_vs_capsules_shuffled {campaign.mean_delta_vs_capsules_shuffled}",
            f"effect_vs_source_bias_off {vs_off.standardized_delta_lite} {vs_off.interpretation}",
            f"effect_vs_capsules_off {vs_none.standardized_delta_lite} {vs_none.interpretation}",
            f"effect_vs_capsules_shuffled {vs_shuffled.standardized_delta_lite} {vs_shuffled.interpretation}",
            f"holm_adjusted_p {holm}",
            f"replay_matched {campaign.replay_matched}",
            f"claim_ceiling {campaign.claim_ceiling}",
            f"design_claim_ceiling {campaign.design_claim_ceiling}",
            "results_archived False",
            "collective_intelligence False",
            "intelligence False",
            f"digest {campaign.digest}",
            f"standardized_note {_cohens_d_note(vs_off.standardized_delta_lite)}",
        )
    )


def format_hard_experiment_01_dose_summary(dose: HardExperiment01DoseResponse) -> str:
    """Print-friendly dose-ladder summary. Honest null is valid."""

    means = ", ".join(f"{level}={mean}" for level, mean in dose.mean_fitness_by_level)
    return "\n".join(
        (
            f"dose_knob {dose.knob}",
            f"levels {list(dose.levels)}",
            f"seed_count {len(dose.seeds)}",
            f"statistical_tier {dose.statistical_tier}",
            f"mean_fitness_by_level {means}",
            f"monotone_report {dose.monotone_report}",
            f"replay_matched {dose.replay_matched}",
            f"claim_ceiling {dose.claim_ceiling}",
            "results_archived False",
            f"digest {dose.digest}",
        )
    )
