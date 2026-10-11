"""Generic swarm coordination: membership, commands, trust, fusion, diagnosis,
active sampling and a pure coordinator core, plus a population adapter.

Transport-free and storage-free; ``codontrace.swarm`` composes this core with
``codontrace.genesis.journal`` and its wire protocol. Not imported by
``codontrace.genesis`` itself. Layering follows Mesa 3 (core model separate from
data collection and visualization; Masad et al. / ter Hoeven et al., JOSS 2025,
doi:10.21105/joss.07668) and ros2_control (state-only sensor interfaces).
"""
from __future__ import annotations

from codontrace.genesis.swarm import (
    active_sampling,
    commands,
    coordinator,
    diagnosis,
    fusion,
    membership,
    metrics,
    population_adapter,
    readings,
    trust,
)
from codontrace.genesis.swarm.active_sampling import measurement_candidates, plan_oldest_first
from codontrace.genesis.swarm.coordinator import SwarmConfig, SwarmCoordinatorCore
from codontrace.genesis.swarm.diagnosis import peer_disagreement
from codontrace.genesis.swarm.fusion import median_absolute_deviation, robust_fuse
from codontrace.genesis.swarm.membership import SwarmMember
from codontrace.genesis.swarm.population_adapter import (
    PopulationMember,
    members_from_population,
    members_from_registry,
)

__all__ = ['PopulationMember', 'SwarmConfig', 'SwarmCoordinatorCore', 'SwarmMember', 'active_sampling', 'commands',
           'coordinator', 'diagnosis', 'fusion', 'measurement_candidates', 'median_absolute_deviation', 'members_from_population',
           'members_from_registry', 'membership', 'metrics', 'peer_disagreement', 'plan_oldest_first',
           'population_adapter', 'readings', 'robust_fuse', 'trust']
