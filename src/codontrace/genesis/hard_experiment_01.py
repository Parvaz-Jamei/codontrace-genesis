"""Hard experiment 01: preregistered capsule source-bias causal design.

Wave 1 confirmatory measurement, not a new Phase letter. Four paired arms
plus a Goldsby-style dose ladder. Causal reading uses the explicit DAG in
``docs/HARD_EXPERIMENT_01_PREREG.md`` (Okasha & Otsuka 2020). Claim ceiling
is ``runtime_observation`` unless the preregistered decision rule holds and
``ScientificClaimGate`` allows existing ``intervention_supported``.

Forbidden: intelligence / collective_intelligence / AGI /
tokyo_type1_passed / avida_replacement. ClaimGate is never loosened.
A null finding is valid. This module does not mutate a global ClaimGate.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.capsule import (
    CapsuleAdoptionPolicy,
    CapsuleShuffleMode,
    CapsuleTransferConfig,
)
from codontrace.genesis.causal_validation import InterventionResult
from codontrace.genesis.claim_gate import ClaimDecision, ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.statistical_protocol import (
    EffectSizeResult,
    MultipleComparisonAudit,
    PairedComparisonResult,
    PreregisteredMetric,
    SeedSweepPlan,
    StatisticalTestPolicy,
    bootstrap_ci_paired,
    estimate_effect_size_lite,
    exact_sign_flip_permutation_p,
    holm_correction,
    paired_effect_size,
)
from codontrace.rng import RNGManager

CLAIM_CEILING = "runtime_observation"
INTERVENTION_CLAIM = "intervention_supported"
SMOKE_SEED_COUNT = 12
RESEARCH_SEED_COUNT = 30
SMOKE_TICK_COUNT = 6
SMOKE_POPULATION = 4
RESEARCH_TICK_COUNT = 40
RESEARCH_POPULATION = 16
DEFAULT_TICK_COUNT = SMOKE_TICK_COUNT
DEFAULT_POPULATION = SMOKE_POPULATION
EXPERIMENT_ID = "hard_experiment_01_capsule_source_bias"
SCHEMA_VERSION = "hard_experiment_01_v2"
PREREG_RELATIVE_PATH = "docs/HARD_EXPERIMENT_01_PREREG.md"
INFERENTIAL_SEED = 20260911
BOOTSTRAP_RESAMPLES = 10000
DOSE_PERMUTATION_DRAWS = 10000
ALPHA = 0.05
DOSE_LEVELS: tuple[float, ...] = (0.0, 1.0, 2.0, 4.0)
ScaleName = Literal["smoke", "research"]

ArmName = Literal["source_bias_on", "source_bias_off", "capsules_off", "capsules_shuffled"]
ARMS: tuple[ArmName, ...] = (
    "source_bias_on",
    "source_bias_off",
    "capsules_off",
    "capsules_shuffled",
)
PRIMARY_CONTRASTS: tuple[tuple[ArmName, ArmName], ...] = (
    ("source_bias_on", "source_bias_off"),
    ("source_bias_on", "capsules_off"),
    ("source_bias_on", "capsules_shuffled"),
)
INTERVENTION_SUPPORTED_FLAGS: tuple[str, ...] = (
    "intervention_result_artifact",
    "intervention_result_digest",
    "baseline_digest",
    "treatment_digest",
    "intervention_protocol_digest",
    "effect_size",
    "paired_seed_protocol_digest",
    "claim_gate_decision_digest",
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
    "Does source-fitness-weighted capsule transfer raise last-tick / "
    "next-generation mean fitness relative to (a) the same capsule channel "
    "with source-fitness gating ablated, (b) capsules off, and (c) the "
    "capsule channel on with content scrambled?"
)

_DAG_NODES = (
    "gate",
    "which_capsule_is_adopted",
    "action",
    "ATP",
    "terminal_fitness",
)
_DAG_EDGES = (
    ("gate", "which_capsule_is_adopted", "e1"),
    ("which_capsule_is_adopted", "action", "e2"),
    ("action", "ATP", "e3"),
    ("ATP", "terminal_fitness", "e4"),
)

_PRIMARY_METRIC = PreregisteredMetric(
    metric_name="terminal_mean_fitness",
    objective="source_bias_on_greater_than_baseline",
    direction="maximize",
)


def hard_experiment_01_causal_dag() -> dict[str, JsonValue]:
    """Okasha & Otsuka (2020) explicit DAG. Not a Price causal proof by itself."""

    return {
        "citation": "Okasha & Otsuka 2020 Phil Trans B",
        "note": "Price/Cov is a statistical identity; causal reading needs this DAG.",
        "nodes": list(_DAG_NODES),
        "edges": [[src, dst, label] for src, dst, label in _DAG_EDGES],
        "path": "gate → which capsule is adopted → action → ATP → terminal fitness",
    }


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def hard_experiment_01_prereg_path() -> Path:
    return _repo_root() / PREREG_RELATIVE_PATH


def hard_experiment_01_prereg_digest() -> str:
    """SHA-256 of the frozen preregistration file (UTF-8 bytes)."""

    path = hard_experiment_01_prereg_path()
    if not path.is_file():
        raise ConfigurationError(f"missing preregistration file: {PREREG_RELATIVE_PATH}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hard_experiment_01_protocol_digest(prereg_digest: str | None = None) -> str:
    """Digest of the confirmatory protocol + DAG, not of campaign numbers."""

    digest = prereg_digest or hard_experiment_01_prereg_digest()
    return canonical_digest(
        {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": SCHEMA_VERSION,
            "question": _QUESTION,
            "dag": hard_experiment_01_causal_dag(),
            "arms": [item.to_dict() for item in hard_experiment_01_interventions()],
            "dose_levels": list(DOSE_LEVELS),
            "primary_contrasts": [list(item) for item in PRIMARY_CONTRASTS],
            "prereg_path": PREREG_RELATIVE_PATH,
            "prereg_digest": digest,
            "inferential_seed": INFERENTIAL_SEED,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "alpha": ALPHA,
        }
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
    cuts_edges: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "arm": self.arm,
            "role": self.role,
            "target_mechanism": self.target_mechanism,
            "action": self.action,
            "knob": self.knob,
            "applied_value": self.applied_value,
            "compared_to": self.compared_to,
            "cuts_edges": list(self.cuts_edges),
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
            applied_value="min_source_fitness=2.0,FITNESS_WEIGHTED,shuffle=off",
            compared_to="life_loop_world default capsules-off overlay",
            cuts_edges=(),
        ),
        HardExperiment01Intervention(
            arm="source_bias_off",
            role="mechanism_ablation",
            target_mechanism="capsule_source_fitness_bias",
            action="disable_source_fitness_gating_keep_capsule_channel",
            knob="CapsuleTransferConfig.min_source_fitness+adoption_policy",
            applied_value="min_source_fitness=0.0,THRESHOLD,shuffle=off",
            compared_to="source_bias_on",
            cuts_edges=("e1",),
        ),
        HardExperiment01Intervention(
            arm="capsules_off",
            role="channel_off",
            target_mechanism="capsule_transfer_channel",
            action="disable_capsule_transfer",
            knob="CapsuleTransferConfig.enabled",
            applied_value="enabled=False",
            compared_to="source_bias_on",
            cuts_edges=("e1", "e2"),
        ),
        HardExperiment01Intervention(
            arm="capsules_shuffled",
            role="negative_control",
            target_mechanism="capsule_content_information",
            action="scramble_capsule_content_keep_channel",
            knob="CapsuleTransferConfig.shuffle_mode",
            applied_value="CapsuleShuffleMode.CONTENT",
            compared_to="source_bias_on",
            cuts_edges=("e2_content",),
        ),
    )


def default_research_seeds(seed_count: int = RESEARCH_SEED_COUNT) -> tuple[int, ...]:
    """Deterministic seed tuple. Smoke n=12; research-grade n=30."""

    count = int(seed_count)
    if count < 2:
        raise ConfigurationError("hard experiment 01 seed_count must be >= 2.")
    return tuple(range(11, 11 + count))


def default_smoke_seeds(seed_count: int = SMOKE_SEED_COUNT) -> tuple[int, ...]:
    return default_research_seeds(seed_count)


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


def _enabled_capsule(
    *,
    min_source_fitness: float,
    adoption_policy: CapsuleAdoptionPolicy,
    shuffle_mode: CapsuleShuffleMode,
) -> CapsuleTransferConfig:
    return CapsuleTransferConfig(
        enabled=True,
        min_confidence=0.1,
        min_source_fitness=float(min_source_fitness),
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


def _capsule_for_arm(arm: ArmName) -> CapsuleTransferConfig:
    if arm == "capsules_off":
        return CapsuleTransferConfig(enabled=False)
    if arm == "source_bias_on":
        return _enabled_capsule(
            min_source_fitness=2.0,
            adoption_policy=CapsuleAdoptionPolicy.FITNESS_WEIGHTED,
            shuffle_mode=CapsuleShuffleMode.OFF,
        )
    if arm == "source_bias_off":
        return _enabled_capsule(
            min_source_fitness=0.0,
            adoption_policy=CapsuleAdoptionPolicy.THRESHOLD,
            shuffle_mode=CapsuleShuffleMode.OFF,
        )
    if arm == "capsules_shuffled":
        return _enabled_capsule(
            min_source_fitness=2.0,
            adoption_policy=CapsuleAdoptionPolicy.FITNESS_WEIGHTED,
            shuffle_mode=CapsuleShuffleMode.CONTENT,
        )
    raise ConfigurationError(f"unknown hard experiment 01 arm: {arm!r}")


def _apply_capsule_overlay(
    *,
    seed: int,
    tick_count: int,
    population: int,
    capsule: CapsuleTransferConfig,
    arm_label: str,
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
        "hard_experiment_01_arm": arm_label,
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
    return _apply_capsule_overlay(
        seed=seed,
        tick_count=tick_count,
        population=population,
        capsule=_capsule_for_arm(arm),
        arm_label=arm,
    )


def build_hard_experiment_01_dose_spec(
    *,
    seed: int,
    min_source_fitness: float,
    tick_count: int = DEFAULT_TICK_COUNT,
    population: int = DEFAULT_POPULATION,
) -> GenesisExperimentSpec:
    """FITNESS_WEIGHTED dose overlay. ``min_source_fitness=2.0`` matches treatment."""

    if float(min_source_fitness) not in DOSE_LEVELS:
        raise ConfigurationError(f"dose min_source_fitness must be one of {DOSE_LEVELS}.")
    if float(min_source_fitness) == 2.0:
        return build_hard_experiment_01_spec(
            seed=seed, arm="source_bias_on", tick_count=tick_count, population=population
        )
    return _apply_capsule_overlay(
        seed=seed,
        tick_count=tick_count,
        population=population,
        capsule=_enabled_capsule(
            min_source_fitness=float(min_source_fitness),
            adoption_policy=CapsuleAdoptionPolicy.FITNESS_WEIGHTED,
            shuffle_mode=CapsuleShuffleMode.OFF,
        ),
        arm_label=f"dose_{int(min_source_fitness)}",
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


def _final_population(result: object) -> int | None:
    pack = getattr(result, "evidence_pack", None)
    summary = getattr(pack, "summary", None)
    value = getattr(summary, "final_population", None)
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    return None


def _run_spec(spec: GenesisExperimentSpec) -> object:
    return GenesisEngine.from_spec(spec).run_ticks()


def _result_identity_digest(result: object) -> str:
    """Replay identity for one run.

    Full ``GenesisRunResult.digest()`` hashes every tick plus maturity
    reports and is too expensive for a 30×40×16 campaign. The snapshot
    digest is the Phase A pin surface and is sufficient to detect a
    mismatched re-run.
    """

    snapshot = getattr(result, "snapshot", None)
    digest = getattr(snapshot, "digest", None)
    if callable(digest):
        value = str(digest())
        if len(value) == 64:
            return value
    raise ConfigurationError("hard experiment 01 run is missing a 64-hex snapshot digest.")


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
    extinct: bool = False
    final_population: int | None = None

    def __post_init__(self) -> None:
        if self.outcome_missing:
            object.__setattr__(self, "terminal_mean_fitness", None)
        elif self.terminal_mean_fitness is None:
            raise ConfigurationError(
                "terminal_mean_fitness is required when outcome_missing is false."
            )
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
            "extinct": self.extinct,
            "final_population": self.final_population,
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
class HardExperiment01PairedContrast:
    """One paired contrast: dz + BCa CI + sign-flip p + Holm slot."""

    treatment_arm: ArmName
    baseline_arm: ArmName
    n: int
    mean_delta: float
    sd_delta: float
    dz: float | None
    ci_low: float | None
    ci_high: float | None
    p_raw: float | None
    p_holm: float | None
    claim_downgraded: bool
    dropped_pairs: int
    paired_result: PairedComparisonResult | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "treatment_arm": self.treatment_arm,
            "baseline_arm": self.baseline_arm,
            "n": self.n,
            "mean_delta": self.mean_delta,
            "sd_delta": self.sd_delta,
            "dz": self.dz,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "p_raw": self.p_raw,
            "p_holm": self.p_holm,
            "claim_downgraded": self.claim_downgraded,
            "dropped_pairs": self.dropped_pairs,
            "paired_result": None if self.paired_result is None else self.paired_result.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01DoseRecord:
    """One seed × one FITNESS_WEIGHTED dose level."""

    seed: int
    min_source_fitness: float
    terminal_mean_fitness: float | None
    births: int
    capsule_adoptions: int
    spec_digest: str
    result_digest: str
    outcome_missing: bool
    extinct: bool

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "min_source_fitness": self.min_source_fitness,
            "terminal_mean_fitness": self.terminal_mean_fitness,
            "births": self.births,
            "capsule_adoptions": self.capsule_adoptions,
            "spec_digest": self.spec_digest,
            "result_digest": self.result_digest,
            "outcome_missing": self.outcome_missing,
            "extinct": self.extinct,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01DoseTrend:
    """Spearman + seed-fixed permutation trend on the dose ladder."""

    min_source_fitness: tuple[float, ...]
    means: tuple[float | None, ...]
    sample_counts: tuple[int, ...]
    spearman_rho: float | None
    permutation_p: float | None
    monotonic_non_decreasing: bool
    same_direction_as_h1: bool
    trend_supported: bool
    complete_case_seeds: int
    dropped_seeds: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "min_source_fitness": list(self.min_source_fitness),
            "means": list(self.means),
            "sample_counts": list(self.sample_counts),
            "spearman_rho": self.spearman_rho,
            "permutation_p": self.permutation_p,
            "monotonic_non_decreasing": self.monotonic_non_decreasing,
            "same_direction_as_h1": self.same_direction_as_h1,
            "trend_supported": self.trend_supported,
            "complete_case_seeds": self.complete_case_seeds,
            "dropped_seeds": self.dropped_seeds,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01ArmSummary:
    """Complete-case descriptive stats for one arm. Not a claim."""

    arm: str
    n: int
    mean: float | None
    sd: float | None
    births_mean: float | None
    extinction_rate: float
    adoption_mean: float | None
    missing: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "arm": self.arm,
            "n": self.n,
            "mean": self.mean,
            "sd": self.sd,
            "births_mean": self.births_mean,
            "extinction_rate": self.extinction_rate,
            "adoption_mean": self.adoption_mean,
            "missing": self.missing,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01Campaign:
    """Multi-seed source-bias campaign. Ceiling follows the prereg rule + ClaimGate."""

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
    scale: ScaleName = "smoke"
    tick_count: int = DEFAULT_TICK_COUNT
    population: int = DEFAULT_POPULATION
    prereg_digest: str = ""
    protocol_digest: str = ""
    paired_contrasts: tuple[HardExperiment01PairedContrast, ...] = ()
    shuffled_vs_capsules_off: HardExperiment01PairedContrast | None = None
    multiple_comparison_audit: MultipleComparisonAudit | None = None
    dose_records: tuple[HardExperiment01DoseRecord, ...] = ()
    dose_trend: HardExperiment01DoseTrend | None = None
    arm_summaries: tuple[HardExperiment01ArmSummary, ...] = ()
    decision_rule_passed: bool = False
    decision_rule_failures: tuple[str, ...] = ()
    claim_gate_allowed: bool = False
    claim_gate_decision_digest: str = ""
    claim_gate_final_claim: str = CLAIM_CEILING
    intervention_result: InterventionResult | None = None
    statistical_tier: str = "exploratory_only"

    def __post_init__(self) -> None:
        if len(self.seeds) < 2 or len(self.seeds) != len(self.seed_records):
            raise ConfigurationError("campaign requires paired seed records for every seed.")
        if self.claim_ceiling in _FORBIDDEN:
            raise ConfigurationError("hard experiment 01 must not use a forbidden claim ceiling.")
        if self.claim_ceiling not in {CLAIM_CEILING, INTERVENTION_CLAIM}:
            raise ConfigurationError(
                "hard experiment 01 ceiling must be an existing ClaimGate label."
            )
        if self.claim_ceiling == INTERVENTION_CLAIM and not self.claim_gate_allowed:
            raise ConfigurationError(
                "intervention_supported ceiling requires an allowed ClaimGate decision."
            )
        if not self.replay_records:
            raise ConfigurationError(
                "hard experiment 01 requires replay records for first and last seeds."
            )
        if not self.replay_matched or not all(item.matched for item in self.replay_records):
            raise ConfigurationError("hard experiment 01 requires a matching replay digest.")
        replay_arms = {item.arm for item in self.replay_records}
        if replay_arms != set(ARMS):
            raise ConfigurationError("hard experiment 01 must replay every arm.")
        if not self.interventions:
            object.__setattr__(self, "interventions", hard_experiment_01_interventions())
        if not self.missing_outcomes_per_arm:
            object.__setattr__(self, "missing_outcomes_per_arm", tuple((arm, 0) for arm in ARMS))
        missing_arms = {item[0] for item in self.missing_outcomes_per_arm}
        if missing_arms != set(ARMS):
            raise ConfigurationError("missing_outcomes_per_arm must cover every arm.")
        if any(count < 0 for _, count in self.missing_outcomes_per_arm):
            raise ConfigurationError("missing outcome counts must be >= 0.")
        expected_arms = {item.arm for item in self.interventions}
        if expected_arms != set(ARMS):
            raise ConfigurationError("hard experiment 01 interventions must cover every arm.")
        if not self.prereg_digest:
            object.__setattr__(self, "prereg_digest", hard_experiment_01_prereg_digest())
        if not self.protocol_digest:
            object.__setattr__(
                self, "protocol_digest", hard_experiment_01_protocol_digest(self.prereg_digest)
            )
        audit = self.multiple_comparison_audit
        if audit is None:
            audit = MultipleComparisonAudit(metric_count=3)
            object.__setattr__(self, "multiple_comparison_audit", audit)
        if audit.metric_count != 3:
            raise ConfigurationError("primary family is exactly three contrasts.")
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
            "scale": self.scale,
            "tick_count": self.tick_count,
            "population": self.population,
            "statistical_tier": self.statistical_tier,
            "prereg_digest": self.prereg_digest,
            "prereg_path": PREREG_RELATIVE_PATH,
            "protocol_digest": self.protocol_digest,
            "causal_dag": hard_experiment_01_causal_dag(),
            "seeds": list(self.seeds),
            "seed_records": [item.to_dict() for item in self.seed_records],
            "mean_delta_vs_source_bias_off": self.mean_delta_vs_source_bias_off,
            "mean_delta_vs_capsules_off": self.mean_delta_vs_capsules_off,
            "effect_vs_source_bias_off": self.effect_vs_source_bias_off.to_dict(),
            "effect_vs_capsules_off": self.effect_vs_capsules_off.to_dict(),
            "paired_contrasts": [item.to_dict() for item in self.paired_contrasts],
            "shuffled_vs_capsules_off": None
            if self.shuffled_vs_capsules_off is None
            else self.shuffled_vs_capsules_off.to_dict(),
            "multiple_comparison_audit": None
            if self.multiple_comparison_audit is None
            else self.multiple_comparison_audit.to_dict(),
            "dose_records": [item.to_dict() for item in self.dose_records],
            "dose_trend": None if self.dose_trend is None else self.dose_trend.to_dict(),
            "arm_summaries": [item.to_dict() for item in self.arm_summaries],
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
            "decision_rule_passed": self.decision_rule_passed,
            "decision_rule_failures": list(self.decision_rule_failures),
            "claim_gate_allowed": self.claim_gate_allowed,
            "claim_gate_decision_digest": self.claim_gate_decision_digest,
            "claim_gate_final_claim": self.claim_gate_final_claim,
            "intervention_result": None
            if self.intervention_result is None
            else self.intervention_result.to_dict(),
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
                "capsules_shuffled_is_content_scramble_not_channel_off",
                "price_identity_is_not_causal_without_the_explicit_dag",
                "null_or_small_effect_is_a_valid_finding",
                "not_knowledge_transfer_proof",
                "smoke_is_exploratory_only",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _record_from_run(
    *,
    seed: int,
    arm: ArmName,
    spec: GenesisExperimentSpec,
    result: object,
) -> HardExperiment01ArmRecord:
    births = _birth_count(result)
    sources, utilities, transfers, adoptions = _capsule_counts(result)
    fitness = _mean_last_tick_fitness(result)
    final_pop = _final_population(result)
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
        result_digest=_result_identity_digest(result),
        next_generation_observed=births > 0,
        outcome_missing=fitness is None,
        extinct=final_pop == 0,
        final_population=final_pop,
    )


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
    return _record_from_run(seed=seed, arm=arm, spec=spec, result=result)


def _dose_record(
    *,
    seed: int,
    min_source_fitness: float,
    tick_count: int,
    population: int,
    reused: HardExperiment01ArmRecord | None = None,
) -> HardExperiment01DoseRecord:
    if reused is not None:
        return HardExperiment01DoseRecord(
            seed=seed,
            min_source_fitness=float(min_source_fitness),
            terminal_mean_fitness=reused.terminal_mean_fitness,
            births=reused.births,
            capsule_adoptions=reused.capsule_adoptions,
            spec_digest=reused.spec_digest,
            result_digest=reused.result_digest,
            outcome_missing=reused.outcome_missing,
            extinct=reused.extinct,
        )
    spec = build_hard_experiment_01_dose_spec(
        seed=seed,
        min_source_fitness=min_source_fitness,
        tick_count=tick_count,
        population=population,
    )
    result = _run_spec(spec)
    fitness = _mean_last_tick_fitness(result)
    final_pop = _final_population(result)
    _sources, _utilities, _transfers, adoptions = _capsule_counts(result)
    return HardExperiment01DoseRecord(
        seed=seed,
        min_source_fitness=float(min_source_fitness),
        terminal_mean_fitness=fitness,
        births=_birth_count(result),
        capsule_adoptions=adoptions,
        spec_digest=spec.digest(),
        result_digest=_result_identity_digest(result),
        outcome_missing=fitness is None,
        extinct=final_pop == 0,
    )


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 10)


def _sample_sd(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


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
            found = getattr(record, arm)
            if isinstance(found, HardExperiment01ArmRecord):
                return found
            raise ConfigurationError(f"seed {seed} arm {arm} is not an arm record.")
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
    result_digest = _result_identity_digest(result)
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


def _ranks(values: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(indexed):
        end = index
        while end + 1 < len(indexed) and indexed[end + 1][1] == indexed[index][1]:
            end += 1
        average = (index + end) / 2.0 + 1.0
        for cursor in range(index, end + 1):
            ranks[indexed[cursor][0]] = average
        index = end + 1
    return ranks


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0.0 or den_y == 0.0:
        return None
    return num / (den_x * den_y)


def _spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    return _pearson(_ranks(xs), _ranks(ys))


def _ci_excludes_zero(ci_low: float | None, ci_high: float | None) -> bool:
    if ci_low is None or ci_high is None:
        return False
    return not (ci_low <= 0.0 <= ci_high)


def _paired_contrast(
    records: Sequence[HardExperiment01SeedRecord],
    *,
    treatment_arm: ArmName,
    baseline_arm: ArmName,
    p_holm: float | None = None,
) -> HardExperiment01PairedContrast:
    baseline, treatment = _complete_pair_values(
        records, treatment_arm=treatment_arm, baseline_arm=baseline_arm
    )
    dropped = len(records) - len(baseline)
    if not baseline:
        return HardExperiment01PairedContrast(
            treatment_arm=treatment_arm,
            baseline_arm=baseline_arm,
            n=0,
            mean_delta=0.0,
            sd_delta=0.0,
            dz=None,
            ci_low=None,
            ci_high=None,
            p_raw=None,
            p_holm=p_holm,
            claim_downgraded=True,
            dropped_pairs=dropped,
        )
    deltas = [treat - base for treat, base in zip(treatment, baseline, strict=True)]
    mean_delta = _mean(deltas)
    sd_delta = _sample_sd(deltas)
    dz: float | None
    try:
        dz = paired_effect_size(deltas) if len(deltas) >= 2 else None
    except ConfigurationError:
        dz = None
    ci_low, ci_high = bootstrap_ci_paired(
        deltas, method="bca", resamples=BOOTSTRAP_RESAMPLES, seed=INFERENTIAL_SEED
    )
    p_raw = exact_sign_flip_permutation_p(deltas, seed=INFERENTIAL_SEED)
    paired: PairedComparisonResult | None = None
    if dz is not None:
        plan = SeedSweepPlan(
            seeds=tuple(
                record.seed
                for record in records
                if not getattr(record, treatment_arm).outcome_missing
                and not getattr(record, baseline_arm).outcome_missing
            ),
            paired=True,
            min_seeds=2,
        )
        paired = PairedComparisonResult(
            metric=_PRIMARY_METRIC,
            baseline_values_digest=canonical_digest({"values": baseline}),
            treatment_values_digest=canonical_digest({"values": treatment}),
            paired_seed_digest=plan.digest(),
            effect_size=dz,
            sample_count=len(deltas),
            ci_low=ci_low,
            ci_high=ci_high,
        )
    claim_downgraded = True if paired is None else paired.claim_downgraded
    return HardExperiment01PairedContrast(
        treatment_arm=treatment_arm,
        baseline_arm=baseline_arm,
        n=len(deltas),
        mean_delta=mean_delta,
        sd_delta=sd_delta,
        dz=None if dz is None else round(dz, 10),
        ci_low=round(ci_low, 10),
        ci_high=round(ci_high, 10),
        p_raw=round(p_raw, 12),
        p_holm=p_holm,
        claim_downgraded=claim_downgraded,
        dropped_pairs=dropped,
        paired_result=paired,
    )


def _apply_holm(
    contrasts: Sequence[HardExperiment01PairedContrast],
) -> tuple[HardExperiment01PairedContrast, ...]:
    raw = [item.p_raw for item in contrasts]
    if any(value is None for value in raw):
        return tuple(
            replace(item, p_holm=None, claim_downgraded=True) for item in contrasts
        )
    adjusted = holm_correction([float(value) for value in raw if value is not None])
    updated: list[HardExperiment01PairedContrast] = []
    for item, p_holm in zip(contrasts, adjusted, strict=True):
        updated.append(replace(item, p_holm=round(p_holm, 12)))
    return tuple(updated)


def _arm_summary(
    records: Sequence[HardExperiment01SeedRecord], arm: ArmName
) -> HardExperiment01ArmSummary:
    items = [getattr(record, arm) for record in records]
    fitness = [
        item.terminal_mean_fitness
        for item in items
        if not item.outcome_missing and item.terminal_mean_fitness is not None
    ]
    births = [float(item.births) for item in items]
    adoptions = [float(item.capsule_adoptions) for item in items]
    extinct = sum(1 for item in items if item.extinct)
    missing = sum(1 for item in items if item.outcome_missing)
    return HardExperiment01ArmSummary(
        arm=arm,
        n=len(fitness),
        mean=None if not fitness else _mean(fitness),
        sd=None if len(fitness) < 2 else round(_sample_sd(fitness), 10),
        births_mean=_mean(births) if births else None,
        extinction_rate=round(extinct / len(items), 10) if items else 0.0,
        adoption_mean=_mean(adoptions) if adoptions else None,
        missing=missing,
    )


def _dose_means(
    dose_records: Sequence[HardExperiment01DoseRecord],
) -> tuple[tuple[float | None, ...], tuple[int, ...], int, int]:
    by_level: dict[float, list[float]] = {level: [] for level in DOSE_LEVELS}
    by_seed: dict[int, dict[float, float]] = {}
    for record in dose_records:
        if record.outcome_missing or record.terminal_mean_fitness is None:
            continue
        by_level[record.min_source_fitness].append(record.terminal_mean_fitness)
        by_seed.setdefault(record.seed, {})[record.min_source_fitness] = (
            record.terminal_mean_fitness
        )
    complete = [seed for seed, values in by_seed.items() if set(values) == set(DOSE_LEVELS)]
    all_seeds = {record.seed for record in dose_records}
    means = tuple(
        None if not by_level[level] else _mean(by_level[level]) for level in DOSE_LEVELS
    )
    counts = tuple(len(by_level[level]) for level in DOSE_LEVELS)
    return means, counts, len(complete), len(all_seeds) - len(complete)


def _dose_complete_matrix(
    dose_records: Sequence[HardExperiment01DoseRecord],
) -> list[list[float]]:
    by_seed: dict[int, dict[float, float]] = {}
    for record in dose_records:
        if record.outcome_missing or record.terminal_mean_fitness is None:
            continue
        by_seed.setdefault(record.seed, {})[record.min_source_fitness] = (
            record.terminal_mean_fitness
        )
    matrix: list[list[float]] = []
    for seed in sorted(by_seed):
        values = by_seed[seed]
        if set(values) != set(DOSE_LEVELS):
            continue
        matrix.append([values[level] for level in DOSE_LEVELS])
    return matrix


def _analyze_dose_trend(
    dose_records: Sequence[HardExperiment01DoseRecord],
) -> HardExperiment01DoseTrend:
    means, counts, complete_n, dropped = _dose_means(dose_records)
    numeric_means = [item for item in means if item is not None]
    monotonic = False
    if len(numeric_means) == len(DOSE_LEVELS):
        monotonic = all(
            numeric_means[index] <= numeric_means[index + 1] + 1e-15
            for index in range(len(numeric_means) - 1)
        )
    rho = _spearman(DOSE_LEVELS, numeric_means) if len(numeric_means) == len(DOSE_LEVELS) else None
    matrix = _dose_complete_matrix(dose_records)
    p_value: float | None = None
    if rho is not None and matrix:
        observed = abs(rho)
        rng = RNGManager(seed=INFERENTIAL_SEED, namespace="hard_experiment_01_dose_trend")
        extreme = 0
        for _ in range(DOSE_PERMUTATION_DRAWS):
            perm_means = [0.0] * len(DOSE_LEVELS)
            for row in matrix:
                order = list(range(len(DOSE_LEVELS)))
                shuffled: list[int] = []
                remaining = list(order)
                while remaining:
                    pick = rng.randrange(len(remaining))
                    shuffled.append(remaining.pop(pick))
                for index, source in enumerate(shuffled):
                    perm_means[index] += row[source]
            perm_means = [item / len(matrix) for item in perm_means]
            perm_rho = _spearman(DOSE_LEVELS, perm_means)
            if perm_rho is not None and abs(perm_rho) + 1e-15 >= observed:
                extreme += 1
        p_value = (1 + extreme) / (1 + DOSE_PERMUTATION_DRAWS)
    same_direction = bool(rho is not None and rho > 0.0)
    trend_supported = bool(
        monotonic
        and same_direction
        and rho is not None
        and p_value is not None
        and p_value < ALPHA
    )
    return HardExperiment01DoseTrend(
        min_source_fitness=DOSE_LEVELS,
        means=means,
        sample_counts=counts,
        spearman_rho=None if rho is None else round(rho, 10),
        permutation_p=None if p_value is None else round(p_value, 12),
        monotonic_non_decreasing=monotonic,
        same_direction_as_h1=same_direction,
        trend_supported=trend_supported,
        complete_case_seeds=complete_n,
        dropped_seeds=dropped,
    )


def _contrast_by_baseline(
    contrasts: Sequence[HardExperiment01PairedContrast], baseline: ArmName
) -> HardExperiment01PairedContrast | None:
    for item in contrasts:
        if item.treatment_arm == "source_bias_on" and item.baseline_arm == baseline:
            return item
    return None


def _decision_rule_failures(
    *,
    scale: ScaleName,
    statistical_tier: str,
    contrasts: Sequence[HardExperiment01PairedContrast],
    shuffled_vs_off: HardExperiment01PairedContrast | None,
    dose_trend: HardExperiment01DoseTrend | None,
    replay_matched: bool,
) -> tuple[str, ...]:
    failures: list[str] = []
    if scale != "research":
        failures.append("not_research_scale")
    if statistical_tier != "research_grade_benchmark_candidate":
        failures.append("statistical_tier_not_research_grade")
    if not replay_matched:
        failures.append("replay_mismatch")
    vs_off = _contrast_by_baseline(contrasts, "source_bias_off")
    vs_shuffled = _contrast_by_baseline(contrasts, "capsules_shuffled")
    if vs_off is None or vs_shuffled is None:
        failures.append("missing_primary_contrast")
        return tuple(failures)
    if vs_off.dz is None or vs_shuffled.dz is None:
        failures.append("dz_undefined")
    if not _ci_excludes_zero(vs_off.ci_low, vs_off.ci_high):
        failures.append("ci_on_vs_off_includes_0")
    if vs_off.p_holm is None or vs_off.p_holm >= ALPHA:
        failures.append("holm_on_vs_off_not_below_alpha")
    if not _ci_excludes_zero(vs_shuffled.ci_low, vs_shuffled.ci_high):
        failures.append("ci_on_vs_shuffled_includes_0")
    if vs_shuffled.p_holm is None or vs_shuffled.p_holm >= ALPHA:
        failures.append("holm_on_vs_shuffled_not_below_alpha")
    if shuffled_vs_off is None or shuffled_vs_off.ci_low is None or shuffled_vs_off.ci_high is None:
        failures.append("missing_shuffled_vs_capsules_off")
    elif _ci_excludes_zero(shuffled_vs_off.ci_low, shuffled_vs_off.ci_high):
        failures.append("shuffled_not_equivalent_to_capsules_off")
    if dose_trend is None or not dose_trend.trend_supported:
        failures.append("dose_trend_not_monotonic_same_direction")
    return tuple(failures)


def _request_intervention_supported(
    *,
    vs_off: HardExperiment01PairedContrast,
    protocol_digest: str,
    prereg_digest: str,
    intervention: InterventionResult,
) -> ClaimDecision:
    flags = {name: True for name in INTERVENTION_SUPPORTED_FLAGS}
    return ScientificClaimGate().decide(
        ClaimRequest(
            INTERVENTION_CLAIM,
            flags,
            evidence_digests=(
                intervention.digest,
                protocol_digest,
                prereg_digest,
                (
                    vs_off.paired_result.digest()
                    if vs_off.paired_result is not None
                    else protocol_digest
                ),
            ),
        )
    )


def run_hard_experiment_01(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    tick_count: int | None = None,
    population: int | None = None,
    scale: ScaleName = "smoke",
    include_dose: bool = True,
) -> HardExperiment01Campaign:
    """Paired source-bias campaign. Default is smoke (12/6/4, CI)."""

    if scale not in {"smoke", "research"}:
        raise ConfigurationError("scale must be 'smoke' or 'research'.")
    resolved_ticks = (
        RESEARCH_TICK_COUNT if scale == "research" else SMOKE_TICK_COUNT
    ) if tick_count is None else int(tick_count)
    resolved_pop = (
        RESEARCH_POPULATION if scale == "research" else SMOKE_POPULATION
    ) if population is None else int(population)
    default_n = RESEARCH_SEED_COUNT if scale == "research" else SMOKE_SEED_COUNT
    seed_tuple = _resolve_seeds(seeds, seed_count, default_count=default_n)
    records: list[HardExperiment01SeedRecord] = []
    dose_records: list[HardExperiment01DoseRecord] = []
    for seed in seed_tuple:
        by_arm = {
            arm: _arm_record(
                seed=seed, arm=arm, tick_count=resolved_ticks, population=resolved_pop
            )
            for arm in ARMS
        }
        records.append(
            HardExperiment01SeedRecord(
                seed=seed,
                source_bias_on=by_arm["source_bias_on"],
                source_bias_off=by_arm["source_bias_off"],
                capsules_off=by_arm["capsules_off"],
                capsules_shuffled=by_arm["capsules_shuffled"],
                delta_vs_source_bias_off=_optional_delta(
                    by_arm["source_bias_on"].terminal_mean_fitness,
                    by_arm["source_bias_off"].terminal_mean_fitness,
                ),
                delta_vs_capsules_off=_optional_delta(
                    by_arm["source_bias_on"].terminal_mean_fitness,
                    by_arm["capsules_off"].terminal_mean_fitness,
                ),
                delta_vs_capsules_shuffled=_optional_delta(
                    by_arm["source_bias_on"].terminal_mean_fitness,
                    by_arm["capsules_shuffled"].terminal_mean_fitness,
                ),
            )
        )
        if include_dose:
            for level in DOSE_LEVELS:
                reused = by_arm["source_bias_on"] if level == 2.0 else None
                dose_records.append(
                    _dose_record(
                        seed=seed,
                        min_source_fitness=level,
                        tick_count=resolved_ticks,
                        population=resolved_pop,
                        reused=reused,
                    )
                )
    off_fits, on_vs_off = _complete_pair_values(
        records, treatment_arm="source_bias_on", baseline_arm="source_bias_off"
    )
    none_fits, on_vs_none = _complete_pair_values(
        records, treatment_arm="source_bias_on", baseline_arm="capsules_off"
    )
    primary = _apply_holm(
        tuple(
            _paired_contrast(records, treatment_arm=treatment, baseline_arm=baseline)
            for treatment, baseline in PRIMARY_CONTRASTS
        )
    )
    shuffled_vs_off = _paired_contrast(
        records, treatment_arm="capsules_shuffled", baseline_arm="capsules_off"
    )
    dose_trend = _analyze_dose_trend(dose_records) if dose_records else None
    replay_seeds = tuple(dict.fromkeys((seed_tuple[0], seed_tuple[-1])))
    replay_records = tuple(
        _replay_arm(
            _original_arm(records, seed, arm),
            tick_count=resolved_ticks,
            population=resolved_pop,
        )
        for seed in replay_seeds
        for arm in ARMS
    )
    replay_matched = all(item.matched for item in replay_records)
    first_replay = next(
        item
        for item in replay_records
        if item.seed == seed_tuple[0] and item.arm == "source_bias_on"
    )
    statistical_tier = StatisticalTestPolicy().tier_for_n(len(seed_tuple))
    failures = _decision_rule_failures(
        scale=scale,
        statistical_tier=statistical_tier,
        contrasts=primary,
        shuffled_vs_off=shuffled_vs_off,
        dose_trend=dose_trend,
        replay_matched=replay_matched,
    )
    prereg_digest = hard_experiment_01_prereg_digest()
    protocol_digest = hard_experiment_01_protocol_digest(prereg_digest)
    vs_off = _contrast_by_baseline(primary, "source_bias_off")
    intervention: InterventionResult | None = None
    if (
        vs_off is not None
        and vs_off.n >= 2
        and vs_off.ci_low is not None
        and vs_off.ci_high is not None
    ):
        baseline_values, treatment_values = _complete_pair_values(
            records, treatment_arm="source_bias_on", baseline_arm="source_bias_off"
        )
        intervention = InterventionResult(
            scenario_id=f"{EXPERIMENT_ID}:source_bias_on_vs_source_bias_off",
            baseline_digest=canonical_digest({"values": baseline_values}),
            treatment_digest=canonical_digest({"values": treatment_values}),
            effect_size=0.0 if vs_off.dz is None else vs_off.dz,
            confidence_interval=(vs_off.ci_low, vs_off.ci_high),
            paired_seed_count=vs_off.n,
            evidence_level=INTERVENTION_CLAIM if not failures else CLAIM_CEILING,
        )
    gate = ScientificClaimGate()
    if not failures and vs_off is not None and intervention is not None:
        decision = _request_intervention_supported(
            vs_off=vs_off,
            protocol_digest=protocol_digest,
            prereg_digest=prereg_digest,
            intervention=intervention,
        )
        claim_gate_allowed = bool(decision.allowed and decision.final_claim == INTERVENTION_CLAIM)
        ceiling = INTERVENTION_CLAIM if claim_gate_allowed else CLAIM_CEILING
    else:
        decision = gate.decide(
            ClaimRequest(CLAIM_CEILING, {}, evidence_digests=(prereg_digest, protocol_digest))
        )
        claim_gate_allowed = False
        ceiling = CLAIM_CEILING
    campaign = HardExperiment01Campaign(
        seeds=seed_tuple,
        seed_records=tuple(records),
        mean_delta_vs_source_bias_off=_mean(
            [
                item.delta_vs_source_bias_off
                for item in records
                if item.delta_vs_source_bias_off is not None
            ]
        ),
        mean_delta_vs_capsules_off=_mean(
            [
                item.delta_vs_capsules_off
                for item in records
                if item.delta_vs_capsules_off is not None
            ]
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
        replay_matched=replay_matched,
        missing_outcomes_per_arm=_missing_outcomes_per_arm(records),
        scale=scale,
        tick_count=resolved_ticks,
        population=resolved_pop,
        prereg_digest=prereg_digest,
        protocol_digest=protocol_digest,
        paired_contrasts=primary,
        shuffled_vs_capsules_off=shuffled_vs_off,
        multiple_comparison_audit=MultipleComparisonAudit(metric_count=3),
        dose_records=tuple(dose_records),
        dose_trend=dose_trend,
        arm_summaries=tuple(_arm_summary(records, arm) for arm in ARMS),
        decision_rule_passed=not failures and claim_gate_allowed,
        decision_rule_failures=failures,
        claim_gate_allowed=claim_gate_allowed,
        claim_gate_decision_digest=decision.digest,
        claim_gate_final_claim=decision.final_claim if claim_gate_allowed else CLAIM_CEILING,
        intervention_result=intervention,
        statistical_tier=statistical_tier,
        claim_ceiling=ceiling,
    )
    _assert_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


def evaluate_hard_experiment_01_claim(
    payload: Mapping[str, JsonValue] | object,
) -> ClaimDecision:
    """Decide the campaign ceiling. Intelligence claims stay blocked."""

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
    ceiling = str(data.get("claim_ceiling") or CLAIM_CEILING)
    if ceiling in _FORBIDDEN:
        raise ConfigurationError(f"hard experiment 01 must not request {ceiling}.")
    if ceiling == INTERVENTION_CLAIM and data.get("claim_gate_allowed") is True:
        flags = {name: True for name in INTERVENTION_SUPPORTED_FLAGS}
        decision = gate.decide(
            ClaimRequest(INTERVENTION_CLAIM, flags, evidence_digests=(digest,) if digest else ())
        )
    else:
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
    primary_lines = []
    for item in campaign.paired_contrasts:
        primary_lines.append(
            f"contrast {item.treatment_arm}_vs_{item.baseline_arm} "
            f"n={item.n} dz={item.dz} ci95=({item.ci_low},{item.ci_high}) "
            f"p_holm={item.p_holm} claim_downgraded={item.claim_downgraded}"
        )
    dose = campaign.dose_trend
    return "\n".join(
        (
            f"experiment {campaign.experiment_id}",
            f"question {campaign.question}",
            f"scale {campaign.scale}",
            f"seed_count {len(campaign.seeds)}",
            f"statistical_tier {campaign.statistical_tier}",
            f"prereg_digest {campaign.prereg_digest}",
            f"mean_delta_vs_source_bias_off {campaign.mean_delta_vs_source_bias_off}",
            f"mean_delta_vs_capsules_off {campaign.mean_delta_vs_capsules_off}",
            f"effect_vs_source_bias_off {vs_off.standardized_delta_lite} {vs_off.interpretation}",
            f"effect_vs_capsules_off {vs_none.standardized_delta_lite} {vs_none.interpretation}",
            *primary_lines,
            f"dose_trend_supported {None if dose is None else dose.trend_supported}",
            f"decision_rule_passed {campaign.decision_rule_passed}",
            f"replay_matched {campaign.replay_matched}",
            f"claim_ceiling {campaign.claim_ceiling}",
            "collective_intelligence False",
            "intelligence False",
            f"digest {campaign.digest}",
            f"standardized_note {_cohens_d_note(vs_off.standardized_delta_lite)}",
        )
    )


def committed_research_results_path() -> Path:
    return _repo_root() / "docs" / "hard_experiment_01" / "results_v1.json"


def write_hard_experiment_01_research_results(path: Path | None = None) -> Path:
    """Run the research campaign and write the digest-backed JSON artifact."""

    import json

    dest = path or committed_research_results_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    campaign = run_hard_experiment_01(scale="research")
    dest.write_text(
        json.dumps(campaign.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return dest
