"""Normalize actual Genesis population records; never infer death from disappearance."""
from __future__ import annotations

from typing import Any

from codontrace.swarm.protocol import integer, number, text

MAX_AGENTS = 20000


def frame_from_population(population: dict[str, Any], world: dict[str, Any], *, run_id: str,
                          seed: int, summary: dict[str, Any] | None = None,
                          previous: dict[str, Any] | None = None) -> dict[str, Any]:
    integer(seed); text(run_id, 128)
    generation = integer(population['generation'], high=999999999999); tick = integer(population['tick'])
    width = integer(world['width'], high=100000); height = integer(world['height'], high=100000)
    if width < 1 or height < 1:
        raise ValueError('positive world dimensions required')
    if 'agents' not in population and 'organisms' not in population:
        raise ValueError('explicit spatial population records required')
    raw = population.get('agents', population.get('organisms'))
    if not isinstance(raw, list) or len(raw) > MAX_AGENTS:
        raise ValueError('bounded agent records required')
    agents = []
    ids = set()
    for a in raw:
        aid = text(a.get('organism_id', a.get('id')), 256)
        if aid in ids:
            raise ValueError('duplicate agent identity')
        ids.add(aid)
        position = a['position']
        if not isinstance(position, (list, tuple)) or len(position) != 2:
            raise ValueError('2D position required')
        x = integer(position[0], high=width-1); y = integer(position[1], high=height-1)
        energy = a.get('runtime_atp')
        if energy is None and isinstance(a.get('atp_state'), dict):
            energy = a['atp_state'].get('runtime_available')
        agents.append({'id': aid, 'position': [x, y], 'energy': None if energy is None else number(energy),
                       'genome_digest': str(a.get('genome_digest', 'unknown'))[:128]})
    positions = {a['id']: a['position'] for a in agents}
    old = {} if previous is None else {a['id']: a['position'] for a in previous['agents']}
    previous_tick = -1 if previous is None else previous['tick']
    # The engine's organism-action tick can stay fixed after extinction while
    # generation boundaries continue. Generation order is the playback clock.
    if previous is not None and (tick < previous_tick or
            ('generation' in previous and generation <= previous['generation'])):
        raise ValueError('recorded generations must increase and ticks cannot reverse')
    lineage = population.get('lineage')
    if lineage is not None and not isinstance(lineage, list):
        raise ValueError('lineage must be an explicit record list')
    links = []; born = []; died = []; two_parent_births = 0
    if isinstance(lineage, list):
        lineage_ids = set()
        for record in lineage:
            aid = text(record['organism_id'], 256)
            if aid in lineage_ids:
                raise ValueError('duplicate lineage identity')
            lineage_ids.add(aid)
            # An initial snapshot has no observed interval; do not replay old births.
            if previous is None:
                continue
            birth_tick = record.get('birth_tick')
            if record.get('parent_id') and isinstance(birth_tick, int) and previous_tick < birth_tick <= tick:
                if aid in positions:
                    born.append(aid)
                parents = [record['parent_id']]
                second = record.get('second_parent_id')
                if second and second != parents[0]:
                    parents.append(second); two_parent_births += 1
                for parent in parents:
                    source = positions.get(parent, old.get(parent)); target = positions.get(aid)
                    if source is not None and target is not None:
                        links.append({'source': str(parent), 'target': aid, 'kind': 'parentage',
                                      'source_position': source, 'target_position': target,
                                      'historical_source': parent not in positions})
                if len(parents) == 2:
                    a = positions.get(parents[0], old.get(parents[0])); b = positions.get(parents[1], old.get(parents[1]))
                    if a is not None and b is not None:
                        links.append({'source': str(parents[0]), 'target': str(parents[1]), 'kind': 'two_parent_birth',
                                      'source_position': a, 'target_position': b,
                                      'historical_source': parents[0] not in positions or parents[1] not in positions})
            death_tick = record.get('death_tick')
            if isinstance(death_tick, int) and previous_tick < death_tick <= tick and aid in old:
                died.append({'id': aid, 'position': old[aid], 'position_scope': 'last_recorded_position'})
    metrics = {'population': len(agents), 'births': None, 'deaths': None,
               'two_parent_births': two_parent_births if isinstance(lineage, list) and previous is not None else None}
    if summary is not None:
        for key in ('births', 'deaths'):
            if key in summary:
                metrics[key] = integer(summary[key])
        if 'after_count' in summary and integer(summary['after_count']) != len(agents):
            raise ValueError('population count differs from engine summary')
    return {'schema': 'genesis_simulation_frame_v1', 'run_id': run_id, 'seed': seed,
            'generation': generation, 'tick': tick, 'world': {'width': width, 'height': height},
            'agents': agents, 'links': links, 'born_ids': born if previous else [],
            'deaths': died, 'metrics': metrics, 'lineage_recorded': isinstance(lineage, list),
            'world_digest': summary.get('world_after_digest') if summary else None,
            'population_digest': population.get('population_digest'),
            'position_scope': 'generation_boundary', 'events_scope': 'explicit_engine_records_only'}
