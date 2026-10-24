"""Section 5: identification of do-queries (ID and IDC).

``identify`` is the ID algorithm for semi-Markovian models: a recursion
over C-components that is sound and complete. It returns an expression for
``P(y | do(x))`` in terms of the observational P(V), or raises
:class:`NotIdentifiable` carrying the hedge ``(F, F')`` that witnesses
non-identifiability (an effect is identifiable exactly when no hedge exists).

``identify_conditional`` is IDC. It uses rule 2 of the do-calculus to move
conditioning variables into the intervention set.

Positivity of P(V) is assumed. The comments ``line k`` refer to the
numbered lines of the standard ID and IDC pseudocode.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from codontrace.errors import ConfigurationError

from .expressions import Expression, Fraction, Prob, product, sum_over
from .graph import CausalDiagram
from .separation import d_separated

__all__ = ["NotIdentifiable", "identify", "identify_conditional", "is_identifiable"]


class NotIdentifiable(ConfigurationError):
    """Raised by ID line 5. ``hedge`` is the pair of C-forests ``(F, F')``."""

    def __init__(self, hedge: tuple[frozenset[str], frozenset[str]]) -> None:
        self.hedge = hedge
        super().__init__(
            f"effect not identifiable; hedge F={sorted(hedge[0])}, F'={sorted(hedge[1])}"
        )


@dataclass(frozen=True)
class _Dist:
    """A distribution over ``variables`` written as an expression in P(V)."""

    expr: Expression
    variables: frozenset[str]
    base: bool  # True when expr is the observational marginal P(variables)

    def marginalize(self, drop: frozenset[str]) -> _Dist:
        keep = self.variables - drop
        if self.base:
            return _Dist(Prob(keep), keep, True)
        return _Dist(sum_over(drop & self.variables, self.expr), keep, False)

    def conditional(self, target: str, prior: frozenset[str]) -> Expression:
        """``P(target | prior)`` under this distribution."""
        if self.base:
            return Prob(frozenset([target]), prior)
        rest = self.variables - prior - {target}
        num = sum_over(rest, self.expr)
        if not prior:
            return num
        return Fraction(num, sum_over(rest | {target}, self.expr))


def _id(y: frozenset[str], x: frozenset[str], p: _Dist, g: CausalDiagram) -> Expression:
    v = g.nodes
    # line 1
    if not x:
        return p.marginalize(v - y).expr
    # line 2
    an_y = g.ancestors(y)
    if v - an_y:
        return _id(y, x & an_y, p.marginalize(v - an_y), g.subgraph(an_y))
    # line 3
    w = (v - x) - g.do(x).ancestors(y)
    if w:
        return _id(y, x | w, p, g)
    # line 4
    comps = g.subgraph(v - x).c_components()
    if len(comps) > 1:
        return sum_over(v - (y | x), product([_id(s, v - s, p, g) for s in comps]))
    (s,) = comps
    g_comps = g.c_components()
    # line 5
    if g_comps == (v,):
        raise NotIdentifiable((v, s))
    order = g.topological_order()

    def prior(vi: str) -> frozenset[str]:
        return frozenset(order[: order.index(vi)])

    # line 6
    if s in g_comps:
        terms = [p.conditional(vi, prior(vi)) for vi in order if vi in s]
        return sum_over(s - y, product(terms))
    # line 7
    for big in g_comps:
        if s < big:
            terms = [p.conditional(vi, prior(vi)) for vi in order if vi in big]
            return _id(y, x & big, _Dist(product(terms), big, False), g.subgraph(big))
    raise AssertionError("ID: unreachable (C(G\\X) must lie inside a C-component of G)")


def _sets(g: CausalDiagram, *groups: Iterable[str]) -> list[frozenset[str]]:
    out = [g._check(s) for s in groups]
    for i, a in enumerate(out):
        for b in out[i + 1 :]:
            if a & b:
                raise ConfigurationError("query variable sets must be disjoint")
    return out


def identify(g: CausalDiagram, ys: Iterable[str], xs: Iterable[str]) -> Expression:
    """Expression for ``P(ys | do(xs))`` over P(V), or raise :class:`NotIdentifiable`.

    The expression may keep free variables outside ``ys | xs`` that ID line 3
    added to the intervention set; its value does not depend on them (see
    :meth:`DiscreteJoint.evaluate`, ``fill_unbound``).
    """
    y, x = _sets(g, ys, xs)
    if not y:
        raise ConfigurationError("outcome set must be non-empty")
    return _id(y, x, _Dist(Prob(g.nodes), g.nodes, True), g)


def identify_conditional(
    g: CausalDiagram, ys: Iterable[str], xs: Iterable[str], zs: Iterable[str]
) -> Expression:
    """IDC: expression for ``P(ys | do(xs), zs)``."""
    y, x, z = _sets(g, ys, xs, zs)
    if not y:
        raise ConfigurationError("outcome set must be non-empty")
    for zi in sorted(z):
        rest = z - {zi}
        if d_separated(g.do(x).remove_outgoing({zi}), y, {zi}, x | rest):
            return identify_conditional(g, y, x | {zi}, rest)
    joint = identify(g, y | z, x)
    if not z:
        return joint
    return Fraction(joint, sum_over(y, joint))


def is_identifiable(g: CausalDiagram, ys: Iterable[str], xs: Iterable[str]) -> bool:
    try:
        identify(g, ys, xs)
    except NotIdentifiable:
        return False
    return True
