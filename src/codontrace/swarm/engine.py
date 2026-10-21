"""Explicit generation-boundary integration; never replaces GenesisEngine."""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from codontrace.swarm.runtime import SwarmCoordinator


class SwarmEngineLink:
    """Observer attached to a real GenesisEngine, with opt-in physical-input mapping.

    Default records sensor context without changing the ALife ecology. A mapper,
    if supplied, changes a generation's input world through link.run_ticks().
    This does not imply digital ATP equals measured joules.
    """
    def __init__(self, coordinator: SwarmCoordinator, *, quantity: str, unit: str,
                 clock_ms: Callable[[], int] | None = None,
                 environment_mapper: Callable[[Any, dict[str, Any]], None] | None = None,
                 request_budget: int = 0, required: bool | None = None) -> None:
        if type(request_budget) is not int or not 0 <= request_budget <= 32:
            raise ValueError('request budget must be 0..32')
        self.coordinator = coordinator; self.quantity = quantity; self.unit = unit
        self.clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        self.environment_mapper = environment_mapper; self.request_budget = request_budget
        self.required = environment_mapper is not None if required is None else required
        if type(self.required) is not bool:
            raise ValueError('required must be boolean')
        if environment_mapper is not None and not self.required:
            raise ValueError('sensor-mapped experiments require strict input failures')
        self.last_error: dict[str, Any] | None = None
        self.errors: list[dict[str, Any]] = []
        self.engine: Any = None
        self._mapping: dict[str, Any] | None = None

    def attach(self, engine: Any) -> SwarmEngineLink:
        if self.engine is not None:
            raise ValueError('link already attached')
        self.engine = engine
        engine.generation_boundary_observers.append(self)
        return self

    def _failure(self, error: Exception, phase: str, generation: int) -> None:
        self.last_error = {'phase': phase, 'generation': generation, 'error_type': type(error).__name__,
                           'experiment_requires_swarm': self.required}
        self.errors.append(self.last_error.copy()); self.errors = self.errors[-128:]
        if self.required:
            raise RuntimeError('required Swarm input/evidence unavailable; inspect link.last_error') from error

    def __call__(self, *, generation_index: int) -> None:
        try:
            self._observe(generation_index=generation_index)
            self.last_error = None
        except (OSError, ValueError, TypeError, KeyError) as error:
            self._failure(error, 'generation_boundary', generation_index)

    def _observe(self, *, generation_index: int) -> None:
        if self.engine is None:
            raise ValueError('attach link to an engine first')
        now = self.clock_ms()
        fusion = self.coordinator.fuse(self.quantity, self.unit, now_ms=now)
        mapping = self._mapping or {'mapped': False, 'before': self.engine.runner.world.digest(),
                                    'after': self.engine.runner.world.digest()}
        running = self.coordinator.snapshot(now_ms=now)['state']['status'] == 'running'
        commands = self.coordinator.plan(self.quantity, self.unit, now_ms=now,
                                         budget=self.request_budget) if self.request_budget and running else []
        self.coordinator.boundary({'generation': generation_index, 'engine_run_id': self.engine.run.run_id,
            'spec_digest': self.engine.spec.digest(), 'fusion': mapping.get('fusion', fusion), 'mapped_before_generation': mapping['mapped'],
            'world_before': mapping['before'], 'world_after': mapping['after'],
            'command_ids': [c['command_id'] for c in commands]}, now_ms=now)

    def run_ticks(self, count: int | None = None) -> Any:
        """Explicit sensor-input wrapper; mapping happens BEFORE each engine step."""
        if self.engine is None:
            raise ValueError('attach link first')
        count = self.engine.spec.tick_count if count is None else count
        if type(count) is not int or count < 0:
            raise ValueError('nonnegative integer tick count required')
        result = None
        for _ in range(count):
            now = self.clock_ms()
            try:
                fusion = self.coordinator.fuse(self.quantity, self.unit, now_ms=now)
                if self.required and fusion['value'] is None:
                    raise ValueError('required fresh sensor data unavailable')
            except (OSError, ValueError, TypeError, KeyError) as error:
                self._failure(error, 'before_generation', self.engine.runner.population.generation)
                fusion = {'value': None, 'status': 'swarm_unavailable'}
            before = self.engine.runner.world.digest()
            mapped = self.environment_mapper is not None and fusion['value'] is not None
            if mapped and self.environment_mapper is not None:  # same condition; narrows for mypy
                self.environment_mapper(self.engine.runner.world, fusion)
            self._mapping = {'mapped': mapped, 'before': before, 'after': self.engine.runner.world.digest(), 'fusion': fusion}
            try:
                result = self.engine.run_ticks(1)
            finally:
                self._mapping = None
        return self.engine.run_ticks(0) if result is None else result
