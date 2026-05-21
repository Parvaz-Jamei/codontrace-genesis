from __future__ import annotations

import pytest

from codontrace import ConfigurationError, Simulation, SimulationConfig, World2D


def test_clear_custom_errors_are_raised() -> None:
    with pytest.raises(ConfigurationError, match="requires at least one agent"):
        Simulation.run(world=World2D(2, 2), agents=(), config=SimulationConfig(steps=1))
