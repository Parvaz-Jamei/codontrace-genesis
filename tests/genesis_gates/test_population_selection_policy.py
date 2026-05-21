from __future__ import annotations

from codontrace.genesis.selection import (
    ElitismSelection,
    EvolutionConfig,
    FitnessProportionalSelection,
    NoveltyWeightedSelection,
    TournamentSelection,
    select_population,
)


class Candidate:
    def __init__(self, id: str) -> None:
        self.id = id


def test_selection_policies_are_deterministic_and_fitness_sensitive() -> None:
    candidates = [Candidate("weak"), Candidate("mid"), Candidate("strong")]
    fitness = {"weak": 1.0, "mid": 2.0, "strong": 5.0}
    selected, audit = select_population(
        candidates,
        fitness_scores=fitness,
        max_population=2,
        config=EvolutionConfig(selection_policy=FitnessProportionalSelection()),
    )
    assert [item.id for item in selected] == ["strong", "mid"]
    assert audit.dropped_ids == ("weak",)
    assert (
        TournamentSelection(tournament_size=2)
        .select(candidates, fitness_scores=fitness, max_population=1)[0]
        .id
        == "strong"
    )
    assert (
        ElitismSelection(elitism_count=1)
        .select(candidates, fitness_scores=fitness, max_population=1)[0]
        .id
        == "strong"
    )
    novelty = NoveltyWeightedSelection(fitness_weight=0.0, novelty_weight=1.0).select(
        candidates,
        fitness_scores=fitness,
        novelty_scores={"weak": 10.0},
        max_population=1,
    )
    assert novelty[0].id == "weak"
