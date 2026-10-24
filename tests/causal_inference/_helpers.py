"""Shared strategies and brute-force oracles for the causal-inference tests."""

from __future__ import annotations

import importlib
import os
from itertools import product as cartesian

import pytest
from hypothesis import strategies as st

from codontrace.causal_inference import CausalDiagram


@st.composite
def admgs(draw, min_nodes=2, max_nodes=6, bidirected=True):
    n = draw(st.integers(min_nodes, max_nodes))
    names = [f"V{i}" for i in range(n)]
    directed, bi = [], []
    for i in range(n):
        for j in range(i + 1, n):
            if draw(st.booleans()):
                directed.append((names[i], names[j]))
            if bidirected and draw(st.integers(0, 3)) == 0:
                bi.append((names[i], names[j]))
    # random relabelling so topological order is not the name order
    perm = draw(st.permutations(names))
    ren = dict(zip(names, perm))
    return CausalDiagram.build(
        [(ren[a], ren[b]) for a, b in directed],
        [(ren[a], ren[b]) for a, b in bi],
        nodes=perm,
    )


def brute_force_d_separated(g, x, y, z):
    """Enumerate every simple path of the skeleton (the path-blocking definition)."""
    dag, _ = g.canonical_dag()
    adj = {v: set() for v in dag.nodes}
    for a, b in dag.directed:
        adj[a].add(b)
        adj[b].add(a)
    anc_z = dag.ancestors(z)

    def blocked(path):
        for i in range(1, len(path) - 1):
            a, m, b = path[i - 1], path[i], path[i + 1]
            collider = (a, m) in dag.directed and (b, m) in dag.directed
            if collider and m not in anc_z:
                return True
            if not collider and m in z:
                return True
        return False

    def paths(start):
        stack = [[start]]
        while stack:
            p = stack.pop()
            if p[-1] in y and len(p) > 1:
                yield p
                continue
            for w in adj[p[-1]]:
                if w not in p:
                    stack.append(p + [w])

    return all(blocked(p) for s in x for p in paths(s))


def assignments(variables):
    vs = sorted(variables)
    for vals in cartesian((0, 1), repeat=len(vs)):
        yield dict(zip(vs, vals))


def backdoor_value(joint, x, y, z):
    """sum_z P(y | x, z) P(z)  (back-door adjustment), computed directly."""
    total = 0.0
    for zv in assignments(z):
        pz = joint.marginal(zv)
        den = joint.marginal({**x, **zv})
        if den:
            total += joint.marginal({**y, **x, **zv}) / den * pz
    return total


def frontdoor_value(joint, x, y, z):
    """sum_z P(z|x) sum_x' P(y|x',z) P(x')  (front-door adjustment), directly."""
    xs = sorted(x)
    total = 0.0
    for zv in assignments(z):
        pz_x = joint.marginal({**zv, **x}) / joint.marginal(x)
        inner = 0.0
        for xv in assignments(xs):
            den = joint.marginal({**xv, **zv})
            if den:
                inner += joint.marginal({**y, **xv, **zv}) / den * joint.marginal(xv)
        total += pz_x * inner
    return total


__all__ = [
    "admgs", "assignments", "backdoor_value", "brute_force_d_separated", "frontdoor_value",
]


def require_y0(module: str):
    """Import a y0 module for the oracle tests.

    Skips when y0 is not installed, except under ``CODONTRACE_REQUIRE_Y0=1``
    (set by the CI oracle job), where a missing y0 is a failure, not a skip.
    """
    if os.environ.get("CODONTRACE_REQUIRE_Y0") == "1":
        return importlib.import_module(module)
    return pytest.importorskip(module)


def to_y0(g):
    from y0.dsl import Variable
    from y0.graph import NxMixedGraph

    ng = NxMixedGraph()
    for v in sorted(g.nodes):  # y0 0.2.11 needs every node in both layers
        ng.directed.add_node(Variable(v))
        ng.undirected.add_node(Variable(v))
    for a, b in sorted(g.directed):
        ng.add_directed_edge(Variable(a), Variable(b))
    for a, b in sorted(g.bidirected):
        ng.add_undirected_edge(Variable(a), Variable(b))
    return ng


def networkx_m_separated(g, xs, ys, zs):
    """m-separation via networkx on an independent latent expansion (no project code)."""
    nx = pytest.importorskip("networkx")

    dag = nx.DiGraph()
    dag.add_nodes_from(g.nodes)
    dag.add_edges_from(g.directed)
    for k, (a, b) in enumerate(sorted(g.bidirected)):
        dag.add_edge(("latent", k), a)
        dag.add_edge(("latent", k), b)
    return nx.is_d_separator(dag, set(xs), set(ys), set(zs))
