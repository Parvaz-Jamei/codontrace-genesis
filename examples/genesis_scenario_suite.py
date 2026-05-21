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

from codontrace.genesis import (
    ComponentToggle,
    ComponentToggleMatrix,
    ScenarioSuite,
    SeedMatrix,
    ValidationScenario,
    validate_scenario_suite,
)

scenario = ValidationScenario(
    scenario_id="d0_qd_smoke",
    description="Object-only validation scenario for D0/QD evidence.",
    required_components=("d0", "qd"),
    config_digest="cfg-demo",
    expected_evidence=("trace", "qd"),
    non_claims=("no discovery proof",),
)
suite = ScenarioSuite(
    suite_id="genesis_demo_suite",
    description="Compact scenario suite example.",
    scenarios=(scenario,),
    seed_matrix=SeedMatrix(seeds=(1, 2, 3), min_seeds=3),
    component_matrix=ComponentToggleMatrix(
        (ComponentToggle("d0", True), ComponentToggle("qd", True))
    ),
    required_evidence=("trace",),
    limitations=("pre-public alpha",),
)
result = validate_scenario_suite(suite)
print({"suite_digest": suite.digest(), "succeeded": result.succeeded})
