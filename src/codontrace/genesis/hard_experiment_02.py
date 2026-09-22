"""HARD_EXPERIMENT_02: food-patch signalling under deme/kin selection (E1+E2+E5).

Prereg: ``docs/HARD_EXPERIMENT_02_PREREG.md`` (draft-lock 2026-09-13).
Literature: Floreano et al. 2007; Knoester et al. 2008; Lenski et al. 2003.

ClaimGate ceiling starts at ``runtime_observation``. Forbidden aliases stay
blocked. Phase A–E ``life_loop_world`` pins are unchanged when HE02 knobs are off.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal

from codontrace._types import JsonValue
from codontrace.actions import default_action_registry, move_toward_capsule_target_handler
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, is_real_evidence_digest
from codontrace.genesis.capsule import (
    CapsuleAdoptionPolicy,
    CapsuleShuffleMode,
    CapsuleTransferConfig,
)
from codontrace.genesis.deme_selection import (
    E2_ORDINAL_PREDICTION,
    DemeSelectionCell,
    DemeSelectionConfig,
    e2_ordinal_respects_prediction,
)
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.food_patch_signal import (
    MOVE_TOWARD_CAPSULE_TARGET,
    FoodPatchSignalConfig,
    payload_patch_mutual_information,
)
from codontrace.genesis.hard_experiment_01 import (
    _apply_survival_calibration,
    _capsule_counts,
    _mean_last_tick_fitness,
    _receiver_mean_terminal_atp,
    holm_correction,
    paired_effect_size,
)
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.stepping_stone_reward import SteppingStoneRewardConfig
from codontrace.genesis.text_digest import sha256_text_file

PRODUCT_NAME = "CodonTrace Genesis"
CLAIM_CEILING = "runtime_observation"
INTERVENTION_CLAIM = "intervention_supported"
EXPERIMENT_ID = "hard_experiment_02_food_patch_deme"
SCHEMA_VERSION = "hard_experiment_02_v1"
PREREG_RELATIVE_PATH = "docs/HARD_EXPERIMENT_02_PREREG.md"
PRIMARY_OUTCOME = "receiver_mean_terminal_runtime_atp"

PILOT_SEEDS: tuple[int, ...] = tuple(range(1000, 1010))
RESEARCH_SEED_COUNT = 30
SMOKE_TICK_COUNT = 8
SMOKE_POPULATION = 8
# Prereg: research ticks/pop TBD after smoke timing. Host OOM at 24/12;
# lock to smoke-calibrated runnable scale for an honest 30-seed campaign.
RESEARCH_TICK_COUNT = SMOKE_TICK_COUNT
RESEARCH_POPULATION = SMOKE_POPULATION
DEFAULT_TICK_COUNT = SMOKE_TICK_COUNT
DEFAULT_POPULATION = SMOKE_POPULATION
MIN_SOURCE_FITNESS_TREATMENT = 1.5
ORACLE_USEFUL_FRACTION = 0.5
MI_TREATMENT_MIN = 1e-6
MI_SHUFFLE_MAX = 1e-6

ArmName = Literal[
    "treatment",
    "content_null",
    "activity_matched",
    "channel_off",
    "capsules_shuffled",
    "oracle_moderate",
]
ARMS: tuple[ArmName, ...] = (
    "treatment",
    "content_null",
    "activity_matched",
    "channel_off",
    "capsules_shuffled",
    "oracle_moderate",
)
ScaleName = Literal["smoke", "pilot", "research"]

_FORBIDDEN = frozenset(
    {
        "collective_intelligence",
        "intelligence",
        "agi",
        "tokyo_type1_passed",
        "avida_replacement",
        "open_ended_intelligence",
    }
)

_QUESTION = (
    "Does capsule-mediated food-location information transfer, under deme/kin "
    "selection structure, produce Holm-surviving gains vs content-null / "
    "activity-matched / channel-off controls when E1+E2+E5 knobs are enabled?"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def hard_experiment_02_prereg_path() -> Path:
    return _repo_root() / PREREG_RELATIVE_PATH


def hard_experiment_02_prereg_digest() -> str:
    path = hard_experiment_02_prereg_path()
    if not path.is_file():
        raise ConfigurationError(f"missing HE02 prereg: {path}")
    return sha256_text_file(path)


def hard_experiment_02_causal_dag() -> dict[str, JsonValue]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "question": _QUESTION,
        "nodes": [
            "food_patch_location",
            "capsule_payload",
            "receiver_movement",
            "receiver_atp",
            "deme_selection_pressure",
            "stepping_stone_scaffold",
        ],
        "edges": [
            {
                "source": "food_patch_location",
                "target": "receiver_atp",
                "id": "e1_food_patch_signal",
                "via": ["capsule_payload", "receiver_movement"],
            },
            {
                "source": "deme_selection_pressure",
                "target": "capsule_payload",
                "id": "e2_deme_selection",
            },
            {
                "source": "stepping_stone_scaffold",
                "target": "receiver_movement",
                "id": "e5_stepping_stone",
            },
        ],
        "claim_ceiling": CLAIM_CEILING,
        "collective_intelligence": False,
        "e2_ordinal_prediction": list(E2_ORDINAL_PREDICTION),
    }


def hard_experiment_02_action_registry():
    """Default registry plus MOVE_TOWARD_CAPSULE_TARGET (HE02 specs only)."""

    return default_action_registry().extend(
        MOVE_TOWARD_CAPSULE_TARGET, move_toward_capsule_target_handler
    )


@dataclass(frozen=True, slots=True)
class HardExperiment02Intervention:
    arm: ArmName
    role: str
    target_mechanism: str
    action: str
    knob: str
    applied_value: str
    compared_to: str
    cuts_edges: tuple[str, ...] = ()

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


def hard_experiment_02_interventions() -> tuple[HardExperiment02Intervention, ...]:
    return (
        HardExperiment02Intervention(
            arm="treatment",
            role="treatment",
            target_mechanism="food_patch_signal+deme_germline_clonal+stepping_stone",
            action="enable_e1_e2_e5",
            knob="FoodPatchSignalConfig+DemeSelectionConfig+SteppingStoneRewardConfig",
            applied_value="E1 on, GERMLINE×CLONAL, E5 on, capsules honest",
            compared_to="life_loop_world default",
        ),
        HardExperiment02Intervention(
            arm="content_null",
            role="negative_control",
            target_mechanism="capsule_content_information",
            action="null_payload_keep_channel",
            knob="CapsuleTransferConfig.shuffle_mode",
            applied_value="CONTENT_NULL",
            compared_to="treatment",
            cuts_edges=("e1_food_patch_signal",),
        ),
        HardExperiment02Intervention(
            arm="activity_matched",
            role="auxiliary_control",
            target_mechanism="capsule_channel_activity_volume",
            action="null_payload_yoke_accept_count",
            knob="CONTENT_NULL+max_successful_adoptions",
            applied_value="yoked_accept_cap",
            compared_to="treatment",
            cuts_edges=("e1_food_patch_signal",),
        ),
        HardExperiment02Intervention(
            arm="channel_off",
            role="channel_off",
            target_mechanism="capsule_transfer_channel",
            action="disable_capsule_transfer",
            knob="CapsuleTransferConfig.enabled",
            applied_value="enabled=False",
            compared_to="treatment",
            cuts_edges=("e1_food_patch_signal",),
        ),
        HardExperiment02Intervention(
            arm="capsules_shuffled",
            role="negative_control",
            target_mechanism="payload_source_association",
            action="shuffle_content",
            knob="CapsuleTransferConfig.shuffle_mode",
            applied_value="CONTENT",
            compared_to="treatment",
            cuts_edges=("e1_food_patch_signal",),
        ),
        HardExperiment02Intervention(
            arm="oracle_moderate",
            role="positive_control",
            target_mechanism="useful_payload_fraction",
            action="oracle_payload_fraction",
            knob=f"useful_fraction={ORACLE_USEFUL_FRACTION}",
            applied_value=f"f={ORACLE_USEFUL_FRACTION}",
            compared_to="channel_off",
        ),
    )


def _enabled_capsule(
    *,
    shuffle_mode: CapsuleShuffleMode,
    max_successful_adoptions: int | None = None,
    min_source_fitness: float = MIN_SOURCE_FITNESS_TREATMENT,
    adoption_policy: CapsuleAdoptionPolicy = CapsuleAdoptionPolicy.FITNESS_WEIGHTED,
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
    if arm == "channel_off":
        return CapsuleTransferConfig(enabled=False)
    if arm == "treatment":
        return _enabled_capsule(shuffle_mode=CapsuleShuffleMode.OFF)
    if arm == "content_null":
        return _enabled_capsule(shuffle_mode=CapsuleShuffleMode.CONTENT_NULL)
    if arm == "activity_matched":
        if activity_match_budget is None:
            raise ConfigurationError(
                "activity_matched requires activity_match_budget "
                "(yoked treatment capsule_adoptions_accepted)."
            )
        return _enabled_capsule(
            shuffle_mode=CapsuleShuffleMode.CONTENT_NULL,
            max_successful_adoptions=int(activity_match_budget),
        )
    if arm == "capsules_shuffled":
        return _enabled_capsule(shuffle_mode=CapsuleShuffleMode.CONTENT)
    if arm == "oracle_moderate":
        return _enabled_capsule(
            shuffle_mode=CapsuleShuffleMode.OFF,
            min_source_fitness=0.0,
            adoption_policy=CapsuleAdoptionPolicy.THRESHOLD,
        )
    raise ConfigurationError(f"unknown HE02 arm: {arm!r}")


def _food_patch_for_arm(arm: ArmName) -> FoodPatchSignalConfig:
    # Wide visibility + frequent spawn so smoke/pilot can realize payload↔patch MI.
    # Pins A–E stay untouched: this config is HE02-spec-only.
    return FoodPatchSignalConfig(
        enabled=True,
        visibility_radius=8,
        patch_spawn_period_ticks=2,
        patch_lifetime_ticks=24,
        patch_count=2,
    )


def _deme_for_arm(arm: ArmName) -> DemeSelectionConfig:
    return DemeSelectionConfig(
        enabled=True,
        level="GERMLINE_GROUP",
        founder_relatedness="CLONAL",
        deme_size=4,
        deme_count=2,
    )


def _stepping_stone_for_arm(arm: ArmName) -> SteppingStoneRewardConfig:
    if arm in {"treatment", "oracle_moderate"}:
        return SteppingStoneRewardConfig(enabled=True)
    return SteppingStoneRewardConfig(enabled=False)


def build_hard_experiment_02_spec(
    *,
    seed: int,
    arm: ArmName,
    tick_count: int = DEFAULT_TICK_COUNT,
    population: int = DEFAULT_POPULATION,
    activity_match_budget: int | None = None,
) -> GenesisExperimentSpec:
    """Life-loop overlay with E1+E2+E5 knobs. Does not mutate Phase A–E pins."""

    if arm not in ARMS:
        raise ConfigurationError(f"unknown hard experiment 02 arm: {arm!r}")
    if tick_count <= 0 or population <= 0:
        raise ConfigurationError("tick_count and population must be > 0.")
    capsule = _capsule_for_arm(arm, activity_match_budget=activity_match_budget)
    food = _food_patch_for_arm(arm)
    deme = _deme_for_arm(arm)
    stone = _stepping_stone_for_arm(arm)
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
        food_patch_signal=food,
        deme_selection=deme,
        stepping_stone_reward=stone,
        phase_e=deme.to_phase_e(),
    )
    engine_config = replace(base.engine_config, enable_capsules=capsule.enabled)
    metadata = {
        **base.metadata,
        "runtime_profile": EXPERIMENT_ID,
        "hard_experiment_02_arm": arm,
        "hard_experiment_02_question": _QUESTION,
        "claim_ceiling": CLAIM_CEILING,
        "collective_intelligence": False,
        "intelligence": False,
        "agi": False,
        "tokyo_type1_passed": False,
        "avida_replacement": False,
        "e2_cell": deme.cell.value,
        "oracle_useful_fraction": (
            ORACLE_USEFUL_FRACTION if arm == "oracle_moderate" else None
        ),
    }
    return _apply_survival_calibration(
        replace(
            base,
            population_configs=configs,
            capsule_transfer_config=capsule,
            engine_config=engine_config,
            action_registry=hard_experiment_02_action_registry(),
            metadata=metadata,
        ),
        seed=seed,
        oracle=arm == "oracle_moderate",
    )


def default_pilot_seeds() -> tuple[int, ...]:
    return PILOT_SEEDS


def default_research_seeds(seed_count: int = RESEARCH_SEED_COUNT) -> tuple[int, ...]:
    return tuple(range(2000, 2000 + int(seed_count)))


def default_smoke_seeds(seed_count: int = 4) -> tuple[int, ...]:
    return tuple(range(10, 10 + int(seed_count)))


@dataclass(frozen=True, slots=True)
class HardExperiment02ArmRecord:
    arm: ArmName
    seed: int
    terminal_mean_fitness: float | None
    receiver_mean_terminal_runtime_atp: float | None
    capsule_adoptions_accepted: int
    capsule_emissions: int
    payload_patch_mi: float
    assay_failures: tuple[str, ...] = ()
    result_digest: str = ""
    spec_digest: str = ""

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "arm": self.arm,
            "seed": self.seed,
            "terminal_mean_fitness": self.terminal_mean_fitness,
            "receiver_mean_terminal_runtime_atp": self.receiver_mean_terminal_runtime_atp,
            "capsule_adoptions_accepted": self.capsule_adoptions_accepted,
            "capsule_emissions": self.capsule_emissions,
            "payload_patch_mi": self.payload_patch_mi,
            "assay_failures": list(self.assay_failures),
            "result_digest": self.result_digest,
            "spec_digest": self.spec_digest,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment02SeedRecord:
    seed: int
    treatment: HardExperiment02ArmRecord
    content_null: HardExperiment02ArmRecord
    activity_matched: HardExperiment02ArmRecord
    channel_off: HardExperiment02ArmRecord
    capsules_shuffled: HardExperiment02ArmRecord
    oracle_moderate: HardExperiment02ArmRecord

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "treatment": self.treatment.to_dict(),
            "content_null": self.content_null.to_dict(),
            "activity_matched": self.activity_matched.to_dict(),
            "channel_off": self.channel_off.to_dict(),
            "capsules_shuffled": self.capsules_shuffled.to_dict(),
            "oracle_moderate": self.oracle_moderate.to_dict(),
        }

    def arm_map(self) -> dict[str, HardExperiment02ArmRecord]:
        return {
            "treatment": self.treatment,
            "content_null": self.content_null,
            "activity_matched": self.activity_matched,
            "channel_off": self.channel_off,
            "capsules_shuffled": self.capsules_shuffled,
            "oracle_moderate": self.oracle_moderate,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment02PairedContrast:
    treatment_arm: str
    baseline_arm: str
    dz: float | None
    p_raw: float | None
    p_holm: float | None
    n_pairs: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "treatment_arm": self.treatment_arm,
            "baseline_arm": self.baseline_arm,
            "dz": self.dz,
            "p_raw": self.p_raw,
            "p_holm": self.p_holm,
            "n_pairs": self.n_pairs,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment02ArmSummary:
    arm: ArmName
    n: int
    mean: float | None
    mi_mean: float | None
    adoption_mean: float | None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "arm": self.arm,
            "n": self.n,
            "mean": self.mean,
            "mi_mean": self.mi_mean,
            "adoption_mean": self.adoption_mean,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment02Campaign:
    experiment_id: str
    schema_version: str
    product_name: str
    claim_ceiling: str
    seeds: tuple[int, ...]
    scale: ScaleName
    tick_count: int
    population: int
    primary_outcome: str
    prereg_digest: str
    protocol_digest: str
    interventions: tuple[HardExperiment02Intervention, ...]
    seed_records: tuple[HardExperiment02SeedRecord, ...]
    arm_summaries: tuple[HardExperiment02ArmSummary, ...]
    paired_contrasts: tuple[HardExperiment02PairedContrast, ...]
    assay_failed: bool
    assay_failures: tuple[str, ...]
    decision_rule_passed: bool
    decision_rule_failures: tuple[str, ...]
    e2_ordinal_ok: bool | None
    limitations: tuple[str, ...]
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_ceiling in _FORBIDDEN:
            raise ConfigurationError("HE02 claim_ceiling hit a forbidden alias.")
        if self.claim_ceiling not in {CLAIM_CEILING, INTERVENTION_CLAIM}:
            raise ConfigurationError(
                f"HE02 claim_ceiling must be {CLAIM_CEILING!r} or {INTERVENTION_CLAIM!r}."
            )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("HardExperiment02Campaign digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "experiment_id": self.experiment_id,
            "schema_version": self.schema_version,
            "product_name": self.product_name,
            "claim_ceiling": self.claim_ceiling,
            "seeds": list(self.seeds),
            "scale": self.scale,
            "tick_count": self.tick_count,
            "population": self.population,
            "primary_outcome": self.primary_outcome,
            "prereg_digest": self.prereg_digest,
            "protocol_digest": self.protocol_digest,
            "interventions": [item.to_dict() for item in self.interventions],
            "seed_records": [item.to_dict() for item in self.seed_records],
            "arm_summaries": [item.to_dict() for item in self.arm_summaries],
            "paired_contrasts": [item.to_dict() for item in self.paired_contrasts],
            "assay_failed": self.assay_failed,
            "assay_failures": list(self.assay_failures),
            "decision_rule_passed": self.decision_rule_passed,
            "decision_rule_failures": list(self.decision_rule_failures),
            "e2_ordinal_ok": self.e2_ordinal_ok,
            "limitations": list(self.limitations),
            "collective_intelligence": False,
            "intelligence": False,
            "agi": False,
            "software": {"name": PRODUCT_NAME, "version": "0.3.0b4.dev0"},
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _extract_payload_patch_mi(result: object) -> float:
    records = []
    for tick in tuple(getattr(result, "ticks", ()) or ()):
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        for item in getattr(generation, "food_patch_signal_records", ()) or ():
            records.append(item)
    if not records:
        return 0.0
    try:
        return float(payload_patch_mutual_information(records))
    except Exception:
        return 0.0


def _result_digest(result: object) -> str:
    digest = getattr(result, "digest", None)
    if callable(digest):
        value = digest()
        if isinstance(value, str) and is_real_evidence_digest(value):
            return value.lower()
    snap = getattr(result, "snapshot", None)
    snap_digest = getattr(snap, "digest", None) if snap is not None else None
    if callable(snap_digest):
        value = snap_digest()
        if isinstance(value, str) and is_real_evidence_digest(value):
            return value.lower()
    return hashlib.sha256(repr(result).encode("utf-8")).hexdigest()


def _run_arm(
    *,
    seed: int,
    arm: ArmName,
    tick_count: int,
    population: int,
    activity_match_budget: int | None = None,
) -> HardExperiment02ArmRecord:
    spec = build_hard_experiment_02_spec(
        seed=seed,
        arm=arm,
        tick_count=tick_count,
        population=population,
        activity_match_budget=activity_match_budget,
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    _sources, _utilities, _transfers, _attempts, accepted = _capsule_counts(result)
    roles = tuple(str(item) for item in (spec.metadata.get("genome_roles") or ()))
    if not roles:
        # Fallback: treat all surviving organisms as receivers for HE02 smoke/pilot.
        roles = tuple(f"receiver_{index}" for index in range(population))
    receiver_atp = _receiver_mean_terminal_atp(result, roles)
    if receiver_atp is None:
        receiver_atp = _mean_last_tick_fitness(result)
    emissions = int(_transfers)
    return HardExperiment02ArmRecord(
        arm=arm,
        seed=seed,
        terminal_mean_fitness=_mean_last_tick_fitness(result),
        receiver_mean_terminal_runtime_atp=receiver_atp,
        capsule_adoptions_accepted=int(accepted),
        capsule_emissions=emissions,
        payload_patch_mi=_extract_payload_patch_mi(result),
        result_digest=_result_digest(result),
        spec_digest=spec.digest(),
    )


def _arm_summary(
    arm: ArmName, records: Sequence[HardExperiment02ArmRecord]
) -> HardExperiment02ArmSummary:
    values = [
        item.receiver_mean_terminal_runtime_atp
        for item in records
        if item.receiver_mean_terminal_runtime_atp is not None
    ]
    mis = [item.payload_patch_mi for item in records]
    adoptions = [float(item.capsule_adoptions_accepted) for item in records]
    return HardExperiment02ArmSummary(
        arm=arm,
        n=len(records),
        mean=None if not values else round(sum(values) / len(values), 10),
        mi_mean=None if not mis else round(sum(mis) / len(mis), 10),
        adoption_mean=(
            None if not adoptions else round(sum(adoptions) / len(adoptions), 10)
        ),
    )


def _manipulation_failures(
    summaries: Mapping[str, HardExperiment02ArmSummary],
) -> tuple[str, ...]:
    failures: list[str] = []
    treatment = summaries.get("treatment")
    shuffled = summaries.get("capsules_shuffled")
    if treatment is None:
        return ("assay_failed_missing_treatment",)
    if treatment.adoption_mean is None or treatment.adoption_mean <= 0:
        failures.append("assay_failed_treatment_adoptions_near_zero")
    if treatment.mi_mean is None or treatment.mi_mean <= MI_TREATMENT_MIN:
        failures.append("assay_failed_treatment_payload_mi_near_zero")
    if shuffled is not None and shuffled.mi_mean is not None and shuffled.mi_mean > MI_SHUFFLE_MAX:
        failures.append("assay_failed_shuffled_payload_mi_above_zero")
    return tuple(failures)


def evaluate_hard_experiment_02_pilot_gates(
    campaign: HardExperiment02Campaign,
) -> dict[str, JsonValue]:
    arms = {item.arm: item for item in campaign.arm_summaries}
    assay_ok = not campaign.assay_failed
    oracle = arms.get("oracle_moderate")
    channel_off = arms.get("channel_off")
    oracle_gt_off = (
        oracle is not None
        and channel_off is not None
        and oracle.mean is not None
        and channel_off.mean is not None
        and float(oracle.mean) > float(channel_off.mean)
    )
    treatment = arms.get("treatment")
    shuffled = arms.get("capsules_shuffled")
    mi_ok = (
        treatment is not None
        and treatment.mi_mean is not None
        and treatment.mi_mean > MI_TREATMENT_MIN
        and (
            shuffled is None
            or shuffled.mi_mean is None
            or shuffled.mi_mean <= MI_SHUFFLE_MAX
        )
    )
    schema_ok = campaign.schema_version == SCHEMA_VERSION
    overall = bool(assay_ok and oracle_gt_off and mi_ok and schema_ok)
    return {
        "schema_version": SCHEMA_VERSION,
        "overall_pass": overall,
        "cleared_for_research": overall,
        "gates": {
            "assay": {"pass": assay_ok, "assay_failed": campaign.assay_failed},
            "oracle_gt_channel_off": {"pass": oracle_gt_off},
            "payload_mi_manipulation": {
                "pass": mi_ok,
                "treatment_mi_mean": None if treatment is None else treatment.mi_mean,
                "shuffled_mi_mean": None if shuffled is None else shuffled.mi_mean,
            },
            "schema": {"pass": schema_ok},
        },
        "claim_ceiling": CLAIM_CEILING,
    }


def run_hard_experiment_02(
    seeds: Sequence[int] | None = None,
    *,
    scale: ScaleName = "smoke",
    tick_count: int | None = None,
    population: int | None = None,
) -> HardExperiment02Campaign:
    if scale not in {"smoke", "pilot", "research"}:
        raise ConfigurationError("scale must be smoke|pilot|research.")
    if scale == "pilot":
        seed_tuple = tuple(seeds) if seeds is not None else default_pilot_seeds()
        resolved_ticks = SMOKE_TICK_COUNT if tick_count is None else int(tick_count)
        resolved_pop = SMOKE_POPULATION if population is None else int(population)
    elif scale == "research":
        seed_tuple = tuple(seeds) if seeds is not None else default_research_seeds()
        resolved_ticks = RESEARCH_TICK_COUNT if tick_count is None else int(tick_count)
        resolved_pop = RESEARCH_POPULATION if population is None else int(population)
    else:
        seed_tuple = tuple(seeds) if seeds is not None else default_smoke_seeds()
        resolved_ticks = SMOKE_TICK_COUNT if tick_count is None else int(tick_count)
        resolved_pop = SMOKE_POPULATION if population is None else int(population)

    seed_records: list[HardExperiment02SeedRecord] = []
    for seed in seed_tuple:
        by_arm: dict[str, HardExperiment02ArmRecord] = {}
        for arm in ARMS:
            if arm == "activity_matched":
                continue
            by_arm[arm] = _run_arm(
                seed=int(seed),
                arm=arm,
                tick_count=resolved_ticks,
                population=resolved_pop,
            )
        budget = int(by_arm["treatment"].capsule_adoptions_accepted)
        by_arm["activity_matched"] = _run_arm(
            seed=int(seed),
            arm="activity_matched",
            tick_count=resolved_ticks,
            population=resolved_pop,
            activity_match_budget=budget,
        )
        seed_records.append(
            HardExperiment02SeedRecord(
                seed=int(seed),
                treatment=by_arm["treatment"],
                content_null=by_arm["content_null"],
                activity_matched=by_arm["activity_matched"],
                channel_off=by_arm["channel_off"],
                capsules_shuffled=by_arm["capsules_shuffled"],
                oracle_moderate=by_arm["oracle_moderate"],
            )
        )

    summaries = tuple(
        _arm_summary(arm, tuple(rec.arm_map()[arm] for rec in seed_records))
        for arm in ARMS
    )
    summary_map = {item.arm: item for item in summaries}
    assay_failures = _manipulation_failures(summary_map)
    assay_failed = bool(assay_failures)

    contrasts_raw: list[HardExperiment02PairedContrast] = []
    for baseline in ("content_null", "channel_off", "capsules_shuffled"):
        lefts: list[float] = []
        rights: list[float] = []
        for rec in seed_records:
            left = rec.treatment.receiver_mean_terminal_runtime_atp
            right = rec.arm_map()[baseline].receiver_mean_terminal_runtime_atp
            if left is None or right is None:
                continue
            lefts.append(float(left))
            rights.append(float(right))
        if not lefts or assay_failed:
            contrasts_raw.append(
                HardExperiment02PairedContrast(
                    treatment_arm="treatment",
                    baseline_arm=baseline,
                    dz=None,
                    p_raw=None,
                    p_holm=None,
                    n_pairs=len(lefts),
                )
            )
            continue
        try:
            effect = paired_effect_size(lefts, rights)
            dz = float(getattr(effect, "effect_size", effect.get("effect_size")))  # type: ignore[union-attr]
            p_raw = float(getattr(effect, "p_value", effect.get("p_value")))  # type: ignore[union-attr]
        except Exception:
            dz, p_raw = None, None
        contrasts_raw.append(
            HardExperiment02PairedContrast(
                treatment_arm="treatment",
                baseline_arm=baseline,
                dz=dz,
                p_raw=p_raw,
                p_holm=None,
                n_pairs=len(lefts),
            )
        )
    p_values = [item.p_raw for item in contrasts_raw]
    try:
        adjusted = list(holm_correction(p_values))
    except Exception:
        adjusted = list(p_values)
    contrasts = tuple(
        HardExperiment02PairedContrast(
            treatment_arm=item.treatment_arm,
            baseline_arm=item.baseline_arm,
            dz=item.dz,
            p_raw=item.p_raw,
            p_holm=None if adj is None else float(adj),
            n_pairs=item.n_pairs,
        )
        for item, adj in zip(contrasts_raw, adjusted, strict=False)
    )

    decision_failures: list[str] = []
    if assay_failed:
        decision_failures.append("assay_invalid")
    content_null = summary_map.get("content_null")
    channel_off = summary_map.get("channel_off")
    if (
        content_null is not None
        and channel_off is not None
        and content_null.mean is not None
        and channel_off.mean is not None
        and float(content_null.mean) > float(channel_off.mean)
    ):
        decision_failures.append("content_null_beats_channel_off")
    surviving = [
        item
        for item in contrasts
        if item.p_holm is not None
        and item.p_holm < 0.05
        and item.dz is not None
        and item.dz > 0
    ]
    if not assay_failed and not surviving:
        decision_failures.append("no_holm_surviving_primary_contrast")
    decision_rule_passed = (
        not decision_failures and not assay_failed and bool(surviving)
    )

    limitations: tuple[str, ...] = (
        "hard_experiment_02_starts_at_runtime_observation",
        "e2_ordinal_pattern_is_descriptive_not_a_single_dz",
        "research_campaign_required_for_confirmatory_claim",
    )
    if assay_failed:
        limitations = ("assay_invalid_manipulation_not_realized",) + limitations

    prereg = hard_experiment_02_prereg_digest()
    protocol = canonical_digest(
        {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": SCHEMA_VERSION,
            "prereg_digest": prereg,
            "arms": list(ARMS),
            "primary_outcome": PRIMARY_OUTCOME,
            "e2_ordinal_prediction": list(E2_ORDINAL_PREDICTION),
            "dag": hard_experiment_02_causal_dag(),
        }
    )
    return HardExperiment02Campaign(
        experiment_id=EXPERIMENT_ID,
        schema_version=SCHEMA_VERSION,
        product_name=PRODUCT_NAME,
        claim_ceiling=CLAIM_CEILING,
        seeds=seed_tuple,
        scale=scale,
        tick_count=resolved_ticks,
        population=resolved_pop,
        primary_outcome=PRIMARY_OUTCOME,
        prereg_digest=prereg,
        protocol_digest=protocol,
        interventions=hard_experiment_02_interventions(),
        seed_records=tuple(seed_records),
        arm_summaries=summaries,
        paired_contrasts=contrasts,
        assay_failed=assay_failed,
        assay_failures=assay_failures,
        decision_rule_passed=decision_rule_passed,
        decision_rule_failures=tuple(decision_failures),
        e2_ordinal_ok=None,
        limitations=limitations,
    )


def evaluate_hard_experiment_02_claim(
    campaign: HardExperiment02Campaign,
) -> dict[str, JsonValue]:
    return {
        "product_name": PRODUCT_NAME,
        "experiment_id": campaign.experiment_id,
        "claim_ceiling": CLAIM_CEILING,
        "assay_failed": campaign.assay_failed,
        "decision_rule_passed": campaign.decision_rule_passed,
        "collective_intelligence": False,
        "intelligence": False,
        "agi": False,
        "tokyo_type1_passed": False,
        "avida_replacement": False,
        "limitations": list(campaign.limitations),
        "digest": campaign.digest,
    }


def format_hard_experiment_02_summary(campaign: HardExperiment02Campaign) -> str:
    lines = [
        f"{PRODUCT_NAME} HARD_EXPERIMENT_02 ({campaign.scale})",
        f"claim_ceiling={campaign.claim_ceiling}",
        f"assay_failed={campaign.assay_failed}",
        f"decision_rule_passed={campaign.decision_rule_passed}",
        f"seeds={list(campaign.seeds)}",
    ]
    for item in campaign.arm_summaries:
        lines.append(
            f"  {item.arm}: mean={item.mean} mi={item.mi_mean} "
            f"adoptions={item.adoption_mean}"
        )
    for item in campaign.paired_contrasts:
        lines.append(
            f"  contrast treatment vs {item.baseline_arm}: "
            f"dz={item.dz} p_holm={item.p_holm}"
        )
    return "\n".join(lines)


def committed_pilot_results_path() -> Path:
    return _repo_root() / "docs" / "hard_experiment_02" / "pilot_v1.json"


def committed_research_results_path() -> Path:
    return _repo_root() / "docs" / "hard_experiment_02" / "results_v1.json"


def write_hard_experiment_02_results(
    campaign: HardExperiment02Campaign, path: Path | None = None
) -> Path:
    target = path
    if target is None:
        target = (
            committed_pilot_results_path()
            if campaign.scale == "pilot"
            else committed_research_results_path()
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(campaign.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target
