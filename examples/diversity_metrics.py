"""Compute pure diversity metrics for a deterministic CodonTrace scenario."""

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

from codontrace import ScenarioAgentProfile, ScenarioConfig, ScenarioFactory, WorldConfig
from codontrace.metrics.diversity import diversity_report

config = ScenarioConfig(
    seed=7,
    world=WorldConfig(
        width=10,
        height=10,
        seed=7,
        resource_density=0.10,
        resource_distribution="uniform",
    ),
    profiles=(ScenarioAgentProfile(name="default", count=3),),
)
scenario = ScenarioFactory.from_config(config)
report = diversity_report(scenario)
print(report["config_hash"])
print(report["unique_genome_count"])
