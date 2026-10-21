"""Section 2: d-separation (DAGs) and m-separation (ADMGs).

``d_separated`` implements the linear-time "Reachable" procedure of Koller &
Friedman (2009, *Probabilistic Graphical Models*, Algorithm 3.1), which is the
Bayes-ball algorithm of Shachter (1998). It decides whether every path between
X and Y is blocked by Z in the sense of Pearl (2009, *Causality*, 2nd ed.,
Definition 1.2.3).

For an ADMG each bidirected edge is replaced by an explicit latent parent and
the question is answered by d-separation in that DAG; this is m-separation
(Richardson 2003, Scand. J. Statist. 30:145-157).

The property tests compare this against brute-force enumeration of all simple
paths (tests/causal_inference/test_separation_properties.py).
"""

from __future__ import annotations

from collections.abc import Iterable

from codontrace.errors import ConfigurationError

from .graph import CausalDiagram

__all__ = ["d_separated", "reachable"]


def reachable(g: CausalDiagram, xs: Iterable[str], zs: Iterable[str]) -> frozenset[str]:
    """Nodes reachable from X by an active trail given Z.

    Accepts a DAG or an ADMG. An ADMG is first replaced by its canonical DAG
    (:meth:`CausalDiagram.canonical_dag`), so the result can include latent
    ``U[a,b]`` nodes; :func:`d_separated` only intersects it with Y.
    """
    if g.bidirected:
        g, _ = g.canonical_dag()
    x = g._check(xs)
    z = g._check(zs)
    parents = g._parent_map()
    children = g._child_map()
    # Phase 1: ancestors of Z (colliders in An(Z) are opened).
    anc_z = g.ancestors(z)
    # Phase 2: traverse (node, direction) pairs. "up" means we arrived from a
    # child (travelling against the arrow), "down" means from a parent.
    visited: set[tuple[str, str]] = set()
    stack = [(v, "up") for v in sorted(x)]
    result: set[str] = set()
    while stack:
        v, d = stack.pop()
        if (v, d) in visited:
            continue
        visited.add((v, d))
        if v not in z:
            result.add(v)
        if d == "up" and v not in z:
            for p in parents[v]:
                stack.append((p, "up"))
            for c in children[v]:
                stack.append((c, "down"))
        elif d == "down":
            if v not in z:
                for c in children[v]:
                    stack.append((c, "down"))
            if v in anc_z:
                for p in parents[v]:
                    stack.append((p, "up"))
    return frozenset(result)


def d_separated(
    g: CausalDiagram, xs: Iterable[str], ys: Iterable[str], zs: Iterable[str] = ()
) -> bool:
    """True iff X and Y are d-separated (m-separated for an ADMG) given Z."""
    x = g._check(xs)
    y = g._check(ys)
    z = g._check(zs)
    if not x or not y:
        raise ConfigurationError("d-separation needs non-empty X and Y")
    if x & y:
        return False
    if (x | y) & z:
        raise ConfigurationError("X, Y and Z must be disjoint")
    return not (reachable(g, x, z) & y)
