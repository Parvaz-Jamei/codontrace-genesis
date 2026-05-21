from codontrace.genesis.qd_search import QDDescriptorConfig, QDSearchConfig, QDSearchRunner


def evaluator(genome: str) -> tuple[float, dict[str, float]]:
    ones = genome.count("1")
    return float(ones), {"ones": float(ones), "length": float(len(genome))}


def test_qd_search_loop_updates_archive_and_generates_offspring() -> None:
    config = QDSearchConfig(
        descriptor_config=QDDescriptorConfig(("ones",), {"ones": 4}, {"ones": 0.0}, {"ones": 4.0}),
        generations=3,
        offspring_per_generation=3,
        seed=42,
    )
    result = QDSearchRunner(config, evaluator).run(["0000"])
    assert len(result.steps) == 3
    assert result.archive.elites
    assert result.steps[-1].archive_digest == result.archive.digest()


def test_qd_descriptor_schema_changes_digest_and_novelty_affects_selection() -> None:
    base = QDDescriptorConfig(("ones",), {"ones": 4}, {"ones": 0.0}, {"ones": 4.0})
    changed = QDDescriptorConfig(
        ("ones", "length"),
        {"ones": 4, "length": 2},
        {"ones": 0.0, "length": 0.0},
        {"ones": 4.0, "length": 8.0},
    )
    assert base.digest() != changed.digest()
    config = QDSearchConfig(
        descriptor_config=base,
        generations=2,
        offspring_per_generation=3,
        novelty_weight=1.0,
        seed=7,
    )
    result = QDSearchRunner(config, evaluator).run(["0000", "1111"])
    assert any(
        selection.source == "archive_novelty"
        for step in result.steps
        for selection in step.parent_selections
    )


def test_qd_search_reproducible_with_seed() -> None:
    config = QDSearchConfig(
        descriptor_config=QDDescriptorConfig(("ones",), {"ones": 4}, {"ones": 0.0}, {"ones": 4.0}),
        seed=5,
    )
    assert (
        QDSearchRunner(config, evaluator).run(["0000"]).digest()
        == QDSearchRunner(config, evaluator).run(["0000"]).digest()
    )
