"""ILW-0: integration DAG load + fail-first orphan / event consumer gates."""

from __future__ import annotations

import pytest

from codontrace.genesis.ilw import (
    CLAIM_CEILING,
    SCIENTIFIC_NAME,
    IntegrationDAGError,
    OrphanEventError,
    OrphanSubsystemError,
    RegisteredEventConsumer,
    SubsystemRegistry,
    load_integration_dag,
)


def test_integration_dag_loads_with_required_edges_and_ceiling():
    dag = load_integration_dag()
    assert dag.schema == "ilw_integration_dag_v0"
    assert dag.claim_ceiling == CLAIM_CEILING == "runtime_observation"
    assert dag.scientific_name == SCIENTIFIC_NAME
    required = dag.required_edge_ids
    expected = {
        "genome_to_toolchain",
        "toolchain_to_vm_phenotype",
        "vm_phenotype_to_action",
        "action_to_resource_world",
        "resource_world_to_experienced_event",
        "experience_to_capsule",
        "capsule_transport_accept_apply",
        "capsule_to_policy",
        "policy_to_survival_reproduction",
        "survival_reproduction_to_mutation_lineage",
        "lineage_inheritance",
        "mutation_lineage_to_next_ecological_state",
        "ecological_feedback",
    }
    assert required == expected
    assert "edge_id" in dag.required_telemetry_fields
    assert "attempted" in dag.required_telemetry_fields
    assert "accepted" in dag.required_telemetry_fields
    assert "applied" in dag.required_telemetry_fields
    for knockout in (
        "toolchain_to_action_off",
        "experience_to_capsule_off",
        "capsule_transport_off",
        "capsule_to_policy_off",
        "mutation_off",
        "ecological_feedback_off",
        "lineage_inheritance_off",
    ):
        assert knockout in dag.knockout_ids


def test_missing_required_edge_fails_before_world_claim():
    dag = load_integration_dag()
    observed = set(dag.required_edge_ids)
    observed.remove("experience_to_capsule")
    with pytest.raises(IntegrationDAGError, match="Missing required integration edges"):
        dag.assert_required_edges_present(observed)


def test_orphan_edge_id_fails():
    dag = load_integration_dag()
    with pytest.raises(IntegrationDAGError, match="orphan edges"):
        dag.assert_required_edges_present(set(dag.required_edge_ids) | {"not_a_real_edge"})


def test_orphan_subsystem_registry_fails_loudly():
    registry = SubsystemRegistry()
    registry.register("genome")
    with pytest.raises(OrphanSubsystemError, match="Orphan / unregistered subsystems"):
        registry.assert_no_orphans()
    with pytest.raises(OrphanSubsystemError, match="orphan subsystem"):
        registry.register("not_in_dag")


def test_subsystem_registry_ready_requires_full_edges_and_subsystems():
    dag = load_integration_dag()
    registry = SubsystemRegistry(dag)
    registry.register_many(dag.subsystems)
    # Missing one required edge still fails.
    observed = set(dag.required_edge_ids)
    observed.remove("capsule_to_policy")
    with pytest.raises(IntegrationDAGError, match="Missing required"):
        registry.assert_ready_for_world_claim(observed)
    registry.assert_ready_for_world_claim(dag.required_edge_ids)


def test_event_consumer_rejects_orphan_and_unregistered_events():
    consumer = RegisteredEventConsumer()
    seen: list[str] = []

    def _handler(event: dict) -> None:
        seen.append(str(event["edge_id"]))

    with pytest.raises(OrphanEventError, match="orphan edge_id"):
        consumer.register("totally_unknown_edge", _handler)

    consumer.register("experience_to_capsule", _handler)

    with pytest.raises(OrphanEventError, match="missing edge_id"):
        consumer.consume({"event_id": "e1"})

    with pytest.raises(OrphanEventError, match="Orphan event edge_id"):
        consumer.consume({"edge_id": "fabricated_edge", "event_id": "e2"})

    with pytest.raises(OrphanEventError, match="No registered consumer"):
        consumer.consume({"edge_id": "genome_to_toolchain", "event_id": "e3"})

    consumer.consume(
        {
            "edge_id": "experience_to_capsule",
            "event_id": "e4",
            "attempted": 1,
            "accepted": 1,
            "applied": 0,
        }
    )
    assert seen == ["experience_to_capsule"]

    with pytest.raises(OrphanEventError, match="collapsed counter"):
        consumer.consume(
            {
                "edge_id": "experience_to_capsule",
                "attempt_accepted_applied": 1,
            }
        )
