"""One-call experiment quickstart for codontrace."""

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

from codontrace import AgentProfile, Experiment

result = Experiment.quick(
    world_ascii="""
........
..#.....
....*...
........
""",
    agent_count=3,
    seed=42,
    steps=5,
    profiles=(
        AgentProfile(name="explorer", count=2, preferred_codons=("101", "011")),
        AgentProfile(name="collector", count=1, preferred_codons=("111", "001")),
    ),
)

print(result.summary())
