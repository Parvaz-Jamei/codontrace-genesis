"""ILW-2: full genome→lineage causal chain in a dual-resource world."""

from __future__ import annotations

import pytest

from codontrace.genesis.ilw import (
    CLAIM_CEILING,
    SCIENTIFIC_NAME,
    DualResourceWorld,
    EventLedger,
    IlwChainRuntime,
    IlwScheduler,
    KnockoutConfig,
    WorldSpec,
    assert_claim_ceiling_runtime_observation,
    load_integration_dag,
)


def test_dual_resource_world_runs_under_one_run_id():
    spec = WorldSpec.s0_unit(seed=11)
    assert len(spec.resource_kinds) >= 2
    rt = IlwChainRuntime(run_id="ilw2-one-run", world_spec=spec)
    assert rt.scheduler.run_id == "ilw2-one-run"
    assert rt.ledger.run_id == "ilw2-one-run"
    assert rt.seed_namespace.run_id == "ilw2-one-run"
    assert rt.world_spec.digest() == spec.digest()

    summary = rt.run()
    assert summary["run_id"] == "ilw2-one-run"
    assert summary["tick"] == spec.tick_horizon
    assert set(summary["resource_totals"]) == set(spec.resource_kinds)
    # Single scheduler / ledger / spec binding.
    assert isinstance(rt.scheduler, IlwScheduler)
    assert isinstance(rt.ledger, EventLedger)
    assert isinstance(rt.world, DualResourceWorld)
    assert rt.world.niche_count >= 2
    assert len(rt.world.resource_kinds) >= 2
    # All events share the same run_id.
    assert all(event.payload["run_id"] == "ilw2-one-run" for event in rt.ledger.events)


def test_required_dag_edges_appear_with_non_orphan_events():
    dag = load_integration_dag()
    rt = IlwChainRuntime.s0(run_id="ilw2-edges", seed=11)
    rt.run()
    observed = rt.ledger.observed_edge_ids
    missing = sorted(dag.required_edge_ids - observed)
    assert missing == [], f"missing required edges: {missing}"
    # No orphan edge_ids (ledger already rejects unknowns; assert coverage gate).
    rt.assert_required_edges_covered()
    # Attempt / accepted / applied remain separate on every event.
    for event in rt.ledger.events:
        payload = event.payload
        assert "attempted" in payload and "accepted" in payload and "applied" in payload
        assert "attempt_accepted_applied" not in payload
        assert payload["edge_id"] in dag.edge_ids
        assert "state_before_digest" in payload and "state_after_digest" in payload
        # Causal parents exist (roots may be empty).
        for parent in event.causal_parent_ids:
            assert parent in rt.ledger.event_ids


def test_capsule_path_and_lineage_path_recordable():
    rt = IlwChainRuntime.s0(run_id="ilw2-paths", seed=11)
    rt.run()
    assert len(rt.capsules) >= 1
    assert len(rt.capsule_genealogy) >= 1
    # Capsule provenance fields present on experience_to_capsule applied events.
    capsule_events = [
        e
        for e in rt.ledger.events
        if e.edge_id == "experience_to_capsule" and int(e.payload["applied"]) > 0
    ]
    assert capsule_events
    for event in capsule_events:
        assert event.payload["capsule_id"]
        assert event.payload["payload_digest"]
        assert event.payload["provenance_digest"]

    transport = [
        e
        for e in rt.ledger.events
        if e.edge_id == "capsule_transport_accept_apply"
    ]
    assert transport
    assert any(int(e.payload["attempted"]) > 0 for e in transport)
    # Separate counters: at least one accepted and one applied somewhere on path.
    policy = [e for e in rt.ledger.events if e.edge_id == "capsule_to_policy"]
    assert any(int(e.payload["applied"]) > 0 for e in policy)

    # Lineage path: birth + mutation record.
    assert any(rec.get("parent_id") for rec in rt.lineage_records)
    mut_events = [
        e
        for e in rt.ledger.events
        if e.edge_id == "survival_reproduction_to_mutation_lineage"
        and int(e.payload["applied"]) > 0
    ]
    assert mut_events
    inherit = [
        e
        for e in rt.ledger.events
        if e.edge_id == "lineage_inheritance" and int(e.payload["applied"]) > 0
    ]
    assert inherit


def test_knockout_edge_off_fail_first_severed_edge():
    """At least one edge-off path: severed edge records blocked telemetry, no apply."""

    ko = KnockoutConfig.only("experience_to_capsule_off")
    rt = IlwChainRuntime.s0(run_id="ilw2-ko", seed=11, knockouts=ko)
    rt.run()
    severed = [
        e for e in rt.ledger.events if e.edge_id == "experience_to_capsule"
    ]
    assert severed
    assert all(int(e.payload["applied"]) == 0 for e in severed)
    assert all(e.payload.get("blocked_reason") == "experience_to_capsule_off" for e in severed)
    assert all(int(e.payload["attempted"]) == 1 for e in severed)
    # No fabricated capsules when the edge is off.
    assert len(rt.capsules) == 0
    # Downstream transport cannot honestly apply a real capsule.
    transport_applied = [
        e
        for e in rt.ledger.events
        if e.edge_id == "capsule_transport_accept_apply" and int(e.payload["applied"]) > 0
    ]
    assert transport_applied == []


def test_toolchain_knockout_cuts_declared_edges():
    ko = KnockoutConfig.only("toolchain_to_action_off")
    assert ko.cuts_edge("toolchain_to_vm_phenotype")
    assert ko.cuts_edge("vm_phenotype_to_action")
    rt = IlwChainRuntime.s0(run_id="ilw2-ko-tool", seed=3, knockouts=ko)
    rt.run()
    for edge_id in ("toolchain_to_vm_phenotype", "vm_phenotype_to_action"):
        events = [e for e in rt.ledger.events if e.edge_id == edge_id]
        assert events
        assert all(int(e.payload["applied"]) == 0 for e in events)
        assert all(e.payload.get("blocked_reason") == "toolchain_to_action_off" for e in events)


def test_claim_ceiling_unchanged_and_no_science_claim_language():
    assert_claim_ceiling_runtime_observation()
    rt = IlwChainRuntime.s0(run_id="ilw2-ceiling", seed=1)
    summary = rt.run()
    assert summary["claim_ceiling"] == CLAIM_CEILING == "runtime_observation"
    assert rt.world_spec.scientific_name == SCIENTIFIC_NAME
    blob = " ".join(
        [
            str(summary["claim_ceiling"]),
            SCIENTIFIC_NAME,
            rt.world_spec.scientific_name,
        ]
    ).lower()
    for banned in ("agi", "collective intelligence", "tokyo type 1", "avida replacement"):
        assert banned not in blob


def test_unknown_knockout_rejected():
    with pytest.raises(Exception, match="Unknown knockout"):
        KnockoutConfig.only("not_a_real_knockout")
