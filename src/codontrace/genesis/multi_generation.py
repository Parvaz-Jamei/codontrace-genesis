"""Phase D multi-generation instinct/behavior evidence metrics.

This module is a first-class library measurement layer. It reads already-executed
life-loop (and optional sexual / dynamic-environment) runtime records and
exports digest-backed trajectories. It does **not** change Phase A/B/C default
physics, presets, or replay digests.

Literature grounding (measurement design only — not proof of OEE or intelligence):

- MODES toolbox: Dolson, Vostinar, Wiser, Ofria 2019 *Artificial Life* —
  change, novelty, complexity, ecological potential, with a persistence filter
  so only lineages that still have descendants after ``persistence_window_t``
  generations count. The filter is an organism-id descendant graph over a
  coalescence window, not a full Empirical systematics / shadow phylogeny.
- Bedau evolutionary activity statistics: novelty, diversity, and (cumulative)
  activity of components over time.
- ALife OEE encyclopedia hallmarks and the ISAL 2024 MODES assessment
  (Bohm / Zhang / Dolson) as the reporting checklist this pack cites.

User philosophy encoded here: survivors reproduce; next-generation
instincts/behavior may improve. This library **measures** fitness and
behavior trajectories. It does not claim open-ended evolution, AGI, or
instinct evolution proved.

Claim ceiling: ``runtime_observation`` by default. ``instinct_improved`` is a
ClaimGate label for metric deltas only and is never publication-grade without
multi-seed protocol objects. ``oee_measurement_only`` is the OEE ceiling;
``tokyo_type1_measurement_only`` is a Channon 2024 vocabulary alias of that
ceiling (Type 1 is never passed). Open-ended intelligence remains blocked.
CLIP / ASAL foundation-model OE is not implemented here.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.claim_gate import (
    TOKYO_TYPE1_MEASUREMENT_CLAIM,
    ClaimDecision,
    ClaimRequest,
    ScientificClaimGate,
)
from codontrace.genesis.statistical_protocol import (
    EffectSizeResult,
    OEEMetricsReport,
    StatisticalProtocolConfig,
    build_oee_metrics_report,
    estimate_effect_size_lite,
)

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "modes_dolson_2019",
        "Dolson, Vostinar, Wiser, Ofria 2019 Artificial Life: MODES toolbox "
        "(change, novelty, complexity, ecological potential) plus persistence "
        "filter on lineages with descendants after persistence_window_t "
        "generations (coalescence-window organism-id graph, not Empirical "
        "systematics).",
    ),
    (
        "bedau_evolutionary_activity",
        "Bedau evolutionary activity statistics: novelty (first appearances), "
        "diversity (currently present components), and cumulative activity.",
    ),
    (
        "alife_oee_encyclopedia_hallmarks",
        "ALife open-ended evolution encyclopedia hallmarks used as a "
        "descriptive checklist (ongoing novelty/complexity/activity), never as proof.",
    ),
    (
        "isal_2024_modes_assessment",
        "ISAL 2024 MODES assessment (Bohm, Zhang, Dolson): report the four "
        "MODES axes with persistence filtering; this pack cites that assessment "
        "protocol rather than claiming a bit-identical C++ toolbox port.",
    ),
    (
        "codontrace_survivor_philosophy",
        "Survivors reproduce; next-gen instincts/behavior may improve — measure "
        "fitness/behavior trajectories without claiming OEE or intelligence proved.",
    ),
)

_PHASE_D_CLAIM_CEILING = "runtime_observation"
_MAX_CANDIDATE_CEILING = "candidate_evidence"
_PACK_SCHEMA = "multi_generation_evidence_pack_v1"
MODES_PERSISTENCE_LIMITATIONS: tuple[str, ...] = (
    "coalescence_window_organism_id_graph_not_full_phylogeny",
    "no_empirical_systematics_shadow_run",
    "self_survival_counts_as_lineage_continuation",
    "window_longer_than_mrca_filters_more_historical_types",
    "not_a_bit_identical_modes_cpp_port",
)
_FORBIDDEN_PACK_CLAIMS = frozenset(
    {
        "proved_open_endedness",
        "open_ended_intelligence",
        "instinct_evolution_proved",
        "proved_instinct_evolution",
        "agi",
        "collective_intelligence",
    }
)


@dataclass(frozen=True, slots=True)
class MultiGenerationEvidenceConfig:
    """Opt-in measurement knobs. Defaults keep analysis cheap and honest."""

    persistence_window_generations: int = 2
    ancestor_generation: int = 0
    descendant_generation: int | None = None
    component_kind: str = "genotype"
    paired_seed_reevaluation: bool = False
    reevaluation_tick_count: int = 4
    include_modes: bool = True
    include_bedau: bool = True
    include_oee_scaffold: bool = True
    claim_ceiling: str = _PHASE_D_CLAIM_CEILING

    def __post_init__(self) -> None:
        if self.persistence_window_generations < 1:
            raise ConfigurationError("persistence_window_generations must be >= 1.")
        if self.ancestor_generation < 0:
            raise ConfigurationError("ancestor_generation must be >= 0.")
        if self.component_kind not in {"genotype", "behavior", "genotype_and_behavior"}:
            raise ConfigurationError(
                "component_kind must be genotype, behavior, or genotype_and_behavior."
            )
        if self.reevaluation_tick_count < 1:
            raise ConfigurationError("reevaluation_tick_count must be >= 1.")
        if self.claim_ceiling not in {_PHASE_D_CLAIM_CEILING, _MAX_CANDIDATE_CEILING}:
            raise ConfigurationError(
                "MultiGenerationEvidenceConfig.claim_ceiling must stay at "
                "runtime_observation or candidate_evidence."
            )
        if self.claim_ceiling in _FORBIDDEN_PACK_CLAIMS:
            raise ConfigurationError("Phase D config must never request a blocked proof claim.")

    @property
    def persistence_window_t(self) -> int:
        """Explicit MODES persistence / coalescence window (generations)."""

        return self.persistence_window_generations

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "persistence_window_generations": self.persistence_window_generations,
            "ancestor_generation": self.ancestor_generation,
            "descendant_generation": self.descendant_generation,
            "component_kind": self.component_kind,
            "paired_seed_reevaluation": self.paired_seed_reevaluation,
            "reevaluation_tick_count": self.reevaluation_tick_count,
            "include_modes": self.include_modes,
            "include_bedau": self.include_bedau,
            "include_oee_scaffold": self.include_oee_scaffold,
            "claim_ceiling": self.claim_ceiling,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class OrganismCensusRecord:
    """One organism's measured state at one generation (descriptive)."""

    organism_id: str
    generation: int
    genome_digest: str
    genome_bits: str
    parent_id: str | None
    second_parent_id: str | None
    fitness: float
    selection_fitness: float
    runtime_atp: float
    lumen_eaten: int
    action_counts: tuple[tuple[str, int], ...]
    role_signature: str
    unique_positions: int
    behavior_key: str

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "generation": self.generation,
            "genome_digest": self.genome_digest,
            "genome_bits": self.genome_bits,
            "parent_id": self.parent_id,
            "second_parent_id": self.second_parent_id,
            "fitness": self.fitness,
            "selection_fitness": self.selection_fitness,
            "runtime_atp": self.runtime_atp,
            "lumen_eaten": self.lumen_eaten,
            "action_counts": [[name, count] for name, count in self.action_counts],
            "role_signature": self.role_signature,
            "unique_positions": self.unique_positions,
            "behavior_key": self.behavior_key,
        }

    def component_key(self, kind: str) -> str:
        if kind == "behavior":
            return self.behavior_key
        if kind == "genotype_and_behavior":
            return f"{self.genome_digest}:{self.behavior_key}"
        return self.genome_digest


@dataclass(frozen=True, slots=True)
class GenerationCensus:
    """Per-generation snapshot used by all Phase D metric surfaces."""

    generation: int
    mean_fitness: float
    max_fitness: float
    selection_mean_fitness: float
    selection_max_fitness: float
    survival_count: int
    births: int
    deaths: int
    mean_runtime_atp: float
    resource_intake: int
    organisms: tuple[OrganismCensusRecord, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "generation": self.generation,
            "mean_fitness": self.mean_fitness,
            "max_fitness": self.max_fitness,
            "selection_mean_fitness": self.selection_mean_fitness,
            "selection_max_fitness": self.selection_max_fitness,
            "survival_count": self.survival_count,
            "births": self.births,
            "deaths": self.deaths,
            "mean_runtime_atp": self.mean_runtime_atp,
            "resource_intake": self.resource_intake,
            "organisms": [item.to_dict() for item in self.organisms],
        }


@dataclass(frozen=True, slots=True)
class GenerationFitnessPoint:
    """One generation of fitness / survival / ATP / intake statistics."""

    generation: int
    mean_fitness: float
    max_fitness: float
    selection_mean_fitness: float
    selection_max_fitness: float
    survival_count: int
    births: int
    deaths: int
    mean_runtime_atp: float
    resource_intake: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "generation": self.generation,
            "mean_fitness": self.mean_fitness,
            "max_fitness": self.max_fitness,
            "selection_mean_fitness": self.selection_mean_fitness,
            "selection_max_fitness": self.selection_max_fitness,
            "survival_count": self.survival_count,
            "births": self.births,
            "deaths": self.deaths,
            "mean_runtime_atp": self.mean_runtime_atp,
            "resource_intake": self.resource_intake,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class FitnessTrajectory:
    """Digest-backed per-generation fitness series."""

    points: tuple[GenerationFitnessPoint, ...]
    run_digest: str
    seed: int | None
    schema_version: str = "fitness_trajectory_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "run_digest": self.run_digest,
            "seed": self.seed,
            "points": [item.to_dict() for item in self.points],
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class GenerationBehaviorSummary:
    """Genome→action phenotype aggregates for one generation."""

    generation: int
    unique_genotypes: int
    unique_behaviors: int
    mean_lumen_eaten: float
    mean_unique_actions: float
    dominant_role_signature: str
    eater_like_count: int
    waiter_like_count: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "generation": self.generation,
            "unique_genotypes": self.unique_genotypes,
            "unique_behaviors": self.unique_behaviors,
            "mean_lumen_eaten": self.mean_lumen_eaten,
            "mean_unique_actions": self.mean_unique_actions,
            "dominant_role_signature": self.dominant_role_signature,
            "eater_like_count": self.eater_like_count,
            "waiter_like_count": self.waiter_like_count,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class InstinctBehaviorTrajectory:
    """Descriptive phenotype trajectory. Not an instinct-evolution proof."""

    summaries: tuple[GenerationBehaviorSummary, ...]
    schema_version: str = "instinct_behavior_trajectory_v1"
    claim_ceiling: str = _PHASE_D_CLAIM_CEILING

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "claim_ceiling": self.claim_ceiling,
            "summaries": [item.to_dict() for item in self.summaries],
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CohortComparison:
    """Ancestor vs descendant cohort on the same environment seed.

    A positive fitness_delta is a runtime observation of a metric delta.
    It is not publication-grade instinct improvement and not OEE.
    """

    ancestor_generation: int
    descendant_generation: int
    env_seed: int | None
    comparison_kind: str
    ancestor_mean_fitness: float
    descendant_mean_fitness: float
    fitness_delta: float
    ancestor_mean_intake: float
    descendant_mean_intake: float
    intake_delta: float
    ancestor_count: int
    descendant_count: int
    descendant_outperforms_ancestors: bool
    effect_size: EffectSizeResult | None = None
    claim_ceiling: str = _PHASE_D_CLAIM_CEILING
    schema_version: str = "cohort_comparison_v1"

    def __post_init__(self) -> None:
        if self.claim_ceiling not in {_PHASE_D_CLAIM_CEILING, _MAX_CANDIDATE_CEILING}:
            raise ConfigurationError("CohortComparison claim_ceiling is too strong.")
        if self.comparison_kind not in {"same_run", "paired_seed_reeval"}:
            raise ConfigurationError("comparison_kind must be same_run or paired_seed_reeval.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "ancestor_generation": self.ancestor_generation,
            "descendant_generation": self.descendant_generation,
            "env_seed": self.env_seed,
            "comparison_kind": self.comparison_kind,
            "ancestor_mean_fitness": self.ancestor_mean_fitness,
            "descendant_mean_fitness": self.descendant_mean_fitness,
            "fitness_delta": self.fitness_delta,
            "ancestor_mean_intake": self.ancestor_mean_intake,
            "descendant_mean_intake": self.descendant_mean_intake,
            "intake_delta": self.intake_delta,
            "ancestor_count": self.ancestor_count,
            "descendant_count": self.descendant_count,
            "descendant_outperforms_ancestors": self.descendant_outperforms_ancestors,
            "effect_size": None if self.effect_size is None else self.effect_size.to_dict(),
            "claim_ceiling": self.claim_ceiling,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class InstinctAblationControl:
    """Treatment vs control hook (e.g. mutation off). Not causal proof."""

    control_kind: str
    treatment_fitness_delta: float
    control_fitness_delta: float
    treatment_exceeds_control: bool
    treatment_run_digest: str
    control_run_digest: str
    claim_ceiling: str = _PHASE_D_CLAIM_CEILING
    schema_version: str = "instinct_ablation_control_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "control_kind": self.control_kind,
            "treatment_fitness_delta": self.treatment_fitness_delta,
            "control_fitness_delta": self.control_fitness_delta,
            "treatment_exceeds_control": self.treatment_exceeds_control,
            "treatment_run_digest": self.treatment_run_digest,
            "control_run_digest": self.control_run_digest,
            "claim_ceiling": self.claim_ceiling,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class PersistentLineageFilter:
    """MODES-inspired persistence window: descendants still alive after t.

    This is a coalescence-window organism-id descendant graph, not a full
    Empirical phylogenetic systematics / shadow run. An ancestor persists if
    it or any descendant is alive at ``generation + persistence_window_t``.
    Self-survival counts as lineage continuation.
    """

    window_t: int
    generation: int
    horizon_generation: int
    persistent_organism_ids: tuple[str, ...]
    persistent_component_keys: tuple[str, ...]
    alive_at_generation: int
    alive_at_horizon: int
    schema_version: str = "persistent_lineage_filter_v1"
    empirical_systematics_shadow_run: bool = False
    coalescence_window_semantics: str = "organism_id_descendant_graph_at_generation_plus_t"
    self_survival_counts_as_lineage_continuation: bool = True
    horizon_observed: bool = True

    @property
    def persistence_window_t(self) -> int:
        return self.window_t

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "window_t": self.window_t,
            "persistence_window_t": self.window_t,
            "generation": self.generation,
            "horizon_generation": self.horizon_generation,
            "persistent_organism_ids": list(self.persistent_organism_ids),
            "persistent_component_keys": list(self.persistent_component_keys),
            "alive_at_generation": self.alive_at_generation,
            "alive_at_horizon": self.alive_at_horizon,
            "empirical_systematics_shadow_run": False,
            "coalescence_window_semantics": self.coalescence_window_semantics,
            "self_survival_counts_as_lineage_continuation": (
                self.self_survival_counts_as_lineage_continuation
            ),
            "horizon_observed": self.horizon_observed,
            "limitations": list(MODES_PERSISTENCE_LIMITATIONS),
            "oee_proved": False,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ModesMetricPoint:
    """One generation of persistence-filtered MODES-style axes."""

    generation: int
    change: float
    novelty: float
    complexity: float
    ecological_potential: float
    persistent_count: int
    persistent_type_count: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "generation": self.generation,
            "change": self.change,
            "novelty": self.novelty,
            "complexity": self.complexity,
            "ecological_potential": self.ecological_potential,
            "persistent_count": self.persistent_count,
            "persistent_type_count": self.persistent_type_count,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ModesAssessment:
    """MODES-inspired assessment object. Descriptive; not a C++ toolbox clone."""

    points: tuple[ModesMetricPoint, ...]
    persistence_window_generations: int
    literature_refs: tuple[str, ...]
    claim_ceiling: str = _PHASE_D_CLAIM_CEILING
    schema_version: str = "modes_assessment_v1"

    @property
    def persistence_window_t(self) -> int:
        return self.persistence_window_generations

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "persistence_window_generations": self.persistence_window_generations,
            "literature_refs": list(self.literature_refs),
            "claim_ceiling": self.claim_ceiling,
            "points": [item.to_dict() for item in self.points],
            "oee_proved": False,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class BedauActivityPoint:
    """Bedau-style novelty / diversity / activity at one time."""

    time: int
    novelty: int
    diversity: int
    activity: int
    cumulative_activity: int
    new_activity: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "time": self.time,
            "novelty": self.novelty,
            "diversity": self.diversity,
            "activity": self.activity,
            "cumulative_activity": self.cumulative_activity,
            "new_activity": self.new_activity,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class BedauActivitySurface:
    """Time series of Bedau activity statistics from genotype/behavior presence."""

    points: tuple[BedauActivityPoint, ...]
    component_kind: str
    persistence_filtered: bool
    literature_refs: tuple[str, ...]
    claim_ceiling: str = _PHASE_D_CLAIM_CEILING
    schema_version: str = "bedau_activity_surface_v1"

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "component_kind": self.component_kind,
            "persistence_filtered": self.persistence_filtered,
            "literature_refs": list(self.literature_refs),
            "claim_ceiling": self.claim_ceiling,
            "points": [item.to_dict() for item in self.points],
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class OEEHallmarkObservation:
    """ALife OEE encyclopedia hallmarks as observed metric flags, not proof."""

    ongoing_novelty_metric: bool
    ongoing_complexity_metric: bool
    ongoing_activity_metric: bool
    persistence_filter_applied: bool
    claim_ceiling: str = _PHASE_D_CLAIM_CEILING
    oee_proved: bool = False
    schema_version: str = "oee_hallmark_observation_v1"

    def __post_init__(self) -> None:
        if self.oee_proved:
            raise ConfigurationError("OEEHallmarkObservation must never set oee_proved.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "ongoing_novelty_metric": self.ongoing_novelty_metric,
            "ongoing_complexity_metric": self.ongoing_complexity_metric,
            "ongoing_activity_metric": self.ongoing_activity_metric,
            "persistence_filter_applied": self.persistence_filter_applied,
            "claim_ceiling": self.claim_ceiling,
            "oee_proved": False,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MultiGenerationEvidencePack:
    """First-class Python export of Phase D metrics (JSON + digest).

    Stretch vs typical Avida post-hoc analyze-mode workflows: callers get a
    library object with ``to_dict`` / ``to_json`` / ``digest`` rather than only
    an external analysis dump. This still does not prove OEE or intelligence.
    """

    fitness_trajectory: FitnessTrajectory
    instinct_trajectory: InstinctBehaviorTrajectory
    cohort_comparison: CohortComparison | None
    modes_assessment: ModesAssessment | None
    bedau_surface: BedauActivitySurface | None
    oee_metrics_report: OEEMetricsReport | None
    hallmark_observation: OEEHallmarkObservation | None
    ablation_control: InstinctAblationControl | None
    config: MultiGenerationEvidenceConfig
    run_digest: str
    seed: int | None
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    multi_seed_protocol: StatisticalProtocolConfig | None = None
    instinct_improved_status: str = "runtime_observation"
    claim_ceiling: str = _PHASE_D_CLAIM_CEILING
    schema_version: str = _PACK_SCHEMA
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_ceiling not in {_PHASE_D_CLAIM_CEILING, _MAX_CANDIDATE_CEILING}:
            raise ConfigurationError("MultiGenerationEvidencePack claim_ceiling is too strong.")
        if (
            self.claim_ceiling in _FORBIDDEN_PACK_CLAIMS
            or self.instinct_improved_status in _FORBIDDEN_PACK_CLAIMS
        ):
            raise ConfigurationError(
                "MultiGenerationEvidencePack must never claim OEE/intelligence proved."
            )
        if (
            self.oee_metrics_report is not None
            and self.oee_metrics_report.claim_level == "proved_open_endedness"
        ):
            raise ConfigurationError("OEEMetricsReport must never claim proof of open-endedness.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("MultiGenerationEvidencePack digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "run_digest": self.run_digest,
            "seed": self.seed,
            "claim_ceiling": self.claim_ceiling,
            "instinct_improved_status": self.instinct_improved_status,
            "config": self.config.to_dict(),
            "fitness_trajectory": self.fitness_trajectory.to_dict(),
            "instinct_trajectory": self.instinct_trajectory.to_dict(),
            "cohort_comparison": None
            if self.cohort_comparison is None
            else self.cohort_comparison.to_dict(),
            "modes_assessment": None
            if self.modes_assessment is None
            else self.modes_assessment.to_dict(),
            "bedau_surface": None if self.bedau_surface is None else self.bedau_surface.to_dict(),
            "oee_metrics_report": None
            if self.oee_metrics_report is None
            else self.oee_metrics_report.to_dict(),
            "hallmark_observation": None
            if self.hallmark_observation is None
            else self.hallmark_observation.to_dict(),
            "ablation_control": None
            if self.ablation_control is None
            else self.ablation_control.to_dict(),
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "multi_seed_protocol": None
            if self.multi_seed_protocol is None
            else self.multi_seed_protocol.to_dict(),
            "oee_proved": False,
            "open_ended_intelligence": False,
            "instinct_evolution_proved": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}

    def to_json(self) -> str:
        """Return canonical JSON for library export (does not write files)."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def export_json(self) -> str:
        return self.to_json()


def export_multi_generation_evidence_pack(
    pack: MultiGenerationEvidencePack,
) -> dict[str, JsonValue]:
    """Return a JSON-ready dict with digest. Callers may write it; the library does not."""

    return pack.to_dict()


def censuses_from_run(result: object) -> tuple[GenerationCensus, ...]:
    """Extract per-generation census records from a ``GenesisRunResult``."""

    ticks = getattr(result, "ticks", ())
    parent_by_id: dict[str, tuple[str | None, str | None]] = {}
    censuses: list[GenerationCensus] = []
    for tick in ticks:
        generation_result = getattr(tick, "generation_result", None)
        if generation_result is None:
            continue
        generation = int(getattr(tick, "index", len(censuses)))
        population = getattr(generation_result, "population", None)
        lineage_records = () if population is None else getattr(population, "lineage", ())
        for lineage in lineage_records:
            organism_id = str(getattr(lineage, "organism_id", "") or "")
            if not organism_id:
                continue
            parent_by_id[organism_id] = (
                getattr(lineage, "parent_id", None),
                getattr(lineage, "second_parent_id", None),
            )
        traces_by_agent: dict[str, object] = {}
        for trace in getattr(generation_result, "traces", ()):
            events = getattr(trace, "events", ())
            agent_id = ""
            if events:
                agent_id = str(getattr(events[0], "agent_id", "") or "")
            if agent_id:
                traces_by_agent[agent_id] = trace
        organisms: list[OrganismCensusRecord] = []
        atp_values: list[float] = []
        intake_total = 0
        live_ids = {
            str(organism.id)
            for organism in (getattr(population, "organisms", ()) if population is not None else ())
        }
        bits_by_id = {
            str(organism.id): organism.genome.to_compact()
            for organism in (getattr(population, "organisms", ()) if population is not None else ())
        }
        digest_by_id = {
            str(organism.id): organism.genome.digest()
            for organism in (getattr(population, "organisms", ()) if population is not None else ())
        }
        for record in getattr(generation_result, "organism_records", ()):
            organism_id = str(getattr(record, "organism_id", "") or "")
            if organism_id not in live_ids:
                continue
            fitness_result = getattr(record, "fitness_result", None)
            fitness = float(getattr(fitness_result, "score", 0.0) or 0.0)
            selection = getattr(record, "selection_fitness_score", None)
            if selection is None and fitness_result is not None:
                selection = getattr(fitness_result, "selection_fitness_score", None)
            selection_fitness = float(getattr(selection, "selection_score", fitness) or fitness)
            runtime_atp = float(getattr(record, "runtime_atp_after", 0.0) or 0.0)
            lumen_eaten = int(getattr(fitness_result, "lumen_eaten", 0) or 0)
            descriptor = getattr(record, "behavior_descriptor", None)
            role = str(getattr(descriptor, "role_signature", "unknown") or "unknown")
            unique_positions = int(getattr(descriptor, "unique_positions", 0) or 0)
            action_counts = _action_counts(traces_by_agent.get(organism_id))
            behavior_key = _behavior_key(role, action_counts, lumen_eaten)
            parent_id, second_parent_id = parent_by_id.get(organism_id, (None, None))
            atp_values.append(runtime_atp)
            intake_total += lumen_eaten
            organisms.append(
                OrganismCensusRecord(
                    organism_id=organism_id,
                    generation=generation,
                    genome_digest=digest_by_id.get(
                        organism_id, str(getattr(record, "genome_digest", "") or "")
                    ),
                    genome_bits=bits_by_id.get(organism_id, ""),
                    parent_id=None if parent_id is None else str(parent_id),
                    second_parent_id=None if second_parent_id is None else str(second_parent_id),
                    fitness=round(require_finite_float("fitness", fitness), 10),
                    selection_fitness=round(
                        require_finite_float("selection_fitness", selection_fitness), 10
                    ),
                    runtime_atp=round(
                        require_finite_float("runtime_atp", runtime_atp, non_negative=True), 10
                    ),
                    lumen_eaten=lumen_eaten,
                    action_counts=action_counts,
                    role_signature=role,
                    unique_positions=unique_positions,
                    behavior_key=behavior_key,
                )
            )
        recorded_ids = {item.organism_id for item in organisms}
        fitness_by_id = {
            str(getattr(item, "organism_id", "") or ""): item
            for item in (getattr(population, "fitness", ()) if population is not None else ())
        }
        live_organisms = getattr(population, "organisms", ()) if population is not None else ()
        for organism in live_organisms:
            organism_id = str(organism.id)
            if organism_id in recorded_ids:
                continue
            fit = fitness_by_id.get(organism_id)
            fitness = float(getattr(fit, "score", 0.0) or 0.0)
            selection = getattr(fit, "selection_fitness_score", None)
            selection_fitness = float(getattr(selection, "selection_score", fitness) or fitness)
            runtime_atp = float(organism.atp_state.runtime_available)
            lumen_eaten = int(getattr(fit, "lumen_eaten", 0) or 0)
            parent_id, second_parent_id = parent_by_id.get(organism_id, (None, None))
            action_counts = _action_counts(traces_by_agent.get(organism_id))
            role = "unknown"
            atp_values.append(runtime_atp)
            intake_total += lumen_eaten
            organisms.append(
                OrganismCensusRecord(
                    organism_id=organism_id,
                    generation=generation,
                    genome_digest=digest_by_id.get(organism_id, organism.genome.digest()),
                    genome_bits=bits_by_id.get(organism_id, organism.genome.to_compact()),
                    parent_id=None if parent_id is None else str(parent_id),
                    second_parent_id=None if second_parent_id is None else str(second_parent_id),
                    fitness=round(require_finite_float("fitness", fitness), 10),
                    selection_fitness=round(
                        require_finite_float("selection_fitness", selection_fitness), 10
                    ),
                    runtime_atp=round(
                        require_finite_float("runtime_atp", runtime_atp, non_negative=True), 10
                    ),
                    lumen_eaten=lumen_eaten,
                    action_counts=action_counts,
                    role_signature=role,
                    unique_positions=0,
                    behavior_key=_behavior_key(role, action_counts, lumen_eaten),
                )
            )
        mean_atp = round(sum(atp_values) / len(atp_values), 10) if atp_values else 0.0
        censuses.append(
            GenerationCensus(
                generation=generation,
                mean_fitness=round(
                    float(getattr(generation_result, "mean_fitness", 0.0) or 0.0), 10
                ),
                max_fitness=round(
                    float(getattr(generation_result, "best_fitness", 0.0) or 0.0), 10
                ),
                selection_mean_fitness=round(
                    float(getattr(generation_result, "selection_mean_fitness", 0.0) or 0.0), 10
                ),
                selection_max_fitness=round(
                    float(getattr(generation_result, "selection_best_fitness", 0.0) or 0.0), 10
                ),
                survival_count=int(getattr(generation_result, "after_count", len(organisms)) or 0),
                births=int(getattr(generation_result, "births", 0) or 0),
                deaths=int(getattr(generation_result, "deaths", 0) or 0),
                mean_runtime_atp=mean_atp,
                resource_intake=intake_total,
                organisms=tuple(organisms),
            )
        )
    return tuple(censuses)


def build_fitness_trajectory(
    censuses: Sequence[GenerationCensus],
    *,
    run_digest: str = "",
    seed: int | None = None,
) -> FitnessTrajectory:
    points = tuple(
        GenerationFitnessPoint(
            generation=item.generation,
            mean_fitness=item.mean_fitness,
            max_fitness=item.max_fitness,
            selection_mean_fitness=item.selection_mean_fitness,
            selection_max_fitness=item.selection_max_fitness,
            survival_count=item.survival_count,
            births=item.births,
            deaths=item.deaths,
            mean_runtime_atp=item.mean_runtime_atp,
            resource_intake=item.resource_intake,
        )
        for item in censuses
    )
    return FitnessTrajectory(points=points, run_digest=run_digest, seed=seed)


def build_instinct_behavior_trajectory(
    censuses: Sequence[GenerationCensus],
) -> InstinctBehaviorTrajectory:
    summaries: list[GenerationBehaviorSummary] = []
    for census in censuses:
        genotypes = {item.genome_digest for item in census.organisms}
        behaviors = {item.behavior_key for item in census.organisms}
        roles = Counter(item.role_signature for item in census.organisms)
        dominant = roles.most_common(1)[0][0] if roles else "unknown"
        mean_eat = (
            sum(item.lumen_eaten for item in census.organisms) / len(census.organisms)
            if census.organisms
            else 0.0
        )
        mean_actions = (
            sum(len(item.action_counts) for item in census.organisms) / len(census.organisms)
            if census.organisms
            else 0.0
        )
        summaries.append(
            GenerationBehaviorSummary(
                generation=census.generation,
                unique_genotypes=len(genotypes),
                unique_behaviors=len(behaviors),
                mean_lumen_eaten=round(mean_eat, 10),
                mean_unique_actions=round(mean_actions, 10),
                dominant_role_signature=dominant,
                eater_like_count=sum(
                    1 for item in census.organisms if item.genome_bits.startswith("101")
                ),
                waiter_like_count=sum(
                    1 for item in census.organisms if item.genome_bits.startswith("000")
                ),
            )
        )
    return InstinctBehaviorTrajectory(summaries=tuple(summaries))


def build_children_map(censuses: Sequence[GenerationCensus]) -> dict[str, tuple[str, ...]]:
    children: dict[str, list[str]] = defaultdict(list)
    for census in censuses:
        for organism in census.organisms:
            if organism.parent_id:
                children[organism.parent_id].append(organism.organism_id)
            if organism.second_parent_id:
                children[organism.second_parent_id].append(organism.organism_id)
    return {key: tuple(dict.fromkeys(values)) for key, values in children.items()}


def describe_modes_persistence_semantics() -> dict[str, JsonValue]:
    """Return the coalescence-window contract for the Phase D persistence filter.

    This is documentation/measurement design, not a claim that Empirical
    systematics or open-endedness has been run.
    """

    return {
        "persistence_window_t_alias_of": "persistence_window_generations",
        "coalescence_window_semantics": "organism_id_descendant_graph_at_generation_plus_t",
        "self_survival_counts_as_lineage_continuation": True,
        "empirical_systematics_shadow_run": False,
        "limitations": list(MODES_PERSISTENCE_LIMITATIONS),
        "oee_proved": False,
        "literature_refs": ["modes_dolson_2019", "empirical_systematics_persistence_filter_notes"],
    }


def filter_persistent_lineages(
    censuses: Sequence[GenerationCensus],
    *,
    generation: int,
    window_t: int | None = None,
    persistence_window_t: int | None = None,
    component_kind: str = "genotype",
) -> PersistentLineageFilter:
    """Return organisms at ``generation`` that still have descendants at ``generation+t``.

    ``persistence_window_t`` is the explicit coalescence-window alias of
    ``window_t``. The horizon census must exist; otherwise no lineage is
    counted as persistent (the window was not observed). This is not a full
    Empirical phylogenetic systematics / shadow run.
    """

    if window_t is None and persistence_window_t is None:
        raise ConfigurationError(
            "filter_persistent_lineages requires window_t or persistence_window_t."
        )
    if (
        window_t is not None
        and persistence_window_t is not None
        and window_t != persistence_window_t
    ):
        raise ConfigurationError(
            "window_t and persistence_window_t must match when both are provided."
        )
    resolved_t = persistence_window_t if persistence_window_t is not None else window_t
    if resolved_t is None or resolved_t < 1:
        raise ConfigurationError("persistence_window_t must be >= 1.")
    by_gen = {item.generation: item for item in censuses}
    horizon = generation + resolved_t
    current = by_gen.get(generation)
    future = by_gen.get(horizon)
    if current is None or future is None:
        return PersistentLineageFilter(
            window_t=resolved_t,
            generation=generation,
            horizon_generation=horizon,
            persistent_organism_ids=(),
            persistent_component_keys=(),
            alive_at_generation=0 if current is None else len(current.organisms),
            alive_at_horizon=0 if future is None else len(future.organisms),
            horizon_observed=False,
        )
    children = build_children_map(censuses)
    alive_horizon = {item.organism_id for item in future.organisms}
    persistent: list[str] = []
    keys: list[str] = []
    for organism in current.organisms:
        if _has_living_descendant(organism.organism_id, children, alive_horizon):
            persistent.append(organism.organism_id)
            keys.append(organism.component_key(component_kind))
    return PersistentLineageFilter(
        window_t=resolved_t,
        generation=generation,
        horizon_generation=horizon,
        persistent_organism_ids=tuple(persistent),
        persistent_component_keys=tuple(dict.fromkeys(keys)),
        alive_at_generation=len(current.organisms),
        alive_at_horizon=len(future.organisms),
        horizon_observed=True,
    )


def build_modes_assessment(
    censuses: Sequence[GenerationCensus],
    config: MultiGenerationEvidenceConfig,
) -> ModesAssessment:
    """Persistence-filtered change/novelty/complexity/ecological-potential series."""

    window = config.persistence_window_generations
    kind = config.component_kind
    points: list[ModesMetricPoint] = []
    previous_keys: set[str] = set()
    seen_keys: set[str] = set()
    generations = {item.generation for item in censuses}
    for census in censuses:
        if census.generation + window not in generations:
            continue
        filt = filter_persistent_lineages(
            censuses, generation=census.generation, window_t=window, component_kind=kind
        )
        current = {item.organism_id: item for item in census.organisms}
        persistent_orgs = [current[oid] for oid in filt.persistent_organism_ids if oid in current]
        keys = [item.component_key(kind) for item in persistent_orgs]
        key_set = set(keys)
        change = _jaccard_distance(previous_keys, key_set) if previous_keys or key_set else 0.0
        novelty = float(len(key_set - seen_keys))
        complexity = _shannon(Counter(keys))
        niches = {
            (item.role_signature, item.lumen_eaten > 0, item.unique_positions > 1)
            for item in persistent_orgs
        }
        ecological = float(len(niches))
        points.append(
            ModesMetricPoint(
                generation=census.generation,
                change=round(change, 10),
                novelty=round(novelty, 10),
                complexity=round(complexity, 10),
                ecological_potential=round(ecological, 10),
                persistent_count=len(persistent_orgs),
                persistent_type_count=len(key_set),
            )
        )
        previous_keys = key_set
        seen_keys.update(key_set)
    return ModesAssessment(
        points=tuple(points),
        persistence_window_generations=window,
        literature_refs=(
            "modes_dolson_2019",
            "isal_2024_modes_assessment",
            "empirical_systematics_persistence_filter_notes",
        ),
    )


def build_bedau_activity_surface(
    censuses: Sequence[GenerationCensus],
    config: MultiGenerationEvidenceConfig,
    *,
    persistence_filtered: bool = True,
) -> BedauActivitySurface:
    """Bedau novelty / diversity / activity from component presence over time."""

    kind = config.component_kind
    window = config.persistence_window_generations
    generations = {item.generation for item in censuses}
    introduced: dict[str, int] = {}
    points: list[BedauActivityPoint] = []
    cumulative = 0
    for census in censuses:
        if persistence_filtered:
            filt = filter_persistent_lineages(
                censuses, generation=census.generation, window_t=window, component_kind=kind
            )
            if census.generation + window not in generations:
                present_keys = [item.component_key(kind) for item in census.organisms]
            else:
                allowed = set(filt.persistent_organism_ids)
                present_keys = [
                    item.component_key(kind)
                    for item in census.organisms
                    if item.organism_id in allowed
                ]
        else:
            present_keys = [item.component_key(kind) for item in census.organisms]
        present = set(present_keys)
        new_keys = [key for key in present if key not in introduced]
        for key in new_keys:
            introduced[key] = census.generation
        novelty = len(new_keys)
        diversity = len(present)
        activity = sum(1 for key in present if key in introduced)
        cumulative += activity
        points.append(
            BedauActivityPoint(
                time=census.generation,
                novelty=novelty,
                diversity=diversity,
                activity=activity,
                cumulative_activity=cumulative,
                new_activity=novelty,
            )
        )
    return BedauActivitySurface(
        points=tuple(points),
        component_kind=kind,
        persistence_filtered=persistence_filtered,
        literature_refs=("bedau_evolutionary_activity",),
    )


def compare_descendant_cohorts(
    censuses: Sequence[GenerationCensus],
    config: MultiGenerationEvidenceConfig,
    *,
    env_seed: int | None = None,
    comparison_kind: str = "same_run",
) -> CohortComparison | None:
    """Compare descendant vs ancestor cohorts. Descriptive metric delta only."""

    if not censuses:
        return None
    by_gen = {item.generation: item for item in censuses}
    ancestor_g = config.ancestor_generation
    descendant_g = (
        config.descendant_generation if config.descendant_generation is not None else max(by_gen)
    )
    ancestor = by_gen.get(ancestor_g)
    descendant = by_gen.get(descendant_g)
    if descendant is not None and not descendant.organisms and config.descendant_generation is None:
        nonempty = [item for item in censuses if item.organisms and item.generation > ancestor_g]
        descendant = nonempty[-1] if nonempty else descendant
        if descendant is not None:
            descendant_g = descendant.generation
    if ancestor is None or descendant is None or not ancestor.organisms or not descendant.organisms:
        return None
    ancestor_fitness = [item.fitness for item in ancestor.organisms]
    descendant_fitness = [item.fitness for item in descendant.organisms]
    ancestor_intake = [float(item.lumen_eaten) for item in ancestor.organisms]
    descendant_intake = [float(item.lumen_eaten) for item in descendant.organisms]
    ancestor_mean = sum(ancestor_fitness) / len(ancestor_fitness)
    descendant_mean = sum(descendant_fitness) / len(descendant_fitness)
    fitness_delta = descendant_mean - ancestor_mean
    ancestor_eat = sum(ancestor_intake) / len(ancestor_intake)
    descendant_eat = sum(descendant_intake) / len(descendant_intake)
    effect = None
    if len(ancestor_fitness) >= 1 and len(descendant_fitness) >= 1:
        effect = estimate_effect_size_lite("fitness", ancestor_fitness, descendant_fitness)
    return CohortComparison(
        ancestor_generation=ancestor_g,
        descendant_generation=descendant_g,
        env_seed=env_seed,
        comparison_kind=comparison_kind,
        ancestor_mean_fitness=round(ancestor_mean, 10),
        descendant_mean_fitness=round(descendant_mean, 10),
        fitness_delta=round(fitness_delta, 10),
        ancestor_mean_intake=round(ancestor_eat, 10),
        descendant_mean_intake=round(descendant_eat, 10),
        intake_delta=round(descendant_eat - ancestor_eat, 10),
        ancestor_count=len(ancestor.organisms),
        descendant_count=len(descendant.organisms),
        descendant_outperforms_ancestors=fitness_delta > 0,
        effect_size=effect,
    )


def reevaluate_cohorts_on_seed(
    spec: object,
    ancestor_genomes: Sequence[str],
    descendant_genomes: Sequence[str],
    *,
    seed: int | None = None,
    tick_count: int = 4,
) -> CohortComparison:
    """Run ancestor and descendant genomes on the same env seed (paired comparison)."""

    if not ancestor_genomes or not descendant_genomes:
        raise ConfigurationError("reevaluate_cohorts_on_seed requires both genome cohorts.")
    ancestor_result = _run_genome_cohort(spec, ancestor_genomes, seed=seed, tick_count=tick_count)
    descendant_result = _run_genome_cohort(
        spec, descendant_genomes, seed=seed, tick_count=tick_count
    )
    ancestor_c = censuses_from_run(ancestor_result)
    descendant_c = censuses_from_run(descendant_result)
    if not ancestor_c or not descendant_c:
        raise ConfigurationError("paired seed reevaluation produced empty censuses.")
    comparison = compare_descendant_cohorts(
        (
            ancestor_c[-1],
            GenerationCensus(
                generation=ancestor_c[-1].generation + 1,
                mean_fitness=descendant_c[-1].mean_fitness,
                max_fitness=descendant_c[-1].max_fitness,
                selection_mean_fitness=descendant_c[-1].selection_mean_fitness,
                selection_max_fitness=descendant_c[-1].selection_max_fitness,
                survival_count=descendant_c[-1].survival_count,
                births=descendant_c[-1].births,
                deaths=descendant_c[-1].deaths,
                mean_runtime_atp=descendant_c[-1].mean_runtime_atp,
                resource_intake=descendant_c[-1].resource_intake,
                organisms=tuple(
                    replace(item, generation=ancestor_c[-1].generation + 1)
                    for item in descendant_c[-1].organisms
                ),
            ),
        ),
        MultiGenerationEvidenceConfig(
            ancestor_generation=ancestor_c[-1].generation,
            descendant_generation=ancestor_c[-1].generation + 1,
        ),
        env_seed=seed if seed is not None else getattr(spec, "seed", None),
        comparison_kind="paired_seed_reeval",
    )
    if comparison is None:
        raise ConfigurationError("paired seed reevaluation comparison failed.")
    return comparison


def run_mutation_ablation_control(
    spec: object,
    treatment_result: object,
    *,
    control_kind: str = "no_mutation",
) -> InstinctAblationControl:
    """Run a no-mutation (or caller-kind) control on the same spec/seed."""

    treatment_c = censuses_from_run(treatment_result)
    treatment_delta = _trajectory_fitness_delta(treatment_c)
    control_spec = _spec_with_mutation_rate(spec, 0.0)
    from codontrace.genesis.engine import GenesisEngine

    control_result = GenesisEngine.from_spec(control_spec).run_ticks()
    control_c = censuses_from_run(control_result)
    control_delta = _trajectory_fitness_delta(control_c)
    treatment_digest = str(treatment_result.digest()) if hasattr(treatment_result, "digest") else ""
    control_digest = str(control_result.digest()) if hasattr(control_result, "digest") else ""
    return InstinctAblationControl(
        control_kind=control_kind,
        treatment_fitness_delta=round(treatment_delta, 10),
        control_fitness_delta=round(control_delta, 10),
        treatment_exceeds_control=treatment_delta > control_delta,
        treatment_run_digest=treatment_digest,
        control_run_digest=control_digest,
    )


def build_oee_measurement_from_trajectories(
    *,
    fitness: FitnessTrajectory,
    modes: ModesAssessment | None,
    bedau: BedauActivitySurface | None,
    instinct: InstinctBehaviorTrajectory,
    seed_count: int = 1,
) -> OEEMetricsReport:
    """Wire existing ``OEEMetricsReport`` as measurement_only (never OEE proof)."""

    generation_count = len(fitness.points)
    novelty_values = [point.novelty for point in (modes.points if modes is not None else ())]
    complexity_values = [point.complexity for point in (modes.points if modes is not None else ())]
    persistence_values = [
        point.persistent_count for point in (modes.points if modes is not None else ())
    ]
    behavior_entropy = 0.0
    if instinct.summaries:
        last = instinct.summaries[-1]
        behavior_entropy = float(last.unique_behaviors)
    coverage_slope = 0.0
    if len(instinct.summaries) >= 2:
        coverage_slope = (
            instinct.summaries[-1].unique_behaviors - instinct.summaries[0].unique_behaviors
        ) / max(1, len(instinct.summaries) - 1)
    persistent_novelty = sum(novelty_values) / len(novelty_values) if novelty_values else 0.0
    lineage_persistence = (
        sum(persistence_values) / len(persistence_values) if persistence_values else 0.0
    )
    metrics = {
        "archive_coverage_slope": float(coverage_slope),
        "persistent_novelty_rate": float(persistent_novelty),
        "lineage_persistence": float(lineage_persistence),
        "behavior_entropy": float(behavior_entropy),
        "modes_mean_complexity": (
            sum(complexity_values) / len(complexity_values) if complexity_values else 0.0
        ),
        "bedau_cumulative_activity": float(
            bedau.points[-1].cumulative_activity if bedau is not None and bedau.points else 0.0
        ),
    }
    return build_oee_metrics_report(
        seed_count=seed_count,
        generation_count=generation_count,
        metrics=metrics,
        shadow_adjusted=False,
        persistence_window_observed=modes.persistence_window_generations if modes else 0,
        diversity_collapse_flag=bool(instinct.summaries)
        and instinct.summaries[-1].unique_behaviors <= 1,
    )


def build_hallmark_observation(
    modes: ModesAssessment | None,
    bedau: BedauActivitySurface | None,
) -> OEEHallmarkObservation:
    novelty_ongoing = bool(modes and any(point.novelty > 0 for point in modes.points[1:]))
    complexity_ongoing = bool(
        modes and len(modes.points) >= 2 and modes.points[-1].complexity >= 0.0
    )
    activity_ongoing = bool(bedau and any(point.activity > 0 for point in bedau.points))
    return OEEHallmarkObservation(
        ongoing_novelty_metric=novelty_ongoing,
        ongoing_complexity_metric=complexity_ongoing,
        ongoing_activity_metric=activity_ongoing,
        persistence_filter_applied=bool(modes and modes.points),
    )


def build_multi_generation_evidence_pack(
    result: object,
    config: MultiGenerationEvidenceConfig | None = None,
    *,
    spec: object | None = None,
    ablation_control: InstinctAblationControl | None = None,
    multi_seed_protocol: StatisticalProtocolConfig | None = None,
    paired_comparison: CohortComparison | None = None,
) -> MultiGenerationEvidencePack:
    """Build the Phase D evidence pack from one (or precomputed) run."""

    cfg = config or MultiGenerationEvidenceConfig()
    censuses = censuses_from_run(result)
    run_digest = str(result.digest()) if hasattr(result, "digest") else ""
    seed = getattr(getattr(result, "run", None), "seed", None)
    if seed is None:
        seed = getattr(spec, "seed", None)
    fitness = build_fitness_trajectory(censuses, run_digest=run_digest, seed=seed)
    instinct = build_instinct_behavior_trajectory(censuses)
    comparison = paired_comparison or compare_descendant_cohorts(censuses, cfg, env_seed=seed)
    if cfg.paired_seed_reevaluation and spec is not None and comparison is not None:
        ancestor = next(
            (item for item in censuses if item.generation == cfg.ancestor_generation), None
        )
        descendant = censuses[-1] if censuses else None
        if ancestor is not None and descendant is not None:
            comparison = reevaluate_cohorts_on_seed(
                spec,
                tuple(item.genome_bits for item in ancestor.organisms if item.genome_bits),
                tuple(item.genome_bits for item in descendant.organisms if item.genome_bits),
                seed=seed,
                tick_count=cfg.reevaluation_tick_count,
            )
    modes = build_modes_assessment(censuses, cfg) if cfg.include_modes else None
    bedau = build_bedau_activity_surface(censuses, cfg) if cfg.include_bedau else None
    oee = (
        build_oee_measurement_from_trajectories(
            fitness=fitness,
            modes=modes,
            bedau=bedau,
            instinct=instinct,
            seed_count=1 if multi_seed_protocol is None else max(1, multi_seed_protocol.min_seeds),
        )
        if cfg.include_oee_scaffold
        else None
    )
    hallmarks = build_hallmark_observation(modes, bedau)
    status, ceiling = _instinct_status(comparison, multi_seed_protocol, ablation_control, cfg)
    return MultiGenerationEvidencePack(
        fitness_trajectory=fitness,
        instinct_trajectory=instinct,
        cohort_comparison=comparison,
        modes_assessment=modes,
        bedau_surface=bedau,
        oee_metrics_report=oee,
        hallmark_observation=hallmarks,
        ablation_control=ablation_control,
        config=cfg,
        run_digest=run_digest,
        seed=seed,
        multi_seed_protocol=multi_seed_protocol,
        instinct_improved_status=status,
        claim_ceiling=ceiling,
    )


def instinct_improvement_claim_request(
    pack: MultiGenerationEvidencePack,
) -> ClaimRequest:
    """Build a ClaimGate request. ``instinct_improved`` needs multi-seed + ablation."""

    comparison = pack.cohort_comparison
    delta_observed = bool(comparison is not None and comparison.fitness_delta > 0)
    flags = {
        "metric_delta_observed": delta_observed,
        "same_env_seed_paired_comparison": comparison is not None,
        "multi_seed_protocol": pack.multi_seed_protocol is not None
        and pack.multi_seed_protocol.min_seeds >= 2,
        "ablation_or_control_present": pack.ablation_control is not None,
        "persistence_filter_applied": pack.modes_assessment is not None
        and bool(pack.modes_assessment.points),
        "oee_metrics": pack.oee_metrics_report is not None,
    }
    return ClaimRequest(
        "instinct_improved",
        flags,
        evidence_digests=(pack.digest,),
    )


def evaluate_instinct_improvement_claim(
    pack: MultiGenerationEvidencePack,
    gate: ScientificClaimGate | None = None,
) -> ClaimDecision:
    """ClaimGate path: instinct_improved downgrades to runtime_observation by default."""

    return (gate or ScientificClaimGate()).decide(instinct_improvement_claim_request(pack))


def evaluate_oee_measurement_claim(
    pack: MultiGenerationEvidencePack,
    gate: ScientificClaimGate | None = None,
) -> ClaimDecision:
    """OEE ceiling for this pack is measurement_only unless stronger flags exist."""

    resolved = gate or ScientificClaimGate()
    flags = _oee_measurement_flags(pack)
    decision = resolved.decide(
        ClaimRequest("oee_measurement_only", flags, evidence_digests=(pack.digest,)),
    )
    blocked = resolved.decide(
        ClaimRequest("open_ended_intelligence", flags, evidence_digests=(pack.digest,))
    )
    if blocked.allowed:
        raise ConfigurationError("open_ended_intelligence must remain blocked.")
    return decision


def evaluate_tokyo_type1_measurement_claim(
    pack: MultiGenerationEvidencePack,
    gate: ScientificClaimGate | None = None,
) -> ClaimDecision:
    """Channon 2024 Tokyo Type 1 *vocabulary* only — never Type 1 passed.

    ``tokyo_type1_measurement_only`` aliases to ``oee_measurement_only``.
    This does not run a Type 1 protocol, does not implement CLIP/ASAL
    foundation-model open-endedness (arXiv 2412.17799), and must never
    return a Type-1-passed label.
    """

    resolved = gate or ScientificClaimGate()
    evaluate_oee_measurement_claim(pack, gate=resolved)
    flags = _oee_measurement_flags(pack)
    decision = resolved.decide(
        ClaimRequest(
            TOKYO_TYPE1_MEASUREMENT_CLAIM,
            flags,
            evidence_digests=(pack.digest,),
        )
    )
    if decision.final_claim not in {"oee_measurement_only", "experimental_engine"}:
        raise ConfigurationError(
            "tokyo_type1_measurement_only must alias to oee_measurement_only "
            "(Type 1 is not passed)."
        )
    for blocked_label in (
        "tokyo_type1_passed",
        "tokyo_type_1_passed",
        "tokyo_type1_oee_proved",
        "open_ended_intelligence",
    ):
        blocked = resolved.decide(
            ClaimRequest(blocked_label, flags, evidence_digests=(pack.digest,))
        )
        if blocked.allowed:
            raise ConfigurationError(f"{blocked_label} must remain blocked.")
    return decision


def _oee_measurement_flags(pack: MultiGenerationEvidencePack) -> dict[str, bool]:
    return {
        "oee_metrics": pack.oee_metrics_report is not None,
        "oee_report_artifact": pack.oee_metrics_report is not None,
        "oee_report_digest": bool(pack.oee_metrics_report and pack.oee_metrics_report.digest),
        "oee_protocol_executed": False,
        "shadow_run_present": bool(
            pack.oee_metrics_report and pack.oee_metrics_report.shadow_adjusted
        ),
        "min_seed_threshold_met": bool(
            pack.oee_metrics_report and pack.oee_metrics_report.seed_count >= 30
        ),
        "persistence_window_observed": bool(pack.modes_assessment and pack.modes_assessment.points),
        "confidence_intervals_present": False,
        "stagnation_diversity_status_recorded": pack.oee_metrics_report is not None,
        "claim_gate_decision_digest": False,
    }


def genomes_from_census(census: GenerationCensus) -> tuple[str, ...]:
    return tuple(item.genome_bits for item in census.organisms if item.genome_bits)


def _instinct_status(
    comparison: CohortComparison | None,
    multi_seed: StatisticalProtocolConfig | None,
    ablation: InstinctAblationControl | None,
    config: MultiGenerationEvidenceConfig,
) -> tuple[str, str]:
    if comparison is None:
        return "not_observed", _PHASE_D_CLAIM_CEILING
    if comparison.fitness_delta <= 0:
        return "runtime_observation_no_improvement", _PHASE_D_CLAIM_CEILING
    has_protocol = multi_seed is not None and multi_seed.min_seeds >= 2
    if has_protocol and ablation is not None and config.claim_ceiling == _MAX_CANDIDATE_CEILING:
        return "candidate_evidence", _MAX_CANDIDATE_CEILING
    return "runtime_observation_delta", _PHASE_D_CLAIM_CEILING


def _action_counts(trace: object | None) -> tuple[tuple[str, int], ...]:
    if trace is None:
        return ()
    counts: Counter[str] = Counter()
    for event in getattr(trace, "events", ()):
        action = getattr(event, "action", None)
        if isinstance(action, str) and action:
            counts[action] += 1
    return tuple(sorted(counts.items()))


def _behavior_key(role: str, action_counts: Sequence[tuple[str, int]], lumen_eaten: int) -> str:
    actions = ",".join(f"{name}:{count}" for name, count in action_counts)
    return f"{role}|eat:{lumen_eaten}|{actions}"


def _has_living_descendant(
    organism_id: str,
    children: Mapping[str, Sequence[str]],
    alive_horizon: set[str],
) -> bool:
    """True if ``organism_id`` or any descendant is alive at the horizon.

    Self-survival counts as lineage continuation (the coalescence-window
    lineage did not go extinct). This is an organism-id graph walk, not a
    phylogenetic taxon reconstruction.
    """

    stack = [organism_id]
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if current in alive_horizon:
            return True
        stack.extend(children.get(current, ()))
    return False


def _jaccard_distance(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return 1.0 - (len(left & right) / len(union))


def _shannon(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in counts.values():
        if count <= 0:
            continue
        probability = count / total
        entropy -= probability * math.log2(probability)
    return entropy


def _trajectory_fitness_delta(censuses: Sequence[GenerationCensus]) -> float:
    if len(censuses) < 2:
        return 0.0
    return censuses[-1].mean_fitness - censuses[0].mean_fitness


def _run_genome_cohort(
    spec: object,
    genomes: Sequence[str],
    *,
    seed: int | None,
    tick_count: int,
) -> object:
    from codontrace.genesis.engine import GenesisEngine

    updated = replace(
        spec,  # type: ignore[type-var]
        genome_bits=tuple(genomes),
        seed=getattr(spec, "seed", 1) if seed is None else seed,
        tick_count=tick_count,
    )
    return GenesisEngine.from_spec(updated).run_ticks()


def _spec_with_mutation_rate(spec: object, bit_flip_rate: float) -> object:
    configs = getattr(spec, "population_configs", None)
    mutation = getattr(spec, "mutation_config", None)
    if configs is None and mutation is None:
        raise ConfigurationError("spec has no mutation_config to ablate.")
    new_mutation = None if mutation is None else replace(mutation, bit_flip_rate=bit_flip_rate)
    new_configs = configs
    if configs is not None:
        new_configs = replace(
            configs, mutation=replace(configs.mutation, bit_flip_rate=bit_flip_rate)
        )
    return replace(
        spec,  # type: ignore[type-var]
        mutation_config=new_mutation
        if new_mutation is not None
        else getattr(spec, "mutation_config", None),
        population_configs=new_configs,
    )
