"""Ask/tell search over bounded real parameters, archived in ``QDSearchArchive``.

A ``ParameterSpace`` declares named bounded parameters and how each mutates.
Emitters propose ``ParameterCandidate``s from a parent; ``tell`` records
evaluated candidates as MAP-Elites elites in the engine's ``QDSearchArchive``, binned over chosen
parameters (or caller-supplied measures). The ask/tell split mirrors pyribs
(ribs 0.12), whose ``GridArchive`` can be used as an optional backend
(``PyribsGridBackend``, extra ``[qd]``).

Randomness only comes from the ``RNGManager`` passed in. ``HillClimbEmitter``
draws exactly one ``rng.random()`` per non-fixed parameter, in declaration
order, and applies the documented clamp expressions verbatim, so existing
searches (e.g. ``codontrace.swarm.policies.PolicyArchive``) reproduce
bit-for-bit.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.qd_search import QDDescriptorConfig, QDSearchArchive, QDSearchCandidate
from codontrace.rng import RNGManager

__all__ = ['GaussianEmitter', 'HillClimbEmitter', 'MutationRule', 'ParameterBound', 'ParameterCandidate',
           'ParameterEmitter', 'ParameterSpace', 'PyribsGridBackend', 'ask_parameter_candidates',
           'parameter_descriptor_config', 'tell_parameter_results']

MUTATION_KINDS = ('fixed', 'additive', 'multiplicative', 'gaussian')


def _gauss(rng: RNGManager, sigma: float) -> float:
    """Normal draw by Box-Muller from two ``rng.random()`` draws (RNGManager has no gauss)."""
    u1 = 1.0 - rng.random()  # in (0, 1]
    u2 = rng.random()
    return sigma * math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def _digest(payload: Any) -> str:
    # Same bytes as json.dumps(sort_keys, compact separators, allow_nan=False)
    # for these string-keyed JSON payloads; see tests/test_canonical_helpers.py.
    return canonical_digest(payload)


@dataclass(frozen=True, slots=True)
class MutationRule:
    """How a hill-climb step moves one parameter.

    * ``fixed``: copied from the parent.
    * ``additive``: ``max(low, min(high, x + (r - 0.5) * scale))``.
    * ``multiplicative``: ``max(low, x * (scale + r))`` (no upper clamp).
    * ``gaussian``: ``max(low, min(high, x + N(0, scale)))`` (Box-Muller, two draws).

    ``low`` and ``high`` are used exactly as given (an ``int`` bound stays an
    ``int`` when it wins ``min``/``max``), because that is part of the output.
    """

    kind: str = 'fixed'
    scale: float = 0.0
    low: float | None = None
    high: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in MUTATION_KINDS:
            raise ValueError('unknown mutation kind')
        if self.kind != 'fixed' and not (isinstance(self.scale, (int, float)) and math.isfinite(self.scale)):
            raise ValueError('finite mutation scale required')

    def apply(self, value: float, rng: RNGManager) -> float:
        if self.kind == 'fixed':
            return value
        if self.kind == 'additive':
            moved = value + (rng.random() - 0.5) * self.scale
            return self._clamp(moved, upper=True)
        if self.kind == 'multiplicative':
            return self._clamp(value * (self.scale + rng.random()), upper=False)
        return self._clamp(value + _gauss(rng, self.scale), upper=True)

    def _clamp(self, value: float, *, upper: bool) -> float:
        if upper and self.high is not None:
            value = min(self.high, value)
        if self.low is not None:
            value = max(self.low, value)
        return value

    def to_dict(self) -> dict[str, Any]:
        return {'kind': self.kind, 'scale': self.scale, 'low': self.low, 'high': self.high}


@dataclass(frozen=True, slots=True)
class ParameterBound:
    name: str
    low: float
    high: float
    default: float
    mutation: MutationRule = field(default_factory=MutationRule)

    def __post_init__(self) -> None:
        if not self.name or not all(math.isfinite(v) for v in (self.low, self.high, self.default)):
            raise ValueError('named finite parameter bound required')
        if not self.low <= self.default <= self.high:
            raise ValueError('default outside parameter bounds')

    def to_dict(self) -> dict[str, Any]:
        return {'name': self.name, 'low': self.low, 'high': self.high, 'default': self.default,
                'mutation': self.mutation.to_dict()}


@dataclass(frozen=True, slots=True)
class ParameterSpace:
    parameters: tuple[ParameterBound, ...]

    def __post_init__(self) -> None:
        names = [p.name for p in self.parameters]
        if not names or len(names) != len(set(names)):
            raise ValueError('unique parameter names required')

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.parameters)

    def defaults(self) -> dict[str, float]:
        return {p.name: p.default for p in self.parameters}

    def contains(self, params: Mapping[str, float]) -> bool:
        return set(params) == set(self.names) and all(p.low <= params[p.name] <= p.high for p in self.parameters)

    def to_dict(self) -> dict[str, Any]:
        return {'parameters': [p.to_dict() for p in self.parameters]}

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ParameterCandidate:
    params: Mapping[str, float]
    parent_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'params', dict(self.params))
        for name, value in self.params.items():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f'parameter {name} must be finite')

    @property
    def genome(self) -> str:
        """Canonical JSON of the parameters: the archive genome string."""
        return json.dumps(dict(self.params), sort_keys=True, separators=(',', ':'), allow_nan=False)

    def to_dict(self) -> dict[str, Any]:
        return {'params': dict(sorted(self.params.items())), 'parent_id': self.parent_id}

    def digest(self) -> str:
        return _digest(self.to_dict())


class ParameterEmitter(Protocol):
    def emit(self, space: ParameterSpace, parent: Mapping[str, float], rng: RNGManager) -> dict[str, float]: ...


class HillClimbEmitter:
    """One draw per non-fixed parameter, in declaration order, using each parameter's ``MutationRule``."""

    def emit(self, space: ParameterSpace, parent: Mapping[str, float], rng: RNGManager) -> dict[str, float]:
        return {p.name: p.mutation.apply(parent[p.name], rng) for p in space.parameters}


@dataclass(frozen=True, slots=True)
class GaussianEmitter:
    """Isotropic Gaussian step scaled by each bound's width, clamped to bounds (opt-in)."""

    sigma: float = 0.1

    def emit(self, space: ParameterSpace, parent: Mapping[str, float], rng: RNGManager) -> dict[str, float]:
        return {p.name: max(p.low, min(p.high, parent[p.name] + _gauss(rng, self.sigma * (p.high - p.low))))
                for p in space.parameters}


def ask_parameter_candidates(space: ParameterSpace, emitter: ParameterEmitter, parent: Mapping[str, float],
                             rng: RNGManager, count: int) -> tuple[ParameterCandidate, ...]:
    if count < 1:
        raise ValueError('positive candidate count required')
    parent_id = ParameterCandidate(parent).digest()
    return tuple(ParameterCandidate(emitter.emit(space, parent, rng), parent_id) for _ in range(count))


def parameter_descriptor_config(space: ParameterSpace, *, bins: int = 8,
                                names: Sequence[str] | None = None) -> QDDescriptorConfig:
    """Bin the archive over parameters themselves (a parameter-space grid)."""
    chosen = tuple(names or space.names)
    bounds = {p.name: p for p in space.parameters}
    return QDDescriptorConfig(descriptor_names=chosen,
                              min_values={n: float(bounds[n].low) for n in chosen},
                              max_values={n: float(bounds[n].high) for n in chosen},
                              bins_per_descriptor={n: bins for n in chosen})


def tell_parameter_results(archive: QDSearchArchive, config: QDDescriptorConfig,
                           candidates: Sequence[ParameterCandidate], qualities: Sequence[float],
                           measures: Sequence[Mapping[str, float]] | None = None) -> tuple[QDSearchArchive, int]:
    """Insert evaluated candidates; return the new archive and how many new cells were filled.

    ``measures`` default to the candidates' own parameters.
    """
    if len(candidates) != len(qualities) or (measures is not None and len(measures) != len(candidates)):
        raise ValueError('one quality (and measure) per candidate required')
    filled = 0
    for i, (candidate, quality) in enumerate(zip(candidates, qualities, strict=True)):
        descriptors = dict(candidate.params if measures is None else measures[i])
        archive, new = archive.update(QDSearchCandidate(genome=candidate.genome, quality=float(quality),
                                                        descriptors={k: float(v) for k, v in descriptors.items()},
                                                        parent_genome=candidate.parent_id), config)
        filled += int(new)
    return archive, filled


class PyribsGridBackend:
    """Optional pyribs ``GridArchive`` mirror of a parameter-space archive (extra ``[qd]``).

    Parity with ``QDSearchArchive`` holds for the elite set when qualities in a
    cell are distinct and no measure lies within ribs' ``epsilon`` (1e-6) below
    a cell edge. Differences: ribs keeps the first of tied objectives, while
    ``QDSearchArchive`` replaces on ties; ribs adds ``epsilon`` before flooring
    the cell index. Only the archive is used (no ribs emitters), so all
    randomness stays in ``RNGManager``.
    """

    def __init__(self, space: ParameterSpace, config: QDDescriptorConfig) -> None:
        try:
            from ribs.archives import GridArchive  # type: ignore[import-not-found,unused-ignore]
        except ImportError as error:  # pragma: no cover - exercised only without the extra
            raise ImportError('PyribsGridBackend needs the optional dependency ribs (extra [qd])') from error
        self.space = space
        self.config = config
        self.names = tuple(config.descriptor_names)
        self.archive = GridArchive(solution_dim=len(space.names),
                                   dims=[config.bins_per_descriptor.get(n, 8) for n in self.names],
                                   ranges=[(config.min_values.get(n, 0.0), config.max_values.get(n, 1.0))
                                           for n in self.names])

    def tell(self, candidates: Sequence[ParameterCandidate], qualities: Sequence[float]) -> None:
        for candidate, quality in zip(candidates, qualities, strict=True):
            self.archive.add([[candidate.params[n] for n in self.space.names]], [quality],
                             [[candidate.params[n] for n in self.names]])

    def elites(self) -> dict[tuple[int, ...], tuple[dict[str, float], float]]:
        data = self.archive.data()
        out: dict[tuple[int, ...], tuple[dict[str, float], float]] = {}
        for solution, objective, index in zip(data['solution'], data['objective'], data['index'], strict=True):
            cell = tuple(int(i) for i in self.archive.int_to_grid_index([index])[0])
            out[cell] = ({n: float(v) for n, v in zip(self.space.names, solution, strict=True)}, float(objective))
        return out
