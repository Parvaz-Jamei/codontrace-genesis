"""Section 3: back-door and front-door criteria.

* Back-door criterion: Pearl (2009, *Causality*, 2nd ed., Definition 3.3.1 and
  Theorem 3.3.2), generalised to sets: Z contains no descendant of X and
  Z d-separates X from Y in ``G_{\\underline X}``.
* Front-door criterion: Pearl (2009, Definition 3.3.3 and Theorem 3.3.4).

Both work on ADMGs: bidirected edges are latent confounders and are treated
through m-separation (see :mod:`.separation`).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from itertools import combinations

from codontrace.errors import ConfigurationError

from .graph import CausalDiagram
from .separation import d_separated

__all__ = [
    "satisfies_backdoor",
    "satisfies_frontdoor",
    "backdoor_adjustment_sets",
    "frontdoor_sets",
]


def _disjoint(
    g: CausalDiagram, xs: Iterable[str], ys: Iterable[str], zs: Iterable[str]
) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    x, y, z = g._check(xs), g._check(ys), g._check(zs)
    if x & y or x & z or y & z:
        raise ConfigurationError("X, Y and Z must be disjoint")
    if not x or not y:
        raise ConfigurationError("X and Y must be non-empty")
    return x, y, z


def satisfies_backdoor(
    g: CausalDiagram, xs: Iterable[str], ys: Iterable[str], zs: Iterable[str]
) -> bool:
    x, y, z = _disjoint(g, xs, ys, zs)
    if z & g.descendants(x):
        return False
    return d_separated(g.remove_outgoing(x), x, y, z)


def satisfies_frontdoor(
    g: CausalDiagram, xs: Iterable[str], ys: Iterable[str], zs: Iterable[str]
) -> bool:
    x, y, z = _disjoint(g, xs, ys, zs)
    if not z:
        return False
    # (i) Z intercepts every directed path from X to Y.
    no_z = g.subgraph(g.nodes - z)
    if no_z.descendants(x) & y:
        return False
    # (ii) no unblocked back-door path from X to Z.
    if not d_separated(g.remove_outgoing(x), x, z):
        return False
    # (iii) X blocks every back-door path from Z to Y.
    return d_separated(g.remove_outgoing(z), z, y, x)


def _candidate_sets(
    g: CausalDiagram, x: frozenset[str], y: frozenset[str], max_size: int | None
) -> Iterator[frozenset[str]]:
    pool = sorted(g.nodes - x - y)
    top = len(pool) if max_size is None else min(max_size, len(pool))
    for k in range(top + 1):
        for combo in combinations(pool, k):
            yield frozenset(combo)


def _minimal(sets: list[frozenset[str]]) -> tuple[frozenset[str], ...]:
    out = [s for s in sets if not any(t < s for t in sets)]
    return tuple(sorted(out, key=lambda s: (len(s), sorted(s))))


def backdoor_adjustment_sets(
    g: CausalDiagram,
    xs: Iterable[str],
    ys: Iterable[str],
    *,
    minimal: bool = True,
    max_size: int | None = None,
) -> tuple[frozenset[str], ...]:
    """All (by default inclusion-minimal) back-door sets, by exhaustive search.

    Exponential in the number of candidate nodes, intended for the small
    diagrams built over engine variables (tens of nodes).
    """
    x, y = g._check(xs), g._check(ys)
    found = [z for z in _candidate_sets(g, x, y, max_size) if satisfies_backdoor(g, x, y, z)]
    return _minimal(found) if minimal else tuple(sorted(found, key=lambda s: (len(s), sorted(s))))


def frontdoor_sets(
    g: CausalDiagram,
    xs: Iterable[str],
    ys: Iterable[str],
    *,
    minimal: bool = True,
    max_size: int | None = None,
) -> tuple[frozenset[str], ...]:
    x, y = g._check(xs), g._check(ys)
    found = [z for z in _candidate_sets(g, x, y, max_size) if satisfies_frontdoor(g, x, y, z)]
    return _minimal(found) if minimal else tuple(sorted(found, key=lambda s: (len(s), sorted(s))))
