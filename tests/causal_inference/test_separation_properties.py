"""d-separation: textbook cases and Hypothesis against brute-force path enumeration."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from codontrace.causal_inference import CausalDiagram, d_separated

from ._helpers import admgs, brute_force_d_separated


def test_pearl_fig_1_2_sprinkler():
    # Pearl 2009, Fig. 1.2: X1 season, X2 sprinkler, X3 rain, X4 wet, X5 slippery.
    g = CausalDiagram.build([("X1", "X2"), ("X1", "X3"), ("X2", "X4"), ("X3", "X4"), ("X4", "X5")])
    assert d_separated(g, {"X2"}, {"X3"}, {"X1"})
    assert not d_separated(g, {"X2"}, {"X3"}, {"X1", "X4"})  # collider opened
    assert not d_separated(g, {"X2"}, {"X3"}, {"X1", "X5"})  # descendant of collider
    assert d_separated(g, {"X1"}, {"X5"}, {"X4"})
    assert not d_separated(g, {"X2"}, {"X3"})


def test_bidirected_edge_is_a_latent_confounder():
    g = CausalDiagram.build([], [("A", "B")])
    assert not d_separated(g, {"A"}, {"B"})
    g2 = CausalDiagram.build([("A", "C"), ("B", "C")], [])
    assert d_separated(g2, {"A"}, {"B"})
    assert not d_separated(g2, {"A"}, {"B"}, {"C"})


@settings(max_examples=300, deadline=None)
@given(data=st.data())
def test_d_separation_matches_brute_force(data):
    g = data.draw(admgs(max_nodes=6))
    nodes = sorted(g.nodes)
    x = data.draw(st.sets(st.sampled_from(nodes), min_size=1, max_size=2))
    rest = [v for v in nodes if v not in x]
    if not rest:
        return
    y = data.draw(st.sets(st.sampled_from(rest), min_size=1, max_size=2))
    rest2 = [v for v in rest if v not in y]
    z = data.draw(st.sets(st.sampled_from(rest2), max_size=3)) if rest2 else set()
    assert d_separated(g, x, y, z) == brute_force_d_separated(g, x, y, z)


@settings(max_examples=200, deadline=None)
@given(data=st.data())
def test_d_separation_is_symmetric(data):
    g = data.draw(admgs(max_nodes=6))
    nodes = sorted(g.nodes)
    x = data.draw(st.sets(st.sampled_from(nodes), min_size=1, max_size=2))
    rest = [v for v in nodes if v not in x]
    if not rest:
        return
    y = data.draw(st.sets(st.sampled_from(rest), min_size=1, max_size=2))
    z = [v for v in rest if v not in y][:1]
    assert d_separated(g, x, y, z) == d_separated(g, y, x, z)
