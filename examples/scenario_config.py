"""Build a deterministic CodonTrace scenario from public config objects."""

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

config = ScenarioConfig(
    name="scenario-demo",
    seed=42,
    world=WorldConfig(
        width=12,
        height=8,
        seed=42,
        boundary="open",
        wall_density=0.08,
        wall_pattern="rooms",
        resource_density=0.12,
        resource_distribution="clusters",
        resource_amount_range=(1.0, 3.0),
        hazard_density=0.04,
        hazard_distribution="uniform",
        beacon_density=0.03,
        beacon_distribution="uniform",
    ),
    agents=(
        ScenarioAgentProfile(
            name="collector",
            count=4,
            genome_length_range=(3, 5),
            atp_range=(4.0, 6.0),
            codon_bias={"111": 3.0},
            placement_zone="near_resources",
        ),
    ),
)

scenario = ScenarioFactory.from_config(config)
print(scenario.config_hash)
print(scenario.initial_world_digest)
print(scenario.initial_agent_digest)
