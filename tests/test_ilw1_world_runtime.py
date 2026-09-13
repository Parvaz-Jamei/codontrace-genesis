"""ILW-1: WorldSpec, seed namespace, event ledger, and run-scoped scheduler."""

from __future__ import annotations

import pytest

from codontrace.genesis.ilw import (
    CLAIM_CEILING,
    SCIENTIFIC_NAME,
    AdapterHonestyError,
    EventLedger,
    EventLedgerError,
    IlwScheduler,
    IlwSchedulerError,
    SeedNamespace,
    WorldSpec,
    assert_claim_ceiling_runtime_observation,
    assert_no_fixture_outcome_injection,
    load_integration_dag,
)


def test_world_spec_digest_stability():
    a = WorldSpec.s0_unit(seed=7)
    b = WorldSpec.from_mapping(
        {
            "height": 4,
            "width": 4,
            "tick_horizon": 6,
            "seed": 7,
            "resource_kinds": ["lumen", "vitae"],
            "niche_count": 2,
            "population_cap": 8,
            "scale_label": "S0",
        }
    )
    assert a.digest() == b.digest()
    assert a.digest().startswith("ilw_world_spec:")
    assert a.claim_ceiling == CLAIM_CEILING == "runtime_observation"
    assert a.scientific_name == SCIENTIFIC_NAME
    # Reordered construction must not change digest.
    c = WorldSpec(
        height=4,
        width=4,
        seed=7,
        tick_horizon=6,
        niche_count=2,
        population_cap=8,
        resource_kinds=("lumen", "vitae"),
        scale_label="S0",
    )
    assert c.digest() == a.digest()


def test_world_spec_rejects_raised_claim_ceiling():
    with pytest.raises(Exception, match="claim_ceiling"):
        WorldSpec.s0_unit(seed=1).__class__(
            width=4,
            height=4,
            seed=1,
            tick_horizon=6,
            claim_ceiling="measured",
        )


def test_same_seed_namespace_reproducibility_and_no_cross_run_leakage():
    ns_a1 = SeedNamespace(run_id="run-alpha", seed=42)
    ns_a2 = SeedNamespace(run_id="run-alpha", seed=42)
    ns_b = SeedNamespace(run_id="run-beta", seed=42)

    assert ns_a1.path("scheduler") == ns_a2.path("scheduler")
    assert ns_a1.path() != ns_b.path()
    ns_a1.assert_no_cross_run_leakage(ns_b)

    rng_a1 = ns_a1.fork_rng("world", "init")
    rng_a2 = ns_a2.fork_rng("world", "init")
    rng_b = ns_b.fork_rng("world", "init")
    draws_a1 = (rng_a1.random(), rng_a1.randrange(1000))
    draws_a2 = (rng_a2.random(), rng_a2.randrange(1000))
    draws_b = (rng_b.random(), rng_b.randrange(1000))
    assert draws_a1 == draws_a2
    assert draws_a1 != draws_b


def test_event_ledger_rejects_orphan_and_missing_required_fields():
    ledger = EventLedger(run_id="run-1")
    with pytest.raises(EventLedgerError, match="missing required ledger fields"):
        ledger.append({"run_id": "run-1", "event_id": "e0"})

    with pytest.raises(EventLedgerError, match="Orphan edge_id"):
        ledger.append(
            {
                "run_id": "run-1",
                "event_id": "e0",
                "edge_id": "not_in_dag",
                "causal_parent_ids": [],
            }
        )

    with pytest.raises(EventLedgerError, match="Orphan causal_parent_ids"):
        ledger.append(
            {
                "run_id": "run-1",
                "event_id": "e1",
                "edge_id": "genome_to_toolchain",
                "causal_parent_ids": ["missing-parent"],
            }
        )

    root = ledger.append(
        {
            "run_id": "run-1",
            "event_id": "e-root",
            "edge_id": "genome_to_toolchain",
            "causal_parent_ids": [],
            "attempted": 1,
            "accepted": 1,
            "applied": 1,
        }
    )
    child = ledger.append(
        {
            "run_id": "run-1",
            "event_id": "e-child",
            "edge_id": "toolchain_to_vm_phenotype",
            "causal_parent_ids": ["e-root"],
            "attempted": 1,
            "accepted": 1,
            "applied": 0,
        }
    )
    assert root.event_id == "e-root"
    assert child.causal_parent_ids == ("e-root",)
    assert len(ledger) == 2
    assert "genome_to_toolchain" in ledger.observed_edge_ids


def test_event_ledger_rejects_fixture_outcome_injection():
    ledger = EventLedger(run_id="run-1")
    with pytest.raises(EventLedgerError, match="Fixture/oracle|Forbidden fixture"):
        ledger.append(
            {
                "run_id": "run-1",
                "event_id": "e-bad",
                "edge_id": "genome_to_toolchain",
                "causal_parent_ids": [],
                "fixture_outcome": 1.0,
            }
        )


def test_scheduler_advances_under_one_run_id():
    spec = WorldSpec.s0_unit(seed=3)
    sched = IlwScheduler.for_run("run-sched-1", spec)
    assert sched.tick == 0
    assert sched.advance() == 1
    assert sched.advance(run_id="run-sched-1") == 2
    assert sched.advance_many(2) == 4
    assert sched.advanced_ticks == (1, 2, 3, 4)

    with pytest.raises(IlwSchedulerError, match="bound to run_id"):
        sched.advance(run_id="other-run")

    # Exhaust horizon.
    while sched.tick < spec.tick_horizon:
        sched.advance()
    with pytest.raises(IlwSchedulerError, match="tick_horizon"):
        sched.advance()


def test_scheduler_rejects_mismatched_seed_namespace_run_id():
    spec = WorldSpec.s0_unit(seed=1)
    ns = SeedNamespace(run_id="run-a", seed=1)
    with pytest.raises(IlwSchedulerError, match="seed_namespace.run_id"):
        IlwScheduler(run_id="run-b", world_spec=spec, seed_namespace=ns)


def test_adapter_honesty_and_no_scientific_claim_language():
    assert_claim_ceiling_runtime_observation()
    assert_no_fixture_outcome_injection({"edge_id": "genome_to_toolchain", "attempted": 1})
    with pytest.raises(AdapterHonestyError, match="outcome injection"):
        assert_no_fixture_outcome_injection({"fixture_outcome": 99})

    dag = load_integration_dag()
    assert dag.claim_ceiling == "runtime_observation"
    blob = " ".join(
        [
            WorldSpec.s0_unit().scientific_name,
            dag.scientific_name,
            CLAIM_CEILING,
        ]
    ).lower()
    for banned in ("agi", "collective intelligence", "tokyo type 1", "avida replacement"):
        assert banned not in blob
    # Positive scientific name stays descriptive, not promotional.
    assert SCIENTIFIC_NAME == "integrated eco-evolutionary runtime"
