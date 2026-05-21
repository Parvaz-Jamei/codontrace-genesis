"""Strong-library Phase 2 smoke check for GENESIS scientific primitives.

This example is intentionally small: it verifies that the library APIs for
structural genomes, ADF source attribution, contribution ledgers, predictive /
intervention / OEE evidence objects, translation profiles, and ClaimGate
rejection behavior can be exercised without app/server/UI assumptions.
"""

from __future__ import annotations

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:  # direct script or runpy execution outside the examples package
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from codontrace.codon import Codon, CodonTable
from codontrace.genesis import (
    EvidenceValidationContext,
    canonical_digest,
    GenesisEngine,
    GenesisEngineConfig,
    GenesisExperimentSpec,
    GenesisOrganism,
    Ribosome,
    StatisticalTestPolicy,
    TranslationWeight,
    build_contribution_ledger,
    build_genome_program,
    build_intervention_result,
    build_oee_metrics_report,
    build_translation_profile,
    contribution_from_execution_record,
    granger_lite_probe,
    mutate_genome_program,
)
from codontrace.genesis.adf_runtime import ADFExecutionPolicy, ADFMacroDefinition, ADFMacroRegistry
from codontrace.genesis.event_graph import EventGraph
from codontrace.genesis.ribosome import CodonExecutionRecord
from codontrace.trace import Trace
from codontrace.world import World2D


def main() -> None:
    program = build_genome_program("000001011", lineage_tags=("phase2-smoke",))
    child, mutation = mutate_genome_program(program, kind="insert", payload_codon="111")
    assert child.structural_mutation_digest == mutation.digest

    table = CodonTable([Codon("000", "ADF_PAIR", 0.0)])
    registry = ADFMacroRegistry().register(
        ADFMacroDefinition(
            macro_id="ADF_PAIR",
            primitive_actions=("WAIT", "MOVE_EAST"),
            body_codons=("000", "001"),
        )
    )
    organism = GenesisOrganism.from_bits(
        "phase2-org",
        "000",
        ribosome=Ribosome(table),
        execution_source_enabled=True,
        adf_macro_registry=registry,
        adf_execution_policy=ADFExecutionPolicy(max_expansion_length=4),
    )
    trace = Trace()
    event = organism.step(World2D(4, 4), trace)
    records_raw = event.world_delta["codon_execution_records"]
    assert isinstance(records_raw, list)
    records = tuple(
        CodonExecutionRecord.from_dict(item) for item in records_raw if isinstance(item, dict)
    )
    assert len(records) == 2
    ledger = build_contribution_ledger(
        "phase2-org",
        0,
        tuple(contribution_from_execution_record(record) for record in records),
    )
    assert ledger.aggregate_by_macro

    graph = EventGraph().add_edge("WAIT", "MOVE_EAST", lag=1, evidence_count=2)
    probe = granger_lite_probe([0, 1, 2, 3], [0, 1, 3, 6], max_lag=1)
    assert graph.digest() and probe.digest

    intervention = build_intervention_result("phase2", [1.0, 2.0, 3.0], [2.0, 3.0, 4.0])
    policy = StatisticalTestPolicy()
    assert policy.tier_for_n(7) == "descriptive_only"
    oee_report = build_oee_metrics_report(
        seed_count=30,
        generation_count=1000,
        metrics={
            "archive_coverage_slope": 0.2,
            "persistent_novelty_rate": 0.3,
            "lineage_persistence": 10.0,
            "behavior_entropy": 1.5,
        },
        confidence_intervals={
            "archive_coverage_slope": (0.1, 0.3),
            "persistent_novelty_rate": (0.2, 0.4),
            "lineage_persistence": (10.0, 12.0),
            "behavior_entropy": (1.2, 1.8),
        },
        shadow_adjusted=True,
        persistence_window_observed=10,
        stagnation_window=5,
        diversity_collapse_flag=False,
    )
    assert oee_report.claim_level == "oee_candidate"

    profile = build_translation_profile(
        "phase2-profile",
        "genome-spec-digest",
        (TranslationWeight("000", "WAIT", 1.0, 1, 0),),
    )
    assert profile.digest

    metadata_only_spec = GenesisExperimentSpec(
        tick_count=0,
        engine_config=GenesisEngineConfig(claim_level="intervention_supported"),
        metadata={
            "validated_intervention_result_digest": canonical_digest({"metadata_only": "intervention"}),
            "effect_size": 1.0,
            "claim_gate_decision_digest": canonical_digest({"metadata_only": "ignored_user_claim_gate"}),
        },
    )
    metadata_only = GenesisEngine.from_spec(metadata_only_spec).run_ticks()
    assert metadata_only.manifest.claim_level == "event_association_only"
    assert metadata_only.manifest.claim_gate_allowed is False

    validated_spec = GenesisExperimentSpec(
        tick_count=0,
        engine_config=GenesisEngineConfig(claim_level="intervention_supported"),
        evidence_validation_context=EvidenceValidationContext(
            intervention_results=(intervention,),
            intervention_protocol_digests=("protocol-artifact",),
            paired_seed_protocol_digests=("paired-seed-artifact",),
        ),
    )
    validated = GenesisEngine.from_spec(validated_spec).run_ticks()
    assert validated.manifest.claim_level == "intervention_supported"
    assert validated.manifest.claim_gate_allowed is True

    print(
        {
            "genome": child.digest[:12],
            "mutation": mutation.digest[:12],
            "adf_records": len(records),
            "ledger": ledger.digest[:12],
            "probe": probe.digest[:12],
            "oee": oee_report.digest[:12],
            "translation": profile.digest[:12],
            "metadata_only_claim": metadata_only.manifest.claim_level,
            "validated_claim": validated.manifest.claim_level,
        }
    )


if __name__ == "__main__":
    main()
