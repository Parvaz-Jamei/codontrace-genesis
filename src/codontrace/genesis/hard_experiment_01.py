"""Hard experiment 01: preregistered capsule source-bias causal design.

Wave 1 confirmatory measurement, not a new Phase letter. Four paired arms
plus a Goldsby-style dose ladder. Causal reading uses the explicit DAG in
``docs/HARD_EXPERIMENT_01_PREREG.md`` (Okasha & Otsuka 2020). Claim ceiling
is ``runtime_observation`` unless the preregistered decision rule holds and
``ScientificClaimGate`` allows existing ``intervention_supported``.

Wave 1b keeps the same question, arms, seeds, and decision rule. A survival
calibration overlay (food / energy / death / initial genomes) plus an assay
gate sit in front of confirmatory claims: if the treatment arm does not
emit/adopt capsules or goes extinct, contrasts are recorded but
``assay_failed`` keeps the ceiling at ``runtime_observation``.

Wave 1d′ (SCHEMA v5 / Amendment 03) keeps seed-permuted roles from Amd 02
and reverts food/respawn to Amendment 01 / v3 (every-cell food;
``respawn_draws_per_tick = max(1, population_size)``). Amd 02 / SCHEMA v4
remains the frozen failed-calibration trail. No new engine semantics;
estimand unchanged.

Wave 1d″ is evidence-honesty only (no new ClaimGate claim, no Amd rewrite,
no re-campaign): document that peer-rotation shuffle preserves the payload
marginal; split adoption attempts vs accepts; surface shuffle
content/source-changed rates; correct the dose pattern display label.

Wave 1e (SCHEMA v6 / Amendment 04) adds confirmatory ``capsules_content_null``
(fixed WAIT payload) and auxiliary ``capsules_activity_matched`` (yoked accept
count). Legacy ``capsules_shuffled`` is sensitivity-only. Amendment 05 demotes
activity_matched off the pilot gate after Wave 1e pilot FAIL on volume yoke
only; content_null remains confirmatory; SCHEMA stays v6. ClaimGate ceiling
stays ``runtime_observation``; Amd 04/05 alone never raise it.

SCHEMA v7 / ``HARD_EXPERIMENT_01_PREREG_AMENDMENT_LOCK`` keeps every-cell food
coverage and role Fisher–Yates, and adds seed-contingent initial food amounts
(discrete multipliers; mean 1.0) so analysis seeds are distinct environment
realizations (Avida spatial-heterogeneity lesson). Confirmatory null remains
``capsules_content_null``; shuffled stays sensitivity-only. Lock alone never
raises ClaimGate; ceiling at most ``intervention_supported`` when the full
rule holds with a healthy control.

Forbidden: intelligence / collective_intelligence / AGI /
tokyo_type1_passed / avida_replacement. ClaimGate is never loosened.
A null finding is valid. This module does not mutate a global ClaimGate.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.capsule import (
    CapsuleAdoptionBlockedReason,
    CapsuleAdoptionPolicy,
    CapsuleShuffleMode,
    CapsuleTransferConfig,
)
from codontrace.genesis.causal_validation import InterventionResult
from codontrace.genesis.claim_gate import ClaimDecision, ClaimRequest, ScientificClaimGate
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.population import MetabolicConfig
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
from codontrace.genesis.substrate import world2d_to_element_grid
from codontrace.genesis.text_digest import sha256_text_file
from codontrace.rng import RNGManager
from codontrace.world import World2D

CLAIM_CEILING = "runtime_observation"
INTERVENTION_CLAIM = "intervention_supported"
SMOKE_SEED_COUNT = 12
RESEARCH_SEED_COUNT = 30
# Smoke = 8 ticks x 8 organisms: the smallest overlay on which every Wave 1c
# manipulation check can pass (good + poor emitter + receivers within reach).
SMOKE_TICK_COUNT = 8
SMOKE_POPULATION = 8
RESEARCH_TICK_COUNT = 40
RESEARCH_POPULATION = 16
DEFAULT_TICK_COUNT = SMOKE_TICK_COUNT
DEFAULT_POPULATION = SMOKE_POPULATION
EXPERIMENT_ID = "hard_experiment_01_capsule_source_bias"
SCHEMA_VERSION = "hard_experiment_01_v7"
PREREG_RELATIVE_PATH = "docs/HARD_EXPERIMENT_01_PREREG.md"
PREREG_AMENDMENT_RELATIVE_PATH = "docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_01.md"
PREREG_AMENDMENT_02_RELATIVE_PATH = "docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_02.md"
PREREG_AMENDMENT_03_RELATIVE_PATH = "docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_03.md"
PREREG_AMENDMENT_04_RELATIVE_PATH = "docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_04.md"
PREREG_AMENDMENT_05_RELATIVE_PATH = "docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_05.md"
PREREG_AMENDMENT_LOCK_RELATIVE_PATH = "docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_LOCK.md"
# Amd 04 reporting reference: mean |activity_match_gap| vs epsilon (accepts).
# Amd 05: activity match is exploratory / non-blocking for the pilot gate;
# do not silent-retune epsilon inside Amd 04.
ACTIVITY_MATCH_EPSILON = 1
ACTIVITY_MATCH_PILOT_GATE = False  # Amd 05: demoted off pilot clearance
CONTENT_NULL_PAYLOAD_ACTION = "WAIT"
# Wave 1c primary outcome: mean terminal runtime ATP of the *receiver* class
# (the units the intervention acts on). The v1/v2 composite selection score is
# kept as a secondary, descriptive field (``legacy_terminal_selection_fitness``).
PRIMARY_OUTCOME = "receiver_mean_terminal_runtime_atp"
PILOT_SEEDS: tuple[int, ...] = tuple(range(1000, 1010))
INFERENTIAL_SEED = 20260911
BOOTSTRAP_RESAMPLES = 10000
DOSE_PERMUTATION_DRAWS = 10000
ALPHA = 0.05
# Dose ladder on ``min_source_fitness``. Emitter per-tick source fitness is
# discrete on this substrate (poor emitter 1.0, good emitter 3.0; pilot seeds
# 1000-1009), so the gate is a step function of the threshold. Preregistered
# pattern (amendment 01): outcome(0.0) < outcome(1.5) and outcome(4.0) <
# outcome(1.5) — "step up, then saturate to capsules_off when no source passes".
DOSE_LEVELS: tuple[float, ...] = (0.0, 1.5, 4.0)
DOSE_PEAK_INDEX = 1
ScaleName = Literal["smoke", "research"]
MIN_SOURCE_FITNESS_TREATMENT = 1.5
ASSAY_ADOPTIONS_NEAR_ZERO = 1e-12
ASSAY_EXTINCTION_NEAR_ONE = 1.0 - 1e-12
# Peer-rotation often sits just under 0.99 (window-size-1 identity); CONTENT_NULL
# is the confirmatory null and must clear this bar. Shuffled arm only fails
# never_changed; rate_below is applied to content_null (Amd 04).
ASSAY_SHUFFLE_CONTENT_CHANGE_MIN = 0.99
# Wave 1b survival / channel-activity calibration. Overlay only — does not
# mutate ``life_loop_world`` defaults or Phase A–E pins. Existing Genesis v0
# actions only (no new signaling pathway).
# Wave 1c population design (prereg amendment 01). Three genome classes so
# that source quality actually varies and the ``min_source_fitness`` gate has
# something to select on:
#   good emitter  EAT_LUMEN, EMIT_NEXUS, WAIT  -> payload EAT_LUMEN (useful)
#   poor emitter  SENSE_DANGER, EMIT_NEXUS, WAIT -> payload SENSE_DANGER (costly, useless)
#   receiver      WAIT, WAIT, WAIT             -> WAIT is substitutable by an adopted payload
CALIBRATION_EATER_GENOME = "101000000"
CALIBRATION_EMITTER_GENOME = "101110000"
CALIBRATION_POOR_EMITTER_GENOME = "010110000"
CALIBRATION_WAITER_GENOME = "000000000"
CALIBRATION_GOOD_PAYLOAD_ACTION = "EAT_LUMEN"
CALIBRATION_POOR_PAYLOAD_ACTION = "SENSE_DANGER"
# index % CALIBRATION_ROLE_PERIOD: 0 -> good emitter, 1 -> poor emitter, else receiver
CALIBRATION_ROLE_PERIOD = 4
CALIBRATION_INITIAL_RUNTIME_ATP = 48.0
CALIBRATION_BASAL_COST = 0.4
# Renewable food: every cell starts with a small Lumen bite and the eaten
# cell refills under the eater on the next tick (``respawn_under_organisms``),
# so EAT_LUMEN is sustainably positive (+amount - 0.8 per tick) while WAIT
# (-0.1) and SENSE_DANGER (-0.4) are sustainably negative.
CALIBRATION_RESOURCE_AMOUNT = 2.0
# SCHEMA v7 / LOCK: seed-contingent initial food amounts (coverage stays 1.0).
# Mean multiplier = 1.0 in expectation — avoids Amd 02 sparse-food assay inversion.
FOOD_AMOUNT_MULTIPLIERS: tuple[float, ...] = (0.75, 1.0, 1.25)
CALIBRATION_RESPAWN_RATE = 1.0
CALIBRATION_RESPAWN_UNDER_ORGANISMS = True
CALIBRATION_STARVATION_CONSECUTIVE_TICKS = 3

ArmName = Literal[
    "source_bias_on",
    "source_bias_off",
    "capsules_off",
    "capsules_content_null",
    "capsules_activity_matched",
    "capsules_shuffled",
    "oracle_capsule",
]
ARMS: tuple[ArmName, ...] = (
    "source_bias_on",
    "source_bias_off",
    "capsules_off",
    "capsules_content_null",
    "capsules_activity_matched",
    "capsules_shuffled",
    "oracle_capsule",
)
# Confirmatory analysis arms (Amd 04). ``oracle_capsule`` is a positive
# control; ``capsules_shuffled`` is sensitivity/archival; activity_matched is
# auxiliary (yoked volume).
ANALYSIS_ARMS: tuple[ArmName, ...] = (
    "source_bias_on",
    "source_bias_off",
    "capsules_off",
    "capsules_content_null",
)
SENSITIVITY_ARMS: tuple[ArmName, ...] = ("capsules_shuffled",)
AUXILIARY_ARMS: tuple[ArmName, ...] = ("capsules_activity_matched",)
PRIMARY_CONTRASTS: tuple[tuple[ArmName, ArmName], ...] = (
    ("source_bias_on", "source_bias_off"),
    ("source_bias_on", "capsules_off"),
    ("source_bias_on", "capsules_content_null"),
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
    "Does source-fitness-gated capsule transfer raise receiver mean terminal "
    "runtime ATP relative to (a) the same capsule channel with source-fitness "
    "gating ablated, (b) capsules off, and (c) the capsule channel on with "
    "informative payload destroyed (content null)?"
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
    metric_name=PRIMARY_OUTCOME,
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
        "e2_runtime_coupling": (
            "CapsuleTransferConfig.adoption_effect_action: adopted payload substitutes "
            "WAIT in the receiver (Wave 1c). Without it e2 is absent and arms are inert."
        ),
    }


def hard_experiment_01_prereg_amendment_path() -> Path:
    return _repo_root() / PREREG_AMENDMENT_RELATIVE_PATH


def hard_experiment_01_prereg_amendment_digest() -> str:
    """SHA-256 of the frozen amendment 01 file (UTF-8 bytes)."""

    path = hard_experiment_01_prereg_amendment_path()
    if not path.is_file():
        raise ConfigurationError(
            f"missing preregistration amendment: {PREREG_AMENDMENT_RELATIVE_PATH}"
        )
    return sha256_text_file(path)


def hard_experiment_01_prereg_amendment_02_path() -> Path:
    return _repo_root() / PREREG_AMENDMENT_02_RELATIVE_PATH


def hard_experiment_01_prereg_amendment_02_digest() -> str:
    """SHA-256 of the frozen amendment 02 file (UTF-8 bytes)."""

    path = hard_experiment_01_prereg_amendment_02_path()
    if not path.is_file():
        raise ConfigurationError(
            f"missing preregistration amendment: {PREREG_AMENDMENT_02_RELATIVE_PATH}"
        )
    return sha256_text_file(path)


def hard_experiment_01_prereg_amendment_03_path() -> Path:
    return _repo_root() / PREREG_AMENDMENT_03_RELATIVE_PATH


def hard_experiment_01_prereg_amendment_03_digest() -> str:
    """SHA-256 of the frozen amendment 03 file (UTF-8 bytes)."""

    path = hard_experiment_01_prereg_amendment_03_path()
    if not path.is_file():
        raise ConfigurationError(
            f"missing preregistration amendment: {PREREG_AMENDMENT_03_RELATIVE_PATH}"
        )
    return sha256_text_file(path)


def hard_experiment_01_prereg_amendment_04_path() -> Path:
    return _repo_root() / PREREG_AMENDMENT_04_RELATIVE_PATH


def hard_experiment_01_prereg_amendment_04_digest() -> str:
    """SHA-256 of the frozen amendment 04 file (UTF-8 bytes)."""

    path = hard_experiment_01_prereg_amendment_04_path()
    if not path.is_file():
        raise ConfigurationError(
            f"missing preregistration amendment: {PREREG_AMENDMENT_04_RELATIVE_PATH}"
        )
    return sha256_text_file(path)


def hard_experiment_01_prereg_amendment_05_path() -> Path:
    return _repo_root() / PREREG_AMENDMENT_05_RELATIVE_PATH


def hard_experiment_01_prereg_amendment_05_digest() -> str:
    """SHA-256 of the frozen amendment 05 file (UTF-8 bytes)."""

    path = hard_experiment_01_prereg_amendment_05_path()
    if not path.is_file():
        raise ConfigurationError(
            f"missing preregistration amendment: {PREREG_AMENDMENT_05_RELATIVE_PATH}"
        )
    return sha256_text_file(path)


def hard_experiment_01_prereg_amendment_lock_path() -> Path:
    return _repo_root() / PREREG_AMENDMENT_LOCK_RELATIVE_PATH


def hard_experiment_01_prereg_amendment_lock_digest() -> str:
    """SHA-256 of the frozen SCHEMA v7 amendment LOCK file (UTF-8 bytes)."""

    path = hard_experiment_01_prereg_amendment_lock_path()
    if not path.is_file():
        raise ConfigurationError(
            f"missing preregistration amendment lock: {PREREG_AMENDMENT_LOCK_RELATIVE_PATH}"
        )
    return sha256_text_file(path)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def hard_experiment_01_prereg_path() -> Path:
    return _repo_root() / PREREG_RELATIVE_PATH


def hard_experiment_01_prereg_digest() -> str:
    """SHA-256 of the frozen preregistration file (UTF-8 bytes)."""

    path = hard_experiment_01_prereg_path()
    if not path.is_file():
        raise ConfigurationError(f"missing preregistration file: {PREREG_RELATIVE_PATH}")
    return sha256_text_file(path)


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
            "prereg_amendment_path": PREREG_AMENDMENT_RELATIVE_PATH,
            "prereg_amendment_digest": hard_experiment_01_prereg_amendment_digest(),
            "prereg_amendment_02_path": PREREG_AMENDMENT_02_RELATIVE_PATH,
            "prereg_amendment_02_digest": hard_experiment_01_prereg_amendment_02_digest(),
            "prereg_amendment_03_path": PREREG_AMENDMENT_03_RELATIVE_PATH,
            "prereg_amendment_03_digest": hard_experiment_01_prereg_amendment_03_digest(),
            "prereg_amendment_04_path": PREREG_AMENDMENT_04_RELATIVE_PATH,
            "prereg_amendment_04_digest": hard_experiment_01_prereg_amendment_04_digest(),
            "prereg_amendment_05_path": PREREG_AMENDMENT_05_RELATIVE_PATH,
            "prereg_amendment_05_digest": hard_experiment_01_prereg_amendment_05_digest(),
            "prereg_amendment_lock_path": PREREG_AMENDMENT_LOCK_RELATIVE_PATH,
            "prereg_amendment_lock_digest": hard_experiment_01_prereg_amendment_lock_digest(),
            "role_layout": "seed_permuted_v3_multiset",
            "food_layout": "every_cell_seed_amounts_v7",
            "food_amount_multipliers": list(FOOD_AMOUNT_MULTIPLIERS),
            "respawn_draws_per_tick": "max(1, population_size)",
            "primary_outcome": PRIMARY_OUTCOME,
            "analysis_arms": list(ANALYSIS_ARMS),
            "sensitivity_arms": list(SENSITIVITY_ARMS),
            "auxiliary_arms": list(AUXILIARY_ARMS),
            "positive_control_arm": "oracle_capsule",
            "dose_peak_index": DOSE_PEAK_INDEX,
            "pilot_seeds": list(PILOT_SEEDS),
            "inferential_seed": INFERENTIAL_SEED,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "alpha": ALPHA,
            "activity_match_epsilon": ACTIVITY_MATCH_EPSILON,
            "activity_match_pilot_gate": ACTIVITY_MATCH_PILOT_GATE,
            "content_null_payload_action": CONTENT_NULL_PAYLOAD_ACTION,
        }
    )


def hard_experiment_01_calibration_knobs() -> dict[str, JsonValue]:
    """Survival / channel-activity knobs. Not a new mechanism and not the estimand."""

    return {
        "wave": "1e_lock_v7",
        "dated": "2026-09-17",
        "scope": "hard_experiment_01_overlay_only",
        "life_loop_defaults_unchanged": True,
        "good_emitter_genome": CALIBRATION_EMITTER_GENOME,
        "poor_emitter_genome": CALIBRATION_POOR_EMITTER_GENOME,
        "receiver_genome": CALIBRATION_WAITER_GENOME,
        "good_payload_action": CALIBRATION_GOOD_PAYLOAD_ACTION,
        "poor_payload_action": CALIBRATION_POOR_PAYLOAD_ACTION,
        "role_period": CALIBRATION_ROLE_PERIOD,
        "role_layout": "seed_permuted_v3_multiset",
        "initial_runtime_atp": CALIBRATION_INITIAL_RUNTIME_ATP,
        "basal_runtime_atp_cost": CALIBRATION_BASAL_COST,
        "resource_amount": CALIBRATION_RESOURCE_AMOUNT,
        "respawn_rate": CALIBRATION_RESPAWN_RATE,
        "respawn_under_organisms": CALIBRATION_RESPAWN_UNDER_ORGANISMS,
        "respawn_draws_per_tick": "max(1, population_size)",
        "starvation_consecutive_ticks": CALIBRATION_STARVATION_CONSECUTIVE_TICKS,
        "food_layout": "every_cell_seed_amounts_v7",
        "food_amount_multipliers": list(FOOD_AMOUNT_MULTIPLIERS),
        "food_coverage": 1.0,
        "adoption_effect_action": True,
        "adoption_substitutable_actions": ["WAIT"],
        "primary_outcome": PRIMARY_OUTCOME,
        "note": (
            "SCHEMA v7 / LOCK: keep Amd 03 ecology + Amd 04/05 confirmatory "
            "content_null; add seed-contingent initial food amounts "
            "(multipliers mean 1.0). Shuffled sensitivity-only. ClaimGate "
            "ceiling at most intervention_supported when full rule holds."
        ),
        "content_null_payload_action": CONTENT_NULL_PAYLOAD_ACTION,
        "activity_match_epsilon": ACTIVITY_MATCH_EPSILON,
        "activity_match_pilot_gate": ACTIVITY_MATCH_PILOT_GATE,
    }


def _calibration_food_cells(
    width: int, height: int
) -> tuple[tuple[int, int], ...]:
    """Every lattice cell (Amd 01 / v3 / Amd 03 / LOCK). Coverage stays 1.0."""

    cells = tuple((x, y) for y in range(int(height)) for x in range(int(width)))
    if not cells:
        raise ConfigurationError("hard experiment 01 food layout requires a non-empty lattice.")
    return cells


def calibration_food_amount_layout(
    seed: int, width: int, height: int
) -> tuple[tuple[tuple[int, int], float], ...]:
    """SCHEMA v7 / LOCK: every-cell coverage with seed-contingent amounts.

    Discrete multipliers ``FOOD_AMOUNT_MULTIPLIERS`` (mean 1.0) so each analysis
    seed realizes a distinct resource field without Amd 02 sparse-food failure.
    Namespace ``hard_experiment_01/food_amounts`` (does not steal engine streams).
    """

    cells = _calibration_food_cells(width, height)
    rng = RNGManager(seed=int(seed), namespace="hard_experiment_01/food_amounts")
    n_mult = len(FOOD_AMOUNT_MULTIPLIERS)
    layout: list[tuple[tuple[int, int], float]] = []
    for cell in cells:
        mult = FOOD_AMOUNT_MULTIPLIERS[rng.randrange(n_mult)]
        layout.append((cell, float(CALIBRATION_RESOURCE_AMOUNT) * float(mult)))
    return tuple(layout)


def calibration_role_for_index(index: int, *, oracle: bool = False) -> str:
    """Genome class for organism ``index`` (see prereg amendment 01)."""

    slot = int(index) % CALIBRATION_ROLE_PERIOD
    if slot == 0:
        return "good_emitter"
    if slot == 1:
        return "good_emitter" if oracle else "poor_emitter"
    return "receiver"


def permute_roles_for_seed(
    seed: int, n: int, *, oracle: bool = False
) -> tuple[str, ...]:
    """Fisher–Yates permute the v3 role multiset (Amd 02 §3.1)."""

    roles = [calibration_role_for_index(index, oracle=oracle) for index in range(int(n))]
    rng = RNGManager(seed=seed, namespace="hard_experiment_01/roles")
    for index in range(len(roles) - 1, 0, -1):
        swap = rng.randrange(index + 1)
        roles[index], roles[swap] = roles[swap], roles[index]
    return tuple(roles)


_ROLE_GENOME: dict[str, str] = {
    "good_emitter": CALIBRATION_EMITTER_GENOME,
    "poor_emitter": CALIBRATION_POOR_EMITTER_GENOME,
    "receiver": CALIBRATION_WAITER_GENOME,
}


def _calibrated_genomes(
    base_genomes: Sequence[str], *, seed: int, oracle: bool = False
) -> tuple[str, ...]:
    roles = permute_roles_for_seed(seed, len(base_genomes), oracle=oracle)
    return tuple(_ROLE_GENOME[role] for role in roles)


def _apply_survival_calibration(
    spec: GenesisExperimentSpec, *, seed: int, oracle: bool = False
) -> GenesisExperimentSpec:
    """Keep research-scale overlays alive long enough for capsules to act.

    Overlay-only. Does not change ``life_loop_world`` defaults.
    """

    configs = spec.population_configs
    if configs is None:
        raise ConfigurationError("hard experiment 01 overlay requires population_configs.")
    width = int(spec.world_width)
    height = int(spec.world_height)
    food_layout = calibration_food_amount_layout(seed, width, height)
    food_cells = tuple(cell for cell, _amount in food_layout)
    food_coverage = len(food_cells) / float(width * height)
    world = World2D(width, height)
    for position, amount in food_layout:
        world.place_resource(position, amount)
    # Amd 03: revert respawn draws to Amd 01 / v3 (smoke 8→8, research 16→16).
    # Food is every-cell again; max_resources remains the full lattice.
    population_size = len(spec.genome_bits)
    respawn_draws_per_tick = max(1, population_size)
    lattice_cells = width * height
    resource_policy = replace(
        configs.runtime_resource_policy,
        respawn_enabled=True,
        respawn_rate=CALIBRATION_RESPAWN_RATE,
        max_resources=lattice_cells,
        amount=CALIBRATION_RESOURCE_AMOUNT,
        status="runtime_effective_default_on",
        respawn_under_organisms=CALIBRATION_RESPAWN_UNDER_ORGANISMS,
        respawn_draws_per_tick=respawn_draws_per_tick,
    )
    configs = replace(
        configs,
        metabolism=MetabolicConfig(enabled=True, basal_runtime_atp_cost=CALIBRATION_BASAL_COST),
        runtime_resource_policy=resource_policy,
        death_monitoring=replace(
            configs.death_monitoring,
            starvation_consecutive_ticks=CALIBRATION_STARVATION_CONSECUTIVE_TICKS,
        ),
    )
    genome_roles = permute_roles_for_seed(seed, len(spec.genome_bits), oracle=oracle)
    metadata: dict[str, JsonValue] = {
        **spec.metadata,
        "hard_experiment_01_calibration": hard_experiment_01_calibration_knobs(),
        "food_cells": [list(item) for item in food_cells],
        "food_amounts": [float(amount) for _cell, amount in food_layout],
        "food_amount_multipliers": list(FOOD_AMOUNT_MULTIPLIERS),
        "food_layout": "every_cell_seed_amounts_v7",
        "food_coverage": food_coverage,
        "initial_food_patches": len(food_cells),
        "max_resources": resource_policy.max_resources,
        "respawn_rate": CALIBRATION_RESPAWN_RATE,
        "resource_amount": CALIBRATION_RESOURCE_AMOUNT,
        "basal_runtime_atp_cost": CALIBRATION_BASAL_COST,
        "starvation_consecutive_ticks": CALIBRATION_STARVATION_CONSECUTIVE_TICKS,
        "genome_roles": list(genome_roles),
    }
    return replace(
        spec,
        genome_bits=_calibrated_genomes(spec.genome_bits, seed=seed, oracle=oracle),
        initial_runtime_atp=CALIBRATION_INITIAL_RUNTIME_ATP,
        element_grid=world2d_to_element_grid(world),
        population_configs=configs,
        metadata=metadata,
    )


def evaluate_hard_experiment_01_assay(
    summaries: Sequence[HardExperiment01ArmSummary] | Sequence[Mapping[str, JsonValue]],
    *,
    treatment_arm: ArmName = "source_bias_on",
    seed_records: Sequence[HardExperiment01SeedRecord] = (),
) -> tuple[bool, tuple[str, ...]]:
    """Refuse confirmatory claims when the treatment channel was not exercised.

    Assay failure is a quality gate, not a change to the causal estimand.
    Contrasts remain recorded; ClaimGate stays at ``runtime_observation``.
    """

    treatment: HardExperiment01ArmSummary | Mapping[str, JsonValue] | None = None
    for item in summaries:
        arm = item.arm if isinstance(item, HardExperiment01ArmSummary) else str(item.get("arm", ""))
        if arm == treatment_arm:
            treatment = item
            break
    if treatment is None:
        return True, ("assay_failed_missing_treatment_summary",)
    if isinstance(treatment, HardExperiment01ArmSummary):
        adoption_mean = treatment.adoption_mean
        extinction_rate = treatment.extinction_rate
    else:
        raw_adoptions = treatment.get("adoption_mean")
        raw_extinction = treatment.get("extinction_rate")
        adoption_mean = (
            float(raw_adoptions) if isinstance(raw_adoptions, (int, float)) else None
        )
        extinction_rate = (
            float(raw_extinction) if isinstance(raw_extinction, (int, float)) else 1.0
        )
    failures: list[str] = []
    if adoption_mean is None or adoption_mean <= ASSAY_ADOPTIONS_NEAR_ZERO:
        failures.append("assay_failed_treatment_adoptions_near_zero")
    if extinction_rate >= ASSAY_EXTINCTION_NEAR_ONE:
        failures.append("assay_failed_treatment_extinction_near_one")
    failures.extend(_manipulation_check_failures(summaries, seed_records=seed_records))
    return bool(failures), tuple(failures)


def _summary_field(
    item: HardExperiment01ArmSummary | Mapping[str, JsonValue], name: str
) -> JsonValue:
    if isinstance(item, HardExperiment01ArmSummary):
        value = getattr(item, name, None)
        return dict(value) if isinstance(value, Mapping) else value
    return item.get(name)


def _manipulation_check_failures(
    summaries: Sequence[HardExperiment01ArmSummary] | Sequence[Mapping[str, JsonValue]],
    *,
    seed_records: Sequence[HardExperiment01SeedRecord] = (),
) -> list[str]:
    """Wave 1c manipulation check (Okasha & Otsuka do-operator sanity).

    Each arm must have done what its intervention says it does; otherwise a
    null is uninterpretable (``assay_invalid``), whatever the p-values say.
    """

    by_arm: dict[str, HardExperiment01ArmSummary | Mapping[str, JsonValue]] = {}
    for item in summaries:
        arm = item.arm if isinstance(item, HardExperiment01ArmSummary) else str(item.get("arm", ""))
        by_arm[arm] = item
    if not all(name in by_arm for name in ARMS):
        return []  # legacy (v1/v2) payloads: only the adoption/extinction checks apply
    failures: list[str] = []

    def _num(arm: str, name: str) -> float | None:
        value = _summary_field(by_arm[arm], name)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value)

    def _payloads(arm: str) -> set[str]:
        value = _summary_field(by_arm[arm], "bias_payload_totals")
        if not isinstance(value, Mapping):
            return set()
        return {str(key) for key, count in value.items() if int(count) > 0}

    applied_on = _num("source_bias_on", "bias_applied_mean")
    if applied_on is None or applied_on <= 0.0:
        failures.append("assay_failed_treatment_bias_never_applied")
    rejected_on = _num("source_bias_on", "rejected_by_source_fitness_mean")
    if rejected_on is None or rejected_on <= 0.0:
        failures.append("assay_failed_source_gate_never_rejected")
    if _payloads("source_bias_on") - {CALIBRATION_GOOD_PAYLOAD_ACTION}:
        failures.append("assay_failed_treatment_adopted_poor_payload")
    if CALIBRATION_POOR_PAYLOAD_ACTION not in _payloads("source_bias_off"):
        failures.append("assay_failed_gate_off_never_adopted_poor_payload")
    applied_none = _num("capsules_off", "bias_applied_mean")
    adoptions_none = _num("capsules_off", "adoption_mean")
    if (applied_none or 0.0) > 0.0 or (adoptions_none or 0.0) > 0.0:
        failures.append("assay_failed_capsules_off_channel_active")
    # Wave 1d″: historical adoption_mean counts *attempts*, so a checks that
    # only looks at attempts is vacuous when blocked records dominate. Prefer
    # successful accepts and/or shuffle content_changed when those additive
    # fields exist (new runs). Legacy artifacts without the fields keep the
    # attempts fallback so frozen v5 JSON tests stay green.
    adoptions_shuffled = _num("capsules_shuffled", "adoption_mean")
    accepted_shuffled = _num("capsules_shuffled", "adoption_accepted_mean")
    content_changed_rate = _num("capsules_shuffled", "shuffle_content_changed_rate")
    if accepted_shuffled is not None or content_changed_rate is not None:
        channel_active = (accepted_shuffled or 0.0) > ASSAY_ADOPTIONS_NEAR_ZERO or (
            content_changed_rate or 0.0
        ) > 0.0
    else:
        channel_active = (
            adoptions_shuffled is not None
            and adoptions_shuffled > ASSAY_ADOPTIONS_NEAR_ZERO
        )
    if not channel_active:
        failures.append("assay_failed_shuffled_channel_silent")
    # B2: scramble must have fired when shuffle telemetry exists.
    shuffle_records = _num("capsules_shuffled", "shuffle_record_mean")
    if (
        content_changed_rate is not None
        and shuffle_records is not None
        and shuffle_records > 0.0
        and content_changed_rate <= 0.0
    ):
        failures.append("assay_failed_shuffle_never_changed_content")
    # Amd 04: confirmatory content_null must destroy profitable payload marginal.
    if "capsules_content_null" in by_arm:
        null_payloads = _payloads("capsules_content_null")
        if CALIBRATION_GOOD_PAYLOAD_ACTION in null_payloads:
            failures.append("assay_failed_content_null_adopted_profitable_payload")
        content_changed_null = _num("capsules_content_null", "shuffle_content_changed_rate")
        accepted_null = _num("capsules_content_null", "adoption_accepted_mean")
        adoptions_null = _num("capsules_content_null", "adoption_mean")
        null_channel = False
        if content_changed_null is not None or accepted_null is not None:
            null_channel = (content_changed_null or 0.0) > 0.0 or (
                accepted_null or 0.0
            ) > ASSAY_ADOPTIONS_NEAR_ZERO
        elif adoptions_null is not None:
            null_channel = adoptions_null > ASSAY_ADOPTIONS_NEAR_ZERO
        if not null_channel:
            failures.append("assay_failed_content_null_channel_silent")
        if (
            content_changed_null is not None
            and content_changed_null + 1e-15 < ASSAY_SHUFFLE_CONTENT_CHANGE_MIN
        ):
            failures.append("assay_failed_shuffle_content_change_rate_below_threshold")
    oracle_mean = _num("oracle_capsule", "mean")
    none_mean = _num("capsules_off", "mean")
    if oracle_mean is None or none_mean is None or oracle_mean <= none_mean:
        failures.append("assay_failed_positive_control_did_not_move_outcome")
    if seed_records and all(
        record.source_bias_on.result_digest == record.source_bias_off.result_digest
        for record in seed_records
    ):
        failures.append("assay_failed_arms_bitwise_identical")
    # SCHEMA v7 / LOCK: refuse 30 bitwise replays on the treatment estimand.
    if seed_records:
        treatment_outcomes = [
            record.source_bias_on.terminal_mean_fitness
            for record in seed_records
            if record.source_bias_on.terminal_mean_fitness is not None
        ]
        if len(treatment_outcomes) >= 2 and len(set(treatment_outcomes)) < 2:
            failures.append("assay_failed_treatment_seed_variance_zero")
    return failures


@dataclass(frozen=True, slots=True)
class HardExperiment01TickDiagnostic:
    """Per-tick food / energy / vital / capsule counters. Not a claim."""

    tick: int
    population: int
    food_cells: int
    mean_runtime_atp: float | None
    births: int
    deaths: int
    capsule_emits: int
    capsule_adoptions: int
    agents_at_or_above_min_source_fitness: int
    max_fitness: float | None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "tick": self.tick,
            "population": self.population,
            "food_cells": self.food_cells,
            "mean_runtime_atp": self.mean_runtime_atp,
            "births": self.births,
            "deaths": self.deaths,
            "capsule_emits": self.capsule_emits,
            "capsule_adoptions": self.capsule_adoptions,
            "agents_at_or_above_min_source_fitness": self.agents_at_or_above_min_source_fitness,
            "max_fitness": self.max_fitness,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01RunDiagnostic:
    """Instrument one overlay run. Observation only."""

    seed: int
    arm: str
    tick_count: int
    population: int
    final_population: int | None
    extinct: bool
    total_births: int
    total_deaths: int
    total_emits: int
    total_adoptions: int
    any_agent_reached_min_source_fitness: bool
    ticks: tuple[HardExperiment01TickDiagnostic, ...]
    claim_ceiling: str = CLAIM_CEILING

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "arm": self.arm,
            "tick_count": self.tick_count,
            "population": self.population,
            "final_population": self.final_population,
            "extinct": self.extinct,
            "total_births": self.total_births,
            "total_deaths": self.total_deaths,
            "total_emits": self.total_emits,
            "total_adoptions": self.total_adoptions,
            "any_agent_reached_min_source_fitness": self.any_agent_reached_min_source_fitness,
            "ticks": [item.to_dict() for item in self.ticks],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
        }


def diagnose_hard_experiment_01_run(
    *,
    seed: int,
    arm: ArmName,
    tick_count: int,
    population: int,
    min_source_fitness: float = MIN_SOURCE_FITNESS_TREATMENT,
) -> HardExperiment01RunDiagnostic:
    """Food / ATP / vital / capsule series for one calibrated overlay run."""

    spec, result = _run_arm(seed=seed, arm=arm, tick_count=tick_count, population=population)
    tick_rows: list[HardExperiment01TickDiagnostic] = []
    reached = False
    total_emits = 0
    total_adoptions = 0
    total_births = 0
    total_deaths = 0
    for index, tick in enumerate(getattr(result, "ticks", ()) or ()):
        generation = getattr(tick, "generation_result", None)
        pop_state = None if generation is None else getattr(generation, "population", None)
        raw_organisms = () if pop_state is None else getattr(pop_state, "organisms", ()) or ()
        organisms = tuple(raw_organisms)
        resources = getattr(getattr(generation, "world_after", None), "resources", None)
        food_cells = len(resources) if isinstance(resources, dict) else 0
        atps = [
            float(getattr(getattr(item, "atp_state", None), "runtime_available", 0.0) or 0.0)
            for item in organisms
        ]
        fitness_scores = [
            float(getattr(item, "score", 0.0) or 0.0)
            for item in getattr(pop_state, "fitness", ()) or ()
        ]
        above = sum(1 for score in fitness_scores if score >= min_source_fitness)
        if above:
            reached = True
        emits = 0
        adoptions = 0
        for record in getattr(generation, "organism_records", ()) or ():
            trace = getattr(record, "trace", None)
            events = getattr(trace, "events", ()) or ()
            for event in events:
                action = getattr(event, "action", "")
                if action == "EMIT_NEXUS":
                    emits += 1
                delta = getattr(event, "world_delta", {}) or {}
                if delta.get("capsule_adoption_success") is True:
                    adoptions += 1
        if adoptions == 0:
            adoptions = int(getattr(generation, "capsule_adoption_successes", 0) or 0)
        births = int(getattr(generation, "births", 0) or 0)
        deaths = int(getattr(generation, "deaths", 0) or 0)
        total_emits += emits
        total_adoptions += adoptions
        total_births += births
        total_deaths += deaths
        tick_rows.append(
            HardExperiment01TickDiagnostic(
                tick=index,
                population=len(organisms),
                food_cells=food_cells,
                mean_runtime_atp=None if not atps else round(sum(atps) / len(atps), 10),
                births=births,
                deaths=deaths,
                capsule_emits=emits,
                capsule_adoptions=adoptions,
                agents_at_or_above_min_source_fitness=above,
                max_fitness=None if not fitness_scores else round(max(fitness_scores), 10),
            )
        )
    sources, _utilities, _transfers, recorded_adoptions, _accepted = _capsule_counts(result)
    if total_adoptions == 0:
        total_adoptions = recorded_adoptions
    if total_emits == 0:
        total_emits = sources
    final_pop = _final_population(result)
    _ = spec
    return HardExperiment01RunDiagnostic(
        seed=seed,
        arm=arm,
        tick_count=tick_count,
        population=population,
        final_population=final_pop,
        extinct=final_pop == 0,
        total_births=total_births,
        total_deaths=total_deaths,
        total_emits=total_emits,
        total_adoptions=total_adoptions,
        any_agent_reached_min_source_fitness=reached,
        ticks=tuple(tick_rows),
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
            applied_value=(
                f"min_source_fitness={MIN_SOURCE_FITNESS_TREATMENT:g},FITNESS_WEIGHTED,shuffle=off"
            ),
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
            arm="capsules_content_null",
            role="negative_control",
            target_mechanism="capsule_content_information",
            action="null_capsule_payload_keep_channel",
            knob="CapsuleTransferConfig.shuffle_mode",
            applied_value="CapsuleShuffleMode.CONTENT_NULL",
            compared_to="source_bias_on",
            cuts_edges=("e2_content",),
        ),
        HardExperiment01Intervention(
            arm="capsules_activity_matched",
            role="auxiliary_control",
            target_mechanism="capsule_channel_activity_volume",
            action="null_payload_yoke_accept_count_to_treatment",
            knob="CapsuleTransferConfig.shuffle_mode+max_successful_adoptions",
            applied_value="CONTENT_NULL+yoked_accept_cap",
            compared_to="source_bias_on",
            cuts_edges=("e2_content",),
        ),
        HardExperiment01Intervention(
            arm="capsules_shuffled",
            role="sensitivity_negative_control",
            target_mechanism="capsule_content_information",
            action="peer_rotate_capsule_content_keep_channel",
            knob="CapsuleTransferConfig.shuffle_mode",
            applied_value="CapsuleShuffleMode.CONTENT",
            compared_to="source_bias_on",
            cuts_edges=("e2_content",),
        ),
        HardExperiment01Intervention(
            arm="oracle_capsule",
            role="positive_control",
            target_mechanism="capsule_channel_capacity",
            action="all_emitters_good_gate_off",
            knob="genome_roles",
            applied_value="poor_emitter->good_emitter; min_source_fitness=0.0",
            compared_to="capsules_off",
            cuts_edges=(),
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
    max_successful_adoptions: int | None = None,
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
        max_adoptions_per_organism=1,
        max_capsules_read_per_tick=4,
        accept_provisional_source_fitness=True,
        adoption_effect_action=True,
        adoption_substitutable_actions=("WAIT",),
        max_successful_adoptions=max_successful_adoptions,
    )


def _capsule_for_arm(
    arm: ArmName, *, activity_match_budget: int | None = None
) -> CapsuleTransferConfig:
    if arm == "capsules_off":
        return CapsuleTransferConfig(enabled=False)
    if arm == "source_bias_on":
        return _enabled_capsule(
            min_source_fitness=MIN_SOURCE_FITNESS_TREATMENT,
            adoption_policy=CapsuleAdoptionPolicy.FITNESS_WEIGHTED,
            shuffle_mode=CapsuleShuffleMode.OFF,
        )
    if arm in {"source_bias_off", "oracle_capsule"}:
        return _enabled_capsule(
            min_source_fitness=0.0,
            adoption_policy=CapsuleAdoptionPolicy.THRESHOLD,
            shuffle_mode=CapsuleShuffleMode.OFF,
        )
    if arm == "capsules_content_null":
        return _enabled_capsule(
            min_source_fitness=MIN_SOURCE_FITNESS_TREATMENT,
            adoption_policy=CapsuleAdoptionPolicy.FITNESS_WEIGHTED,
            shuffle_mode=CapsuleShuffleMode.CONTENT_NULL,
        )
    if arm == "capsules_activity_matched":
        if activity_match_budget is None:
            raise ConfigurationError(
                "capsules_activity_matched requires activity_match_budget "
                "(yoked source_bias_on capsule_adoptions_accepted)."
            )
        return _enabled_capsule(
            min_source_fitness=MIN_SOURCE_FITNESS_TREATMENT,
            adoption_policy=CapsuleAdoptionPolicy.FITNESS_WEIGHTED,
            shuffle_mode=CapsuleShuffleMode.CONTENT_NULL,
            max_successful_adoptions=int(activity_match_budget),
        )
    if arm == "capsules_shuffled":
        return _enabled_capsule(
            min_source_fitness=MIN_SOURCE_FITNESS_TREATMENT,
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
    oracle: bool = False,
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
    return _apply_survival_calibration(
        replace(
            base,
            population_configs=configs,
            capsule_transfer_config=capsule,
            engine_config=engine_config,
            metadata=metadata,
        ),
        seed=seed,
        oracle=oracle,
    )


def build_hard_experiment_01_spec(
    *,
    seed: int,
    arm: ArmName,
    tick_count: int = DEFAULT_TICK_COUNT,
    population: int = DEFAULT_POPULATION,
    activity_match_budget: int | None = None,
) -> GenesisExperimentSpec:
    """Life-loop overlay. Does not mutate default Phase A–E preset digests.

    ``activity_match_budget`` is required for ``capsules_activity_matched``
    (yoked ``source_bias_on`` successful accepts for the same seed).
    """

    if arm not in ARMS:
        raise ConfigurationError(f"unknown hard experiment 01 arm: {arm!r}")
    return _apply_capsule_overlay(
        seed=seed,
        tick_count=tick_count,
        population=population,
        capsule=_capsule_for_arm(arm, activity_match_budget=activity_match_budget),
        arm_label=arm,
        oracle=arm == "oracle_capsule",
    )


def build_hard_experiment_01_dose_spec(
    *,
    seed: int,
    min_source_fitness: float,
    tick_count: int = DEFAULT_TICK_COUNT,
    population: int = DEFAULT_POPULATION,
) -> GenesisExperimentSpec:
    """FITNESS_WEIGHTED dose overlay. The treatment threshold reuses the treatment arm."""

    if float(min_source_fitness) not in DOSE_LEVELS:
        raise ConfigurationError(f"dose min_source_fitness must be one of {DOSE_LEVELS}.")
    if float(min_source_fitness) == MIN_SOURCE_FITNESS_TREATMENT:
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
        arm_label=f"dose_{float(min_source_fitness):g}",
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


def _genome_roles(spec: GenesisExperimentSpec) -> tuple[str, ...]:
    raw = spec.metadata.get("genome_roles")
    if not isinstance(raw, list):
        raise ConfigurationError("hard experiment 01 spec is missing genome_roles metadata.")
    return tuple(str(item) for item in raw)


def _organism_index(organism_id: str) -> int | None:
    tail = str(organism_id).rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else None


def _receiver_mean_terminal_atp(result: object, roles: Sequence[str]) -> float | None:
    """Primary outcome: mean terminal runtime ATP across surviving receivers.

    ``None`` when no receiver is alive at the last tick (the pair is dropped,
    not zero-filled). Newborns (index beyond the initial roster) are ignored.
    """

    ticks = tuple(getattr(result, "ticks", ()) or ())
    if not ticks:
        return None
    generation = getattr(ticks[-1], "generation_result", None)
    population = getattr(generation, "population", None)
    values: list[float] = []
    for organism in getattr(population, "organisms", ()) or ():
        index = _organism_index(getattr(organism, "id", ""))
        if index is None or index >= len(roles) or roles[index] != "receiver":
            continue
        atp_state = getattr(organism, "atp_state", None)
        available = getattr(atp_state, "runtime_available", None)
        if isinstance(available, (int, float)) and not isinstance(available, bool):
            values.append(float(available))
    if not values:
        return None
    return round(sum(values) / len(values), 10)


def _manipulation_metrics(result: object) -> tuple[int, dict[str, int], int]:
    """(bias_applied_events, payload->count, adoptions rejected by source gate)."""

    applied = 0
    payloads: dict[str, int] = {}
    for tick in getattr(result, "ticks", ()) or ():
        generation = getattr(tick, "generation_result", None)
        for trace in getattr(generation, "traces", ()) or ():
            for event in getattr(trace, "events", ()) or ():
                delta = getattr(event, "world_delta", {}) or {}
                if delta.get("capsule_action_bias_applied") is True:
                    applied += 1
                    payload = str(delta.get("capsule_action_bias_to", ""))
                    payloads[payload] = payloads.get(payload, 0) + 1
    rejected = sum(
        1
        for record in getattr(result, "capsule_adoption_records", ()) or ()
        if getattr(record, "blocked_reason", None)
        == CapsuleAdoptionBlockedReason.SOURCE_FITNESS_BELOW_THRESHOLD.value
    )
    return applied, dict(sorted(payloads.items())), rejected


def _birth_count(result: object) -> int:
    total = 0
    for tick in getattr(result, "ticks", ()) or ():
        generation = getattr(tick, "generation_result", None)
        total += int(getattr(generation, "births", 0) or 0)
    return total


def _capsule_counts(result: object) -> tuple[int, int, int, int, int]:
    """Count source, utility, transfer, adoption attempts, and successful accepts.

    ``capsule_adoptions`` / adoption attempts = len(capsule_adoption_records),
    including blocked attempts. Successful accepts require
    ``adoption_success is True``. These surfaces are not interchangeable.
    """

    sources = len(tuple(getattr(result, "capsule_source_fitness_records", ()) or ()))
    utilities = len(tuple(getattr(result, "capsule_utility_records", ()) or ()))
    transfers = len(tuple(getattr(result, "capsule_transfer_metrics", ()) or ()))
    adoption_records = tuple(getattr(result, "capsule_adoption_records", ()) or ())
    adoptions = len(adoption_records)
    accepted = sum(
        1 for record in adoption_records if getattr(record, "adoption_success", False) is True
    )
    return sources, utilities, transfers, adoptions, accepted


def _shuffle_change_counts(result: object) -> tuple[int, int, int]:
    """(shuffle_record_count, content_changed_count, source_changed_count)."""

    records = tuple(getattr(result, "capsule_shuffle_records", ()) or ())
    content = sum(1 for record in records if getattr(record, "content_changed", False) is True)
    source = sum(1 for record in records if getattr(record, "source_changed", False) is True)
    return len(records), content, source


def _adoption_blocked_by_reason(result: object) -> dict[str, int]:
    """Blocked-reason histogram for adoption attempts (B1 invariant)."""

    counts: dict[str, int] = {}
    for record in getattr(result, "capsule_adoption_records", ()) or ():
        reason = getattr(record, "blocked_reason", None)
        if reason is None:
            continue
        key = str(reason)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _source_fitness_support(
    result: object,
) -> tuple[float | None, float | None, float | None]:
    """min / median / max of adoption-record source_fitness (B5 dose support)."""

    values: list[float] = []
    for record in getattr(result, "capsule_adoption_records", ()) or ():
        raw = getattr(record, "source_fitness", None)
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            values.append(float(raw))
    if not values:
        return None, None, None
    values.sort()
    mid = values[len(values) // 2]
    return values[0], mid, values[-1]


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
    activity_match_budget: int | None = None,
) -> tuple[GenesisExperimentSpec, object]:
    spec = build_hard_experiment_01_spec(
        seed=seed,
        arm=arm,
        tick_count=tick_count,
        population=population,
        activity_match_budget=activity_match_budget,
    )
    return spec, _run_spec(spec)


@dataclass(frozen=True, slots=True)
class HardExperiment01ArmRecord:
    """One seed × one arm. Fitness is a runtime observation, not intelligence.

    ``capsule_adoptions`` counts adoption *attempts* (len of
    ``capsule_adoption_records``, including blocked). Successful accepts are
    ``capsule_adoptions_accepted``. Shuffle peer-rotation audits live in the
    ``shuffle_*`` fields (Wave 1d″ honesty).
    """

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
    legacy_terminal_selection_fitness: float | None = None
    receiver_count: int = 0
    bias_applied_events: int = 0
    bias_payload_counts: Mapping[str, int] = field(default_factory=dict)
    rejected_by_source_fitness: int = 0
    capsule_adoptions_accepted: int = 0
    shuffle_record_count: int = 0
    shuffle_content_changed_count: int = 0
    shuffle_source_changed_count: int = 0
    capsule_adoption_blocked_by_reason: Mapping[str, int] = field(default_factory=dict)
    source_fitness_min: float | None = None
    source_fitness_median: float | None = None
    source_fitness_max: float | None = None
    activity_match_budget: int | None = None
    activity_match_gap: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "bias_payload_counts", dict(self.bias_payload_counts))
        object.__setattr__(
            self,
            "capsule_adoption_blocked_by_reason",
            dict(self.capsule_adoption_blocked_by_reason),
        )
        if min(self.receiver_count, self.bias_applied_events, self.rejected_by_source_fitness) < 0:
            raise ConfigurationError("manipulation-check counts must be >= 0.")
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
            self.capsule_adoptions_accepted,
            self.shuffle_record_count,
            self.shuffle_content_changed_count,
            self.shuffle_source_changed_count,
        ) < 0:
            raise ConfigurationError("counts must be >= 0.")
        if self.capsule_adoptions_accepted > self.capsule_adoptions:
            raise ConfigurationError("accepted adoptions cannot exceed attempts.")
        blocked_total = sum(int(v) for v in self.capsule_adoption_blocked_by_reason.values())
        if self.capsule_adoptions != self.capsule_adoptions_accepted + blocked_total:
            raise ConfigurationError(
                "adoption attempts must equal accepted + sum(blocked_by_reason)."
            )
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
            "capsule_adoption_attempts": self.capsule_adoptions,  # B1 alias
            "capsule_adoptions_semantics": "attempts",
            "capsule_adoptions_accepted": self.capsule_adoptions_accepted,
            "spec_digest": self.spec_digest,
            "result_digest": self.result_digest,
            "next_generation_observed": self.next_generation_observed,
            "outcome_missing": self.outcome_missing,
            "extinct": self.extinct,
            "final_population": self.final_population,
            "primary_outcome": PRIMARY_OUTCOME,
            "legacy_terminal_selection_fitness": self.legacy_terminal_selection_fitness,
            "receiver_count": self.receiver_count,
            "bias_applied_events": self.bias_applied_events,
            "bias_payload_counts": dict(self.bias_payload_counts),
            "rejected_by_source_fitness": self.rejected_by_source_fitness,
            "shuffle_record_count": self.shuffle_record_count,
            "shuffle_content_changed_count": self.shuffle_content_changed_count,
            "shuffle_source_changed_count": self.shuffle_source_changed_count,
            "capsule_adoption_blocked_by_reason": dict(self.capsule_adoption_blocked_by_reason),
            "source_fitness_min": self.source_fitness_min,
            "source_fitness_median": self.source_fitness_median,
            "source_fitness_max": self.source_fitness_max,
            "activity_match_budget": self.activity_match_budget,
            "activity_match_gap": self.activity_match_gap,
            "claim_ceiling": CLAIM_CEILING,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01SeedRecord:
    """Paired record for one seed: confirmatory + auxiliary + sensitivity + oracle."""

    seed: int
    source_bias_on: HardExperiment01ArmRecord
    source_bias_off: HardExperiment01ArmRecord
    capsules_off: HardExperiment01ArmRecord
    capsules_shuffled: HardExperiment01ArmRecord
    delta_vs_source_bias_off: float | None
    delta_vs_capsules_off: float | None
    delta_vs_capsules_shuffled: float | None
    oracle_capsule: HardExperiment01ArmRecord | None = None
    capsules_content_null: HardExperiment01ArmRecord | None = None
    capsules_activity_matched: HardExperiment01ArmRecord | None = None
    delta_vs_capsules_content_null: float | None = None
    delta_vs_capsules_activity_matched: float | None = None

    def __post_init__(self) -> None:
        arms = tuple(
            item
            for item in (
                self.source_bias_on,
                self.source_bias_off,
                self.capsules_off,
                self.capsules_content_null,
                self.capsules_activity_matched,
                self.capsules_shuffled,
                self.oracle_capsule,
            )
            if item is not None
        )
        if any(item.seed != self.seed for item in arms):
            raise ConfigurationError("seed records must share one seed.")
        for name in (
            "delta_vs_source_bias_off",
            "delta_vs_capsules_off",
            "delta_vs_capsules_shuffled",
            "delta_vs_capsules_content_null",
            "delta_vs_capsules_activity_matched",
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
            "capsules_content_null": (
                None
                if self.capsules_content_null is None
                else self.capsules_content_null.to_dict()
            ),
            "capsules_activity_matched": (
                None
                if self.capsules_activity_matched is None
                else self.capsules_activity_matched.to_dict()
            ),
            "capsules_shuffled": self.capsules_shuffled.to_dict(),
            "oracle_capsule": (
                None if self.oracle_capsule is None else self.oracle_capsule.to_dict()
            ),
            "delta_vs_source_bias_off": self.delta_vs_source_bias_off,
            "delta_vs_capsules_off": self.delta_vs_capsules_off,
            "delta_vs_capsules_content_null": self.delta_vs_capsules_content_null,
            "delta_vs_capsules_activity_matched": self.delta_vs_capsules_activity_matched,
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
    """Preregistered pattern test on the threshold ladder (amendment 01).

    Statistic S = (m_peak - m_low) + (m_peak - m_high); one-sided
    seed-fixed permutation p by shuffling levels within each complete seed.

    Wave 1d′/″ honesty: Amd 01 frozen text still says ``step_up_then_saturate``,
    but new-run display uses ``peak_at_intermediate_dose_then_channel_closure``
    because dose(4.0) is outside support (equals capsules_off / total gate
    closure). ``dose(1.5)`` is identical to the treatment arm; S is the
    algebraic sum of two primary contrasts and adds no independent information
    (``independent: false``; Hothorn 2020; Simpson & Margolin 1986). Descriptive
    only — excluded from the confirmatory decision rule and from metric_count.
    """

    min_source_fitness: tuple[float, ...]
    means: tuple[float | None, ...]
    sample_counts: tuple[int, ...]
    pattern_statistic: float | None
    permutation_p: float | None
    pattern_matched: bool
    trend_supported: bool
    complete_case_seeds: int
    dropped_seeds: int
    pattern: str = "peak_at_intermediate_dose_then_channel_closure"
    independent: bool = False
    pattern_label_note: str = (
        "Amd 01 frozen label was step_up_then_saturate; display is "
        "peak_at_intermediate_dose_then_channel_closure (dose 4.0 ≡ capsules_off "
        "/ channel closure, not saturation). dose(1.5)≡source_bias_on; "
        "S=(m_1.5-m_0)+(m_1.5-m_4) is the algebraic sum of two primary contrasts "
        "(independent=false; zero inferential info). Descriptive only — not in "
        "decision rule / metric_count. Cite Hothorn 2020; Simpson & Margolin 1986."
    )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "min_source_fitness": list(self.min_source_fitness),
            "means": list(self.means),
            "sample_counts": list(self.sample_counts),
            "pattern": self.pattern,
            "pattern_label_note": self.pattern_label_note,
            "independent": self.independent,
            "peak_index": DOSE_PEAK_INDEX,
            "pattern_statistic": self.pattern_statistic,
            "permutation_p": self.permutation_p,
            "pattern_matched": self.pattern_matched,
            "trend_supported": self.trend_supported,
            "complete_case_seeds": self.complete_case_seeds,
            "dropped_seeds": self.dropped_seeds,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment01ArmSummary:
    """Complete-case descriptive stats for one arm. Not a claim.

    ``adoption_mean`` is mean adoption *attempts* (historical). Successful
    accepts are ``adoption_accepted_mean``. Shuffle rates are Wave 1d″ additive.
    """

    arm: str
    n: int
    mean: float | None
    sd: float | None
    births_mean: float | None
    extinction_rate: float
    adoption_mean: float | None
    missing: int
    bias_applied_mean: float | None = None
    bias_payload_totals: Mapping[str, int] = field(default_factory=dict)
    rejected_by_source_fitness_mean: float | None = None
    legacy_fitness_mean: float | None = None
    adoption_accepted_mean: float | None = None
    shuffle_content_changed_rate: float | None = None
    shuffle_source_changed_rate: float | None = None
    shuffle_record_mean: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "bias_payload_totals", dict(self.bias_payload_totals))

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "arm": self.arm,
            "n": self.n,
            "mean": self.mean,
            "sd": self.sd,
            "births_mean": self.births_mean,
            "extinction_rate": self.extinction_rate,
            "adoption_mean": self.adoption_mean,
            "adoption_mean_semantics": "attempts",
            "adoption_accepted_mean": self.adoption_accepted_mean,
            "missing": self.missing,
            "primary_outcome": PRIMARY_OUTCOME,
            "bias_applied_mean": self.bias_applied_mean,
            "bias_payload_totals": dict(self.bias_payload_totals),
            "rejected_by_source_fitness_mean": self.rejected_by_source_fitness_mean,
            "legacy_fitness_mean": self.legacy_fitness_mean,
            "shuffle_record_mean": self.shuffle_record_mean,
            "shuffle_content_changed_rate": self.shuffle_content_changed_rate,
            "shuffle_source_changed_rate": self.shuffle_source_changed_rate,
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
    content_null_vs_capsules_off: HardExperiment01PairedContrast | None = None
    multiple_comparison_audit: MultipleComparisonAudit | None = None
    dose_records: tuple[HardExperiment01DoseRecord, ...] = ()
    dose_trend: HardExperiment01DoseTrend | None = None
    arm_summaries: tuple[HardExperiment01ArmSummary, ...] = ()
    decision_rule_passed: bool = False
    decision_rule_failures: tuple[str, ...] = ()
    sensitivity_failures: tuple[str, ...] = ()
    mean_abs_activity_match_gap: float | None = None
    claim_gate_allowed: bool = False
    claim_gate_decision_digest: str = ""
    claim_gate_final_claim: str = CLAIM_CEILING
    intervention_result: InterventionResult | None = None
    statistical_tier: str = "exploratory_only"
    assay_failed: bool = False
    assay_failures: tuple[str, ...] = ()

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
        primary_n = len(PRIMARY_CONTRASTS)
        if audit is None:
            audit = MultipleComparisonAudit(metric_count=primary_n)
            object.__setattr__(self, "multiple_comparison_audit", audit)
        if audit.metric_count != primary_n:
            raise ConfigurationError(
                f"primary family metric_count must equal len(PRIMARY_CONTRASTS)={primary_n}."
            )
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
            "prereg_amendment_path": PREREG_AMENDMENT_RELATIVE_PATH,
            "prereg_amendment_digest": hard_experiment_01_prereg_amendment_digest(),
            "prereg_amendment_02_path": PREREG_AMENDMENT_02_RELATIVE_PATH,
            "prereg_amendment_02_digest": hard_experiment_01_prereg_amendment_02_digest(),
            "prereg_amendment_03_path": PREREG_AMENDMENT_03_RELATIVE_PATH,
            "prereg_amendment_03_digest": hard_experiment_01_prereg_amendment_03_digest(),
            "prereg_amendment_04_path": PREREG_AMENDMENT_04_RELATIVE_PATH,
            "prereg_amendment_04_digest": hard_experiment_01_prereg_amendment_04_digest(),
            "prereg_amendment_05_path": PREREG_AMENDMENT_05_RELATIVE_PATH,
            "prereg_amendment_05_digest": hard_experiment_01_prereg_amendment_05_digest(),
            "prereg_amendment_lock_path": PREREG_AMENDMENT_LOCK_RELATIVE_PATH,
            "prereg_amendment_lock_digest": hard_experiment_01_prereg_amendment_lock_digest(),
            "role_layout": "seed_permuted_v3_multiset",
            "food_layout": "every_cell_seed_amounts_v7",
            "food_amount_multipliers": list(FOOD_AMOUNT_MULTIPLIERS),
            "respawn_draws_per_tick": "max(1, population_size)",
            "primary_outcome": PRIMARY_OUTCOME,
            "analysis_arms": list(ANALYSIS_ARMS),
            "sensitivity_arms": list(SENSITIVITY_ARMS),
            "auxiliary_arms": list(AUXILIARY_ARMS),
            "positive_control_arm": "oracle_capsule",
            "pilot_seeds": list(PILOT_SEEDS),
            "activity_match_epsilon": ACTIVITY_MATCH_EPSILON,
            "activity_match_pilot_gate": ACTIVITY_MATCH_PILOT_GATE,
            "content_null_payload_action": CONTENT_NULL_PAYLOAD_ACTION,
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
            "content_null_vs_capsules_off": None
            if self.content_null_vs_capsules_off is None
            else self.content_null_vs_capsules_off.to_dict(),
            "sensitivity_failures": list(self.sensitivity_failures),
            "mean_abs_activity_match_gap": self.mean_abs_activity_match_gap,
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
            "sensitivity_failures_note": "shuffled_better_than_capsules_off is sensitivity-only under Amd 04",
            "assay_failed": self.assay_failed,
            "assay_failures": list(self.assay_failures),
            "calibration": hard_experiment_01_calibration_knobs(),
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
                "primary_outcome_is_receiver_mean_terminal_runtime_atp_last_tick",
                "legacy_selection_fitness_is_secondary_descriptive_only",
                "emitter_roles_and_payloads_are_designed_not_evolved",
                "source_fitness_gate_is_a_step_function_on_this_substrate",
                "oracle_capsule_is_a_positive_control_not_a_hypothesis_arm",
                "missing_last_tick_outcomes_are_dropped_not_zero_filled",
                "capsules_content_null_is_confirmatory_negative_control",
                "capsules_shuffled_is_sensitivity_peer_rotation_not_confirmatory_null",
                "capsules_shuffled_peer_rotation_preserves_payload_marginal",
                "capsules_activity_matched_is_auxiliary_yoked_accept_control",
                "activity_match_gap_is_exploratory_non_blocking_under_amd05",
                "unmatched_activity_volume_is_limitation_not_content_null_fail",
                "wave_1e_amd05_does_not_auto_grant_intervention_supported",
                "capsule_adoptions_count_attempts_not_successful_accepts",
                "dose_pattern_display_is_peak_at_intermediate_dose_then_channel_closure",
                "dose_statistic_is_algebraic_sum_of_two_primary_contrasts",
                "dose_trend_is_descriptive_independent_false",
                "dose_1_5_identical_to_treatment_arm",
                "price_identity_is_not_causal_without_the_explicit_dag",
                "null_or_small_effect_is_a_valid_finding",
                "not_knowledge_transfer_proof",
                "smoke_is_exploratory_only",
                "wave_1b_survival_calibration_does_not_change_the_estimand",
                "wave_1c_e2_coupling_is_an_opt_in_engine_knob_default_off",
                "wave_1d_double_prime_evidence_honesty_only_no_new_claim",
                "wave_1e_amd04_does_not_auto_grant_intervention_supported",
                "assay_failure_keeps_runtime_observation",
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
    activity_match_budget: int | None = None,
) -> HardExperiment01ArmRecord:
    births = _birth_count(result)
    sources, utilities, transfers, adoptions, accepted = _capsule_counts(result)
    shuffle_n, content_n, source_n = _shuffle_change_counts(result)
    blocked_by = _adoption_blocked_by_reason(result)
    sf_min, sf_med, sf_max = _source_fitness_support(result)
    roles = _genome_roles(spec)
    outcome = _receiver_mean_terminal_atp(result, roles)
    legacy = _mean_last_tick_fitness(result)
    final_pop = _final_population(result)
    applied, payloads, rejected = _manipulation_metrics(result)
    gap = None
    if activity_match_budget is not None:
        gap = int(accepted) - int(activity_match_budget)
    return HardExperiment01ArmRecord(
        seed=seed,
        arm=arm,
        terminal_mean_fitness=outcome,
        births=births,
        capsule_source_count=sources,
        capsule_utility_count=utilities,
        capsule_transfer_count=transfers,
        capsule_adoptions=adoptions,
        spec_digest=spec.digest(),
        result_digest=_result_identity_digest(result),
        next_generation_observed=births > 0,
        outcome_missing=outcome is None,
        extinct=final_pop == 0,
        final_population=final_pop,
        legacy_terminal_selection_fitness=legacy,
        receiver_count=sum(1 for role in roles if role == "receiver"),
        bias_applied_events=applied,
        bias_payload_counts=payloads,
        rejected_by_source_fitness=rejected,
        capsule_adoptions_accepted=accepted,
        shuffle_record_count=shuffle_n,
        shuffle_content_changed_count=content_n,
        shuffle_source_changed_count=source_n,
        capsule_adoption_blocked_by_reason=blocked_by,
        source_fitness_min=sf_min,
        source_fitness_median=sf_med,
        source_fitness_max=sf_max,
        activity_match_budget=activity_match_budget,
        activity_match_gap=gap,
    )


def _arm_record(
    *,
    seed: int,
    arm: ArmName,
    tick_count: int,
    population: int,
    activity_match_budget: int | None = None,
) -> HardExperiment01ArmRecord:
    spec, result = _run_arm(
        seed=seed,
        arm=arm,
        tick_count=tick_count,
        population=population,
        activity_match_budget=activity_match_budget,
    )
    return _record_from_run(
        seed=seed,
        arm=arm,
        spec=spec,
        result=result,
        activity_match_budget=activity_match_budget,
    )


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
    fitness = _receiver_mean_terminal_atp(result, _genome_roles(spec))
    final_pop = _final_population(result)
    _sources, _utilities, _transfers, adoptions, _accepted = _capsule_counts(result)
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
        if treat is None or base is None or treat.outcome_missing or base.outcome_missing:
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
    budget = original.activity_match_budget
    spec, result = _run_arm(
        seed=original.seed,
        arm=original.arm,
        tick_count=tick_count,
        population=population,
        activity_match_budget=budget,
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
            item = getattr(record, arm)
            if item is not None and item.outcome_missing:
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
    items = [item for item in (getattr(record, arm) for record in records) if item is not None]
    fitness = [
        item.terminal_mean_fitness
        for item in items
        if not item.outcome_missing and item.terminal_mean_fitness is not None
    ]
    births = [float(item.births) for item in items]
    adoptions = [float(item.capsule_adoptions) for item in items]
    accepted = [float(item.capsule_adoptions_accepted) for item in items]
    extinct = sum(1 for item in items if item.extinct)
    missing = sum(1 for item in items if item.outcome_missing)
    applied = [float(item.bias_applied_events) for item in items]
    rejected = [float(item.rejected_by_source_fitness) for item in items]
    legacy = [
        item.legacy_terminal_selection_fitness
        for item in items
        if item.legacy_terminal_selection_fitness is not None
    ]
    totals: dict[str, int] = {}
    for item in items:
        for payload, count in item.bias_payload_counts.items():
            totals[payload] = totals.get(payload, 0) + int(count)
    shuffle_n = sum(item.shuffle_record_count for item in items)
    content_n = sum(item.shuffle_content_changed_count for item in items)
    source_n = sum(item.shuffle_source_changed_count for item in items)
    shuffle_means = [float(item.shuffle_record_count) for item in items]
    return HardExperiment01ArmSummary(
        arm=arm,
        n=len(fitness),
        mean=None if not fitness else _mean(fitness),
        sd=None if len(fitness) < 2 else round(_sample_sd(fitness), 10),
        births_mean=_mean(births) if births else None,
        extinction_rate=round(extinct / len(items), 10) if items else 0.0,
        adoption_mean=_mean(adoptions) if adoptions else None,
        missing=missing,
        bias_applied_mean=_mean(applied) if applied else None,
        bias_payload_totals=dict(sorted(totals.items())),
        rejected_by_source_fitness_mean=_mean(rejected) if rejected else None,
        legacy_fitness_mean=_mean(legacy) if legacy else None,
        adoption_accepted_mean=_mean(accepted) if accepted else None,
        shuffle_record_mean=_mean(shuffle_means) if shuffle_means else None,
        shuffle_content_changed_rate=(
            None if shuffle_n == 0 else round(content_n / shuffle_n, 10)
        ),
        shuffle_source_changed_rate=(
            None if shuffle_n == 0 else round(source_n / shuffle_n, 10)
        ),
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
    statistic: float | None = None
    matched = False
    if len(numeric_means) == len(DOSE_LEVELS):
        statistic = _dose_pattern_statistic(numeric_means)
        peak = numeric_means[DOSE_PEAK_INDEX]
        matched = all(
            peak > value + 1e-15
            for index, value in enumerate(numeric_means)
            if index != DOSE_PEAK_INDEX
        )
    matrix = _dose_complete_matrix(dose_records)
    p_value: float | None = None
    if statistic is not None and matrix:
        rng = RNGManager(seed=INFERENTIAL_SEED, namespace="hard_experiment_01_dose_trend")
        extreme = 0
        for _ in range(DOSE_PERMUTATION_DRAWS):
            perm_means = [0.0] * len(DOSE_LEVELS)
            for row in matrix:
                shuffled: list[int] = []
                remaining = list(range(len(DOSE_LEVELS)))
                while remaining:
                    pick = rng.randrange(len(remaining))
                    shuffled.append(remaining.pop(pick))
                for index, source in enumerate(shuffled):
                    perm_means[index] += row[source]
            perm_means = [item / len(matrix) for item in perm_means]
            if _dose_pattern_statistic(perm_means) + 1e-15 >= statistic:
                extreme += 1
        p_value = (1 + extreme) / (1 + DOSE_PERMUTATION_DRAWS)
    # B5: umbrella/downturn is not a monotone "trend"; keep pattern_matched for
    # the peak-at-intermediate shape, but never claim trend_supported here.
    # Dose block is descriptive (independent=false) and out of the decision rule.
    monotone = False
    if len(numeric_means) == len(DOSE_LEVELS):
        monotone = all(
            numeric_means[index] <= numeric_means[index + 1] + 1e-15
            for index in range(len(numeric_means) - 1)
        )
    trend_supported = bool(
        monotone
        and matched
        and statistic is not None
        and p_value is not None
        and p_value < ALPHA
    )
    return HardExperiment01DoseTrend(
        min_source_fitness=DOSE_LEVELS,
        means=means,
        sample_counts=counts,
        pattern_statistic=None if statistic is None else round(statistic, 10),
        permutation_p=None if p_value is None else round(p_value, 12),
        pattern_matched=matched,
        trend_supported=trend_supported,
        complete_case_seeds=complete_n,
        dropped_seeds=dropped,
        pattern="peak_at_intermediate_dose_then_channel_closure",
        independent=False,
    )


def _dose_pattern_statistic(means: Sequence[float]) -> float:
    peak = means[DOSE_PEAK_INDEX]
    return sum(peak - value for index, value in enumerate(means) if index != DOSE_PEAK_INDEX)


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
    content_null_vs_off: HardExperiment01PairedContrast | None,
    dose_trend: HardExperiment01DoseTrend | None,
    replay_matched: bool,
    assay_failures: Sequence[str] = (),
) -> tuple[str, ...]:
    """Amd 04/05 confirmatory failures (shuffled_better + activity gap sensitivity-only)."""

    failures: list[str] = list(assay_failures)
    if scale != "research":
        failures.append("not_research_scale")
    if statistical_tier != "research_grade_benchmark_candidate":
        failures.append("statistical_tier_not_research_grade")
    if not replay_matched:
        failures.append("replay_mismatch")
    vs_off = _contrast_by_baseline(contrasts, "source_bias_off")
    vs_null = _contrast_by_baseline(contrasts, "capsules_content_null")
    if vs_off is None or vs_null is None:
        failures.append("missing_primary_contrast")
        return tuple(failures)
    if vs_off.dz is None or vs_null.dz is None:
        failures.append("dz_undefined")
    if not _ci_excludes_zero(vs_off.ci_low, vs_off.ci_high):
        failures.append("ci_on_vs_off_includes_0")
    if vs_off.p_holm is None or vs_off.p_holm >= ALPHA:
        failures.append("holm_on_vs_off_not_below_alpha")
    if not _ci_excludes_zero(vs_null.ci_low, vs_null.ci_high):
        failures.append("ci_on_vs_content_null_includes_0")
    if vs_null.p_holm is None or vs_null.p_holm >= ALPHA:
        failures.append("holm_on_vs_content_null_not_below_alpha")
    if (
        content_null_vs_off is None
        or content_null_vs_off.ci_low is None
        or content_null_vs_off.ci_high is None
    ):
        failures.append("missing_content_null_vs_capsules_off")
    elif content_null_vs_off.ci_low > 0.0:
        # Amd 04 confirmatory null: content-null must not beat channel-off.
        failures.append("content_null_better_than_capsules_off")
    # B4: dose_trend is descriptive only (independent=false); not a confirmatory
    # failure. ``dose_trend`` retained in signature for call-site stability.
    del dose_trend
    return tuple(failures)


def _sensitivity_failures(
    *,
    shuffled_vs_off: HardExperiment01PairedContrast | None,
) -> tuple[str, ...]:
    """Legacy peer-rotation non-superiority (expected to fail by construction)."""

    failures: list[str] = []
    if shuffled_vs_off is None or shuffled_vs_off.ci_low is None or shuffled_vs_off.ci_high is None:
        failures.append("missing_shuffled_vs_capsules_off")
    elif shuffled_vs_off.ci_low > 0.0:
        failures.append("shuffled_better_than_capsules_off")
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
    """Paired source-bias campaign. Default is smoke (12 seeds / 8 ticks / 8 organisms, CI)."""

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
        by_arm: dict[str, HardExperiment01ArmRecord] = {}
        # Treatment first so activity_matched can yoke accept count.
        for arm in ARMS:
            if arm == "capsules_activity_matched":
                continue
            by_arm[arm] = _arm_record(
                seed=seed, arm=arm, tick_count=resolved_ticks, population=resolved_pop
            )
        budget = int(by_arm["source_bias_on"].capsule_adoptions_accepted)
        by_arm["capsules_activity_matched"] = _arm_record(
            seed=seed,
            arm="capsules_activity_matched",
            tick_count=resolved_ticks,
            population=resolved_pop,
            activity_match_budget=budget,
        )
        records.append(
            HardExperiment01SeedRecord(
                seed=seed,
                source_bias_on=by_arm["source_bias_on"],
                source_bias_off=by_arm["source_bias_off"],
                capsules_off=by_arm["capsules_off"],
                capsules_content_null=by_arm["capsules_content_null"],
                capsules_activity_matched=by_arm["capsules_activity_matched"],
                capsules_shuffled=by_arm["capsules_shuffled"],
                oracle_capsule=by_arm["oracle_capsule"],
                delta_vs_source_bias_off=_optional_delta(
                    by_arm["source_bias_on"].terminal_mean_fitness,
                    by_arm["source_bias_off"].terminal_mean_fitness,
                ),
                delta_vs_capsules_off=_optional_delta(
                    by_arm["source_bias_on"].terminal_mean_fitness,
                    by_arm["capsules_off"].terminal_mean_fitness,
                ),
                delta_vs_capsules_content_null=_optional_delta(
                    by_arm["source_bias_on"].terminal_mean_fitness,
                    by_arm["capsules_content_null"].terminal_mean_fitness,
                ),
                delta_vs_capsules_activity_matched=_optional_delta(
                    by_arm["source_bias_on"].terminal_mean_fitness,
                    by_arm["capsules_activity_matched"].terminal_mean_fitness,
                ),
                delta_vs_capsules_shuffled=_optional_delta(
                    by_arm["source_bias_on"].terminal_mean_fitness,
                    by_arm["capsules_shuffled"].terminal_mean_fitness,
                ),
            )
        )
        if include_dose:
            for level in DOSE_LEVELS:
                reused = by_arm["source_bias_on"] if level == MIN_SOURCE_FITNESS_TREATMENT else None
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
    content_null_vs_off = _paired_contrast(
        records, treatment_arm="capsules_content_null", baseline_arm="capsules_off"
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
    arm_summaries = tuple(_arm_summary(records, arm) for arm in ARMS)
    assay_failed, assay_failures = evaluate_hard_experiment_01_assay(
        arm_summaries, seed_records=records
    )
    failures = _decision_rule_failures(
        scale=scale,
        statistical_tier=statistical_tier,
        contrasts=primary,
        content_null_vs_off=content_null_vs_off,
        dose_trend=dose_trend,
        replay_matched=replay_matched,
        assay_failures=assay_failures,
    )
    sensitivity_failures = _sensitivity_failures(shuffled_vs_off=shuffled_vs_off)
    activity_gaps = [
        abs(int(item.capsules_activity_matched.activity_match_gap))
        for item in records
        if item.capsules_activity_matched is not None
        and item.capsules_activity_matched.activity_match_gap is not None
    ]
    mean_abs_gap = None if not activity_gaps else _mean([float(g) for g in activity_gaps])
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
        effect_vs_source_bias_off=_effect_or_insufficient(PRIMARY_OUTCOME, off_fits, on_vs_off),
        effect_vs_capsules_off=_effect_or_insufficient(PRIMARY_OUTCOME, none_fits, on_vs_none),
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
        content_null_vs_capsules_off=content_null_vs_off,
        multiple_comparison_audit=MultipleComparisonAudit(metric_count=len(PRIMARY_CONTRASTS)),
        dose_records=tuple(dose_records),
        dose_trend=dose_trend,
        arm_summaries=arm_summaries,
        assay_failed=assay_failed,
        assay_failures=assay_failures,
        decision_rule_passed=not failures and claim_gate_allowed,
        decision_rule_failures=failures,
        sensitivity_failures=sensitivity_failures,
        mean_abs_activity_match_gap=mean_abs_gap,
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
    if data.get("assay_failed") is True:
        ceiling = CLAIM_CEILING
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



def evaluate_hard_experiment_01_wave1e_pilot_gates(
    campaign: HardExperiment01Campaign,
) -> dict[str, JsonValue]:
    """Amd 05 pilot clearance helper (docs companion for Wave 1e pilot scripts).

    Confirmatory gates: assay valid, content_null profitable rate ≈ 0 with
    content-changed evidence, SCHEMA v6 + amd04 + amd05 digests present.
    ``mean_abs_activity_match_gap`` is **reported** against Amd 04 ε but does
    **not** block clearance (ACTIVITY_MATCH_PILOT_GATE=False). Decision rule
    for content_null is unchanged; ClaimGate is not raised here.
    """

    payload = campaign.to_dict()
    arms = {item.arm: item for item in campaign.arm_summaries}
    oracle = arms.get("oracle_capsule")
    caps_off = arms.get("capsules_off")
    content_null = arms.get("capsules_content_null")

    # Assay / positive control
    assay_ok = not campaign.assay_failed
    oracle_gt_off = (
        oracle is not None
        and caps_off is not None
        and oracle.mean is not None
        and caps_off.mean is not None
        and float(oracle.mean) > float(caps_off.mean)
    )
    gate_assay = bool(assay_ok and oracle_gt_off)

    # Content null manipulation (confirmatory)
    eat = 0
    total = 0
    changed = 0
    shuffle_records = 0
    for seed_rec in campaign.seed_records:
        arm_rec = seed_rec.capsules_content_null
        if arm_rec is None:
            continue
        for key, value in dict(arm_rec.bias_payload_counts or {}).items():
            total += int(value)
            if key == CALIBRATION_GOOD_PAYLOAD_ACTION:
                eat += int(value)
        changed += int(arm_rec.shuffle_content_changed_count or 0)
        shuffle_records += int(arm_rec.shuffle_record_count or 0)
    eat_rate = 0.0 if total == 0 else eat / total
    if content_null is not None and content_null.shuffle_content_changed_rate is not None:
        content_changed_rate = float(content_null.shuffle_content_changed_rate)
    elif shuffle_records > 0:
        content_changed_rate = changed / shuffle_records
    else:
        content_changed_rate = float(changed > 0)
    gate_content_null = eat_rate <= 1e-9 and content_changed_rate > 0.0

    # Digests / schema (v7 lock)
    amd04 = str(payload.get("prereg_amendment_04_digest") or "")
    amd05 = str(payload.get("prereg_amendment_05_digest") or "")
    lock = str(payload.get("prereg_amendment_lock_digest") or "")
    schema_ok = str(payload.get("schema_version") or campaign.schema_version) == SCHEMA_VERSION
    gate_digests = (
        schema_ok
        and SCHEMA_VERSION == "hard_experiment_01_v7"
        and len(amd04) >= 16
        and len(amd05) >= 16
        and len(lock) >= 16
        and amd04 == hard_experiment_01_prereg_amendment_04_digest()
        and amd05 == hard_experiment_01_prereg_amendment_05_digest()
        and lock == hard_experiment_01_prereg_amendment_lock_digest()
    )

    # Treatment seed variance (LOCK): not 30 bitwise replays
    treatment = arms.get("source_bias_on")
    treatment_sd = None if treatment is None else treatment.sd
    gate_variance = treatment_sd is not None and float(treatment_sd) > 0.0

    gap = campaign.mean_abs_activity_match_gap
    gap_within_epsilon = gap is not None and float(gap) <= float(ACTIVITY_MATCH_EPSILON) + 1e-9
    # Amd 05: exploratory report only — never blocks overall clearance.
    gate_activity_exploratory = {
        "blocking": ACTIVITY_MATCH_PILOT_GATE,
        "mean_abs_activity_match_gap": gap,
        "epsilon": ACTIVITY_MATCH_EPSILON,
        "within_epsilon": gap_within_epsilon,
        "note": (
            "reported non-blocking sensitivity; unmatched volume is a "
            "limitation not a silent fail of content_null"
        ),
    }

    overall = gate_assay and gate_content_null and gate_digests and gate_variance
    return {
        "schema_version": SCHEMA_VERSION,
        "amendment": "lock_v7",
        "overall_pass": overall,
        "cleared_for_11_40": overall,
        "activity_match_pilot_gate": ACTIVITY_MATCH_PILOT_GATE,
        "gates": {
            "assay": {
                "pass": gate_assay,
                "assay_failed": campaign.assay_failed,
                "oracle_gt_off": oracle_gt_off,
            },
            "content_null": {
                "pass": gate_content_null,
                "eat_rate": eat_rate,
                "content_changed_rate": content_changed_rate,
            },
            "treatment_seed_variance": {
                "pass": gate_variance,
                "treatment_sd": treatment_sd,
            },
            "activity_match_exploratory": gate_activity_exploratory,
            "schema_amd_digests": {
                "pass": gate_digests,
                "prereg_amendment_04_digest": amd04,
                "prereg_amendment_05_digest": amd05,
                "prereg_amendment_lock_digest": lock,
            },
        },
    }


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
            f"sensitivity_failures {list(campaign.sensitivity_failures)}",
            f"mean_abs_activity_match_gap {campaign.mean_abs_activity_match_gap}",
            f"assay_failed {campaign.assay_failed}",
            f"replay_matched {campaign.replay_matched}",
            f"claim_ceiling {campaign.claim_ceiling}",
            "collective_intelligence False",
            "intelligence False",
            f"digest {campaign.digest}",
            f"standardized_note {_cohens_d_note(vs_off.standardized_delta_lite)}",
        )
    )


def committed_research_results_v1_path() -> Path:
    return _repo_root() / "docs" / "hard_experiment_01" / "results_v1.json"


def committed_research_results_v2_path() -> Path:
    return _repo_root() / "docs" / "hard_experiment_01" / "results_v2.json"


def committed_research_results_path() -> Path:
    """Current (v3, Wave 1c) research artifact."""

    return _repo_root() / "docs" / "hard_experiment_01" / "results_v3.json"


def committed_research_results_v5_path() -> Path:
    """Wave 1d′ / Amendment 03 research artifact (SCHEMA v5)."""

    return _repo_root() / "docs" / "hard_experiment_01" / "results_v5.json"


def committed_research_results_v6_path() -> Path:
    """Wave 1e / Amendments 04+05 research artifact (SCHEMA v6)."""

    return _repo_root() / "docs" / "hard_experiment_01" / "results_v6.json"


def committed_research_results_v7_path() -> Path:
    """SCHEMA v7 / LOCK research artifact (seed-contingent food amounts)."""

    return _repo_root() / "docs" / "hard_experiment_01" / "results_v7.json"


def write_hard_experiment_01_research_results(path: Path | None = None) -> Path:
    """Run the research campaign and write the digest-backed JSON artifact."""

    import json

    dest = path or committed_research_results_v7_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    campaign = run_hard_experiment_01(scale="research")
    dest.write_text(
        json.dumps(campaign.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return dest
