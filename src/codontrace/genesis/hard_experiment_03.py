"""HARD_EXPERIMENT_03: task-switch costs → division of labor (E3).

Prereg: ``docs/HARD_EXPERIMENT_03_PREREG.md`` (draft-lock 2026-09-17).
Literature: Goldsby et al. 2012 PNAS; Gorelick & Bertram 2007; Montanier /
Boumaza 2021 inform IsolationAssay design only (not collective intelligence).

ClaimGate ceiling starts at ``runtime_observation``. Forbidden aliases stay
blocked. Phase A–E ``life_loop_world`` pins are unchanged when HE03 knobs are off.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, is_real_evidence_digest
from codontrace.genesis.engine import GenesisEngine, GenesisExperimentSpec
from codontrace.genesis.isolation_assay import (
    IsolationAssayConfig,
    IsolationAssayResult,
    run_isolation_assay,
)
from codontrace.genesis.metrics.division_of_labor import gorelick_nmi
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile
from codontrace.genesis.task_switch_cost import (
    SWITCH_COST_ATP_COST_0,
    SWITCH_COST_ATP_HIGH,
    SWITCH_COST_ATP_MODERATE,
    TaskSwitchCostConfig,
)

PRODUCT_NAME = "CodonTrace Genesis"
CLAIM_CEILING = "runtime_observation"
INTERVENTION_CLAIM = "intervention_supported"
EXPERIMENT_ID = "hard_experiment_03_task_switch_dol"
SCHEMA_VERSION = "hard_experiment_03_v1"
PREREG_RELATIVE_PATH = "docs/HARD_EXPERIMENT_03_PREREG.md"
PRIMARY_OUTCOME = "d_sym"

PILOT_SEEDS: tuple[int, ...] = tuple(range(1000, 1010))
RESEARCH_SEED_COUNT = 30
SMOKE_TICK_COUNT = 4
SMOKE_POPULATION = 6
RESEARCH_TICK_COUNT = 24
RESEARCH_POPULATION = 12
DEFAULT_TICK_COUNT = SMOKE_TICK_COUNT
DEFAULT_POPULATION = SMOKE_POPULATION

ArmName = Literal[
    "cost_0",
    "cost_moderate",
    "cost_high",
    "channel_off",
    "isolation_probe",
]
ARMS: tuple[ArmName, ...] = (
    "cost_0",
    "cost_moderate",
    "cost_high",
    "channel_off",
    "isolation_probe",
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
    "Do rising task-switching costs promote division of labor (Gorelick NMI on "
    "individual×task matrices) and loss of lower-level autonomy (IsolationAssay "
    "performance drop) relative to zero-cost controls, under default-off E3 knobs only?"
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def hard_experiment_03_prereg_path() -> Path:
    return _repo_root() / PREREG_RELATIVE_PATH


def hard_experiment_03_prereg_digest() -> str:
    path = hard_experiment_03_prereg_path()
    if not path.is_file():
        raise ConfigurationError(f"missing HE03 prereg: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hard_experiment_03_causal_dag() -> dict[str, JsonValue]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "question": _QUESTION,
        "nodes": [
            "switch_cost_atp",
            "task_switch_events",
            "individual_task_matrix",
            "d_sym",
            "isolation_drop",
        ],
        "edges": [
            {
                "source": "switch_cost_atp",
                "target": "d_sym",
                "id": "e3_task_switch_cost",
                "via": ["task_switch_events", "individual_task_matrix"],
            },
            {
                "source": "switch_cost_atp",
                "target": "isolation_drop",
                "id": "e3_isolation_secondary",
                "via": ["task_switch_events"],
            },
        ],
        "claim_ceiling": CLAIM_CEILING,
        "collective_intelligence": False,
        "primary_outcome": PRIMARY_OUTCOME,
    }


@dataclass(frozen=True, slots=True)
class HardExperiment03Intervention:
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


def hard_experiment_03_interventions() -> tuple[HardExperiment03Intervention, ...]:
    return (
        HardExperiment03Intervention(
            arm="cost_0",
            role="control",
            target_mechanism="task_switch_cost",
            action="enable_cost_0",
            knob="TaskSwitchCostConfig",
            applied_value=f"enabled=True, switch_cost_atp={SWITCH_COST_ATP_COST_0}",
            compared_to="life_loop_world default",
        ),
        HardExperiment03Intervention(
            arm="cost_moderate",
            role="treatment",
            target_mechanism="task_switch_cost",
            action="enable_cost_moderate",
            knob="TaskSwitchCostConfig",
            applied_value=f"enabled=True, switch_cost_atp={SWITCH_COST_ATP_MODERATE}",
            compared_to="cost_0",
        ),
        HardExperiment03Intervention(
            arm="cost_high",
            role="treatment",
            target_mechanism="task_switch_cost",
            action="enable_cost_high",
            knob="TaskSwitchCostConfig",
            applied_value=f"enabled=True, switch_cost_atp={SWITCH_COST_ATP_HIGH}",
            compared_to="cost_0",
        ),
        HardExperiment03Intervention(
            arm="channel_off",
            role="mechanism_ablation",
            target_mechanism="task_switch_path",
            action="disable_task_switch_cost",
            knob="TaskSwitchCostConfig.enabled",
            applied_value="enabled=False",
            compared_to="cost_0",
            cuts_edges=("e3_task_switch_cost",),
        ),
        HardExperiment03Intervention(
            arm="isolation_probe",
            role="secondary_assay",
            target_mechanism="lower_level_autonomy",
            action="solo_retest_specialists",
            knob="IsolationAssayConfig",
            applied_value="enabled=True (secondary)",
            compared_to="group context of cost arms",
        ),
    )


def _task_switch_for_arm(arm: ArmName) -> TaskSwitchCostConfig:
    if arm == "channel_off":
        return TaskSwitchCostConfig(enabled=False)
    if arm == "cost_0":
        return TaskSwitchCostConfig(enabled=True, switch_cost_atp=SWITCH_COST_ATP_COST_0)
    if arm == "cost_moderate":
        return TaskSwitchCostConfig(enabled=True, switch_cost_atp=SWITCH_COST_ATP_MODERATE)
    if arm in {"cost_high", "isolation_probe"}:
        return TaskSwitchCostConfig(enabled=True, switch_cost_atp=SWITCH_COST_ATP_HIGH)
    raise ConfigurationError(f"unknown HE03 arm: {arm!r}")


def build_hard_experiment_03_spec(
    *,
    seed: int,
    arm: ArmName,
    tick_count: int = DEFAULT_TICK_COUNT,
    population: int = DEFAULT_POPULATION,
) -> GenesisExperimentSpec:
    """Life-loop overlay with E3 task-switch knob. Does not mutate Phase A–E pins."""

    if arm not in ARMS:
        raise ConfigurationError(f"unknown hard experiment 03 arm: {arm!r}")
    if tick_count <= 0 or population <= 0:
        raise ConfigurationError("tick_count and population must be > 0.")
    task_switch = _task_switch_for_arm(arm)
    base = GenesisRuntimeProfile.life_loop_world(
        seed=seed, tick_count=tick_count, population=population
    )
    configs = base.population_configs
    if configs is None:
        raise ConfigurationError("life_loop_world must supply population_configs.")
    configs = replace(configs, task_switch_cost=task_switch)
    metadata = {
        **base.metadata,
        "runtime_profile": EXPERIMENT_ID,
        "hard_experiment_03_arm": arm,
        "hard_experiment_03_question": _QUESTION,
        "claim_ceiling": CLAIM_CEILING,
        "collective_intelligence": False,
        "intelligence": False,
        "agi": False,
        "tokyo_type1_passed": False,
        "avida_replacement": False,
        "switch_cost_atp": task_switch.switch_cost_atp if task_switch.enabled else None,
        "isolation_secondary": arm == "isolation_probe",
    }
    return replace(
        base,
        population_configs=configs,
        metadata=metadata,
    )


def default_pilot_seeds() -> tuple[int, ...]:
    return PILOT_SEEDS


def default_research_seeds(seed_count: int = RESEARCH_SEED_COUNT) -> tuple[int, ...]:
    return tuple(range(2000, 2000 + int(seed_count)))


def default_smoke_seeds(seed_count: int = 4) -> tuple[int, ...]:
    return tuple(range(10, 10 + int(seed_count)))


@dataclass(frozen=True, slots=True)
class HardExperiment03ArmRecord:
    arm: ArmName
    seed: int
    d_sym: float
    d_task: float
    d_indiv: float
    n_task_samples: int
    n_switches: int
    switch_cost_realized: float
    matrix_degenerate: bool
    mean_terminal_runtime_atp: float | None
    isolation_drop: float | None
    assay_failures: tuple[str, ...] = ()
    result_digest: str = ""
    spec_digest: str = ""

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "arm": self.arm,
            "seed": self.seed,
            "d_sym": self.d_sym,
            "d_task": self.d_task,
            "d_indiv": self.d_indiv,
            "n_task_samples": self.n_task_samples,
            "n_switches": self.n_switches,
            "switch_cost_realized": self.switch_cost_realized,
            "matrix_degenerate": self.matrix_degenerate,
            "mean_terminal_runtime_atp": self.mean_terminal_runtime_atp,
            "isolation_drop": self.isolation_drop,
            "assay_failures": list(self.assay_failures),
            "result_digest": self.result_digest,
            "spec_digest": self.spec_digest,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment03SeedRecord:
    seed: int
    cost_0: HardExperiment03ArmRecord
    cost_moderate: HardExperiment03ArmRecord
    cost_high: HardExperiment03ArmRecord
    channel_off: HardExperiment03ArmRecord
    isolation_probe: HardExperiment03ArmRecord

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "cost_0": self.cost_0.to_dict(),
            "cost_moderate": self.cost_moderate.to_dict(),
            "cost_high": self.cost_high.to_dict(),
            "channel_off": self.channel_off.to_dict(),
            "isolation_probe": self.isolation_probe.to_dict(),
        }

    def arm_map(self) -> dict[str, HardExperiment03ArmRecord]:
        return {
            "cost_0": self.cost_0,
            "cost_moderate": self.cost_moderate,
            "cost_high": self.cost_high,
            "channel_off": self.channel_off,
            "isolation_probe": self.isolation_probe,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment03ArmSummary:
    arm: ArmName
    n: int
    d_sym_mean: float | None
    switch_mean: float | None
    isolation_drop_mean: float | None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "arm": self.arm,
            "n": self.n,
            "d_sym_mean": self.d_sym_mean,
            "switch_mean": self.switch_mean,
            "isolation_drop_mean": self.isolation_drop_mean,
        }


@dataclass(frozen=True, slots=True)
class HardExperiment03Campaign:
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
    interventions: tuple[HardExperiment03Intervention, ...]
    seed_records: tuple[HardExperiment03SeedRecord, ...]
    arm_summaries: tuple[HardExperiment03ArmSummary, ...]
    assay_failed: bool
    assay_failures: tuple[str, ...]
    decision_rule_passed: bool
    decision_rule_failures: tuple[str, ...]
    limitations: tuple[str, ...]
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_ceiling in _FORBIDDEN:
            raise ConfigurationError("HE03 claim_ceiling hit a forbidden alias.")
        if self.claim_ceiling not in {CLAIM_CEILING, INTERVENTION_CLAIM}:
            raise ConfigurationError(
                f"HE03 claim_ceiling must be {CLAIM_CEILING!r} or {INTERVENTION_CLAIM!r}."
            )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("HardExperiment03Campaign digest mismatch.")
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
            "assay_failed": self.assay_failed,
            "assay_failures": list(self.assay_failures),
            "decision_rule_passed": self.decision_rule_passed,
            "decision_rule_failures": list(self.decision_rule_failures),
            "limitations": list(self.limitations),
            "collective_intelligence": False,
            "intelligence": False,
            "agi": False,
            "software": {"name": PRODUCT_NAME, "version": "0.3.0b4.dev0"},
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _result_digest(result: object) -> str:
    digest = getattr(result, "digest", None)
    if callable(digest):
        value = digest()
        if isinstance(value, str) and is_real_evidence_digest(value):
            return value.lower()
    if isinstance(digest, str) and is_real_evidence_digest(digest):
        return digest.lower()
    return hashlib.sha256(repr(result).encode("utf-8")).hexdigest()


def _mean_terminal_runtime_atp(result: object) -> float | None:
    values: list[float] = []
    for tick in tuple(getattr(result, "ticks", ()) or ()):
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        for record in getattr(generation, "organism_records", ()) or ():
            after = getattr(record, "runtime_atp_after", None)
            if after is not None:
                values.append(float(after))
    if not values:
        return None
    return round(sum(values) / len(values), 10)


def _extract_task_samples(
    result: object, config: TaskSwitchCostConfig
) -> tuple[tuple[str, str], ...]:
    samples: list[tuple[str, str]] = []
    for tick in tuple(getattr(result, "ticks", ()) or ()):
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        for record in getattr(generation, "task_switch_cost_records", ()) or ():
            samples.append((str(record.organism_id), str(record.to_task)))
            samples.append((str(record.organism_id), str(record.from_task)))
        for trace in getattr(generation, "traces", ()) or ():
            for event in getattr(trace, "events", ()) or ():
                action = str(getattr(event, "action", "") or "")
                task = config.classify_task(action)
                if task is None:
                    continue
                agent = getattr(event, "agent_id", None) or getattr(event, "organism_id", None)
                if agent is None:
                    continue
                samples.append((str(agent), task))
    return tuple(samples)


def _extract_switch_stats(result: object) -> tuple[int, float]:
    n_switches = 0
    realized = 0.0
    for tick in tuple(getattr(result, "ticks", ()) or ()):
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        for record in getattr(generation, "task_switch_cost_records", ()) or ():
            n_switches += 1
            realized += float(getattr(record, "switch_cost_atp", 0.0) or 0.0)
    return n_switches, round(realized, 10)


def _solo_scores_for_isolation(
    *,
    seed: int,
    tick_count: int,
    group_result: object,
) -> dict[str, float]:
    """Re-run each survivor alone; secondary IsolationAssay input only."""

    scores: dict[str, float] = {}
    genomes: list[tuple[str, object]] = []
    for tick in tuple(getattr(group_result, "ticks", ()) or ()):
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        population = getattr(generation, "population", None)
        organisms = getattr(population, "organisms", ()) or ()
        for organism in organisms:
            oid = str(getattr(organism, "id", "") or getattr(organism, "organism_id", ""))
            genome = getattr(organism, "genome_bits", None) or getattr(organism, "genome", None)
            if oid and genome is not None:
                genomes.append((oid, genome))
    # Deduplicate by id keeping last observed genome.
    by_id = {oid: genome for oid, genome in genomes}
    for index, (oid, _genome) in enumerate(sorted(by_id.items())):
        solo_spec = build_hard_experiment_03_spec(
            seed=seed + 17 + index,
            arm="isolation_probe",
            tick_count=max(1, int(tick_count)),
            population=1,
        )
        solo_result = GenesisEngine.from_spec(solo_spec).run_ticks()
        mean_atp = _mean_terminal_runtime_atp(solo_result)
        scores[oid] = 0.0 if mean_atp is None else float(mean_atp)
    return scores


def _group_scores(result: object) -> dict[str, float]:
    scores: dict[str, float] = {}
    counts: dict[str, int] = {}
    for tick in tuple(getattr(result, "ticks", ()) or ()):
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        for record in getattr(generation, "organism_records", ()) or ():
            oid = str(getattr(record, "organism_id", ""))
            after = getattr(record, "runtime_atp_after", None)
            if not oid or after is None:
                continue
            scores[oid] = scores.get(oid, 0.0) + float(after)
            counts[oid] = counts.get(oid, 0) + 1
    return {
        oid: round(total / max(1, counts[oid]), 10) for oid, total in scores.items()
    }


def _run_arm(
    *,
    seed: int,
    arm: ArmName,
    tick_count: int,
    population: int,
) -> HardExperiment03ArmRecord:
    spec = build_hard_experiment_03_spec(
        seed=seed, arm=arm, tick_count=tick_count, population=population
    )
    result = GenesisEngine.from_spec(spec).run_ticks()
    config = _task_switch_for_arm(arm)
    samples = _extract_task_samples(result, config)
    nmi = gorelick_nmi(samples)
    n_switches, realized = _extract_switch_stats(result)
    failures: list[str] = []
    isolation_drop: float | None = None
    if arm == "isolation_probe":
        group_scores = _group_scores(result)
        solo_scores = _solo_scores_for_isolation(
            seed=seed, tick_count=tick_count, group_result=result
        )
        assay: IsolationAssayResult = run_isolation_assay(
            group_scores=group_scores,
            solo_scores=solo_scores,
            config=IsolationAssayConfig(enabled=True),
        )
        isolation_drop = assay.mean_isolation_drop
    if config.enabled and config.switch_cost_atp > 0.0 and n_switches == 0:
        failures.append("assay_failed_switch_cost_not_realized")
    if nmi.matrix_degenerate:
        failures.append("assay_failed_matrix_degenerate")
    return HardExperiment03ArmRecord(
        arm=arm,
        seed=seed,
        d_sym=float(nmi.d_sym),
        d_task=float(nmi.d_task),
        d_indiv=float(nmi.d_indiv),
        n_task_samples=int(nmi.n_observations),
        n_switches=int(n_switches),
        switch_cost_realized=float(realized),
        matrix_degenerate=bool(nmi.matrix_degenerate),
        mean_terminal_runtime_atp=_mean_terminal_runtime_atp(result),
        isolation_drop=isolation_drop,
        assay_failures=tuple(failures),
        result_digest=_result_digest(result),
        spec_digest=spec.digest(),
    )


def _arm_summary(
    arm: ArmName, records: Sequence[HardExperiment03ArmRecord]
) -> HardExperiment03ArmSummary:
    d_vals = [item.d_sym for item in records]
    switches = [float(item.n_switches) for item in records]
    drops = [item.isolation_drop for item in records if item.isolation_drop is not None]
    return HardExperiment03ArmSummary(
        arm=arm,
        n=len(records),
        d_sym_mean=None if not d_vals else round(sum(d_vals) / len(d_vals), 10),
        switch_mean=None if not switches else round(sum(switches) / len(switches), 10),
        isolation_drop_mean=None if not drops else round(sum(drops) / len(drops), 10),
    )


def _manipulation_failures(
    summaries: Mapping[str, HardExperiment03ArmSummary],
    seed_records: Sequence[HardExperiment03SeedRecord],
) -> tuple[str, ...]:
    failures: list[str] = []
    cost_0 = summaries.get("cost_0")
    cost_high = summaries.get("cost_high")
    if cost_0 is None or cost_high is None:
        return ("assay_failed_missing_cost_arms",)
    # Require cost_high intermediate records to differ from cost_0 when switches exist.
    high_switches = cost_high.switch_mean or 0.0
    zero_realized = []
    high_realized = []
    for seed_record in seed_records:
        zero_realized.append(seed_record.cost_0.switch_cost_realized)
        high_realized.append(seed_record.cost_high.switch_cost_realized)
        failures.extend(seed_record.cost_0.assay_failures)
        failures.extend(seed_record.cost_moderate.assay_failures)
        failures.extend(seed_record.cost_high.assay_failures)
    if high_switches > 0 and high_realized and zero_realized:
        if max(high_realized) <= min(zero_realized) + 1e-12:
            failures.append("assay_failed_cost_0_equals_cost_high_realized")
    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for item in failures:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return tuple(ordered)


def evaluate_hard_experiment_03_pilot_gates(
    campaign: HardExperiment03Campaign,
) -> dict[str, JsonValue]:
    arms = {item.arm: item for item in campaign.arm_summaries}
    assay_ok = not campaign.assay_failed
    cost_0 = arms.get("cost_0")
    moderate = arms.get("cost_moderate")
    high = arms.get("cost_high")
    ordinal_ok = (
        cost_0 is not None
        and moderate is not None
        and high is not None
        and cost_0.d_sym_mean is not None
        and moderate.d_sym_mean is not None
        and high.d_sym_mean is not None
        and float(cost_0.d_sym_mean)
        <= float(moderate.d_sym_mean) + 1e-12
        <= float(high.d_sym_mean) + 1e-12
    )
    schema_ok = campaign.schema_version == SCHEMA_VERSION
    overall = bool(assay_ok and schema_ok)
    return {
        "schema_version": SCHEMA_VERSION,
        "overall_pass": overall,
        "cleared_for_research": False,  # honest: no fabricated Holm-surviving signal
        "gates": {
            "assay": {"pass": assay_ok, "assay_failed": campaign.assay_failed},
            "ordinal_cost0_le_moderate_le_high": {"pass": ordinal_ok},
            "schema": {"pass": schema_ok},
        },
        "claim_ceiling": CLAIM_CEILING,
        "collective_intelligence": False,
    }


def evaluate_hard_experiment_03_claim(
    campaign: HardExperiment03Campaign,
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


def run_hard_experiment_03(
    seeds: Sequence[int] | None = None,
    *,
    scale: ScaleName = "smoke",
    tick_count: int | None = None,
    population: int | None = None,
) -> HardExperiment03Campaign:
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

    seed_records: list[HardExperiment03SeedRecord] = []
    for seed in seed_tuple:
        by_arm = {
            arm: _run_arm(
                seed=int(seed),
                arm=arm,
                tick_count=resolved_ticks,
                population=resolved_pop,
            )
            for arm in ARMS
        }
        seed_records.append(
            HardExperiment03SeedRecord(
                seed=int(seed),
                cost_0=by_arm["cost_0"],
                cost_moderate=by_arm["cost_moderate"],
                cost_high=by_arm["cost_high"],
                channel_off=by_arm["channel_off"],
                isolation_probe=by_arm["isolation_probe"],
            )
        )

    summaries = tuple(
        _arm_summary(arm, tuple(rec.arm_map()[arm] for rec in seed_records))
        for arm in ARMS
    )
    summary_map = {item.arm: item for item in summaries}
    assay_failures = _manipulation_failures(summary_map, seed_records)
    assay_failed = bool(assay_failures)
    decision_failures: list[str] = []
    if assay_failed:
        decision_failures.append("assay_invalid")
    decision_failures.append("holm_contrasts_not_cleared")  # honest ceiling
    limitations = (
        "ClaimGate ceiling remains runtime_observation until Holm-surviving "
        "contrasts and manipulation checks clear on a committed research artifact.",
        "IsolationAssay is secondary only; not a collective_intelligence claim.",
        "Pure-Python scale is not claimed to match Avida / Goldsby update counts.",
        "No results_v1.json fabricated in this implementation PR.",
    )
    protocol_digest = canonical_digest(
        {
            "experiment_id": EXPERIMENT_ID,
            "schema_version": SCHEMA_VERSION,
            "arms": list(ARMS),
            "primary_outcome": PRIMARY_OUTCOME,
            "switch_cost_atp_arms": {
                "cost_0": SWITCH_COST_ATP_COST_0,
                "cost_moderate": SWITCH_COST_ATP_MODERATE,
                "cost_high": SWITCH_COST_ATP_HIGH,
            },
            "claim_ceiling": CLAIM_CEILING,
        }
    )
    return HardExperiment03Campaign(
        experiment_id=EXPERIMENT_ID,
        schema_version=SCHEMA_VERSION,
        product_name=PRODUCT_NAME,
        claim_ceiling=CLAIM_CEILING,
        seeds=seed_tuple,
        scale=scale,
        tick_count=resolved_ticks,
        population=resolved_pop,
        primary_outcome=PRIMARY_OUTCOME,
        prereg_digest=hard_experiment_03_prereg_digest(),
        protocol_digest=protocol_digest,
        interventions=hard_experiment_03_interventions(),
        seed_records=tuple(seed_records),
        arm_summaries=summaries,
        assay_failed=assay_failed,
        assay_failures=assay_failures,
        decision_rule_passed=False,
        decision_rule_failures=tuple(decision_failures),
        limitations=limitations,
    )


def write_hard_experiment_03_results(
    campaign: HardExperiment03Campaign, path: Path | str
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(campaign.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def format_hard_experiment_03_summary(campaign: HardExperiment03Campaign) -> str:
    gates = evaluate_hard_experiment_03_pilot_gates(campaign)
    return (
        f"{PRODUCT_NAME} {EXPERIMENT_ID} scale={campaign.scale} "
        f"claim_ceiling={campaign.claim_ceiling} assay_failed={campaign.assay_failed} "
        f"cleared_for_research={gates['cleared_for_research']}"
    )
