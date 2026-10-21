"""Section 6: discrete structural causal models with exact do-semantics.

A :class:`DiscreteSCM` realises a :class:`CausalDiagram`: one binary latent
``U[a,b]`` per bidirected edge and, for every observed variable, a
conditional table ``P(v | pa(v), latents(v))``. Observational and
interventional distributions are computed by exact enumeration (no
sampling), so an identified expression evaluated on the observational joint
must equal the truncated-factorisation ground truth (Pearl 2009, eq. 3.10)
to floating-point precision.

Random parameters are drawn from :class:`codontrace.rng.RNGManager`, so a
model is a pure function of ``(diagram, seed)``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import product as _cartesian

from codontrace.errors import ConfigurationError
from codontrace.rng import RNGManager

from .expressions import DiscreteJoint, Value
from .graph import CausalDiagram

__all__ = ["DiscreteSCM"]

_EPS = 0.05  # keep every probability in [EPS, 1-EPS] so P(V) is positive


@dataclass(frozen=True)
class DiscreteSCM:
    diagram: CausalDiagram
    latent_prior: Mapping[str, float]
    # cpt[v][(parent values..., latent values...)] = P(v = 1 | ...)
    cpt: Mapping[str, Mapping[tuple[int, ...], float]]

    @classmethod
    def random(cls, diagram: CausalDiagram, seed: int) -> DiscreteSCM:
        rng = RNGManager(seed=seed, namespace="causal_inference/scm")
        dag, latents = diagram.latent_projection_dag()
        prior = {u: _EPS + (1 - 2 * _EPS) * rng.random() for u in sorted(latents)}
        cpt: dict[str, dict[tuple[int, ...], float]] = {}
        for v in diagram.topological_order():
            k = len(cls._inputs(dag, v))
            cpt[v] = {
                bits: _EPS + (1 - 2 * _EPS) * rng.random()
                for bits in _cartesian((0, 1), repeat=k)
            }
        return cls(diagram, prior, cpt)

    @staticmethod
    def _inputs(dag: CausalDiagram, v: str) -> tuple[str, ...]:
        return tuple(sorted(dag.parents(v)))

    def joint(self, do: Mapping[str, int] | None = None) -> DiscreteJoint:
        """Exact P(V) or, with ``do``, P(V | do(x)) by truncated factorisation."""
        do = dict(do or {})
        unknown = set(do) - self.diagram.nodes
        if unknown:
            raise ConfigurationError(f"unknown intervention targets: {sorted(unknown)}")
        dag, latents = self.diagram.latent_projection_dag()
        order = self.diagram.topological_order()
        lat = sorted(latents)
        table: dict[tuple[Value, ...], float] = {}
        for uvals in _cartesian((0, 1), repeat=len(lat)):
            pu = 1.0
            for u, b in zip(lat, uvals, strict=True):
                pu *= self.latent_prior[u] if b else 1.0 - self.latent_prior[u]
            env: dict[str, int] = dict(zip(lat, uvals, strict=True))
            self._accumulate(dag, order, 0, env, pu, do, table)
        domains = {v: (0, 1) for v in order}
        return DiscreteJoint(tuple(order), domains, table)

    def _accumulate(
        self,
        dag: CausalDiagram,
        order: tuple[str, ...],
        i: int,
        env: dict[str, int],
        p: float,
        do: Mapping[str, int],
        table: dict[tuple[Value, ...], float],
    ) -> None:
        if p == 0.0:
            return
        if i == len(order):
            key = tuple(env[v] for v in order)
            table[key] = table.get(key, 0.0) + p
            return
        v = order[i]
        if v in do:
            env[v] = int(do[v])
            self._accumulate(dag, order, i + 1, env, p, do, table)
            del env[v]
            return
        key = tuple(env[w] for w in self._inputs(dag, v))
        p1 = self.cpt[v][key]
        for b, pb in ((0, 1.0 - p1), (1, p1)):
            env[v] = b
            self._accumulate(dag, order, i + 1, env, p * pb, do, table)
        del env[v]
