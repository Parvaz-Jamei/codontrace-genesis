from __future__ import annotations

import ast
from pathlib import Path

from codontrace import (
    AgentFactory,
    Experiment,
    InitializationConfig,
    Simulation,
    SimulationConfig,
    World2D,
)


def test_no_print_calls_inside_core() -> None:
    src_root = Path("src/codontrace")
    offenders: list[str] = []
    for path in src_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
            ):
                offenders.append(f"{path}:{node.lineno}")
    assert offenders == []


def test_core_exposes_no_path_based_result_writers() -> None:
    assert not hasattr(Simulation.run, "save")
    result = Experiment.quick(width=4, height=4, agent_count=2, seed=1, steps=1)
    assert not hasattr(result, "save")
    assert not hasattr(result, "load")


def test_simulation_run_creates_no_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    world = World2D(4, 4)
    agents = AgentFactory.create_many(
        world=world,
        config=InitializationConfig(count=2, seed=3, placement_strategy="grid"),
    )
    before = set(tmp_path.iterdir())
    Simulation.run(world=world, agents=agents, config=SimulationConfig(steps=2, seed=3))
    after = set(tmp_path.iterdir())
    assert after == before


def test_experiment_quick_creates_no_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    before = set(tmp_path.iterdir())
    Experiment.quick(width=4, height=4, agent_count=2, seed=5, steps=2)
    after = set(tmp_path.iterdir())
    assert after == before
