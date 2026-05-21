from __future__ import annotations

from pathlib import Path

import pytest

import codontrace
from codontrace import ActionResult, Codon, CodonTable, GenomeSpec
from codontrace.errors import ConfigurationError
from codontrace.genesis import (
    ActionStatusRegistry,
    AliveGateConfig,
    AppliedSubstrateRuleRecord,
    CausalGraph,
    CausalGraphConfig,
    ElementGrid,
    ElementGridConfig,
    ElementRegistry,
    ElementStepResult,
    FitnessConfig,
    GenesisATPState,
    SubstrateRuleConfig,
    evaluate_alive,
    evaluate_fitness,
    update_causal_graph_from_trace,
)
from codontrace.genesis.release_readiness import assert_artifact_has_no_cache_files
from codontrace.trace import Trace, TraceEvent


def _event(status: str = "executed", action: str = "EAT_LUMEN") -> TraceEvent:
    return TraceEvent(
        step=0,
        agent_id="o1",
        codon="000",
        action=action,
        atp_before=1.0,
        atp_after=0.9,
        position_before=(0, 0),
        position_after=(0, 0),
        world_delta={"lumen_interaction": True},
        status=status,
        reason="ok",
    )


def test_version_artifact_identity() -> None:
    assert codontrace.__version__ == "0.3.0a1"
    assert 'version = "0.3.0a1"' in Path("pyproject.toml").read_text(encoding="utf-8")


def test_zip_hygiene_allows_post_build_dist_and_checks_built_artifacts() -> None:
    for artifact in sorted(Path("dist").glob("*")):
        if artifact.suffix in {".whl", ".zip"} or artifact.name.endswith(".tar.gz"):
            assert_artifact_has_no_cache_files(artifact)


def test_substrate_threshold_inclusive() -> None:
    registry = ElementRegistry.genesis_v0().define(
        symbol="Pl", name="Plasma", origin="test", layer="energy"
    )
    rules = SubstrateRuleConfig.empty().add(inputs=("Pl", "Aq"), output="Steam", threshold=1.0)
    registry = registry.define(symbol="Steam", name="Steam", origin="test", layer="phase")
    grid = ElementGrid(
        width=1, height=1, registry=registry, rules=rules, cells={(0, 0): {"Pl": 1.0, "Aq": 1.0}}
    )
    result = grid.step()
    assert result.applied_rules
    assert grid.amount((0, 0), "Steam") > 0

    blocked = ElementGrid(
        width=1, height=1, registry=registry, rules=rules, cells={(0, 0): {"Pl": 0.999, "Aq": 1.0}}
    )
    blocked_result = blocked.step()
    assert blocked_result.applied_rules == ()


def test_element_grid_custom_background_validation() -> None:
    with pytest.raises(ConfigurationError, match="background"):
        ElementGrid(width=1, height=1, registry=ElementRegistry.empty())
    registry = ElementRegistry.empty().define(
        symbol="Vac", name="Vacuum", origin="test", layer="space"
    )
    grid = ElementGrid(
        width=1,
        height=1,
        registry=registry,
        rules=SubstrateRuleConfig.empty(),
        grid_config=ElementGridConfig(background_symbol="Vac"),
    )
    assert grid.amount((0, 0), "Vac") == 1.0


def test_action_result_custom_status_and_status_semantics() -> None:
    registry = ActionStatusRegistry.genesis_v0().define(
        "partially_executed",
        "success",
        counts_as_executed=True,
        counts_as_blocked=False,
        counts_as_failed=False,
    )
    result = ActionResult.custom("partially_executed", reason="partial", status_registry=registry)
    assert result.status == "partially_executed"
    with pytest.raises(ConfigurationError):
        ActionResult(status="partially_executed", reason="missing_registry")

    trace = Trace()
    trace.append(_event(status="partially_executed"))
    alive = evaluate_alive(
        trace, final_runtime_atp=1.0, config=AliveGateConfig(min_ticks=1, status_registry=registry)
    )
    fitness = evaluate_fitness(trace, alive, FitnessConfig(status_registry=registry))
    assert alive.executed_actions == 1
    assert fitness.lumen_eaten == 1

    graph = CausalGraph()
    atp = GenesisATPState.from_runtime(1.0, learning_atp=2.0, learning_enabled=True)
    update_causal_graph_from_trace(
        graph, trace, atp, CausalGraphConfig(status_registry=registry), tick=0, organism_id="o1"
    )
    assert not any(edge.relation == "leads_to_block" for edge in graph.edges)


def test_codon_non_binary_usability_and_bool_width_rejection() -> None:
    dna = GenomeSpec.dna3()
    codon = Codon.from_sequence("ACG", "SENSE", 0.1, spec=dna)
    table = CodonTable((codon,), spec=codontrace.CodonTableSpec(dna, table_name="dna"))
    assert table.decode("ACG").action_name == "SENSE"
    with pytest.raises(ConfigurationError):
        GenomeSpec(codon_width=True)  # type: ignore[arg-type]


def test_element_step_rule_audit_roundtrip() -> None:
    registry = ElementRegistry.genesis_v0().define(
        symbol="Steam", name="Steam", origin="test", layer="phase"
    )
    rules = SubstrateRuleConfig.empty().add(
        inputs=("Ae", "Aq"), output="Steam", threshold=1.0, efficiency=0.5
    )
    grid = ElementGrid(
        width=1, height=1, registry=registry, rules=rules, cells={(0, 0): {"Ae": 1.0, "Aq": 1.0}}
    )
    result = grid.step()
    assert isinstance(result.applied_rules[0], AppliedSubstrateRuleRecord)
    restored = ElementStepResult.from_dict(result.to_dict())
    assert restored.applied_rules[0].rule_id == result.applied_rules[0].rule_id


def test_docs_no_stale_capsule_adf_claims() -> None:
    docs = "\n".join(
        path.read_text(encoding="utf-8") for path in [Path("README.md"), *Path("docs").glob("*.md")]
    )
    forbidden = [
        "Causal Capsule exchange deferred",
        "ADF deferred",
        "Capsule hooks only",
        "full Causal Capsule / Stigmergy exchange foundation",
    ]
    for phrase in forbidden:
        assert phrase not in docs
