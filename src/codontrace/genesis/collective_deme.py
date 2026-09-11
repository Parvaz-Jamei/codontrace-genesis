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
        "devosoft/avida DEMES_* / GermlineReplication: replicate a deme when "
        "mean fitness clears a threshold; copy a germline/propagule.",
    ),
    (
        "goldsby_messaging",
        "Goldsby et al. coordination instructions (send/retrieve/broadcast/"
        "block_propagation) remain the messaging subset; this pack attributes "
        "payoff, not language.",
    ),
    (
        "gecco_2008_digital_germlines",
        "GECCO 2008 digital germlines / cooperative networks: soma vs germline "
        "eligibility tags. Role tags are gates, not evolved division of labor.",
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
    return decision
