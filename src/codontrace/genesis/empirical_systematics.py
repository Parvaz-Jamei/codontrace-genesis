"""Optional Empirical-style shadow / null phylogeny adapter.

Dolson et al. 2019 (MODES) count change/novelty/complexity/ecology only after a
persistence filter. Empirical systematics notes make the coalescence-window
subtlety explicit: a full phylogenetic systematics plus shadow/null run is the
careful publication path (Bedau activity; Channon 2024 Tokyo Type 1 step_4
shadow/normalization).

This module is an **opt-in Python analog**. Default is off. It produces a real
``shadow_digest`` from a shuffled-parentage null phylogeny so Tokyo step_4 can
record a supplied digest. It is **not** a bit-identical Empirical C++
systematics port and **never** auto-passes Tokyo Type 1 / OEE / intelligence.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.claim_gate import ClaimDecision, ClaimRequest, ScientificClaimGate
from codontrace.genesis.multi_generation import (
    GenerationCensus,
    OrganismCensusRecord,
    censuses_from_run,
    filter_persistent_lineages,
)

_PROTOCOL_SCHEMA = "empirical_systematics_shadow_v1"
_CLAIM_CEILING = "oee_measurement_only"
_FORBIDDEN_PASS = frozenset(
    {
        "tokyo_type1_passed",
        "tokyo_type1_proved",
        "channon_2024_passed",
        "proved_open_endedness",
        "open_ended_intelligence",
        "agi",
    }
)

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "modes_dolson_2019",
        "Dolson, Vostinar, Wiser, Ofria 2019 Artificial Life: MODES persistence "
        "filter before change/novelty/complexity/ecology.",
    ),
    (
        "empirical_systematics_shadow_notes",
        "Empirical systematics / shadow phylogeny notes: coalescence-window "
        "sensitivity; a null/shadow phylogeny is the careful path. This adapter "
        "is a Python analog, not a C++ Empirical port.",
    ),
    (
        "bedau_evolutionary_activity",
        "Bedau evolutionary activity statistics as the activity series the "
        "shadow/normalization step sits beside.",
    ),
    (
        "channon_2024_tokyo_type1_step_4",
        "Channon 2024 Artificial Life Tokyo Type 1 procedure step_4 "
        "shadow/normalization. Recording a digest is not a Type 1 pass.",
    ),
)


@dataclass(frozen=True, slots=True)
class EmpiricalSystematicsShadowConfig:
    """Opt-in knobs. ``enabled=False`` is the research default."""

    enabled: bool = False
    null_model: str = "shuffled_parentage"
    seed: int = 0
    persistence_window_t: int = 2

    def __post_init__(self) -> None:
        if self.null_model not in {"shuffled_parentage"}:
            raise ConfigurationError(
                "EmpiricalSystematicsShadowConfig.null_model must be shuffled_parentage."
            )
        if self.persistence_window_t < 1:
            raise ConfigurationError("persistence_window_t must be >= 1.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "null_model": self.null_model,
            "seed": self.seed,
            "persistence_window_t": self.persistence_window_t,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class PhylogenyEdge:
    """One parent→child edge in the observed or shadow phylogeny."""

    child_id: str
    parent_id: str | None
    second_parent_id: str | None
    generation: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "child_id": self.child_id,
            "parent_id": self.parent_id,
            "second_parent_id": self.second_parent_id,
            "generation": self.generation,
        }


@dataclass(frozen=True, slots=True)
class EmpiricalSystematicsShadowRun:
    """Digest-backed shadow/null phylogeny. Never a Tokyo Type 1 pass."""

    config: EmpiricalSystematicsShadowConfig
    observed_edge_count: int
    shadow_edge_count: int
    shadow_digest: str
    observed_digest: str
    persistent_count_observed: int
    persistent_count_shadow: int
    persistence_window_t: int
    empirical_systematics_shadow_run: bool
    null_model: str
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    tokyo_type1_passed: bool = False
    schema_version: str = _PROTOCOL_SCHEMA
    digest: str = ""

    def __post_init__(self) -> None:
        if self.tokyo_type1_passed:
            raise ConfigurationError(
                "EmpiricalSystematicsShadowRun must never set tokyo_type1_passed."
            )
        if self.claim_ceiling in _FORBIDDEN_PASS:
            raise ConfigurationError("EmpiricalSystematicsShadowRun claim_ceiling is too strong.")
        if self.observed_edge_count < 0 or self.shadow_edge_count < 0:
            raise ConfigurationError("edge counts must be non-negative.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("EmpiricalSystematicsShadowRun digest mismatch.")
        object.__setattr__(self, "digest", computed)
        object.__setattr__(self, "tokyo_type1_passed", False)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "config": self.config.to_dict(),
            "observed_edge_count": self.observed_edge_count,
            "shadow_edge_count": self.shadow_edge_count,
            "shadow_digest": self.shadow_digest,
            "observed_digest": self.observed_digest,
            "persistent_count_observed": self.persistent_count_observed,
            "persistent_count_shadow": self.persistent_count_shadow,
            "persistence_window_t": self.persistence_window_t,
            "empirical_systematics_shadow_run": self.empirical_systematics_shadow_run,
            "null_model": self.null_model,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "tokyo_type1_passed": False,
            "open_endedness_proved": False,
            "limitations": [
                "python_analog_not_empirical_cpp_systematics",
                "shuffled_parentage_null_not_full_birth_death_process",
                "measurement_only_not_tokyo_type1_passed",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def phylogeny_edges_from_censuses(
    censuses: Sequence[GenerationCensus],
) -> tuple[PhylogenyEdge, ...]:
    """Collect parent→child edges from Phase D organism-id censuses."""

    edges: list[PhylogenyEdge] = []
    for census in censuses:
        for organism in census.organisms:
            edges.append(
                PhylogenyEdge(
                    child_id=organism.organism_id,
                    parent_id=organism.parent_id,
                    second_parent_id=organism.second_parent_id,
                    generation=census.generation,
                )
            )
    return tuple(edges)


def _stable_permutation(values: Sequence[str], *, seed: int, namespace: str) -> tuple[str, ...]:
    def _key(item: str) -> str:
        payload = f"{namespace}:{seed}:{item}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    return tuple(sorted(values, key=_key))


def _shuffle_parentage(
    edges: Sequence[PhylogenyEdge], *, seed: int
) -> tuple[PhylogenyEdge, ...]:
    parented = [edge for edge in edges if edge.parent_id]
    if not parented:
        return tuple(edges)
    parent_ids = _stable_permutation(
        tuple(str(edge.parent_id) for edge in parented),
        seed=seed,
        namespace="empirical_systematics/parent",
    )
    second_ids = _stable_permutation(
        tuple(str(edge.second_parent_id or "") for edge in parented),
        seed=seed,
        namespace="empirical_systematics/second_parent",
    )
    shuffled: list[PhylogenyEdge] = []
    parented_index = 0
    for edge in edges:
        if edge.parent_id is None:
            shuffled.append(edge)
            continue
        second_raw = second_ids[parented_index]
        shuffled.append(
            PhylogenyEdge(
                child_id=edge.child_id,
                parent_id=parent_ids[parented_index],
                second_parent_id=None if second_raw == "" else second_raw,
                generation=edge.generation,
            )
        )
        parented_index += 1
    return tuple(shuffled)


def _apply_shadow_parents(
    censuses: Sequence[GenerationCensus],
    shadow_edges: Sequence[PhylogenyEdge],
) -> tuple[GenerationCensus, ...]:
    by_child: dict[tuple[int, str], PhylogenyEdge] = {
        (edge.generation, edge.child_id): edge for edge in shadow_edges
    }
    rewritten: list[GenerationCensus] = []
    for census in censuses:
        organisms: list[OrganismCensusRecord] = []
        for organism in census.organisms:
            edge = by_child.get((census.generation, organism.organism_id))
            if edge is None:
                organisms.append(organism)
                continue
            organisms.append(
                OrganismCensusRecord(
                    organism_id=organism.organism_id,
                    generation=organism.generation,
                    genome_digest=organism.genome_digest,
                    genome_bits=organism.genome_bits,
                    parent_id=edge.parent_id,
                    second_parent_id=edge.second_parent_id,
                    fitness=organism.fitness,
                    selection_fitness=organism.selection_fitness,
                    runtime_atp=organism.runtime_atp,
                    lumen_eaten=organism.lumen_eaten,
                    action_counts=organism.action_counts,
                    role_signature=organism.role_signature,
                    unique_positions=organism.unique_positions,
                    behavior_key=organism.behavior_key,
                )
            )
        rewritten.append(
            GenerationCensus(
                generation=census.generation,
                mean_fitness=census.mean_fitness,
                max_fitness=census.max_fitness,
                selection_mean_fitness=census.selection_mean_fitness,
                selection_max_fitness=census.selection_max_fitness,
                survival_count=census.survival_count,
                births=census.births,
                deaths=census.deaths,
                mean_runtime_atp=census.mean_runtime_atp,
                resource_intake=census.resource_intake,
                organisms=tuple(organisms),
            )
        )
    return tuple(rewritten)


def _persistent_count(censuses: Sequence[GenerationCensus], window_t: int) -> int:
    if not censuses:
        return 0
    generations = sorted({item.generation for item in censuses})
    total = 0
    for generation in generations:
        horizon = generation + window_t
        if horizon not in {item.generation for item in censuses}:
            continue
        filt = filter_persistent_lineages(
            censuses, generation=generation, persistence_window_t=window_t
        )
        total += len(filt.persistent_organism_ids)
    return total


def build_empirical_systematics_shadow(
    source: object,
    config: EmpiricalSystematicsShadowConfig | None = None,
    *,
    censuses: Sequence[GenerationCensus] | None = None,
) -> EmpiricalSystematicsShadowRun:
    """Build a real shadow digest from a shuffled-parentage null phylogeny.

    Default config is disabled: callers must pass ``enabled=True``. This never
    returns a Tokyo Type 1 pass. The adapter is a Python analog of Empirical
    systematics/shadow notes, not a C++ port.
    """

    cfg = config or EmpiricalSystematicsShadowConfig()
    if not cfg.enabled:
        raise ConfigurationError(
            "build_empirical_systematics_shadow requires enabled=True; "
            "the adapter stays opt-in and does not invent a shadow run."
        )
    resolved = (
        tuple(censuses)
        if censuses is not None
        else (censuses_from_run(source) if source is not None else ())
    )
    observed = phylogeny_edges_from_censuses(resolved)
    shadow_edges = _shuffle_parentage(observed, seed=cfg.seed)
    observed_digest = canonical_digest(
        {"edges": [edge.to_dict() for edge in observed], "model": "observed"}
    )
    shadow_digest = canonical_digest(
        {
            "edges": [edge.to_dict() for edge in shadow_edges],
            "model": cfg.null_model,
            "seed": cfg.seed,
        }
    )
    shadow_censuses = _apply_shadow_parents(resolved, shadow_edges)
    return EmpiricalSystematicsShadowRun(
        config=cfg,
        observed_edge_count=len(observed),
        shadow_edge_count=len(shadow_edges),
        shadow_digest=shadow_digest,
        observed_digest=observed_digest,
        persistent_count_observed=_persistent_count(resolved, cfg.persistence_window_t),
        persistent_count_shadow=_persistent_count(shadow_censuses, cfg.persistence_window_t),
        persistence_window_t=cfg.persistence_window_t,
        empirical_systematics_shadow_run=True,
        null_model=cfg.null_model,
    )


def evaluate_empirical_systematics_shadow_claim(
    run: EmpiricalSystematicsShadowRun,
    gate: ScientificClaimGate | None = None,
) -> ClaimDecision:
    """Measurement-only: a real shadow digest is not a Type 1 pass."""

    resolved = gate or ScientificClaimGate()
    decision = resolved.decide(
        ClaimRequest(
            _CLAIM_CEILING,
            {
                "oee_metrics": True,
                "shadow_run_present": bool(run.shadow_digest),
                "persistence_window_observed": run.persistence_window_t >= 1,
            },
            evidence_digests=(run.digest, run.shadow_digest),
        )
    )
    blocked = resolved.decide(ClaimRequest("tokyo_type1_passed", {}))
    if blocked.allowed:
        raise ConfigurationError("tokyo_type1_passed must remain blocked.")
    return decision


def empirical_systematics_shadow_from_dict(
    data: Mapping[str, JsonValue],
) -> EmpiricalSystematicsShadowRun:
    config_raw = data.get("config", {})
    if not isinstance(config_raw, Mapping):
        raise ConfigurationError("EmpiricalSystematicsShadowRun.config must be a mapping.")
    cfg = EmpiricalSystematicsShadowConfig(
        enabled=bool(config_raw.get("enabled", False)),
        null_model=str(config_raw.get("null_model", "shuffled_parentage")),
        seed=int(config_raw.get("seed", 0) or 0),
        persistence_window_t=int(config_raw.get("persistence_window_t", 2) or 2),
    )
    run = EmpiricalSystematicsShadowRun(
        config=cfg,
        observed_edge_count=int(data.get("observed_edge_count", 0) or 0),
        shadow_edge_count=int(data.get("shadow_edge_count", 0) or 0),
        shadow_digest=str(data.get("shadow_digest", "") or ""),
        observed_digest=str(data.get("observed_digest", "") or ""),
        persistent_count_observed=int(data.get("persistent_count_observed", 0) or 0),
        persistent_count_shadow=int(data.get("persistent_count_shadow", 0) or 0),
        persistence_window_t=int(data.get("persistence_window_t", cfg.persistence_window_t) or 2),
        empirical_systematics_shadow_run=bool(data.get("empirical_systematics_shadow_run", False)),
        null_model=str(data.get("null_model", cfg.null_model)),
    )
    if data.get("digest") and data.get("digest") != run.digest:
        raise ConfigurationError("EmpiricalSystematicsShadowRun digest mismatch.")
    return run
