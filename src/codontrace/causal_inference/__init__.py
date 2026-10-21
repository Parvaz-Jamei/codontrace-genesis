"""Pearl-style causal inference over Genesis variables.

This package sits *on top of* the engine (``codontrace.genesis.causal_graph``
and ``codontrace.genesis.intervention``); the engine never imports it.

Sections, each importable and testable on its own:

1. :mod:`.graph`: acyclic directed mixed graphs and graph surgery.
2. :mod:`.separation`: d-/m-separation.
3. :mod:`.adjustment`: back-door and front-door criteria.
4. :mod:`.expressions`: probability expressions and exact evaluation.
5. :mod:`.identification`: the ID / IDC algorithms (Shpitser & Pearl 2006).
6. :mod:`.scm`: discrete structural causal models with exact do-semantics.
"""

from .adjustment import (
    backdoor_adjustment_sets,
    frontdoor_sets,
    satisfies_backdoor,
    satisfies_frontdoor,
)
from .expressions import DiscreteJoint, Fraction, Prob, Product, Sum
from .graph import CausalDiagram
from .identification import NotIdentifiable, identify, identify_conditional, is_identifiable
from .separation import d_separated

__all__ = [
    "CausalDiagram",
    "DiscreteJoint",
    "Fraction",
    "NotIdentifiable",
    "Prob",
    "Product",
    "Sum",
    "backdoor_adjustment_sets",
    "d_separated",
    "frontdoor_sets",
    "identify",
    "identify_conditional",
    "is_identifiable",
    "satisfies_backdoor",
    "satisfies_frontdoor",
]
