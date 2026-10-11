"""Opt-in generation recorder. No changes to simulation RNG or engine fitness."""
from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path
from typing import Any

from codontrace.visualization.frames import frame_from_population


def publish_frame(target: Path, frame: dict[str, Any]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError('frame already recorded; use a separate run directory')
    temp = target.with_suffix(f'.{os.getpid()}.{threading.get_ident()}.tmp')
    try:
        with temp.open('x', encoding='utf-8') as handle:
            json.dump(frame, handle, separators=(',', ':'), allow_nan=False)
            handle.flush(); os.fsync(handle.fileno())
        # Atomic publication without overwriting a competing writer.
        os.link(temp, target)
    finally:
        temp.unlink(missing_ok=True)


class SimulationRecorder:
    def __init__(self, directory: Path, *, every: int = 1) -> None:
        if type(every) is not int or not 1 <= every <= 10000:
            raise ValueError('sampling interval must be 1..10000')
        self.directory = Path(directory); self.every = every
        self.engine: Any = None; self.previous: dict[str, Any] | None = None
        self._lock = threading.RLock()
        self._births = 0; self._deaths = 0

    def attach(self, engine: Any) -> SimulationRecorder:
        with self._lock:
            if self.engine is not None:
                raise ValueError('recorder already attached')
            self.engine = engine
            try:
                self.capture(summary=None)
            except Exception:
                self.engine = None
                raise
            engine.generation_boundary_observers.append(self)
            return self

    def __call__(self, *, generation_index: int) -> None:
        # Read existing committed tick outcomes, never change them.
        with self._lock:
            if self.engine is None:
                raise ValueError('attach recorder first')
            latest = self.engine._tick_results[-1].generation_result
            self._births += latest.births; self._deaths += latest.deaths
            if generation_index % self.every == 0:
                self.capture(summary={'births': self._births, 'deaths': self._deaths,
                                      'after_count': latest.after_count, 'world_after_digest': latest.world_after_digest})

    def finalize(self) -> dict[str, Any]:
        with self._lock:
            if self.engine is None:
                raise ValueError('attach recorder first')
            if self.previous is not None and self.previous['generation'] == self.engine.runner.population.generation:
                return copy.deepcopy(self.previous)
            latest = self.engine._tick_results[-1].generation_result
            return self.capture(summary={'births': self._births, 'deaths': self._deaths,
                                         'after_count': latest.after_count, 'world_after_digest': latest.world_after_digest})

    def capture(self, *, summary: dict[str, Any] | None) -> dict[str, Any]:
        with self._lock:
            if self.engine is None:
                raise ValueError('attach recorder first')
            population = self.engine.runner.population
            snapshots = self.engine._snapshots
            committed = snapshots[-1] if snapshots and snapshots[-1].generation == population.generation else self.engine.snapshot().population
            pop = committed.to_dict()
            previous_tick = -1 if self.previous is None else self.previous['tick']
            # Serialize interval events only; never duplicate old historical lineage.
            # Scan is still O(total lineage); core snapshot retention is unchanged.
            pop['lineage'] = [] if self.previous is None else [record.to_dict() for record in population.lineage
                if (record.birth_tick is not None and previous_tick < record.birth_tick <= population.tick)
                or (record.death_tick is not None and previous_tick < record.death_tick <= population.tick)]
            frame = frame_from_population(pop, self.engine.runner.world.to_dict(),
                                          run_id=self.engine.run.run_id, seed=self.engine.run.seed,
                                          summary=summary, previous=self.previous)
            frame['metrics_scope'] = 'since_previous_recorded_frame'
            seed_dir = self.directory / 'simulation' / f'seed_{self.engine.run.seed}'
            target = seed_dir / f"frame_{frame['generation']:012d}.json"
            publish_frame(target, frame)
            self._births = 0; self._deaths = 0
            self.previous = frame
            return copy.deepcopy(frame)
