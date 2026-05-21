"""Backward-readable aliases for GENESIS evolution selection policies."""

from codontrace.genesis.selection import (
    AgeLayeredSelection,
    ElitismSelection,
    EvolutionConfig,
    EvolutionSelectionResult,
    FitnessProportionalSelection,
    NoveltyWeightedSelection,
    SelectionPolicy,
    TournamentSelection,
    policy_from_name,
    select_population,
)

__all__ = [
    "AgeLayeredSelection",
    "ElitismSelection",
    "EvolutionConfig",
    "EvolutionSelectionResult",
    "FitnessProportionalSelection",
    "NoveltyWeightedSelection",
    "SelectionPolicy",
    "TournamentSelection",
    "policy_from_name",
    "select_population",
]
