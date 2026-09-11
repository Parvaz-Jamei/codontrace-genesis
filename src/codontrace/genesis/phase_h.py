"""Phase H collective-intelligence *pathway* scaffolding for CodonTrace Genesis.

Measurement-first engineering: communication ablation, group-vs-individual
effect sizes, Goldsby 2012 task-switching cost hooks, and a checklist printer
for ``collective_intelligence_candidate``. None of this auto-sets ClaimGate
flags. ``collective_intelligence`` / ``intelligence`` / AGI stay blocked.

Claim ceiling: ``runtime_observation``. Group fitness is not intelligence.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.claim_gate import (
    ClaimDecision,
    ClaimRequest,
    ScientificClaimGate,
)
from codontrace.genesis.collective_deme import (
    DemeDivisionOfLaborObservation,
    GroupVsIndividualContrast,
    _mean_organism_fitness,
    _message_count,
    build_collective_deme_payoff_pack,
    build_deme_division_of_labor_observation,
    build_group_vs_individual_contrast,
    rank_demes_by_mean_fitness,
)

_CLAIM_CEILING = "runtime_observation"
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
_CANDIDATE_FLAGS: tuple[str, ...] = (
    "real_partner_event",
    "non_capsule_cooperation",
    "role_complementarity",
    "collective_coordination",
    "heldout_protocol",
    "familiar_partner_protocol",
    "unfamiliar_partner_protocol",
    "ablation_result",
    "collective_report_digest",
    "replay_verification",
)

RESEARCH_SEED_COUNT = 12
SMOKE_SEED_COUNT = 2
DEFAULT_TASK_SWITCHING_COST = 0.0
MEASURED_RUNTIME = "measured_runtime_observation"
GAP_NOT_RUN = "not_run"

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "goldsby_2012_pnas_task_switching",
        "Goldsby et al. PNAS 2012 doi:10.1073/pnas.1202233109: task-switching "
        "costs promote DoL and a shift in individuality. Hook is a measurement "
        "reweight, not that experiment at 50 replicates.",
    ),
    (
        "goldsby_messaging_ablation",
        "Goldsby/Ofria Avida messaging: communication must pay. Phase H runs "
        "messaging on vs off. Status becomes measured_runtime_observation, not "
        "ClaimGate ablation_result.",
    ),
    (
        "chaturvedi_2026_mls_roles",
        "arXiv 2604.00810: role differentiation under MLS in coupled channels. "
        "Not implemented; group-vs-individual effect sizes are the on-ramp.",
    ),
    (
        "szathmary_michod_transition",
        "Major transitions / export-of-fitness remain undemonstrated. "
        "major_transition_in_individuality stays False.",
    ),
)


def default_research_seeds(seed_count: int = RESEARCH_SEED_COUNT) -> tuple[int, ...]:
    """Deterministic seed tuple. Research default is 12; smoke may pass 2."""

    count = int(seed_count)
    if count < 2:
        raise ConfigurationError("Phase H seed_count must be >= 2.")
    return tuple(range(3, 3 + count))


def _resolve_seeds(
    seeds: Sequence[int] | None,
    seed_count: int | None,
    *,
    default_count: int,
) -> tuple[int, ...]:
    if seeds is not None:
        resolved = tuple(int(item) for item in seeds)
        if len(resolved) < 2:
            raise ConfigurationError("Phase H campaigns require at least two seeds.")
        return resolved
    return default_research_seeds(default_count if seed_count is None else seed_count)


def _cohens_d(left: Sequence[float], right: Sequence[float]) -> tuple[float | None, str]:
    if len(left) < 2 or len(right) < 2:
        return None, "undefined_need_two_observations_per_arm"
    mean_l = sum(left) / len(left)
    mean_r = sum(right) / len(right)
    var_l = sum((item - mean_l) ** 2 for item in left) / (len(left) - 1)
    var_r = sum((item - mean_r) ** 2 for item in right) / (len(right) - 1)
    pooled = math.sqrt(
        (((len(left) - 1) * var_l) + ((len(right) - 1) * var_r)) / (len(left) + len(right) - 2)
    )
    if pooled <= 0.0:
        if abs(mean_l - mean_r) <= 1e-12:
            return 0.0, "zero_variance_zero_delta"
        return None, "undefined_zero_pooled_variance"
    return round((mean_l - mean_r) / pooled, 10), "computed"


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 10)


def _assert_ci_blocked(payload: Mapping[str, JsonValue], gate: ScientificClaimGate) -> None:
    if payload.get("collective_intelligence") is True or payload.get("intelligence") is True:
        raise ConfigurationError("Phase H payloads must not set intelligence claims True.")
    for label in (
        "collective_intelligence",
        "proved_collective_intelligence",
        "intelligence",
        "agi",
    ):
        decision = gate.decide(ClaimRequest(label, {}))
        if decision.allowed:
            raise ConfigurationError(f"{label} must remain blocked.")


def _run_phase_e(
    *,
    seed: int,
    tick_count: int,
    population: int,
    enable_demes: bool,
    enable_roles: bool,
    messaging_enabled: bool | None = None,
    replicate_on_mean_fitness: float | None = 0.0,
) -> object:
    from codontrace.genesis.engine import GenesisEngine
    from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

    spec = GenesisRuntimeProfile.phase_e_substrate_world(
        seed=seed,
        tick_count=tick_count,
        population=population,
        enable_demes=enable_demes,
        enable_roles=enable_roles,
        replicate_on_mean_fitness=replicate_on_mean_fitness if enable_demes else None,
    )
    if enable_demes and messaging_enabled is not None:
        configs = spec.population_configs
        if configs is None or configs.phase_e is None:
            raise ConfigurationError("phase_e_substrate_world missing population configs.")
        demes = configs.phase_e.demes
        spec = replace(
            spec,
            population_configs=replace(
                configs,
                phase_e=replace(
                    configs.phase_e,
                    demes=replace(demes, messaging_enabled=bool(messaging_enabled)),
                ),
            ),
        )
    return GenesisEngine.from_spec(spec).run_ticks()


def action_sequences_from_result(result: object) -> dict[str, tuple[str, ...]]:
    """Consecutive executed actions per organism across ticks (Goldsby switch unit)."""

    sequences: dict[str, list[str]] = {}
    for tick in getattr(result, "ticks", ()) or ():
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        for trace in getattr(generation, "traces", ()) or ():
            for event in getattr(trace, "events", ()) or ():
                status = str(getattr(event, "status", "") or "")
                if status not in {"executed", "success", ""}:
                    continue
                oid = str(getattr(event, "agent_id", "") or "")
                action = str(getattr(event, "action", "") or "")
                if oid and action:
                    sequences.setdefault(oid, []).append(action)
    return {key: tuple(value) for key, value in sequences.items()}


def count_task_switches(actions: Sequence[str]) -> int:
    """Count consecutive action-type changes (Goldsby 2012 analog, not CPU cycles)."""

    return sum(1 for left, right in zip(actions, actions[1:], strict=False) if left != right)


@dataclass(frozen=True, slots=True)
class TaskSwitchingCostConfig:
    """Goldsby 2012 analog: penalize consecutive action-type switches in DoL shares.

    Default cost is 0 (no reweight). This is a measurement hook, not a 50-replicate
    PNAS experiment and not evolved division of labor.
    """

    cost: float = DEFAULT_TASK_SWITCHING_COST
    literature_ref: str = "goldsby_etal_2012_pnas_10.1073/pnas.1202233109"
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "task_switching_cost_config_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cost",
            round(require_finite_float("cost", self.cost, non_negative=True), 10),
        )
        if self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError(
                "TaskSwitchingCostConfig ceiling must stay runtime_observation."
            )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("TaskSwitchingCostConfig digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "cost": self.cost,
            "literature_ref": self.literature_ref,
            "claim_ceiling": self.claim_ceiling,
            "evolved_division_of_labor": False,
            "collective_intelligence": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class TaskSwitchingDoLObservation:
    """DoL metrics after a task-switching cost reweight. Still not evolved DoL."""

    deme_id: str
    cost: float
    switch_count_total: int
    mean_switches_per_organism: float
    specialization_index: float
    baseline: DemeDivisionOfLaborObservation
    reweighted: DemeDivisionOfLaborObservation
    fitness_share_changed: bool
    literature_gap: str = "measurement_hook_not_goldsby_2012_experiment"
    digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "cost", round(require_finite_float("cost", self.cost, non_negative=True), 10)
        )
        object.__setattr__(
            self,
            "mean_switches_per_organism",
            round(
                require_finite_float("mean_switches_per_organism", self.mean_switches_per_organism),
                10,
            ),
        )
        object.__setattr__(
            self,
            "specialization_index",
            round(require_finite_float("specialization_index", self.specialization_index), 10),
        )
        if self.switch_count_total < 0:
            raise ConfigurationError("switch_count_total must be >= 0.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("TaskSwitchingDoLObservation digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "deme_id": self.deme_id,
            "cost": self.cost,
            "switch_count_total": self.switch_count_total,
            "mean_switches_per_organism": self.mean_switches_per_organism,
            "specialization_index": self.specialization_index,
            "baseline": self.baseline.to_dict(),
            "reweighted": self.reweighted.to_dict(),
            "fitness_share_changed": self.fitness_share_changed,
            "literature_gap": self.literature_gap,
            "evolved_division_of_labor": False,
            "collective_intelligence": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def apply_task_switching_cost_to_dol(
    result: object,
    *,
    config: TaskSwitchingCostConfig | None = None,
    cost: float | None = None,
) -> tuple[TaskSwitchingDoLObservation, ...]:
    """Reweight deme DoL fitness shares by Goldsby-style switch counts.

    ``adjusted_fitness = max(0, fitness - cost * switches)``. Specialists (few
    switches) keep more share as cost rises. Assigned roles stay assigned.
    """

    resolved = config or TaskSwitchingCostConfig(
        cost=DEFAULT_TASK_SWITCHING_COST if cost is None else cost
    )
    if cost is not None and config is not None and abs(config.cost - cost) > 1e-12:
        raise ConfigurationError(
            "apply_task_switching_cost_to_dol cost conflicts with config.cost."
        )
    baselines = build_deme_division_of_labor_observation(result)
    sequences = action_sequences_from_result(result)
    switches = {oid: count_task_switches(actions) for oid, actions in sequences.items()}
    last_state = None
    last_organisms: tuple[object, ...] = ()
    scores: dict[str, float] = {}
    for tick in getattr(result, "ticks", ()) or ():
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        last_state = getattr(generation, "deme_state", None)
        population = getattr(generation, "population", None)
        last_organisms = getattr(population, "organisms", ()) if population is not None else ()
        for item in getattr(population, "fitness", ()) if population is not None else ():
            oid = str(getattr(item, "organism_id", "") or "")
            if oid:
                scores[oid] = float(getattr(item, "score", 0.0) or 0.0)
    role_by_id: dict[str, str] = {}
    for organism in last_organisms:
        role = getattr(getattr(organism, "phase_e_state", None), "role", None)
        kind = getattr(role, "kind", None)
        value = getattr(kind, "value", None) or (str(kind) if kind else "unassigned")
        role_by_id[str(getattr(organism, "id", ""))] = str(value)
    baseline_by_id = {item.deme_id: item for item in baselines}
    rows: list[TaskSwitchingDoLObservation] = []
    if last_state is None:
        return ()
    for deme in getattr(last_state, "demes", ()) or ():
        member_ids = tuple(str(item) for item in deme.member_ids)
        member_switches = [switches.get(member_id, 0) for member_id in member_ids]
        total_switches = int(sum(member_switches))
        mean_sw = _mean([float(item) for item in member_switches]) if member_ids else 0.0
        max_possible = []
        for member_id in member_ids:
            actions = sequences.get(member_id, ())
            max_possible.append(max(0, len(actions) - 1))
        denom = sum(max_possible)
        specialization = 1.0 if denom == 0 else round(1.0 - (total_switches / denom), 10)
        counts: dict[str, int] = {}
        shares: dict[str, float] = {}
        total = 0.0
        for member_id in member_ids:
            role = role_by_id.get(member_id, "unassigned")
            counts[role] = counts.get(role, 0) + 1
            raw = float(scores.get(member_id, 0.0) or 0.0)
            adjusted = max(0.0, raw - resolved.cost * switches.get(member_id, 0))
            shares[role] = round(shares.get(role, 0.0) + adjusted, 10)
            total = round(total + adjusted, 10)
        normalized = tuple(
            (role, round(value / total, 10) if total else 0.0)
            for role, value in sorted(shares.items())
        )
        reweighted = DemeDivisionOfLaborObservation(
            deme_id=str(deme.deme_id),
            role_counts=tuple(sorted(counts.items())),
            fitness_share_by_role=normalized,
            unique_role_count=len(counts),
            literature_gap="task_switching_cost_reweight_not_evolved_division_of_labor",
        )
        baseline = baseline_by_id.get(str(deme.deme_id))
        if baseline is None:
            baseline = DemeDivisionOfLaborObservation(
                deme_id=str(deme.deme_id),
                role_counts=tuple(sorted(counts.items())),
                fitness_share_by_role=normalized,
                unique_role_count=len(counts),
            )
        rows.append(
            TaskSwitchingDoLObservation(
                deme_id=str(deme.deme_id),
                cost=resolved.cost,
                switch_count_total=total_switches,
                mean_switches_per_organism=mean_sw,
                specialization_index=specialization,
                baseline=baseline,
                reweighted=reweighted,
                fitness_share_changed=baseline.fitness_share_by_role
                != reweighted.fitness_share_by_role,
            )
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class CommunicationAblationSeedRecord:
    """One seed: messaging on vs off. Group fitness, not collective intelligence."""

    seed: int
    messaging_on_mean_fitness: float
    messaging_off_mean_fitness: float
    delta: float
    messages_on: int
    messages_off: int

    def __post_init__(self) -> None:
        for name in ("messaging_on_mean_fitness", "messaging_off_mean_fitness", "delta"):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))
        if self.messages_on < 0 or self.messages_off < 0:
            raise ConfigurationError("message counts must be >= 0.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "messaging_on_mean_fitness": self.messaging_on_mean_fitness,
            "messaging_off_mean_fitness": self.messaging_off_mean_fitness,
            "delta": self.delta,
            "messages_on": self.messages_on,
            "messages_off": self.messages_off,
            "collective_intelligence": False,
        }


@dataclass(frozen=True, slots=True)
class CommunicationAblationCampaign:
    """Multi-seed messaging on vs off. Does not set ClaimGate ``ablation_result``."""

    seeds: tuple[int, ...]
    seed_records: tuple[CommunicationAblationSeedRecord, ...]
    mean_delta: float
    cohens_d: float | None
    effect_size_status: str
    communication_ablation_status: str = MEASURED_RUNTIME
    claim_gate_ablation_result_set: bool = False
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "communication_ablation_campaign_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2:
            raise ConfigurationError("CommunicationAblationCampaign requires seed_count >= 2.")
        object.__setattr__(self, "mean_delta", require_finite_float("mean_delta", self.mean_delta))
        if self.cohens_d is not None:
            object.__setattr__(self, "cohens_d", require_finite_float("cohens_d", self.cohens_d))
        if self.claim_gate_ablation_result_set:
            raise ConfigurationError("Phase H must not auto-set ClaimGate ablation_result.")
        if self.claim_ceiling in _FORBIDDEN or self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError(
                "CommunicationAblationCampaign ceiling must stay runtime_observation."
            )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("CommunicationAblationCampaign digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "seeds": list(self.seeds),
            "seed_records": [item.to_dict() for item in self.seed_records],
            "mean_delta": self.mean_delta,
            "cohens_d": self.cohens_d,
            "effect_size_status": self.effect_size_status,
            "communication_ablation_status": self.communication_ablation_status,
            "claim_gate_ablation_result_set": self.claim_gate_ablation_result_set,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "proved_collective_intelligence": False,
            "group_fitness_is_not_collective_intelligence": True,
            "limitations": [
                "messaging_buffer_not_evolved_coordination_instructions",
                "ablation_measurement_does_not_set_claimgate_ablation_result",
                "not_goldsby_literature_scale",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def run_communication_ablation_experiment(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    tick_count: int = 4,
    population: int = 4,
) -> CommunicationAblationCampaign:
    """Messaging on vs off across seeds. Smoke may use seed_count=2; research default 12."""

    seed_tuple = _resolve_seeds(seeds, seed_count, default_count=RESEARCH_SEED_COUNT)
    records: list[CommunicationAblationSeedRecord] = []
    on_fits: list[float] = []
    off_fits: list[float] = []
    for seed in seed_tuple:
        on_result = _run_phase_e(
            seed=seed,
            tick_count=tick_count,
            population=population,
            enable_demes=True,
            enable_roles=True,
            messaging_enabled=True,
        )
        off_result = _run_phase_e(
            seed=seed,
            tick_count=tick_count,
            population=population,
            enable_demes=True,
            enable_roles=True,
            messaging_enabled=False,
        )
        on_fit = _mean_organism_fitness(on_result)
        off_fit = _mean_organism_fitness(off_result)
        on_fits.append(on_fit)
        off_fits.append(off_fit)
        records.append(
            CommunicationAblationSeedRecord(
                seed=seed,
                messaging_on_mean_fitness=on_fit,
                messaging_off_mean_fitness=off_fit,
                delta=round(on_fit - off_fit, 10),
                messages_on=_message_count(on_result),
                messages_off=_message_count(off_result),
            )
        )
    cohens, status = _cohens_d(on_fits, off_fits)
    campaign = CommunicationAblationCampaign(
        seeds=seed_tuple,
        seed_records=tuple(records),
        mean_delta=_mean([item.delta for item in records]),
        cohens_d=cohens,
        effect_size_status=status,
        communication_ablation_status=MEASURED_RUNTIME,
        claim_gate_ablation_result_set=False,
    )
    _assert_ci_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


@dataclass(frozen=True, slots=True)
class GroupVsIndividualEffectSize:
    """Paired deme-on vs organism-only summary with explicit effect-size fields."""

    seeds: tuple[int, ...]
    contrasts: tuple[GroupVsIndividualContrast, ...]
    mean_deme_fitness: float
    mean_organism_fitness: float
    mean_delta: float
    cohens_d: float | None
    effect_size_status: str
    seed_count: int
    research_default_seed_count: int = RESEARCH_SEED_COUNT
    heldout_partner_status: str = GAP_NOT_RUN
    communication_ablation_status: str = GAP_NOT_RUN
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "group_vs_individual_effect_size_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.seed_count < 2 or len(self.seeds) != self.seed_count:
            raise ConfigurationError(
                "GroupVsIndividualEffectSize requires seed_count >= 2 matching seeds."
            )
        for name in ("mean_deme_fitness", "mean_organism_fitness", "mean_delta"):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))
        if self.cohens_d is not None:
            object.__setattr__(self, "cohens_d", require_finite_float("cohens_d", self.cohens_d))
        if self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError(
                "GroupVsIndividualEffectSize ceiling must stay runtime_observation."
            )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("GroupVsIndividualEffectSize digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "seeds": list(self.seeds),
            "seed_count": self.seed_count,
            "research_default_seed_count": self.research_default_seed_count,
            "contrasts": [item.to_dict() for item in self.contrasts],
            "mean_deme_fitness": self.mean_deme_fitness,
            "mean_organism_fitness": self.mean_organism_fitness,
            "mean_delta": self.mean_delta,
            "cohens_d": self.cohens_d,
            "effect_size_status": self.effect_size_status,
            "heldout_partner_status": self.heldout_partner_status,
            "communication_ablation_status": self.communication_ablation_status,
            "claim_ceiling": self.claim_ceiling,
            "group_fitness_is_not_collective_intelligence": True,
            "collective_intelligence": False,
            "major_transition_in_individuality": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def run_group_vs_individual_effect_size_campaign(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    tick_count: int = 4,
    population: int = 4,
    top_k: int = 1,
    task_switching_cost: float = DEFAULT_TASK_SWITCHING_COST,
) -> GroupVsIndividualEffectSize:
    """Group-vs-individual contrast with Cohen's d. Default seed_count=12; smoke uses 2."""

    seed_tuple = _resolve_seeds(seeds, seed_count, default_count=RESEARCH_SEED_COUNT)
    contrasts: list[GroupVsIndividualContrast] = []
    deme_fits: list[float] = []
    org_fits: list[float] = []
    switching = TaskSwitchingCostConfig(cost=task_switching_cost)
    for seed in seed_tuple:
        deme_result = _run_phase_e(
            seed=seed,
            tick_count=tick_count,
            population=population,
            enable_demes=True,
            enable_roles=True,
            messaging_enabled=True,
        )
        organism_result = _run_phase_e(
            seed=seed,
            tick_count=tick_count,
            population=population,
            enable_demes=False,
            enable_roles=False,
            messaging_enabled=None,
            replicate_on_mean_fitness=None,
        )
        pack = build_collective_deme_payoff_pack(deme_result)
        ranks = rank_demes_by_mean_fitness(deme_result, top_k=top_k)
        contrast = build_group_vs_individual_contrast(
            seed=seed,
            deme_result=deme_result,
            organism_result=organism_result,
            pack=pack,
            ranks=ranks,
        )
        contrasts.append(contrast)
        deme_fits.append(contrast.deme_enabled_mean_fitness)
        org_fits.append(contrast.organism_only_mean_fitness)
        apply_task_switching_cost_to_dol(deme_result, config=switching)
    cohens, status = _cohens_d(deme_fits, org_fits)
    effect = GroupVsIndividualEffectSize(
        seeds=seed_tuple,
        contrasts=tuple(contrasts),
        mean_deme_fitness=_mean(deme_fits),
        mean_organism_fitness=_mean(org_fits),
        mean_delta=_mean([item.delta for item in contrasts]),
        cohens_d=cohens,
        effect_size_status=status,
        seed_count=len(seed_tuple),
        research_default_seed_count=RESEARCH_SEED_COUNT,
        heldout_partner_status=GAP_NOT_RUN,
        communication_ablation_status=GAP_NOT_RUN,
    )
    _assert_ci_blocked(effect.to_dict(), ScientificClaimGate())
    return effect


@dataclass(frozen=True, slots=True)
class CollectiveIntelligenceCandidateChecklist:
    """Missing ClaimGate flags for ``collective_intelligence_candidate``.

    Printing this object does **not** set flags and does **not** allow the claim.
    """

    required_flags: tuple[str, ...]
    present_flags: tuple[str, ...]
    missing_flags: tuple[str, ...]
    claim_allowed: bool
    claim_decision: str
    auto_set_flags: bool = False
    literature_gaps: tuple[str, ...] = (
        "heldout_unfamiliar_partner_generalization_not_run",
        "non_capsule_cooperation_not_shown",
        "role_complementarity_not_evolved",
        "communication_must_pay_under_ablation_at_literature_scale",
        "major_transition_in_individuality_false",
    )
    claim_ceiling: str = "collective_intelligence_candidate"
    schema_version: str = "collective_intelligence_candidate_checklist_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.auto_set_flags:
            raise ConfigurationError("checklist must not auto-set ClaimGate flags.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("CollectiveIntelligenceCandidateChecklist digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "required_flags": list(self.required_flags),
            "present_flags": list(self.present_flags),
            "missing_flags": list(self.missing_flags),
            "claim_allowed": self.claim_allowed,
            "claim_decision": self.claim_decision,
            "auto_set_flags": self.auto_set_flags,
            "literature_gaps": list(self.literature_gaps),
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "intelligence": False,
            "note": "checklist_does_not_unlock_collective_intelligence_candidate",
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}

    def lines(self) -> tuple[str, ...]:
        header = (
            "CodonTrace Genesis collective_intelligence_candidate checklist "
            "(does not set flags; ClaimGate stays honest)",
        )
        missing = tuple(f"MISSING  {name}" for name in self.missing_flags)
        present = tuple(f"present  {name}" for name in self.present_flags)
        gaps = tuple(f"literature_gap  {name}" for name in self.literature_gaps)
        footer = (
            f"claim_allowed {self.claim_allowed}",
            f"claim_decision {self.claim_decision}",
            "collective_intelligence False",
            "intelligence False",
        )
        return header + present + missing + gaps + footer

    def render(self) -> str:
        return "\n".join(self.lines())


def collective_intelligence_candidate_checklist(
    evidence_flags: Mapping[str, bool] | None = None,
    *,
    gate: ScientificClaimGate | None = None,
) -> CollectiveIntelligenceCandidateChecklist:
    """List missing ClaimGate flags without writing them."""

    flags = {str(key): bool(value) for key, value in dict(evidence_flags or {}).items()}
    # Never infer flags from a Phase H measurement payload.
    present = tuple(name for name in _CANDIDATE_FLAGS if flags.get(name, False))
    missing = tuple(name for name in _CANDIDATE_FLAGS if not flags.get(name, False))
    resolved = gate or ScientificClaimGate()
    decision = resolved.decide(ClaimRequest("collective_intelligence_candidate", flags))
    blocked = resolved.decide(ClaimRequest("collective_intelligence", flags))
    if blocked.allowed:
        raise ConfigurationError("collective_intelligence must remain blocked.")
    intelligence = resolved.decide(ClaimRequest("intelligence", flags))
    if intelligence.allowed:
        raise ConfigurationError("intelligence must remain blocked.")
    return CollectiveIntelligenceCandidateChecklist(
        required_flags=_CANDIDATE_FLAGS,
        present_flags=present,
        missing_flags=missing,
        claim_allowed=decision.allowed,
        claim_decision=decision.decision,
        auto_set_flags=False,
    )


def format_collective_intelligence_candidate_checklist(
    evidence_flags: Mapping[str, bool] | None = None,
) -> str:
    return collective_intelligence_candidate_checklist(evidence_flags).render()


def print_collective_intelligence_candidate_checklist(
    evidence_flags: Mapping[str, bool] | None = None,
) -> CollectiveIntelligenceCandidateChecklist:
    """Return the checklist. Does not set ClaimGate flags.

    Core must not call ``print`` (library-as-tool). Examples and CLIs may
    print ``checklist.render()`` or ``format_collective_intelligence_candidate_checklist()``.
    """

    return collective_intelligence_candidate_checklist(evidence_flags)


def evaluate_phase_h_claim(payload: Mapping[str, JsonValue] | object) -> ClaimDecision:
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
        ClaimRequest(_CLAIM_CEILING, {}, evidence_digests=(digest,) if digest else ())
    )
    _assert_ci_blocked(data, gate)
    return decision
