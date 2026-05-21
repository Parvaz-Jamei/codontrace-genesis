"""Causal replay demo for codontrace current alpha."""

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:  # direct script or runpy execution outside the examples package
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from codontrace import (
    ATPAccount,
    CausalReplay,
    CodonTable,
    SemanticGenome,
    Trace,
    WhiteBoxAgent,
    World2D,
)


def main() -> None:
    world = World2D.from_ascii(
        """
...
.A.
...
"""
    )
    snapshot = world.clone()
    agent = WhiteBoxAgent(
        id="agent-1",
        genome=SemanticGenome.from_codons(["101"]),
        codon_table=CodonTable.default_minimal(),
        atp_account=ATPAccount(initial_atp=5.0),
        position=(1, 1),
    )
    trace = Trace()
    agent.step(world, trace)
    explanation = CausalReplay.explain_last_action(trace, snapshot)
    print(explanation.summary)
    for result in explanation.perturbation_results:
        print(result.to_dict())


if __name__ == "__main__":
    main()
