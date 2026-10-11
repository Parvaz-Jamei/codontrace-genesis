"""Bounded, contained read-only access to recorded simulation frames."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from codontrace.console.runs import get_safe_run_dir
from codontrace.contracts.wire_validation import bounded_int as integer
from codontrace.contracts.wire_validation import bounded_text as text
from codontrace.contracts.wire_validation import finite_number as number
from codontrace.contracts.wire_validation import wire_canonical as canonical

MAX_FILE_BYTES = 8 * 1024 * 1024


def _contained(path: Path, root: Path) -> Path:
    result = path.resolve()
    if not result.is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError('simulation artifact escapes run directory')
    return result


def validate_frame(row: Any, seed: int) -> dict[str, Any]:
    if not isinstance(row, dict) or row.get('schema') != 'genesis_simulation_frame_v1' or row.get('seed') != seed:
        raise ValueError('frame schema or seed mismatch')
    canonical(row)  # reject non-finite numbers anywhere, including optional provenance
    integer(row['seed']); integer(row['generation'], high=999999999999); integer(row['tick']); text(row['run_id'], 128)
    if type(row['lineage_recorded']) is not bool:
        raise ValueError('lineage recording flag required')
    width=integer(row['world']['width'],high=100000);height=integer(row['world']['height'],high=100000)
    if not width or not height: raise ValueError('positive world dimensions required')
    agents=row['agents'];links=row['links'];deaths=row['deaths'];born=row['born_ids']
    if not all(isinstance(x,list) for x in (agents,links,deaths,born)) or len(agents)>20000 or len(links)>60000 or len(deaths)>20000 or len(born)>20000:
        raise ValueError('bounded frame arrays required')
    ids=set()
    def position(p: Any) -> None:
        if not isinstance(p,list) or len(p)!=2: raise ValueError('position pair required')
        integer(p[0], high=width-1);integer(p[1], high=height-1)
    for a in agents:
        aid=text(a['id'],256);position(a['position']);text(a['genome_digest'],128)
        if aid in ids or a['position'][0]>=width or a['position'][1]>=height: raise ValueError('invalid agent identity/position')
        ids.add(aid)
        if a['energy'] is not None: number(a['energy'])
    for link in links:
        if link['kind'] not in ('parentage','two_parent_birth'): raise ValueError('unknown recorded link type')
        position(link['source_position']);position(link['target_position']);text(link['source'],256);text(link['target'],256)
        if type(link['historical_source']) is not bool: raise ValueError('historical source flag required')
        if link['kind'] == 'parentage' and link['target'] not in ids:
            raise ValueError('parentage target requires a living recorded child')
    death_ids=set()
    for d in deaths:
        did=text(d['id'],256);position(d['position'])
        if did in death_ids or did in ids: raise ValueError('duplicate or living death identity')
        death_ids.add(did)
    born_ids=set()
    for aid in born:
        text(aid,256)
        if aid in born_ids or aid not in ids: raise ValueError('duplicate birth or missing recorded position')
        born_ids.add(aid)
    metrics=row['metrics']
    if integer(metrics['population'])!=len(agents): raise ValueError('population count mismatch')
    for key in ('births','deaths','two_parent_births'):
        if metrics[key] is not None: integer(metrics[key])
    for key, markers in (('births',born),('deaths',deaths)):
        if metrics[key] is not None and len(markers)>metrics[key]:
            raise ValueError('event markers exceed recorded count')
    if metrics['births'] is not None and metrics['two_parent_births'] is not None and metrics['two_parent_births']>metrics['births']:
        raise ValueError('two-parent births exceed total births')
    return row


def read_simulation(run_id: str, *, seed: int | None = None, cursor: int = 0,
                    limit: int = 8) -> dict[str, Any]:
    integer(cursor, high=100000); integer(limit, high=32)
    if limit < 1:
        raise ValueError('positive limit required')
    if seed is not None:
        integer(seed)
    root = get_safe_run_dir(run_id, must_exist=True)
    if root is None:
        raise FileNotFoundError('run not found')
    source = root / 'simulation'
    if not source.is_dir():
        source = root / 'output' / 'simulation'
    if not source.is_dir():
        return {'schema': 'genesis_simulation_page_v1', 'run_id': run_id, 'available': False,
                'seeds': [], 'frames': [], 'total_frames': 0, 'reason': 'No spatial frames recorded. Attach SimulationRecorder before running.'}
    _contained(source, root)
    seeds = []
    for entry in source.iterdir():
        match = re.fullmatch(r'seed_(\d{1,16})', entry.name)
        if entry.is_dir() and match:
            _contained(entry, root)
            value=integer(int(match[1]))
            if entry.name != f'seed_{value}': raise ValueError('noncanonical seed directory')
            seeds.append(value)
            if len(seeds) > 256:
                raise ValueError('seed listing exceeds supported session size')
    seeds.sort()
    selected = seeds[0] if seed is None and seeds else seed
    if selected is None or selected not in seeds:
        return {'schema': 'genesis_simulation_page_v1', 'run_id': run_id, 'available': False,
                'seeds': seeds, 'frames': [], 'total_frames': 0, 'reason': 'Selected seed has no recorded frames.'}
    directory = _contained(source / f'seed_{selected}', root)
    files = []
    for p in directory.iterdir():
        if re.fullmatch(r'frame_\d{12}\.json', p.name):
            files.append(p)
            if len(files) > 100000:
                raise ValueError('frame index exceeds supported limit')
    files.sort(key=lambda p: p.name)
    expected_run = None
    if files:
        first = _contained(files[0], root)
        with first.open('rb') as handle:
            anchor_content = handle.read(MAX_FILE_BYTES+1)
        if len(anchor_content) > MAX_FILE_BYTES:
            raise ValueError('oversized stream anchor')
        anchor = validate_frame(json.loads(anchor_content), selected)
        if anchor['generation'] != int(first.stem.split('_')[1]):
            raise ValueError('anchor generation/filename mismatch')
        expected_run = anchor['run_id']
    frames = []; budget = 16 * 1024 * 1024
    for path in files[cursor:cursor+limit]:
        _contained(path, root)
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise ValueError('oversized simulation frame')
        if size > budget:
            break
        with path.open('rb') as handle:
            content = handle.read(MAX_FILE_BYTES+1)
        if len(content) > MAX_FILE_BYTES:
            raise ValueError('oversized simulation frame')
        if len(content) > budget:
            break
        row = validate_frame(json.loads(content), selected)
        if row['generation'] != int(path.stem.split('_')[1]):
            raise ValueError('frame generation/filename mismatch')
        if row['run_id'] != expected_run:
            raise ValueError('mixed engine runs within one seed stream')
        frames.append(row); budget -= len(content)
    return {'schema': 'genesis_simulation_page_v1', 'run_id': run_id, 'available': bool(files),
            'seeds': seeds, 'seed': selected, 'cursor': cursor, 'next_cursor': cursor+len(frames),
            'total_frames': len(files), 'generations': [int(p.stem.split('_')[1]) for p in files],
            'frames': frames, 'source': 'recorded_generation_boundaries', 'interpolation': False}
