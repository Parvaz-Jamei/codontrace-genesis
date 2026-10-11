"""Convert exported Genesis core-result JSON to recorded visualization frames."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from codontrace.visualization.frames import frame_from_population
from codontrace.visualization.recorder import publish_frame


def _emit(message: str, *, flush: bool = False) -> None:
    sys.stdout.write(message + '\n')
    if flush:
        sys.stdout.flush()


def export(input_path: Path, output: Path) -> int:
    if input_path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('export input exceeds 64 MiB; use live recorder for long runs')
    data = json.loads(input_path.read_text())
    run = data['run']; previous = None; count = 0
    # Explicit generation results are required. Summary-only reports cannot supply positions.
    for tick in data['ticks']:
        generation = tick['generation_result']
        frame = frame_from_population(generation['population'], generation['world_after'],
            run_id=run['run_id'], seed=run['seed'], summary=generation, previous=previous)
        frame['metrics_scope'] = 'one_generation'; frame['source'] = str(input_path.name)
        path = output / 'simulation' / f"seed_{run['seed']}" / f"frame_{frame['generation']:012d}.json"
        # Atomic publication; no mixing of arms or alternate engine incarnations.
        publish_frame(path, frame)
        previous = frame; count += 1
    return count


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    _emit(f'{export(args.input, args.output)} actual generation frames exported')


if __name__ == '__main__':
    main()
