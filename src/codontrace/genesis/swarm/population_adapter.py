"""Population -> swarm members, so coordination (liveness, fusion, disagreement)
can run over organisms, demes or registry populations as well as devices.

Read-only: nothing here mutates a population. Messages produced for the core
use its plain decoded-message form (no wire schema), one session per
generation, so a new generation is a new boot session for every member.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from codontrace.genesis.population import PopulationState
    from codontrace.life_loop.populations import PopulationRegistry

__all__ = ['POPULATION_SCHEMA', 'PopulationMember', 'hello_messages', 'members_from_population',
           'members_from_registry', 'reading_messages']

POPULATION_SCHEMA = 'genesis_population_member_v1'


@dataclass(frozen=True, slots=True)
class PopulationMember:
    member_id: str
    kind: str  # 'organism' | 'deme' | 'population'
    group_id: str | None = None
    generation: int = 0
    position: tuple[int, int] | None = None
    energy: float | None = None
    member_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {'member_id': self.member_id, 'kind': self.kind, 'group_id': self.group_id,
                'generation': self.generation, 'position': None if self.position is None else list(self.position),
                'energy': self.energy, 'member_ids': list(self.member_ids)}


def members_from_population(population: PopulationState, *, include_demes: bool = True) -> tuple[PopulationMember, ...]:
    """Organisms (with deme membership, position and runtime energy), then demes."""
    demes = population.deme.demes if population.deme is not None else ()
    group_of = {member: deme.deme_id for deme in demes for member in deme.member_ids}
    out = [PopulationMember(member_id=o.id, kind='organism', group_id=group_of.get(o.id),
                            generation=population.generation,
                            position=(int(o.position[0]), int(o.position[1])),
                            energy=float(o.atp_state.runtime.current_atp))
           for o in population.organisms]
    if include_demes:
        out.extend(PopulationMember(member_id=d.deme_id, kind='deme', generation=d.generation,
                                    member_ids=tuple(d.member_ids)) for d in demes)
    return tuple(out)


def members_from_registry(registry: PopulationRegistry) -> tuple[PopulationMember, ...]:
    """One member per registered individual (grouped by population) plus one per population."""
    out: list[PopulationMember] = []
    for record in registry.populations:
        out.extend(PopulationMember(member_id=m, kind='organism', group_id=record.population_id,
                                    generation=registry.tick) for m in record.member_ids)
        out.append(PopulationMember(member_id=record.population_id, kind='population', generation=registry.tick,
                                    member_ids=record.member_ids))
    return tuple(out)


def _wire_id(member_id: str) -> str:
    # Core identifiers are [A-Za-z0-9][A-Za-z0-9_-]{0,63}; organism ids may use other characters.
    safe = ''.join(c if c.isalnum() or c in '_-' else '-' for c in member_id)
    return (safe if safe[:1].isalnum() else 'm' + safe)[:64]


def _wire_ids(members: Sequence[PopulationMember]) -> dict[str, str]:
    """``member_id -> node_id``; raises ``ValueError`` when two distinct member ids
    map to one node id (for example ``'org.1'`` and ``'org-1'``), so readings are
    never merged under one node."""
    out: dict[str, str] = {}
    owner: dict[str, str] = {}
    for m in members:
        wire = _wire_id(m.member_id)
        other = owner.setdefault(wire, m.member_id)
        if other != m.member_id:
            raise ValueError(f'member ids {other!r} and {m.member_id!r} both map to node id {wire!r}')
        out[m.member_id] = wire
    return out


def hello_messages(members: Sequence[PopulationMember], swarm_id: str, *, channel: str = 'energy',
                   quantity: str = 'energy', unit: str = 'atp') -> list[dict[str, Any]]:
    """Decoded hello messages advertising one scalar channel per member."""
    ids = _wire_ids(members)
    return [{'schema': POPULATION_SCHEMA, 'swarm_id': swarm_id, 'node_id': ids[m.member_id],
             'boot_id': f'gen-{m.generation}', 'seq': 1, 'kind': 'hello',
             'payload': {'channels': {channel: {'quantity': quantity, 'unit': unit}}, 'operations': []}}
            for m in members]


def reading_messages(members: Sequence[PopulationMember], values: Mapping[str, float], swarm_id: str, *,
                     sample_ms: int, channel: str = 'energy', quantity: str = 'energy',
                     unit: str = 'atp') -> list[dict[str, Any]]:
    """Decoded untyped readings, one per member that has a value."""
    ids = _wire_ids(members)
    return [{'schema': POPULATION_SCHEMA, 'swarm_id': swarm_id, 'node_id': ids[m.member_id],
             'boot_id': f'gen-{m.generation}', 'seq': 2, 'kind': 'reading',
             'payload': {'channel': channel, 'value': float(values[m.member_id]), 'sample_ms': sample_ms,
                         'quantity': quantity, 'unit': unit, 'processing_version': 'population-v1'}}
            for m in members if m.member_id in values]
