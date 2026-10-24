"""Section 4: probability expressions returned by identification.

A tiny, immutable expression tree over the *observational* distribution P(V):

* :class:`Prob` is ``P(A | B)``,
* :class:`Sum` is ``sum_{vars} body``,
* :class:`Product` and :class:`Fraction` combine terms.

Expressions print in the usual notation and evaluate exactly against a
discrete joint distribution (:class:`DiscreteJoint`). Evaluation is what lets
the tests and the engine validator compare an identified formula with a
ground-truth interventional distribution.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import product as _cartesian

from codontrace.errors import ConfigurationError

__all__ = ["Prob", "Sum", "Product", "Fraction", "Expression", "DiscreteJoint", "ONE"]

Value = int | str | bool
Assignment = Mapping[str, Value]


def _fs(vs: Iterable[str]) -> frozenset[str]:
    return frozenset([vs] if isinstance(vs, str) else vs)


@dataclass(frozen=True)
class Prob:
    """``P(target | given)`` in the observational distribution."""

    target: frozenset[str]
    given: frozenset[str] = frozenset()

    def free(self) -> frozenset[str]:
        return self.target | self.given

    def __str__(self) -> str:
        t = ",".join(sorted(self.target))
        if not self.target:
            return "1"
        return f"P({t}|{','.join(sorted(self.given))})" if self.given else f"P({t})"


@dataclass(frozen=True)
class Sum:
    over: frozenset[str]
    body: Expression

    def free(self) -> frozenset[str]:
        return self.body.free() - self.over

    def __str__(self) -> str:
        return f"sum_{{{','.join(sorted(self.over))}}} [{self.body}]"


@dataclass(frozen=True)
class Product:
    terms: tuple[Expression, ...]

    def free(self) -> frozenset[str]:
        out: frozenset[str] = frozenset()
        for t in self.terms:
            out |= t.free()
        return out

    def __str__(self) -> str:
        return " * ".join(str(t) for t in self.terms) if self.terms else "1"


@dataclass(frozen=True)
class Fraction:
    numerator: Expression
    denominator: Expression

    def free(self) -> frozenset[str]:
        return self.numerator.free() | self.denominator.free()

    def __str__(self) -> str:
        return f"({self.numerator}) / ({self.denominator})"


Expression = Prob | Sum | Product | Fraction
ONE: Expression = Product(())


def sum_over(vs: Iterable[str], body: Expression) -> Expression:
    over = _fs(vs) & body.free()
    if not over:
        return body
    if isinstance(body, Prob) and not (over & body.given):
        return Prob(body.target - over, body.given) if body.target - over else ONE
    if isinstance(body, Sum):
        return Sum(over | body.over, body.body)
    return Sum(over, body)


def product(terms: Sequence[Expression]) -> Expression:
    flat: list[Expression] = []
    for t in terms:
        if isinstance(t, Product):
            flat.extend(t.terms)
        else:
            flat.append(t)
    return flat[0] if len(flat) == 1 else Product(tuple(flat))


@dataclass
class DiscreteJoint:
    """An exact joint distribution over discrete variables.

    ``table`` maps an assignment tuple (ordered as ``variables``) to its
    probability. Marginals are cached.
    """

    variables: tuple[str, ...]
    domains: Mapping[str, tuple[Value, ...]]
    table: Mapping[tuple[Value, ...], float]
    _cache: dict[tuple[tuple[str, ...], tuple[Value, ...]], float] = field(
        default_factory=dict, repr=False
    )

    def __post_init__(self) -> None:
        if set(self.domains) != set(self.variables):
            raise ConfigurationError("domains must cover exactly the variables")
        total = sum(self.table.values())
        if abs(total - 1.0) > 1e-9:
            raise ConfigurationError(f"joint does not sum to 1 (got {total!r})")

    def marginal(self, assignment: Assignment) -> float:
        keys = tuple(sorted(assignment))
        vals = tuple(assignment[k] for k in keys)
        hit = self._cache.get((keys, vals))
        if hit is not None:
            return hit
        idx = [self.variables.index(k) for k in keys]
        total = 0.0
        for row, p in self.table.items():
            if all(row[i] == v for i, v in zip(idx, vals, strict=True)):
                total += p
        self._cache[(keys, vals)] = total
        return total

    def evaluate(
        self, expr: Expression, assignment: Assignment, *, fill_unbound: bool = False
    ) -> float:
        """Evaluate ``expr`` at ``assignment``.

        ID line 3 may add intervention variables that do not affect the
        outcome, so an identified expression can have free variables beyond
        the query (for example Z in the napkin graph). The value is the same
        for every setting of those variables; ``fill_unbound`` sets each one
        to the first value of its domain.
        """
        a = dict(assignment)
        missing = expr.free() - set(a)
        if missing and not fill_unbound:
            raise ConfigurationError(f"expression needs values for {sorted(missing)}")
        for v in sorted(missing):
            a[v] = self.domains[v][0]
        return self._eval(expr, a)

    def _eval(self, expr: Expression, a: dict[str, Value]) -> float:
        if isinstance(expr, Prob):
            num = self.marginal({v: a[v] for v in expr.target | expr.given})
            if not expr.given:
                return num
            den = self.marginal({v: a[v] for v in expr.given})
            return 0.0 if den == 0.0 else num / den
        if isinstance(expr, Product):
            out = 1.0
            for t in expr.terms:
                out *= self._eval(t, a)
                if out == 0.0:
                    return 0.0
            return out
        if isinstance(expr, Fraction):
            den = self._eval(expr.denominator, a)
            return 0.0 if den == 0.0 else self._eval(expr.numerator, a) / den
        if isinstance(expr, Sum):
            over = sorted(expr.over)
            total = 0.0
            for vals in _cartesian(*(self.domains[v] for v in over)):
                b = dict(a)
                b.update(zip(over, vals, strict=True))
                total += self._eval(expr.body, b)
            return total
        raise ConfigurationError(f"unknown expression node {type(expr).__name__}")
