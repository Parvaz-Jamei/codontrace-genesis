from __future__ import annotations

from codontrace import Experiment


def test_experiment_quick_runs_end_to_end() -> None:
    result = Experiment.quick(
        world_ascii="""
...
.*.
...
""",
        agent_count=3,
        seed=1,
        steps=5,
    )

    assert len(result.trace) > 0
    assert result.summary()["agents"] == 3
