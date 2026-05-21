"""Beginner-friendly experiment API."""

from __future__ import annotations

import warnings

from codontrace.initialization import (
    AgentFactory,
    AgentProfile,
    AgentSpec,
    GenomeStrategy,
    InitializationConfig,
    PlacementStrategy,
)
from codontrace.simulation import Simulation, SimulationConfig, SimulationResult
from codontrace.world import World2D


class Experiment:
    """Convenience entrypoint for one-call codontrace experiments."""

    @staticmethod
    def quick(
        *,
        world_ascii: str | None = None,
        width: int = 10,
        height: int = 10,
        agent_count: int = 1,
        seed: int | None = None,
        profiles: tuple[AgentProfile, ...] = (),
        steps: int = 10,
        genome_strategy: GenomeStrategy = "uniform_random",
        placement_strategy: PlacementStrategy = "uniform_random",
    ) -> SimulationResult:
        """Run an end-to-end world + agents + simulation with one call.

        Returns a SimulationResult object only. It performs no printing, file I/O,
        report generation, dashboard creation, or hidden output-directory setup.
        """

        world = (
            World2D.from_ascii(world_ascii, allow_custom_cells=True)
            if world_ascii is not None
            else World2D(width=width, height=height)
        )
        marker_position = world.agent_position
        world.agent_position = None
        resolved_profiles = profiles
        if not resolved_profiles:
            resolved_profiles = (
                AgentProfile(
                    name="default",
                    count=agent_count,
                    genome_length=4,
                    initial_atp=10.0,
                ),
            )
        config = InitializationConfig(
            count=agent_count,
            seed=seed,
            genome_strategy=genome_strategy,
            placement_strategy=placement_strategy,
            profiles=resolved_profiles,
            initial_atp=10.0,
        )
        specs = AgentFactory.create_specs(world=world, config=config)
        if marker_position is not None and agent_count == 1:
            first = specs[0]
            specs = (
                AgentSpec(
                    agent_id=first.agent_id,
                    genome=first.genome,
                    initial_atp=first.initial_atp,
                    position=marker_position,
                    profile=first.profile,
                    lineage_id=first.lineage_id,
                    parent_id=first.parent_id,
                    generation=first.generation,
                ),
            )
        elif marker_position is not None and agent_count > 1:
            warnings.warn(
                "ASCII 'A' marker is ignored when agent_count > 1. "
                "Use profiles/AgentSpec positions for explicit multi-agent placement.",
                UserWarning,
                stacklevel=2,
            )
        agents = AgentFactory.from_specs(specs, world=world)
        return Simulation.run(
            world=world,
            agents=agents,
            config=SimulationConfig(steps=steps, scheduler="random_order", seed=seed),
        )
