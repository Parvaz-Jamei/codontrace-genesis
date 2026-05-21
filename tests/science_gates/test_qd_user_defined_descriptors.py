from dataclasses import dataclass

from codontrace.genesis.qd_descriptors import (
    QDDescriptorConfig,
    QDDescriptorRegistry,
    select_population_with_qd_feedback,
)
from codontrace.genesis.quality_diversity import (
    BehaviorBin,
    QDArchive,
    QDArchiveConfig,
    QDElite,
    update_qd_archive,
)
from codontrace.genesis.selection import EvolutionConfig


@dataclass(frozen=True)
class Candidate:
    id: str
    fitness: float
    novelty_axis: float


def test_qd_descriptor_schema_and_registry_custom_descriptor():
    config = QDDescriptorConfig(
        ("survival_ticks", "custom_metric"), {"custom_metric": (0.0, 5.0, 5)}
    )
    schema = config.to_schema()
    registry = QDDescriptorRegistry().register("custom_metric", lambda obj: obj.novelty_axis)
    descriptor = registry.describe(Candidate("a", 1.0, 3.0), schema.descriptor_names)

    assert schema.digest()
    assert descriptor["custom_metric"] == 3.0
    assert config.digest() != QDDescriptorConfig(("survival_ticks",)).digest()


def test_qd_novelty_can_change_selection_outcome():
    schema = QDDescriptorConfig(("custom_metric",), {"custom_metric": (0.0, 10.0, 10)}).to_schema()
    archive = update_qd_archive(
        QDArchive.empty(QDArchiveConfig(schema)),
        QDElite("elite", 1.0, {"custom_metric": 0.0}, BehaviorBin((0,)), "g", "t"),
    ).archive
    candidates = (Candidate("fit", 10.0, 0.0), Candidate("novel", 1.0, 10.0))
    descriptors = {"fit": {"custom_metric": 0.0}, "novel": {"custom_metric": 10.0}}
    selected, result, novelty = select_population_with_qd_feedback(
        candidates,
        fitness_scores={"fit": 10.0, "novel": 1.0},
        behavior_descriptors=descriptors,
        archive=archive,
        max_population=1,
        evolution_config=EvolutionConfig(
            selection_policy="novelty_weighted", novelty_weight=2.0, fitness_weight=0.0
        ),
    )

    assert selected[0].id == "novel"
    assert novelty["novel"] > novelty["fit"]
    assert result.policy_name == "novelty_weighted"
