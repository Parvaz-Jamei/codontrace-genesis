"""GermlineReplication-style deme payoff + contribution ledger.

Avida ``DEMES_*`` / GermlineReplication (Goldsby messaging; GECCO 2008 digital
germlines) replicate a deme when mean fitness clears a threshold, copying a
germline/propagule. This module records that trigger, preserves the target
deme, and attributes member fitness into a contribution ledger.

Claim ceiling: ``runtime_observation``. ``collective_intelligence`` remains
blocked. Not evolved division of labor and not an Avida C++ deme port.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.claim_gate import ClaimDecision, ClaimRequest, ScientificClaimGate
from codontrace.genesis.contribution_ledger import (
    CodonContributionRecord,
    ContributionLedger,
    build_contribution_ledger,
)
from codontrace.genesis.phase_e import DemeReplicationEvent

_PACK_SCHEMA = "collective_deme_payoff_v1"
_CLAIM_CEILING = "runtime_observation"
_FORBIDDEN = frozenset(
    {
        "collective_intelligence",
        "proved_collective_intelligence",
        "real_collective_intelligence",
        "deme_intelligence_proved",
        "agi",
        "open_ended_intelligence",
        "tokyo_type1_passed",
    }
)

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "avida_demes_germline_replication",
        "devosoft/avida wiki Deme-introduction and avida.cfg DEME_GROUP / "
        "GERMLINE: multilevel selection via deme replicate-on-mean-fitness and "
        "optional germline/propagule copy. Analog, not a C++ port.",
    ),
    (
        "goldsby_messaging_division_of_labor",
        "Goldsby et al. Avida coordination instructions (send/retrieve/broadcast/"
        "block_propagation), division-of-labor / task-switching, and "
        "GermlineReplication. Messaging and role tags here are gates, not evolved "
        "DoL or language.",
    ),
    (
        "gecco_2008_digital_germlines",
        "GECCO 2008 digital germlines / cooperative networks: soma vs germline "
        "eligibility tags. Role tags are gates, not evolved division of labor.",
    ),
    (
        "major_transitions_individuality",
        "Szathmary & Maynard Smith 1995; Michod evolutionary transitions in "
        "individuality / export-of-fitness. Deme tags are not a new Darwinian "
        "individual. Cite as a gap, not a result.",
    ),
)


@dataclass(frozen=True, slots=True)
class DemePayoffRecord:
    """One deme-replication payoff observation."""

    event: DemeReplicationEvent
    member_ids: tuple[str, ...]
    germline_parent_id: str
    mean_fitness: float
    contribution_digest: str = ""

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "event": self.event.to_dict(),
            "member_ids": list(self.member_ids),
            "germline_parent_id": self.germline_parent_id,
            "mean_fitness": self.mean_fitness,
            "contribution_digest": self.contribution_digest,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class CollectiveDemePayoffPack:
    """Digest-backed deme replicate-on-mean-fitness + contribution ledger."""

    records: tuple[DemePayoffRecord, ...]
    ledgers: tuple[ContributionLedger, ...]
    replication_count: int
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = _PACK_SCHEMA
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_ceiling in _FORBIDDEN or self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError(
                "CollectiveDemePayoffPack claim_ceiling must stay runtime_observation."
            )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("CollectiveDemePayoffPack digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "records": [item.to_dict() for item in self.records],
            "ledgers": [item.to_dict() for item in self.ledgers],
            "replication_count": self.replication_count,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "limitations": [
                "germline_replication_analog_not_avida_cpp_port",
                "contribution_ledger_is_attribution_estimate_not_causal_proof",
                "collective_intelligence_blocked",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _ledger_for_deme(
    event: DemeReplicationEvent,
    member_ids: Sequence[str],
    fitness_by_id: Mapping[str, float],
) -> ContributionLedger:
    records: list[CodonContributionRecord] = []
    for index, member_id in enumerate(member_ids):
        fitness = float(fitness_by_id.get(member_id, 0.0) or 0.0)
        records.append(
            CodonContributionRecord(
                execution_ref=f"deme:{event.source_deme_id}:{member_id}:{event.tick}",
                organism_id=member_id,
                generation=max(0, event.tick),
                genome_pos=index,
                codon="deme",
                action="GERMLINE_REPLICATION_CONTRIBUTION",
                macro_id=None,
                local_reward_delta=round(require_finite_float("fitness", fitness), 10),
                novelty_delta=0.0,
                reproduction_progress_delta=1.0 if member_id == event.germline_parent_id else 0.0,
                causal_accuracy_delta=None,
                descendant_success_discounted=0.0,
                method="deme_mean_fitness_share",
                confidence=0.4,
                caveat="attribution_estimate_not_causal_proof",
            )
        )
    return build_contribution_ledger(
        event.source_deme_id, max(0, event.tick), records
    )


def build_collective_deme_payoff_pack(
    result: object,
    *,
    fitness_by_id: Mapping[str, float] | None = None,
) -> CollectiveDemePayoffPack:
    """Build deme-replication payoff + contribution ledgers from a Phase E run."""

    events: list[DemeReplicationEvent] = []
    members_by_deme: dict[str, tuple[str, ...]] = {}
    scores: dict[str, float] = dict(fitness_by_id or {})
    ticks = getattr(result, "ticks", ()) or ()
    for tick in ticks:
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        deme_state = getattr(generation, "deme_state", None)
        if deme_state is None:
            continue
        for deme in getattr(deme_state, "demes", ()) or ():
            members_by_deme[str(deme.deme_id)] = tuple(str(item) for item in deme.member_ids)
        for event in getattr(deme_state, "replication_events", ()) or ():
            events.append(event)
        population = getattr(generation, "population", None)
        for item in getattr(population, "fitness", ()) if population is not None else ():
            oid = str(getattr(item, "organism_id", "") or "")
            if oid:
                scores[oid] = float(getattr(item, "score", 0.0) or 0.0)
    unique: dict[tuple[str, str, int], DemeReplicationEvent] = {}
    for event in events:
        unique[(event.source_deme_id, event.target_deme_id, event.tick)] = event
    ordered = tuple(unique.values())
    records: list[DemePayoffRecord] = []
    ledgers: list[ContributionLedger] = []
    for event in ordered:
        members = members_by_deme.get(event.source_deme_id, ())
        ledger = _ledger_for_deme(event, members, scores)
        ledgers.append(ledger)
        records.append(
            DemePayoffRecord(
                event=event,
                member_ids=members,
                germline_parent_id=event.germline_parent_id,
                mean_fitness=event.mean_fitness,
                contribution_digest=ledger.digest,
            )
        )
    return CollectiveDemePayoffPack(
        records=tuple(records),
        ledgers=tuple(ledgers),
        replication_count=len(ordered),
    )


def evaluate_collective_deme_payoff_claim(
    pack: CollectiveDemePayoffPack,
    gate: ScientificClaimGate | None = None,
) -> ClaimDecision:
    """Runtime observation only. collective_intelligence stays blocked."""

    resolved = gate or ScientificClaimGate()
    decision = resolved.decide(ClaimRequest(_CLAIM_CEILING, {}, evidence_digests=(pack.digest,)))
    blocked = resolved.decide(ClaimRequest("collective_intelligence", {}))
    if blocked.allowed:
        raise ConfigurationError("collective_intelligence must remain blocked.")
    proved = resolved.decide(ClaimRequest("proved_collective_intelligence", {}))
    if proved.allowed:
        raise ConfigurationError("proved_collective_intelligence must remain blocked.")
    return decision


@dataclass(frozen=True, slots=True)
class DemeMeanFitnessRank:
    """Multi-deme ranking record. Group fitness, not collective intelligence."""

    deme_id: str
    rank: int
    mean_fitness: float
    member_count: int
    selected_for_replication: bool = False

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ConfigurationError("DemeMeanFitnessRank.rank must be >= 1.")
        if self.member_count < 0:
            raise ConfigurationError("member_count must be >= 0.")
        object.__setattr__(
            self, "mean_fitness", require_finite_float("mean_fitness", self.mean_fitness)
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "deme_id": self.deme_id,
            "rank": self.rank,
            "mean_fitness": self.mean_fitness,
            "member_count": self.member_count,
            "selected_for_replication": self.selected_for_replication,
            "collective_intelligence": False,
        }


@dataclass(frozen=True, slots=True)
class DemeDivisionOfLaborObservation:
    """Role×fitness shares. Assigned tags, not evolved division of labor."""

    deme_id: str
    role_counts: tuple[tuple[str, int], ...]
    fitness_share_by_role: tuple[tuple[str, float], ...]
    unique_role_count: int
    literature_gap: str = "round_robin_or_gated_roles_not_evolved_division_of_labor"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.unique_role_count < 0:
            raise ConfigurationError("unique_role_count must be >= 0.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("DemeDivisionOfLaborObservation digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "deme_id": self.deme_id,
            "role_counts": [list(item) for item in self.role_counts],
            "fitness_share_by_role": [list(item) for item in self.fitness_share_by_role],
            "unique_role_count": self.unique_role_count,
            "literature_gap": self.literature_gap,
            "evolved_division_of_labor": False,
            "collective_intelligence": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


_GAP_NOT_RUN = "not_run"


def _mean_organism_fitness(result: object) -> float:
    totals: list[float] = []
    ticks = getattr(result, "ticks", ()) or ()
    for tick in ticks:
        generation = getattr(tick, "generation_result", None)
        population = getattr(generation, "population", None) if generation is not None else None
        for item in getattr(population, "fitness", ()) if population is not None else ():
            totals.append(float(getattr(item, "score", 0.0) or 0.0))
    if not totals:
        return 0.0
    return round(sum(totals) / len(totals), 10)


def _message_count(result: object) -> int:
    count = 0
    ticks = getattr(result, "ticks", ()) or ()
    for tick in ticks:
        generation = getattr(tick, "generation_result", None)
        state = getattr(generation, "deme_state", None) if generation is not None else None
        inbox = getattr(state, "inbox", ()) if state is not None else ()
        count = max(count, len(tuple(inbox or ())))
    return int(count)


@dataclass(frozen=True, slots=True)
class GroupVsIndividualContrast:
    """Paired deme-on vs organism-only fitness. Group fitness, not intelligence."""

    seed: int
    deme_enabled_mean_fitness: float
    organism_only_mean_fitness: float
    delta: float
    selected_deme_mean_fitness: float
    unselected_deme_mean_fitness: float
    message_count: int
    ledger_digest: str = ""
    heldout_partner_status: str = _GAP_NOT_RUN
    communication_ablation_status: str = _GAP_NOT_RUN
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "deme_enabled_mean_fitness",
            "organism_only_mean_fitness",
            "delta",
            "selected_deme_mean_fitness",
            "unselected_deme_mean_fitness",
        ):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))
        if self.message_count < 0:
            raise ConfigurationError("message_count must be >= 0.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("GroupVsIndividualContrast digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "deme_enabled_mean_fitness": self.deme_enabled_mean_fitness,
            "organism_only_mean_fitness": self.organism_only_mean_fitness,
            "delta": self.delta,
            "selected_deme_mean_fitness": self.selected_deme_mean_fitness,
            "unselected_deme_mean_fitness": self.unselected_deme_mean_fitness,
            "message_count": self.message_count,
            "ledger_digest": self.ledger_digest,
            "heldout_partner_status": self.heldout_partner_status,
            "communication_ablation_status": self.communication_ablation_status,
            "group_fitness_is_not_collective_intelligence": True,
            "collective_intelligence": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class CollectiveDemeSeedRecord:
    """One seed in a Phase F deme-payoff campaign."""

    seed: int
    pack_digest: str
    replication_count: int
    deme_count: int
    message_count: int = 0
    ledger_digest: str = ""

    def __post_init__(self) -> None:
        if self.message_count < 0:
            raise ConfigurationError("message_count must be >= 0.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "pack_digest": self.pack_digest,
            "replication_count": self.replication_count,
            "deme_count": self.deme_count,
            "message_count": self.message_count,
            "ledger_digest": self.ledger_digest,
            "collective_intelligence": False,
        }


_MULTILEVEL_SCAFFOLD = "scaffold_only"


@dataclass(frozen=True, slots=True)
class CollectiveDemePayoffCampaign:
    """≥2-seed deme payoff + ranking + DoL metrics. Pass remains blocked."""

    seeds: tuple[int, ...]
    seed_records: tuple[CollectiveDemeSeedRecord, ...]
    ranks: tuple[DemeMeanFitnessRank, ...]
    division_of_labor: tuple[DemeDivisionOfLaborObservation, ...]
    replication_count: int
    contrasts: tuple[GroupVsIndividualContrast, ...] = ()
    heldout_partner_status: str = _GAP_NOT_RUN
    communication_ablation_status: str = _GAP_NOT_RUN
    multilevel_selection_experiment: str = _MULTILEVEL_SCAFFOLD
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "collective_deme_payoff_campaign_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2:
            raise ConfigurationError("CollectiveDemePayoffCampaign requires seed_count >= 2.")
        if self.contrasts and len(self.contrasts) != len(self.seeds):
            raise ConfigurationError("CollectiveDemePayoffCampaign contrasts must match seeds.")
        if self.claim_ceiling in _FORBIDDEN or self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError(
                "CollectiveDemePayoffCampaign claim_ceiling must stay runtime_observation."
            )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("CollectiveDemePayoffCampaign digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "seeds": list(self.seeds),
            "seed_records": [item.to_dict() for item in self.seed_records],
            "ranks": [item.to_dict() for item in self.ranks],
            "division_of_labor": [item.to_dict() for item in self.division_of_labor],
            "contrasts": [item.to_dict() for item in self.contrasts],
            "replication_count": self.replication_count,
            "heldout_partner_status": self.heldout_partner_status,
            "communication_ablation_status": self.communication_ablation_status,
            "multilevel_selection_experiment": self.multilevel_selection_experiment,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "proved_collective_intelligence": False,
            "major_transition_in_individuality": False,
            "group_fitness_is_not_collective_intelligence": True,
            "limitations": [
                "group_fitness_is_not_collective_intelligence",
                "role_tags_are_not_evolved_division_of_labor",
                "ranking_is_not_multilevel_selection_experiment",
                "michod_szathmary_transition_not_demonstrated",
                "heldout_partner_generalization_not_run",
                "communication_ablation_not_run",
                "multilevel_selection_experiment_is_scaffold_only",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def rank_demes_by_mean_fitness(
    result: object,
    *,
    top_k: int = 1,
) -> tuple[DemeMeanFitnessRank, ...]:
    """Rank extant demes by mean member fitness (multi-deme selection *record*).

    This is observational ranking for Phase F campaigns. It does not by itself
    run a multilevel-selection experiment and does not grant collective
    intelligence.
    """

    last_state = None
    scores: dict[str, float] = {}
    ticks = getattr(result, "ticks", ()) or ()
    for tick in ticks:
        generation = getattr(tick, "generation_result", None)
        if generation is None:
            continue
        last_state = getattr(generation, "deme_state", None)
        population = getattr(generation, "population", None)
        for item in getattr(population, "fitness", ()) if population is not None else ():
            oid = str(getattr(item, "organism_id", "") or "")
            if oid:
                scores[oid] = float(getattr(item, "score", 0.0) or 0.0)
    if last_state is None:
        return ()
    rows: list[tuple[str, float, int]] = []
    for deme in getattr(last_state, "demes", ()) or ():
        members = tuple(str(item) for item in deme.member_ids)
        member_scores = [scores.get(member_id, 0.0) for member_id in members]
        mean = round(sum(member_scores) / len(member_scores), 10) if member_scores else 0.0
        rows.append((str(deme.deme_id), mean, len(members)))
    rows.sort(key=lambda item: (-item[1], item[0]))
    selected = {item[0] for item in rows[: max(0, top_k)]}
    return tuple(
        DemeMeanFitnessRank(
            deme_id=deme_id,
            rank=index + 1,
            mean_fitness=mean,
            member_count=count,
            selected_for_replication=deme_id in selected,
        )
        for index, (deme_id, mean, count) in enumerate(rows)
    )


def build_deme_division_of_labor_observation(
    result: object,
) -> tuple[DemeDivisionOfLaborObservation, ...]:
    """Role counts and fitness shares per deme. Not evolved division of labor."""

    last_state = None
    last_organisms = ()
    scores: dict[str, float] = {}
    ticks = getattr(result, "ticks", ()) or ()
    for tick in ticks:
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
    if last_state is None:
        return ()
    role_by_id: dict[str, str] = {}
    for organism in last_organisms:
        role = getattr(getattr(organism, "phase_e_state", None), "role", None)
        kind = getattr(role, "kind", None)
        value = getattr(kind, "value", None) or (str(kind) if kind else "unassigned")
        role_by_id[str(organism.id)] = str(value)
    observations: list[DemeDivisionOfLaborObservation] = []
    for deme in getattr(last_state, "demes", ()) or ():
        counts: dict[str, int] = {}
        shares: dict[str, float] = {}
        total = 0.0
        for member_id in deme.member_ids:
            role = role_by_id.get(str(member_id), "unassigned")
            counts[role] = counts.get(role, 0) + 1
            fitness = float(scores.get(str(member_id), 0.0) or 0.0)
            shares[role] = round(shares.get(role, 0.0) + fitness, 10)
            total = round(total + fitness, 10)
        normalized = tuple(
            (role, round(value / total, 10) if total else 0.0)
            for role, value in sorted(shares.items())
        )
        observations.append(
            DemeDivisionOfLaborObservation(
                deme_id=str(deme.deme_id),
                role_counts=tuple(sorted(counts.items())),
                fitness_share_by_role=normalized,
                unique_role_count=len(counts),
            )
        )
    return tuple(observations)


def _combined_ledger_digest(pack: CollectiveDemePayoffPack) -> str:
    digests = [str(item.digest) for item in pack.ledgers]
    if not digests:
        return ""
    if len(digests) == 1:
        return digests[0]
    return canonical_digest(digests)


def _rank_split_means(ranks: Sequence[DemeMeanFitnessRank]) -> tuple[float, float]:
    selected = [item.mean_fitness for item in ranks if item.selected_for_replication]
    unselected = [item.mean_fitness for item in ranks if not item.selected_for_replication]
    selected_mean = round(sum(selected) / len(selected), 10) if selected else 0.0
    unselected_mean = round(sum(unselected) / len(unselected), 10) if unselected else 0.0
    return selected_mean, unselected_mean


def build_group_vs_individual_contrast(
    *,
    seed: int,
    deme_result: object,
    organism_result: object,
    pack: CollectiveDemePayoffPack,
    ranks: Sequence[DemeMeanFitnessRank],
) -> GroupVsIndividualContrast:
    """Paired deme-on vs organism-only fitness. Group fitness, not intelligence."""

    deme_fit = _mean_organism_fitness(deme_result)
    organism_fit = _mean_organism_fitness(organism_result)
    selected, unselected = _rank_split_means(ranks)
    return GroupVsIndividualContrast(
        seed=seed,
        deme_enabled_mean_fitness=deme_fit,
        organism_only_mean_fitness=organism_fit,
        delta=round(deme_fit - organism_fit, 10),
        selected_deme_mean_fitness=selected,
        unselected_deme_mean_fitness=unselected,
        message_count=_message_count(deme_result),
        ledger_digest=_combined_ledger_digest(pack),
    )


def run_collective_deme_payoff_campaign(
    seeds: tuple[int, ...] | list[int] = (3, 7),
    *,
    tick_count: int = 4,
    population: int = 4,
    top_k: int = 1,
) -> CollectiveDemePayoffCampaign:
    """Run ≥2 seeds of the Phase E deme substrate and aggregate payoff metrics.

    Pairs each deme-enabled seed with an organism-only control of the same
    seed/ticks/population. Ranking is observational (``top_k`` selected).
    Heldout-partner generalization and communication ablation stay ``not_run``.
    Multilevel selection stays ``scaffold_only``. Still forbids
    ``collective_intelligence``. This is a Phase F measurement campaign, not a
    major-transition experiment.
    """

    seed_tuple = tuple(int(item) for item in seeds)
    if len(seed_tuple) < 2:
        raise ConfigurationError(
            "run_collective_deme_payoff_campaign requires at least two seeds."
        )
    from codontrace.genesis.engine import GenesisEngine
    from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile

    seed_records: list[CollectiveDemeSeedRecord] = []
    all_ranks: list[DemeMeanFitnessRank] = []
    all_dol: list[DemeDivisionOfLaborObservation] = []
    contrasts: list[GroupVsIndividualContrast] = []
    replications = 0
    for seed in seed_tuple:
        spec = GenesisRuntimeProfile.phase_e_substrate_world(
            seed=seed,
            tick_count=tick_count,
            population=population,
            enable_demes=True,
            enable_roles=True,
            replicate_on_mean_fitness=0.0,
        )
        result = GenesisEngine.from_spec(spec).run_ticks()
        organism_spec = GenesisRuntimeProfile.phase_e_substrate_world(
            seed=seed,
            tick_count=tick_count,
            population=population,
            enable_demes=False,
            enable_roles=False,
        )
        organism_result = GenesisEngine.from_spec(organism_spec).run_ticks()
        pack = build_collective_deme_payoff_pack(result)
        ranks = rank_demes_by_mean_fitness(result, top_k=top_k)
        dol = build_deme_division_of_labor_observation(result)
        contrast = build_group_vs_individual_contrast(
            seed=seed,
            deme_result=result,
            organism_result=organism_result,
            pack=pack,
            ranks=ranks,
        )
        replications += pack.replication_count
        all_ranks.extend(ranks)
        all_dol.extend(dol)
        contrasts.append(contrast)
        seed_records.append(
            CollectiveDemeSeedRecord(
                seed=seed,
                pack_digest=pack.digest,
                replication_count=pack.replication_count,
                deme_count=len(ranks),
                message_count=contrast.message_count,
                ledger_digest=contrast.ledger_digest,
            )
        )
    campaign = CollectiveDemePayoffCampaign(
        seeds=seed_tuple,
        seed_records=tuple(seed_records),
        ranks=tuple(all_ranks),
        division_of_labor=tuple(all_dol),
        replication_count=replications,
        contrasts=tuple(contrasts),
        heldout_partner_status=_GAP_NOT_RUN,
        communication_ablation_status=_GAP_NOT_RUN,
        multilevel_selection_experiment=_MULTILEVEL_SCAFFOLD,
    )
    gate = ScientificClaimGate()
    if gate.decide(ClaimRequest("collective_intelligence", campaign.to_dict())).allowed:
        raise ConfigurationError("collective_intelligence must remain blocked.")
    if gate.decide(ClaimRequest("proved_collective_intelligence", campaign.to_dict())).allowed:
        raise ConfigurationError("proved_collective_intelligence must remain blocked.")
    return campaign


def evaluate_collective_deme_payoff_campaign_claim(
    campaign: CollectiveDemePayoffCampaign,
    gate: ScientificClaimGate | None = None,
) -> ClaimDecision:
    """Runtime observation only. proved collective intelligence stays blocked."""

    resolved = gate or ScientificClaimGate()
    payload = campaign.to_dict()
    decision = resolved.decide(
        ClaimRequest(_CLAIM_CEILING, payload, evidence_digests=(campaign.digest,))
    )
    for label in ("collective_intelligence", "proved_collective_intelligence"):
        blocked = resolved.decide(ClaimRequest(label, payload))
        if blocked.allowed:
            raise ConfigurationError(f"{label} must remain blocked.")
    return decision

