"""Quickstart for codontrace current alpha."""

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

from codontrace import WhiteBoxAgent, World2D


def main() -> None:
    world = World2D.from_ascii(
        """
....
.A*.
....
"""
    )
    agent = WhiteBoxAgent.from_world(world, genome="101111000", initial_atp=5.0)
    result = agent.run_trial(world, steps=3, explain=True)

    print("Last action:", result.trace.last().action)
    if result.explanation is not None:
        print("Explanation:", result.explanation.summary)
    print("Final world:")
    print(result.world.render_ascii())


if __name__ == "__main__":
    main()
