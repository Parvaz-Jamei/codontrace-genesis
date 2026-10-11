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
    """Generation-boundary frame recorder.

    Lineage is an append-only tuple whose existing records only change by gaining
    a ``death_tick``. The incremental cursor therefore checks records appended
    since the previous frame plus records still open (alive) at that frame, so a
    frame costs O(new + living) instead of O(entire history). Any violated
    assumption (shrunk tuple, changed identity) falls back to a full scan.
    ``lineage_cursor=False`` keeps the full scan for verification.
    """

    def __init__(self, directory: Path, *, every: int = 1, lineage_cursor: bool = True) -> None:
        if type(every) is not int or not 1 <= every <= 10000:
            raise ValueError('sampling interval must be 1..10000')
        if type(lineage_cursor) is not bool:
            raise ValueError('lineage_cursor must be boolean')
        self.directory = Path(directory); self.every = every
        self.engine: Any = None; self.previous: dict[str, Any] | None = None
        self._lock = threading.RLock()
        self._births = 0; self._deaths = 0
        self.lineage_cursor = lineage_cursor
        self._lineage_seen = 0
        self._lineage_open: dict[int, str] = {}
        self.lineage_full_scans = 0

    def _reset_cursor(self, lineage: Any) -> None:
        self._lineage_seen = len(lineage)
        self._lineage_open = {i: r.organism_id for i, r in enumerate(lineage) if r.death_tick is None}

    def _interval_lineage(self, lineage: Any, previous_tick: int, tick: int) -> list[Any]:
        """Records born or dead in (previous_tick, tick], in lineage order."""
        def hit(record: Any) -> bool:
            return ((record.birth_tick is not None and previous_tick < record.birth_tick <= tick)
                    or (record.death_tick is not None and previous_tick < record.death_tick <= tick))
        consistent = (self.lineage_cursor and len(lineage) >= self._lineage_seen and
                      all(lineage[i].organism_id == oid for i, oid in self._lineage_open.items()))
        if not consistent:
            self.lineage_full_scans += 1
            selected = [r for r in lineage if hit(r)]
            self._reset_cursor(lineage)
            return selected
        indices = [i for i in self._lineage_open if hit(lineage[i])]
        indices += [i for i in range(self._lineage_seen, len(lineage)) if hit(lineage[i])]
        for i in list(self._lineage_open):
            if lineage[i].death_tick is not None:
                del self._lineage_open[i]
        for i in range(self._lineage_seen, len(lineage)):
            if lineage[i].death_tick is None:
                self._lineage_open[i] = lineage[i].organism_id
        self._lineage_seen = len(lineage)
        return [lineage[i] for i in sorted(indices)]

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
            cursor = (self._lineage_seen, dict(self._lineage_open))
            try:
                return self._capture_frame(population, pop, previous_tick, summary)
            except BaseException:
                # The cursor advances only with a published frame.
                self._lineage_seen, self._lineage_open = cursor
                raise

    def _capture_frame(self, population: Any, pop: dict[str, Any], previous_tick: int,
                       summary: dict[str, Any] | None) -> dict[str, Any]:
        with self._lock:
            # Serialize interval events only; never duplicate old historical lineage.
            if self.previous is None:
                self._reset_cursor(population.lineage)
                pop['lineage'] = []
            else:
                pop['lineage'] = [record.to_dict() for record in
                                  self._interval_lineage(population.lineage, previous_tick, population.tick)]
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
