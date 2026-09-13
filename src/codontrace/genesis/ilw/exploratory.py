"""ILW-6 exploratory phylogeny hooks + novelty/learnability probes.

MODES-inspired (Dolson et al. 2019) measurement *hooks* only. Organism
phylogeny and capsule genealogy remain separate trees that are joinable on
shared keys (``lineage_id``, ``organism_id`` / ``source_id``).

**Exploratory ceiling:** these probes never promote ClaimGate, never claim
CCE / intelligence / AGI / open-endedness, and never raise the scientific
name above ``integrated eco-evolutionary runtime``. ClaimGate stays
``runtime_observation``.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from math import log2
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.ilw.adapter_honesty import (
    assert_claim_ceiling_runtime_observation,
    assert_no_fixture_outcome_injection,
)
from codontrace.genesis.ilw.chain_runtime import IlwChainRuntime
from codontrace.genesis.ilw.dag import CLAIM_CEILING, SCIENTIFIC_NAME
from codontrace.genesis.ilw.prereg import FORBIDDEN_CLAIM_LABELS, MESOUDI_CCE_CRITERIA

ILW6_SCHEMA = "ilw6_exploratory_v1"
ILW6_STATUS = "exploratory_only"
MODES_CITE_DOI = "10.1162/artl_a_00280"
PHYLOTRACK_CITE = "arXiv:2405.09389"

# Explicit denylist mirrored into every export (never promote).
ILW6_FORBIDDEN_PROMOTIONS: frozenset[str] = frozenset(
    {
        *FORBIDDEN_CLAIM_LABELS,
        "cumulative_cultural_evolution",
        "cce_claimed",
        "proved_open_endedness",
        "open_ended_intelligence",
        "modes_passed",
        "modes_score_as_intelligence",
        "tokyo_type1_passed",
        "learnability_proved",
        "novelty_proves_intelligence",
    }
)

ILW6_LIMITATIONS: tuple[str, ...] = (
    "exploratory_only_not_confirmatory",
    "not_a_bit_identical_modes_cpp_port",
    "not_phylotrack_replacement",
    "organism_phylogeny_and_capsule_genealogy_are_separate_joinable_trees",
    "persistence_filter_is_generation_coalescence_window_not_full_systematics",
    "learnability_probe_is_descriptive_correlation_not_causal_cce",
    "no_claimgate_ladder_promotion",
    "no_mesoudi_cce_claim",
    "no_intelligence_agi_collective_intelligence_claim",
)


class Ilw6ExploratoryError(ConfigurationError):
    """Raised when ILW-6 exploratory export cannot proceed honestly."""


def _shannon(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for n in counts.values():
        if n <= 0:
            continue
        p = n / total
        entropy -= p * log2(p)
    return round(entropy, 10)


def _jaccard_distance(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return round(1.0 - (len(a & b) / len(union)), 10)


@dataclass(frozen=True, slots=True)
class OrganismPhyloNode:
    """One node in the organism phylogeny (birth / founder record)."""

    organism_id: str
    parent_id: str | None
    lineage_id: str
    generation: int
    genome_digest: str
    tick: int
    parent_genome_digest: str | None = None
    mutation_digest: str | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "organism_id": self.organism_id,
            "parent_id": self.parent_id,
            "lineage_id": self.lineage_id,
            "generation": self.generation,
            "genome_digest": self.genome_digest,
            "tick": self.tick,
            "parent_genome_digest": self.parent_genome_digest,
            "mutation_digest": self.mutation_digest,
        }


@dataclass(frozen=True, slots=True)
class CapsuleGenealNode:
    """One node in the capsule genealogy (experience→capsule chain)."""

    capsule_id: str
    capsule_parent_id: str | None
    source_id: str
    lineage_id: str
    payload_digest: str
    provenance_digest: str
    tick: int

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "capsule_id": self.capsule_id,
            "capsule_parent_id": self.capsule_parent_id,
            "source_id": self.source_id,
            "lineage_id": self.lineage_id,
            "payload_digest": self.payload_digest,
            "provenance_digest": self.provenance_digest,
            "tick": self.tick,
        }


@dataclass(frozen=True, slots=True)
class PhyloJoinRow:
    """Joinable organism↔capsule row (separate trees, shared keys)."""

    join_key: str
    lineage_id: str
    organism_id: str | None
    capsule_id: str | None
    organism_generation: int | None
    capsule_tick: int | None
    genome_digest: str | None
    payload_digest: str | None

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "join_key": self.join_key,
            "lineage_id": self.lineage_id,
            "organism_id": self.organism_id,
            "capsule_id": self.capsule_id,
            "organism_generation": self.organism_generation,
            "capsule_tick": self.capsule_tick,
            "genome_digest": self.genome_digest,
            "payload_digest": self.payload_digest,
        }


@dataclass(frozen=True, slots=True)
class ModesStylePoint:
    """One exploratory MODES-style (change/novelty/complexity/ecology) point."""

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


@dataclass(frozen=True, slots=True)
class LearnabilityProbe:
    """Exploratory learnability surface (descriptive; not CCE / intelligence).

    Counts capsule→policy apply events and whether a subsequent action /
    energy delta was observed on the same actor. Correlation only — never a
    Mesoudi & Thornton CCE claim.
    """

    capsule_to_policy_applied: int
    subsequent_action_observed: int
    subsequent_energy_delta_nonzero: int
    learnability_ratio: float
    mesoudi_cce_criteria_passed: tuple[str, ...]
    mesoudi_cce_claim: bool
    exploratory_only: bool = True

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "capsule_to_policy_applied": self.capsule_to_policy_applied,
            "subsequent_action_observed": self.subsequent_action_observed,
            "subsequent_energy_delta_nonzero": self.subsequent_energy_delta_nonzero,
            "learnability_ratio": self.learnability_ratio,
            "mesoudi_cce_criteria_passed": list(self.mesoudi_cce_criteria_passed),
            "mesoudi_cce_claim": self.mesoudi_cce_claim,
            "exploratory_only": self.exploratory_only,
            "note": (
                "Descriptive capsule→policy→action coupling surface only; "
                "not cumulative cultural evolution."
            ),
        }


@dataclass(frozen=True, slots=True)
class Ilw6ExploratoryReport:
    """Full ILW-6 exploratory export (digest-stable; promotion-free)."""

    run_id: str
    world_spec_digest: str
    final_digest: str
    organism_phylogeny: tuple[OrganismPhyloNode, ...]
    capsule_genealogy: tuple[CapsuleGenealNode, ...]
    join_rows: tuple[PhyloJoinRow, ...]
    modes_points: tuple[ModesStylePoint, ...]
    learnability: LearnabilityProbe
    persistence_window_generations: int
    claim_ceiling: str = CLAIM_CEILING
    scientific_name: str = SCIENTIFIC_NAME
    status: str = ILW6_STATUS
    schema_version: str = ILW6_SCHEMA
    claim_promotions: tuple[str, ...] = ()
    ladder_promotion: None = None
    scientific_claim_emitted: bool = False
    cce_claimed: bool = False
    intelligence_claimed: bool = False
    limitations: tuple[str, ...] = ILW6_LIMITATIONS
    literature: tuple[dict[str, str], ...] = (
        {
            "id": "modes_dolson_2019",
            "doi": MODES_CITE_DOI,
            "note": "MODES toolbox — measurement hooks only; not a pass.",
        },
        {
            "id": "phylotrack",
            "cite": PHYLOTRACK_CITE,
            "note": "Phylogeny instrumentation inspiration; not a port.",
        },
        {
            "id": "mesoudi_thornton_2018",
            "doi": "10.1098/rspb.2018.0712",
            "note": "Four CCE criteria — explicitly NOT claimed by ILW-6.",
        },
    )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "exploratory_only": True,
            "run_id": self.run_id,
            "world_spec_digest": self.world_spec_digest,
            "final_digest": self.final_digest,
            "claim_ceiling": self.claim_ceiling,
            "scientific_name": self.scientific_name,
            "claim_promotions": list(self.claim_promotions),
            "ladder_promotion": self.ladder_promotion,
            "scientific_claim_emitted": self.scientific_claim_emitted,
            "cce_claimed": self.cce_claimed,
            "intelligence_claimed": self.intelligence_claimed,
            "forbidden_promotions": sorted(ILW6_FORBIDDEN_PROMOTIONS),
            "persistence_window_generations": self.persistence_window_generations,
            "organism_phylogeny": [n.to_dict() for n in self.organism_phylogeny],
            "capsule_genealogy": [n.to_dict() for n in self.capsule_genealogy],
            "join_rows": [r.to_dict() for r in self.join_rows],
            "modes_style_points": [p.to_dict() for p in self.modes_points],
            "learnability_probe": self.learnability.to_dict(),
            "limitations": list(self.limitations),
            "literature": [dict(item) for item in self.literature],
            "mesoudi_cce_criteria_catalog": [dict(item) for item in MESOUDI_CCE_CRITERIA],
            "organism_node_count": len(self.organism_phylogeny),
            "capsule_node_count": len(self.capsule_genealogy),
            "join_row_count": len(self.join_rows),
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict(), prefix="ilw6_exploratory")

    def export(self) -> dict[str, JsonValue]:
        """Public export payload including self-digest; promotion fields empty."""

        payload = self.to_dict()
        payload["export_digest"] = self.digest()
        assert_no_fixture_outcome_injection(payload)
        assert_claim_ceiling_runtime_observation(str(payload["claim_ceiling"]))
        if payload.get("claim_promotions") not in ([], (), None):
            raise Ilw6ExploratoryError("ILW-6 must not emit claim_promotions.")
        if payload.get("ladder_promotion") is not None:
            raise Ilw6ExploratoryError("ILW-6 must not emit ladder_promotion.")
        if payload.get("cce_claimed") or payload.get("intelligence_claimed"):
            raise Ilw6ExploratoryError("ILW-6 must not claim CCE or intelligence.")
        if payload.get("scientific_claim_emitted"):
            raise Ilw6ExploratoryError("ILW-6 must not emit a scientific claim.")
        labels = {
            str(payload.get("status", "")),
            str(payload.get("scientific_name", "")),
        }
        bad = labels & ILW6_FORBIDDEN_PROMOTIONS
        if bad:
            raise Ilw6ExploratoryError(
                f"ILW-6 export contains forbidden promotion labels: {sorted(bad)}"
            )
        return payload


def build_organism_phylogeny(
    runtime: IlwChainRuntime,
) -> tuple[OrganismPhyloNode, ...]:
    """Build organism phylogeny nodes from runtime lineage records."""

    nodes: list[OrganismPhyloNode] = []
    for rec in runtime.lineage_records:
        nodes.append(
            OrganismPhyloNode(
                organism_id=str(rec.get("organism_id", "")),
                parent_id=(
                    None
                    if rec.get("parent_id") in (None, "", "null")
                    else str(rec.get("parent_id"))
                ),
                lineage_id=str(rec.get("lineage_id", "")),
                generation=int(rec.get("generation", 0) or 0),
                genome_digest=str(rec.get("genome_digest", "")),
                tick=int(rec.get("tick", 0) or 0),
                parent_genome_digest=(
                    None
                    if rec.get("parent_genome_digest") in (None, "", "null")
                    else str(rec.get("parent_genome_digest"))
                ),
                mutation_digest=(
                    None
                    if rec.get("mutation_digest") in (None, "", "null")
                    else str(rec.get("mutation_digest"))
                ),
            )
        )
    nodes.sort(key=lambda n: (n.tick, n.generation, n.organism_id))
    return tuple(nodes)


def build_capsule_genealogy(
    runtime: IlwChainRuntime,
) -> tuple[CapsuleGenealNode, ...]:
    """Build capsule genealogy nodes from runtime capsule genealogy records."""

    nodes: list[CapsuleGenealNode] = []
    for rec in runtime.capsule_genealogy:
        nodes.append(
            CapsuleGenealNode(
                capsule_id=str(rec.get("capsule_id", "")),
                capsule_parent_id=(
                    None
                    if rec.get("capsule_parent_id") in (None, "", "null")
                    else str(rec.get("capsule_parent_id"))
                ),
                source_id=str(rec.get("source_id", "")),
                lineage_id=str(rec.get("lineage_id", "")),
                payload_digest=str(rec.get("payload_digest", "")),
                provenance_digest=str(rec.get("provenance_digest", "")),
                tick=int(rec.get("tick", 0) or 0),
            )
        )
    nodes.sort(key=lambda n: (n.tick, n.capsule_id))
    return tuple(nodes)


def join_organism_capsule_phylogenies(
    organism_nodes: Sequence[OrganismPhyloNode],
    capsule_nodes: Sequence[CapsuleGenealNode],
) -> tuple[PhyloJoinRow, ...]:
    """Join organism phylogeny with capsule genealogy on shared keys.

    Join key = ``lineage_id`` + organism/source id. Trees stay separate; the
    join is a relational view only (Phylotrack-inspired instrumentation).
    """

    by_org: dict[str, list[OrganismPhyloNode]] = defaultdict(list)
    for node in organism_nodes:
        by_org[node.organism_id].append(node)

    rows: list[PhyloJoinRow] = []
    seen: set[str] = set()

    for cap in capsule_nodes:
        orgs = by_org.get(cap.source_id, [])
        if orgs:
            # Prefer the latest organism record at or before capsule tick.
            eligible = [o for o in orgs if o.tick <= cap.tick] or orgs
            org = max(eligible, key=lambda o: (o.tick, o.generation))
            join_key = f"{cap.lineage_id}|{org.organism_id}|{cap.capsule_id}"
            rows.append(
                PhyloJoinRow(
                    join_key=join_key,
                    lineage_id=cap.lineage_id,
                    organism_id=org.organism_id,
                    capsule_id=cap.capsule_id,
                    organism_generation=org.generation,
                    capsule_tick=cap.tick,
                    genome_digest=org.genome_digest,
                    payload_digest=cap.payload_digest,
                )
            )
        else:
            join_key = f"{cap.lineage_id}|orphan_source:{cap.source_id}|{cap.capsule_id}"
            rows.append(
                PhyloJoinRow(
                    join_key=join_key,
                    lineage_id=cap.lineage_id,
                    organism_id=None,
                    capsule_id=cap.capsule_id,
                    organism_generation=None,
                    capsule_tick=cap.tick,
                    genome_digest=None,
                    payload_digest=cap.payload_digest,
                )
            )
        seen.add(cap.capsule_id)

    # Organism-only rows (no capsule yet) remain joinable stubs.
    for org in organism_nodes:
        stub_key = f"{org.lineage_id}|{org.organism_id}|no_capsule"
        if any(r.organism_id == org.organism_id and r.capsule_id for r in rows):
            continue
        rows.append(
            PhyloJoinRow(
                join_key=stub_key,
                lineage_id=org.lineage_id,
                organism_id=org.organism_id,
                capsule_id=None,
                organism_generation=org.generation,
                capsule_tick=None,
                genome_digest=org.genome_digest,
                payload_digest=None,
            )
        )

    rows.sort(key=lambda r: (r.lineage_id, r.organism_id or "", r.capsule_id or ""))
    return tuple(rows)


def _children_map(nodes: Sequence[OrganismPhyloNode]) -> dict[str, list[str]]:
    children: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        if node.parent_id:
            children[node.parent_id].append(node.organism_id)
    return children


def _has_descendant_at_or_after(
    organism_id: str,
    *,
    children: Mapping[str, Sequence[str]],
    gen_of: Mapping[str, int],
    horizon_generation: int,
) -> bool:
    stack = [organism_id]
    seen: set[str] = set()
    while stack:
        oid = stack.pop()
        if oid in seen:
            continue
        seen.add(oid)
        if gen_of.get(oid, -1) >= horizon_generation:
            return True
        stack.extend(children.get(oid, ()))
    return False


def modes_style_novelty_probe(
    organism_nodes: Sequence[OrganismPhyloNode],
    *,
    persistence_window_generations: int = 1,
) -> tuple[ModesStylePoint, ...]:
    """Exploratory MODES-style change/novelty/complexity/ecology series.

    Persistence filter: an organism at generation ``g`` counts if it or a
    descendant exists at generation ``g + window`` (coalescence-window
    approximation). Not a C++ MODES port; not an OEE / intelligence claim.
    """

    if persistence_window_generations < 0:
        raise Ilw6ExploratoryError("persistence_window_generations must be >= 0.")

    by_gen: dict[int, list[OrganismPhyloNode]] = defaultdict(list)
    gen_of: dict[str, int] = {}
    for node in organism_nodes:
        by_gen[node.generation].append(node)
        gen_of[node.organism_id] = node.generation

    children = _children_map(organism_nodes)
    generations = sorted(by_gen)
    if not generations:
        return ()

    max_gen = generations[-1]
    points: list[ModesStylePoint] = []
    previous_keys: set[str] = set()
    seen_keys: set[str] = set()

    for g in generations:
        horizon = g + persistence_window_generations
        if horizon > max_gen and persistence_window_generations > 0:
            # Incomplete horizon — skip (honest MODES-style windowing).
            continue
        persistent = [
            n
            for n in by_gen[g]
            if persistence_window_generations == 0
            or _has_descendant_at_or_after(
                n.organism_id,
                children=children,
                gen_of=gen_of,
                horizon_generation=horizon,
            )
            or (gen_of.get(n.organism_id, -1) >= horizon)
        ]
        # Self at same generation always "persists" when window==0.
        if persistence_window_generations == 0:
            persistent = list(by_gen[g])

        keys = [n.genome_digest for n in persistent if n.genome_digest]
        key_set = set(keys)
        lineage_set = {n.lineage_id for n in persistent}
        change = _jaccard_distance(previous_keys, key_set) if previous_keys or key_set else 0.0
        novelty = float(len(key_set - seen_keys))
        complexity = _shannon(Counter(keys))
        ecological = float(len(lineage_set))
        points.append(
            ModesStylePoint(
                generation=g,
                change=change,
                novelty=round(novelty, 10),
                complexity=complexity,
                ecological_potential=round(ecological, 10),
                persistent_count=len(persistent),
                persistent_type_count=len(key_set),
            )
        )
        previous_keys = key_set
        seen_keys.update(key_set)

    return tuple(points)


def learnability_probe(runtime: IlwChainRuntime) -> LearnabilityProbe:
    """Exploratory learnability surface from ledger capsule→policy events.

    Never sets ``mesoudi_cce_claim`` True; ``mesoudi_cce_criteria_passed`` is
    always empty at ILW-6 (all four criteria required for any future claim).
    """

    applied = 0
    subsequent_action = 0
    subsequent_energy = 0

    # Index events by actor for simple subsequent-event scan.
    events = list(runtime.ledger.events)
    by_actor: dict[str, list[Any]] = defaultdict(list)
    for ev in events:
        actor = str(ev.payload.get("actor_id", "") or "")
        by_actor[actor].append(ev)

    for ev in events:
        payload = ev.payload
        if str(payload.get("edge_id", "")) != "capsule_to_policy":
            continue
        if int(payload.get("applied", 0) or 0) < 1:
            continue
        applied += 1
        actor = str(payload.get("actor_id", "") or "")
        tick = int(payload.get("tick", 0) or 0)
        later = [
            other
            for other in by_actor.get(actor, ())
            if int(other.payload.get("tick", 0) or 0) > tick
        ]
        if any(str(o.payload.get("edge_id", "")) == "vm_phenotype_to_action" for o in later):
            subsequent_action += 1
        if any(
            abs(float(o.payload.get("energy_delta", 0.0) or 0.0)) > 0.0
            and str(o.payload.get("edge_id", ""))
            in {
                "action_to_resource_world",
                "vm_phenotype_to_action",
                "policy_to_survival_reproduction",
            }
            for o in later
        ):
            subsequent_energy += 1

    ratio = round((subsequent_action / applied) if applied else 0.0, 10)
    return LearnabilityProbe(
        capsule_to_policy_applied=applied,
        subsequent_action_observed=subsequent_action,
        subsequent_energy_delta_nonzero=subsequent_energy,
        learnability_ratio=ratio,
        mesoudi_cce_criteria_passed=(),
        mesoudi_cce_claim=False,
        exploratory_only=True,
    )


def run_ilw6_exploratory(
    runtime: IlwChainRuntime,
    *,
    persistence_window_generations: int = 1,
) -> Ilw6ExploratoryReport:
    """Build the full ILW-6 exploratory report from a finished chain runtime."""

    assert_claim_ceiling_runtime_observation(runtime.world_spec.claim_ceiling)
    if runtime.scheduler.tick < 0:
        raise Ilw6ExploratoryError("Runtime has not started; call bootstrap()/run() first.")

    organism = build_organism_phylogeny(runtime)
    capsules = build_capsule_genealogy(runtime)
    joins = join_organism_capsule_phylogenies(organism, capsules)
    modes = modes_style_novelty_probe(
        organism, persistence_window_generations=persistence_window_generations
    )
    learn = learnability_probe(runtime)

    report = Ilw6ExploratoryReport(
        run_id=runtime.run_id,
        world_spec_digest=runtime.world_spec.digest(),
        final_digest=runtime.final_digest(),
        organism_phylogeny=organism,
        capsule_genealogy=capsules,
        join_rows=joins,
        modes_points=modes,
        learnability=learn,
        persistence_window_generations=persistence_window_generations,
        claim_ceiling=CLAIM_CEILING,
        scientific_name=SCIENTIFIC_NAME,
        claim_promotions=(),
        ladder_promotion=None,
        scientific_claim_emitted=False,
        cce_claimed=False,
        intelligence_claimed=False,
    )
    # Fail-fast honesty on the constructed report.
    _ = report.export()
    return report


def run_ilw6_exploratory_smoke(
    *,
    run_id: str = "ilw6-exploratory-smoke",
    seed: int = 11,
    population: int = 2,
    persistence_window_generations: int = 1,
) -> Ilw6ExploratoryReport:
    """S0-scale smoke helper: run chain then emit ILW-6 exploratory export."""

    rt = IlwChainRuntime.s0(run_id=run_id, seed=seed)
    rt.bootstrap(population)
    rt.run()
    return run_ilw6_exploratory(
        rt, persistence_window_generations=persistence_window_generations
    )


__all__ = [
    "CLAIM_CEILING",
    "ILW6_FORBIDDEN_PROMOTIONS",
    "ILW6_LIMITATIONS",
    "ILW6_SCHEMA",
    "ILW6_STATUS",
    "MODES_CITE_DOI",
    "PHYLOTRACK_CITE",
    "SCIENTIFIC_NAME",
    "CapsuleGenealNode",
    "Ilw6ExploratoryError",
    "Ilw6ExploratoryReport",
    "LearnabilityProbe",
    "ModesStylePoint",
    "OrganismPhyloNode",
    "PhyloJoinRow",
    "build_capsule_genealogy",
    "build_organism_phylogeny",
    "join_organism_capsule_phylogenies",
    "learnability_probe",
    "modes_style_novelty_probe",
    "run_ilw6_exploratory",
    "run_ilw6_exploratory_smoke",
]
