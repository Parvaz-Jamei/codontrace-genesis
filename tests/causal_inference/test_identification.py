"""ID / IDC: textbook graphs, exact numerical soundness, and completeness.

Ground truth is the truncated factorisation of a random discrete SCM
(the post-intervention distribution), computed by exact enumeration. An identified
expression evaluated on the observational joint must reproduce it.
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from codontrace.causal_inference import (
    CausalDiagram,
    NotIdentifiable,
    backdoor_adjustment_sets,
    frontdoor_sets,
    identify,
    identify_conditional,
    is_identifiable,
    satisfies_backdoor,
    satisfies_frontdoor,
)
from codontrace.causal_inference.scm import DiscreteSCM

from ._helpers import admgs, assignments, backdoor_value, frontdoor_value

B = CausalDiagram.build

# Standard textbook diagrams.
IDENTIFIABLE = {
    # Front door (smoking -> tar -> cancer).
    "front_door": B([("X", "Z"), ("Z", "Y")], [("X", "Y")]),
    # Back door: Z confounds X and Y.
    "back_door": B([("Z", "X"), ("Z", "Y"), ("X", "Y")]),
    # Three confounders Z1..Z3 and a mediator W (classic back-door example).
    "three_confounders_mediator": B([("Z1", "Z3"), ("Z2", "Z3"), ("Z1", "X"), ("Z3", "X"), ("Z3", "Y"),
                        ("Z2", "Y"), ("X", "W"), ("W", "Y")]),
    # Napkin graph: identifiable but by neither criterion.
    "napkin": B([("W", "Z"), ("Z", "X"), ("X", "Y")], [("W", "X"), ("W", "Y")]),
    # Two-mediator front door with an observed confounder of the mediators' parent
    # (derivable with the do-calculus rules).
    "front_door_with_covariate": B([("C", "X"), ("C", "Y"), ("X", "Z"), ("Z", "Y")], [("X", "Y")]),
}
IDENTIFIABLE_QUERY: dict = {}

NOT_IDENTIFIABLE = {
    # The bow arc.
    "bow": B([("X", "Y")], [("X", "Y")]),
    # Confounded mediator.
    "confounded_mediator": B([("X", "Z"), ("Z", "Y")], [("X", "Z")]),
    # Bow plus a mediator.
    "bow_with_mediator": B([("X", "Z"), ("Z", "Y"), ("X", "Y")], [("X", "Z")]),
    # Confounded treatment and outcome with no mediator to exploit
    # (the graph contains a hedge).
    "bow_with_covariate": B([("C", "X"), ("C", "Y"), ("X", "Y")], [("X", "Y")]),
}
NOT_IDENTIFIABLE_QUERY: dict = {}


def _to_y0(g):
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


def _assert_matches_truth(g, y, x, expr, seeds=(1, 2)):
    for seed in seeds:
        scm = DiscreteSCM.random(g, seed)
        obs = scm.joint()
        for xv in assignments(x):
            truth = scm.joint(xv)
            extra = expr.free() - set(x) - set(y)
            for yv in assignments(y):
                # line-3 variables: the value must not depend on their setting
                for ev in assignments(extra):
                    got = obs.evaluate(expr, {**xv, **yv, **ev})
                    assert got == pytest.approx(truth.marginal(yv), abs=1e-9), (str(expr), xv, yv, ev)


@pytest.mark.parametrize("name", sorted(IDENTIFIABLE))
def test_textbook_identifiable(name):
    g = IDENTIFIABLE[name]
    y, x = IDENTIFIABLE_QUERY.get(name, ({"Y"}, {"X"}))
    expr = identify(g, y, x)
    _assert_matches_truth(g, y, x, expr)


@pytest.mark.parametrize("name", sorted(NOT_IDENTIFIABLE))
def test_textbook_not_identifiable(name):
    g = NOT_IDENTIFIABLE[name]
    y, x = NOT_IDENTIFIABLE_QUERY.get(name, ({"Y"}, {"X"}))
    with pytest.raises(NotIdentifiable) as info:
        identify(g, y, x)
    f, f_prime = info.value.hedge
    assert f_prime < f and f & x and not (f_prime & x)
    assert len(g.subgraph(f).c_components()) == 1
    assert len(g.subgraph(f_prime).c_components()) == 1


@pytest.mark.parametrize("name", sorted(IDENTIFIABLE) + sorted(NOT_IDENTIFIABLE))
def test_textbook_verdicts_agree_with_y0(name):
    pytest.importorskip("y0.algorithm.identify")
    from y0.algorithm.identify import identify_outcomes
    from y0.dsl import Variable

    g = IDENTIFIABLE.get(name) or NOT_IDENTIFIABLE[name]
    ng = _to_y0(g)
    theirs = identify_outcomes(ng, treatments={Variable("X")}, outcomes={Variable("Y")})
    assert (theirs is not None) == (name in IDENTIFIABLE)


def test_napkin_needs_id_not_criteria():
    g = IDENTIFIABLE["napkin"]
    assert backdoor_adjustment_sets(g, {"X"}, {"Y"}) == ()
    assert frontdoor_sets(g, {"X"}, {"Y"}) == ()
    assert is_identifiable(g, {"Y"}, {"X"})


def test_backdoor_rejects_descendants_of_treatment():
    # Back-door condition (i): a mediator is not an admissible adjustment.
    g = B([("X", "M"), ("M", "Y")])
    assert satisfies_backdoor(g, {"X"}, {"Y"}, set())
    assert not satisfies_backdoor(g, {"X"}, {"Y"}, {"M"})


def test_front_door_and_back_door_sets_on_textbook_graphs():
    assert frontdoor_sets(IDENTIFIABLE["front_door"], {"X"}, {"Y"}) == (frozenset({"Z"}),)
    sets = backdoor_adjustment_sets(IDENTIFIABLE["three_confounders_mediator"], {"X"}, {"Y"})
    # {Z1, Z3} and {Z2, Z3} are admissible; {Z3} alone opens the collider at Z3.
    assert frozenset({"Z1", "Z3"}) in sets and frozenset({"Z2", "Z3"}) in sets
    assert frozenset({"Z3"}) not in sets
    assert not satisfies_backdoor(IDENTIFIABLE["three_confounders_mediator"], {"X"}, {"Y"}, {"W"})


def _query(data, g, max_y=2):
    nodes = sorted(g.nodes)
    x = data.draw(st.sets(st.sampled_from(nodes), min_size=1, max_size=2))
    rest = [v for v in nodes if v not in x]
    y = data.draw(st.sets(st.sampled_from(rest), min_size=1, max_size=max_y)) if rest else set()
    return x, y


@settings(max_examples=150, deadline=None)
@given(data=st.data())
def test_id_is_sound_on_random_admgs(data):
    g = data.draw(admgs(max_nodes=5))
    x, y = _query(data, g)
    if not y:
        return
    try:
        expr = identify(g, y, x)
    except NotIdentifiable:
        return
    _assert_matches_truth(g, y, x, expr, seeds=(data.draw(st.integers(0, 10_000)),))


@settings(max_examples=150, deadline=None)
@given(data=st.data())
def test_dags_are_always_identifiable(data):
    g = data.draw(admgs(max_nodes=6, bidirected=False))
    x, y = _query(data, g)
    if y:
        assert is_identifiable(g, y, x)


@settings(max_examples=120, deadline=None)
@given(data=st.data())
def test_backdoor_and_frontdoor_formulas_match_truth(data):
    g = data.draw(admgs(max_nodes=5))
    nodes = sorted(g.nodes)
    xv = data.draw(st.sampled_from(nodes))
    yv = data.draw(st.sampled_from([v for v in nodes if v != xv]))
    scm = DiscreteSCM.random(g, data.draw(st.integers(0, 10_000)))
    obs = scm.joint()
    for z in backdoor_adjustment_sets(g, {xv}, {yv}, minimal=False, max_size=2):
        assert satisfies_backdoor(g, {xv}, {yv}, z)
        for xa in assignments({xv}):
            truth = scm.joint(xa).marginal({yv: 1})
            assert backdoor_value(obs, xa, {yv: 1}, z) == pytest.approx(truth, abs=1e-9)
    for z in frontdoor_sets(g, {xv}, {yv}, minimal=False, max_size=2):
        assert satisfies_frontdoor(g, {xv}, {yv}, z)
        for xa in assignments({xv}):
            truth = scm.joint(xa).marginal({yv: 1})
            assert frontdoor_value(obs, xa, {yv: 1}, z) == pytest.approx(truth, abs=1e-9)
    # Either criterion implies ID succeeds.
    if backdoor_adjustment_sets(g, {xv}, {yv}, max_size=2) or frontdoor_sets(g, {xv}, {yv}, max_size=2):
        assert is_identifiable(g, {yv}, {xv})


@settings(max_examples=100, deadline=None)
@given(data=st.data())
def test_idc_is_sound_on_random_admgs(data):
    g = data.draw(admgs(max_nodes=5))
    x, y = _query(data, g, max_y=1)
    rest = sorted(g.nodes - x - y)
    if not y or not rest:
        return
    z = {data.draw(st.sampled_from(rest))}
    try:
        expr = identify_conditional(g, y, x, z)
    except NotIdentifiable:
        return
    scm = DiscreteSCM.random(g, data.draw(st.integers(0, 10_000)))
    obs = scm.joint()
    for xa in assignments(x):
        truth = scm.joint(xa)
        for za in assignments(z):
            pz = truth.marginal(za)
            for ya in assignments(y):
                want = truth.marginal({**ya, **za}) / pz
                got = obs.evaluate(expr, {**xa, **ya, **za}, fill_unbound=True)
                assert got == pytest.approx(want, abs=1e-9)


@settings(max_examples=200, deadline=None)
@given(data=st.data())
def test_identifiability_agrees_with_y0(data):
    """Completeness cross-check against y0 (y0 0.2.x, BSD-3-Clause)."""
    pytest.importorskip("y0.graph")
    y0_identify = pytest.importorskip("y0.algorithm.identify")
    from y0.dsl import Variable

    g = data.draw(admgs(max_nodes=5))
    x, y = _query(data, g)
    if not y:
        return
    ng = _to_y0(g)
    import networkx as nx

    try:
        theirs = y0_identify.identify_outcomes(
            ng, treatments={Variable(v) for v in x}, outcomes={Variable(v) for v in y}
        )
    except nx.NetworkXError:
        # y0 0.2.11 NxMixedGraph.remove_in_edges drops nodes left without a
        # directed edge, then fails on ancestors(); not a verdict either way.
        assume(False)
    assert is_identifiable(g, y, x) == (theirs is not None)
