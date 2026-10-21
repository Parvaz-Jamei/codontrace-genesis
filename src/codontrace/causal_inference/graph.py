"""Acyclic directed mixed graphs (ADMGs) for causal identification.

Section 1 of the causal-inference layer. A graph holds directed edges
``a -> b`` and bidirected edges ``a <-> b``. A bidirected edge stands for an
unobserved common cause (a semi-Markovian model, Pearl 2009, sec. 3.5;
Tian 2002). A DAG is an ADMG with no bidirected edges.

Everything here is pure graph manipulation with deterministic (sorted)
iteration order, so every downstream result is reproducible.

Notation follows Shpitser & Pearl (2006, AAAI, "Identification of Joint
Interventional Distributions in Recursive Semi-Markovian Causal Models"):

* ``An(Y)_G`` is :meth:`CausalDiagram.ancestors` (Y included),
* ``G_{\\bar X}`` (incoming edges of X cut) is :meth:`do`,
* ``G_{\\underline X}`` (outgoing edges of X cut) is :meth:`remove_outgoing`,
* ``G[S]`` is :meth:`subgraph`,
* ``C(G)`` is :meth:`c_components`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from codontrace.errors import ConfigurationError

Edge = tuple[str, str]

__all__ = ["CausalDiagram", "Edge"]


def _norm_bi(a: str, b: str) -> Edge:
    return (a, b) if a <= b else (b, a)


@dataclass(frozen=True)
class CausalDiagram:
    """An immutable ADMG. Construction validates acyclicity of the directed part."""

    nodes: frozenset[str]
    directed: frozenset[Edge] = field(default_factory=frozenset)
    bidirected: frozenset[Edge] = field(default_factory=frozenset)

    # -- construction -------------------------------------------------
    @classmethod
    def build(
        cls,
        directed: Iterable[Edge] = (),
        bidirected: Iterable[Edge] = (),
        nodes: Iterable[str] = (),
    ) -> CausalDiagram:
        d = frozenset((str(a), str(b)) for a, b in directed)
        bi = frozenset(_norm_bi(str(a), str(b)) for a, b in bidirected)
        ns = set(map(str, nodes))
        for a, b in d | bi:
            ns.add(a)
            ns.add(b)
        return cls(frozenset(ns), d, bi)

    def __post_init__(self) -> None:
        for a, b in self.directed | self.bidirected:
            if a not in self.nodes or b not in self.nodes:
                raise ConfigurationError(f"edge {a!r}-{b!r} uses an unknown node")
            if a == b:
                raise ConfigurationError(f"self loop on {a!r}")
        for a, b in self.bidirected:
            if a > b:
                raise ConfigurationError("bidirected edges must be stored sorted; use build()")
        self.topological_order()  # raises on a directed cycle

    # -- local structure ---------------------------------------------
    def parents(self, v: str) -> frozenset[str]:
        return frozenset(a for a, b in self.directed if b == v)

    def children(self, v: str) -> frozenset[str]:
        return frozenset(b for a, b in self.directed if a == v)

    def spouses(self, v: str) -> frozenset[str]:
        out: set[str] = set()
        for a, b in self.bidirected:
            if a == v:
                out.add(b)
            elif b == v:
                out.add(a)
        return frozenset(out)

    def _closure(self, start: Iterable[str], step: Mapping[str, frozenset[str]]) -> frozenset[str]:
        seen = set(start)
        stack = sorted(seen)
        while stack:
            v = stack.pop()
            for w in step.get(v, frozenset()):
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        return frozenset(seen)

    def _parent_map(self) -> dict[str, frozenset[str]]:
        m: dict[str, set[str]] = {v: set() for v in self.nodes}
        for a, b in self.directed:
            m[b].add(a)
        return {k: frozenset(v) for k, v in m.items()}

    def _child_map(self) -> dict[str, frozenset[str]]:
        m: dict[str, set[str]] = {v: set() for v in self.nodes}
        for a, b in self.directed:
            m[a].add(b)
        return {k: frozenset(v) for k, v in m.items()}

    def ancestors(self, vs: Iterable[str]) -> frozenset[str]:
        """``An(vs)``, including ``vs`` themselves (Shpitser & Pearl 2006 convention)."""
        vs = self._check(vs)
        return self._closure(vs, self._parent_map())

    def descendants(self, vs: Iterable[str]) -> frozenset[str]:
        """``De(vs)``, including ``vs``."""
        vs = self._check(vs)
        return self._closure(vs, self._child_map())

    def topological_order(self) -> tuple[str, ...]:
        """Kahn's algorithm with lexicographic tie-breaking (deterministic)."""
        indeg = {v: 0 for v in self.nodes}
        for _, b in self.directed:
            indeg[b] += 1
        children = self._child_map()
        ready = sorted(v for v, k in indeg.items() if k == 0)
        order: list[str] = []
        while ready:
            v = ready.pop(0)
            order.append(v)
            for w in sorted(children[v]):
                indeg[w] -= 1
                if indeg[w] == 0:
                    ready.append(w)
            ready.sort()
        if len(order) != len(self.nodes):
            raise ConfigurationError("directed part of the causal diagram has a cycle")
        return tuple(order)

    # -- graph surgery ------------------------------------------------
    def subgraph(self, vs: Iterable[str]) -> CausalDiagram:
        keep = self._check(vs)
        return CausalDiagram(
            keep,
            frozenset(e for e in self.directed if e[0] in keep and e[1] in keep),
            frozenset(e for e in self.bidirected if e[0] in keep and e[1] in keep),
        )

    def do(self, xs: Iterable[str]) -> CausalDiagram:
        """``G_{\\bar X}``: remove every edge (directed or bidirected) into X."""
        x = self._check(xs)
        return CausalDiagram(
            self.nodes,
            frozenset(e for e in self.directed if e[1] not in x),
            frozenset(e for e in self.bidirected if e[0] not in x and e[1] not in x),
        )

    def remove_outgoing(self, xs: Iterable[str]) -> CausalDiagram:
        """``G_{\\underline X}``: remove directed edges out of X."""
        x = self._check(xs)
        return CausalDiagram(
            self.nodes, frozenset(e for e in self.directed if e[0] not in x), self.bidirected
        )

    def c_components(self) -> tuple[frozenset[str], ...]:
        """Maximal sets connected by bidirected paths (Tian 2002), sorted."""
        spouse: dict[str, set[str]] = {v: set() for v in self.nodes}
        for a, b in self.bidirected:
            spouse[a].add(b)
            spouse[b].add(a)
        sm = {k: frozenset(v) for k, v in spouse.items()}
        seen: set[str] = set()
        comps: list[frozenset[str]] = []
        for v in sorted(self.nodes):
            if v in seen:
                continue
            comp = self._closure([v], sm)
            seen |= comp
            comps.append(comp)
        return tuple(sorted(comps, key=lambda c: sorted(c)))

    def latent_projection_dag(self) -> tuple[CausalDiagram, frozenset[str]]:
        """Replace each ``a <-> b`` by an explicit latent ``U[a,b]`` with ``a <- U -> b``.

        Returns the DAG and the set of latent node names. Used to reduce
        m-separation in an ADMG to d-separation in a DAG (Richardson 2003).
        """
        latents = {f"U[{a},{b}]": (a, b) for a, b in self.bidirected}
        clash = set(latents) & self.nodes
        if clash:
            raise ConfigurationError(f"latent name collision: {sorted(clash)}")
        directed = set(self.directed)
        for u, (a, b) in latents.items():
            directed.add((u, a))
            directed.add((u, b))
        return (
            CausalDiagram(self.nodes | frozenset(latents), frozenset(directed), frozenset()),
            frozenset(latents),
        )

    def _check(self, vs: Iterable[str]) -> frozenset[str]:
        s = frozenset([vs] if isinstance(vs, str) else vs)
        unknown = s - self.nodes
        if unknown:
            raise ConfigurationError(f"unknown variables: {sorted(unknown)}")
        return s

    def to_dict(self) -> dict[str, list[str] | list[list[str]]]:
        return {
            "nodes": sorted(self.nodes),
            "directed": [list(e) for e in sorted(self.directed)],
            "bidirected": [list(e) for e in sorted(self.bidirected)],
        }
