"""IDC verdicts: textbook cases, a y0 oracle, and the resolved y0 disagreements.

IDC (sound and complete) moves a conditioning variable ``Z_i`` into the
intervention set exactly when rule 2 of the do-calculus licenses it,
``(Y _||_ Z_i | X, Z - {Z_i})`` in ``G_{bar X, underline Z_i}``, and
otherwise answers ``ID(Y u Z, X) / sum_Y ID(Y u Z, X)``.

Every "identifiable" verdict here is checked numerically against the
truncated factorisation of random discrete SCMs, so an incomplete IDC (one
that refuses a query it could answer) fails these tests.

y0 0.2.11 (BSD-3-Clause) is the external oracle. Its
``are_d_separated`` moralises over directed parents only and so ignores
bidirected edges (``y0/algorithm/conditional_independencies.py``,
``y0/graph.py: iter_moral_links``); on ADMGs its IDC rule-2 test is therefore
wrong. The oracle used here is y0's IDC and ID with that one predicate
replaced by networkx m-separation on an independent latent expansion.
``test_y0_disagreements_are_y0_rule2_errors`` pins the eight raw y0
disagreements found by a 600-graph differential run and shows, by exact
computation, that each is an invalid rule-2 exchange inside y0.
"""

from __future__ import annotations

import itertools

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# The y0 oracle and the rule-2 checks use networkx m-separation.
pytest.importorskip("networkx")

from codontrace.causal_inference import CausalDiagram, NotIdentifiable, d_separated, identify_conditional
from codontrace.causal_inference.scm import DiscreteSCM

from ._helpers import admgs, assignments, networkx_m_separated, require_y0, to_y0

B = CausalDiagram.build


def _verdict(g, y, x, z):
    try:
        return identify_conditional(g, y, x, z)
    except NotIdentifiable:
        return None


def _cond(joint, ya, za):
    pz = joint.marginal(za)
    return None if pz <= 0 else joint.marginal({**ya, **za}) / pz


def _assert_idc_matches_truth(g, y, x, z, expr, seeds=(1, 2, 3)):
    for seed in seeds:
        scm = DiscreteSCM.random(g, seed)
        obs = scm.joint()
        for xa in assignments(x):
            truth = scm.joint(xa)
            for za in assignments(z):
                for ya in assignments(y):
                    want = _cond(truth, ya, za)
                    got = obs.evaluate(expr, {**xa, **ya, **za}, fill_unbound=True)
                    assert got == pytest.approx(want, abs=1e-9), (str(expr), xa, ya, za)


# (graph, Y, X, Z, identifiable). Each entry names its source or what it pins.
IDC_CASES = {
    # Conditioning on a mediator with the treatment confounded with it:
    # P(c | do(a), b) = P(c | do(a, b)) by rule 2 in G_{bar A, underline B}.
    # Needs the underline (kills an IDC that skips G_{underline Z}).
    "mediator_condition": (B([("A", "B"), ("B", "C")], [("A", "B")]), {"C"}, {"A"}, {"B"}, True),
    # A cause of the treatment given a confounded downstream variable:
    # in G_{bar B} A is cut off, so P(a | do(b), c) = P(a | do(b, c)).
    # Needs the bar (kills an IDC that skips G_{bar X}).
    "upstream_outcome": (B([("A", "B"), ("B", "C")], [("B", "C")]), {"A"}, {"B"}, {"C"}, True),
    # Bidirected edges into X must be cut by do(X), as in G_{bar X}
    # (a do() removes every edge into X). Kills a do() that keeps them.
    "bidirected_into_treatment": (
        B([("B", "D"), ("B", "E"), ("C", "E")], [("A", "B"), ("B", "C"), ("B", "E")]),
        {"A"}, {"B"}, {"E"}, True,
    ),
    # Bow arc with a covariate observed on X's side:
    # the joint P(y, z | do(x)) has a hedge and Z cannot be moved.
    "bow_conditioned": (B([("Z", "X"), ("X", "Y")], [("X", "Y")]), {"Y"}, {"X"}, {"Z"}, False),
    # Front door, conditioning on the mediator.
    "front_door_given_mediator": (B([("X", "Z"), ("Z", "Y")], [("X", "Y")]), {"Y"}, {"X"}, {"Z"}, True),
    # Back door, conditioning on the confounder (back-door adjustment).
    "back_door_given_confounder": (B([("Z", "X"), ("Z", "Y"), ("X", "Y")]), {"Y"}, {"X"}, {"Z"}, True),
}


@pytest.mark.parametrize("name", sorted(IDC_CASES))
def test_idc_textbook_verdicts_and_values(name):
    g, y, x, z, identifiable = IDC_CASES[name]
    expr = _verdict(g, y, x, z)
    assert (expr is not None) == identifiable
    if expr is not None:
        _assert_idc_matches_truth(g, y, x, z, expr)


def _y0_idc_verdict(g, y, x, z):
    """y0 IDC with its rule-2 predicate on networkx m-separation (see module doc)."""
    id_c = require_y0("y0.algorithm.identify.id_c")
    api = require_y0("y0.algorithm.identify")
    from y0.dsl import Variable

    def rule_2(identification, condition):
        treat = {str(v) for v in identification.treatments}
        cond = {str(v) for v in identification.conditions} - {str(condition)}
        outs = {str(v) for v in identification.outcomes}
        mod = g.do(treat).remove_outgoing({str(condition)})
        return networkx_m_separated(mod, outs, {str(condition)}, treat | cond)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(id_c, "rule_2_of_do_calculus_applies", rule_2)
        return api.identify_outcomes(
            to_y0(g), treatments={Variable(v) for v in x}, outcomes={Variable(v) for v in y},
            conditions={Variable(v) for v in z},
        ) is not None


@pytest.mark.parametrize("name", sorted(IDC_CASES))
def test_idc_textbook_verdicts_agree_with_y0(name):
    g, y, x, z, identifiable = IDC_CASES[name]
    assert _y0_idc_verdict(g, y, x, z) == identifiable


@settings(max_examples=200, deadline=None)
@given(data=st.data())
def test_idc_verdicts_agree_with_y0(data):
    """Completeness and soundness of IDC verdicts against the y0 oracle."""
    import networkx as nx

    g = data.draw(admgs(min_nodes=3, max_nodes=6))
    nodes = sorted(g.nodes)
    x = data.draw(st.sets(st.sampled_from(nodes), min_size=1, max_size=2))
    rest = [v for v in nodes if v not in x]
    y = data.draw(st.sets(st.sampled_from(rest), min_size=1, max_size=2))
    rest = [v for v in rest if v not in y]
    assume(rest)
    z = data.draw(st.sets(st.sampled_from(rest), min_size=1, max_size=3))
    try:
        theirs = _y0_idc_verdict(g, y, x, z)
    except nx.NetworkXError:
        # y0 0.2.11 NxMixedGraph.remove_in_edges drops isolated nodes; no verdict.
        assume(False)
    expr = _verdict(g, y, x, z)
    assert (expr is not None) == theirs
    if expr is not None:
        _assert_idc_matches_truth(g, y, x, z, expr, seeds=(data.draw(st.integers(0, 10_000)),))


# The eight raw disagreements with unpatched y0 0.2.11 (differential run,
# 600 random ADMGs, seed 1): graph, X, Y, Z, our verdict, the condition
# y0's rule 2 wrongly moves.
_D = [
    ([("V2", "V1"), ("V4", "V3"), ("V5", "V0"), ("V5", "V1"), ("V5", "V3"), ("V5", "V4")],
     [("V1", "V5"), ("V3", "V4")], {"V0"}, {"V2", "V4"}, {"V1", "V3", "V5"}, True, "V5"),
    ([("V0", "V2"), ("V3", "V0"), ("V3", "V2"), ("V4", "V0")], [("V1", "V2"), ("V2", "V4"), ("V3", "V4")],
     {"V0", "V3"}, {"V1"}, {"V2", "V4"}, False, "V4"),
    ([("V0", "V4"), ("V0", "V5"), ("V1", "V3"), ("V2", "V3"), ("V2", "V4"), ("V3", "V4"), ("V5", "V3"),
      ("V5", "V4")], [("V4", "V5")], {"V1"}, {"V3"}, {"V0", "V4", "V5"}, True, "V5"),
    ([("V0", "V1"), ("V0", "V4"), ("V0", "V5"), ("V0", "V6"), ("V2", "V1"), ("V2", "V4"), ("V5", "V1"),
      ("V6", "V1")], [("V1", "V4"), ("V1", "V5"), ("V2", "V6"), ("V3", "V6")],
     {"V0", "V5"}, {"V3"}, {"V1", "V6"}, False, "V1"),
    ([("V0", "V2"), ("V1", "V3"), ("V2", "V3"), ("V4", "V1"), ("V4", "V3"), ("V4", "V6"), ("V5", "V6"),
      ("V6", "V2"), ("V6", "V3")], [("V0", "V4"), ("V0", "V6"), ("V1", "V3"), ("V2", "V3"), ("V2", "V5"),
                                    ("V3", "V4")], {"V2"}, {"V6"}, {"V0", "V1", "V4"}, True, "V4"),
    ([("V1", "V0"), ("V4", "V0")], [("V0", "V3"), ("V3", "V4")], {"V2", "V4"}, {"V1"}, {"V0", "V3"},
     False, "V3"),
    ([("V0", "V5"), ("V1", "V4"), ("V1", "V5"), ("V2", "V0"), ("V2", "V5"), ("V3", "V4"), ("V4", "V0"),
      ("V4", "V5"), ("V6", "V1"), ("V6", "V4"), ("V6", "V5")],
     [("V0", "V1"), ("V0", "V6"), ("V1", "V3"), ("V3", "V4"), ("V4", "V5")],
     {"V2"}, {"V1"}, {"V0", "V4", "V6"}, True, "V6"),
    ([("V0", "V1"), ("V0", "V2"), ("V0", "V3"), ("V0", "V4"), ("V2", "V3")],
     [("V0", "V1"), ("V1", "V2"), ("V1", "V3")], {"V4"}, {"V2", "V3"}, {"V0", "V1"}, True, "V0"),
]
DISAGREEMENTS = [
    pytest.param(CausalDiagram.build(d, b, nodes=[f"V{i}" for i in range(7)]).subgraph(
        {v for e in d + b for v in e} | x | y | z), x, y, z, ours, wrong, id=f"d{i}")
    for i, (d, b, x, y, z, ours, wrong) in enumerate(_D)
]


@pytest.mark.parametrize(("g", "x", "y", "z", "ours", "wrong"), DISAGREEMENTS)
def test_y0_disagreements_are_y0_rule2_errors(g, x, y, z, ours, wrong):
    expr = _verdict(g, y, x, z)
    assert (expr is not None) == ours
    if expr is not None:
        _assert_idc_matches_truth(g, y, x, z, expr)
    # Our rule-2 test agrees with an independent m-separation for every Z_i.
    for zi in sorted(z):
        mod = g.do(x).remove_outgoing({zi})
        assert d_separated(mod, y, {zi}, x | (z - {zi})) == networkx_m_separated(mod, y, {zi}, x | (z - {zi}))
    # The exchange y0 makes is not valid: P(y | do(x), z) != P(y | do(x, z_i), z - z_i).
    rest = z - {wrong}
    scm = DiscreteSCM.random(g, 1)
    gap = 0.0
    for xa, wa in itertools.product(assignments(x), assignments({wrong})):
        before, after = scm.joint(xa), scm.joint({**xa, **wa})
        for ra, ya in itertools.product(assignments(rest), assignments(y)):
            p, q = _cond(before, ya, {**ra, **wa}), _cond(after, ya, ra)
            if p is not None and q is not None:
                gap = max(gap, abs(p - q))
    assert gap > 1e-3
    # ...and unpatched y0 does make it, while the correct oracle agrees with us.
    id_c = require_y0("y0.algorithm.identify.id_c")
    from y0.algorithm.identify.utils import Identification, Query
    from y0.dsl import Variable

    query = Query(treatments={Variable(v) for v in x}, outcomes={Variable(v) for v in y},
                  conditions={Variable(v) for v in z})
    raw = Identification(graph=to_y0(g), query=query)
    assert id_c.rule_2_of_do_calculus_applies(identification=raw, condition=Variable(wrong))
    assert _y0_idc_verdict(g, y, x, z) == ours
