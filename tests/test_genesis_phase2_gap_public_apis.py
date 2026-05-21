from codontrace.genesis import (
    ChallengeNoveltyReport,
    EvidenceRegistry,
    EvidenceStatus,
    EnvironmentMutationSpec,
    MultiObjectiveQDArchive,
    ParetoEliteRecord,
    ParetoObjectiveVector,
    PluginRegistry,
    PluginSpec,
    RunCheckpoint,
    SeedSweepSpec,
    build_qd_tradeoff_report,
)


def test_evidence_registry_registers_phase2_claim_evidence():
    registry = EvidenceRegistry.phase2_default()
    assert registry.get("event_graph_digest").claim_labels
    assert "adaptive_gp_map_proxy" in registry.claim_labels()
    assert registry.digest()


def test_evidence_status_enum_contains_claim_and_nonclaim_statuses():
    assert EvidenceStatus.MEASURED.value == "measured"
    assert EvidenceStatus.NOT_RUN.value == "not_run"


def test_multi_objective_qd_pareto_archive_replaces_dominated_elite():
    weak = ParetoEliteRecord("weak", (0,), ParetoObjectiveVector(1, 1, 1, 1, 1, 5), "a")
    strong = ParetoEliteRecord("strong", (0,), ParetoObjectiveVector(2, 2, 2, 2, 2, 1), "b")
    archive = MultiObjectiveQDArchive().insert(weak).insert(strong)
    assert [e.elite_id for e in archive.elites] == ["strong"]
    assert build_qd_tradeoff_report(archive).elite_count == 1


def test_plugin_curriculum_and_checkpoint_public_apis_digest():
    registry = PluginRegistry.empty().register(PluginSpec("p", "action_primitive", "1"))
    assert registry.digest()
    assert EnvironmentMutationSpec("env", 1, "resource_shift", 1.0).digest()
    assert ChallengeNoveltyReport("c", "b", 1.0, True).digest()
    assert RunCheckpoint("r", 1, "m", "s", "rng").digest()
    assert SeedSweepSpec((2, 1), "scenario").seeds == (1, 2)
