from codontrace.genesis.artifacts import (
    PHASE2_MANIFEST_FIELDS,
    RunManifest,
    phase2_runtime_hashes,
    validate_phase2_manifest_fields,
)
from codontrace.genesis.claim_gate import ClaimRequest, ScientificClaimGate


def _manifest(hashes, *, include_phase2_statuses: bool = True):
    statuses = (
        {f"phase2.{name}.status": "measured" for name in PHASE2_MANIFEST_FIELDS}
        if include_phase2_statuses
        else {}
    )
    return RunManifest(
        run_id="r",
        seed=1,
        config_hash="c",
        codon_table_hash="ct",
        genome_spec_hash="gs",
        rule_set_hash="rs",
        adf_vocabulary_hash="adf",
        initial_population_hash="pop",
        tick_count=1,
        replay_digest="rep",
        runtime_hashes=hashes,
        protocol_statuses=statuses,
    )


def test_phase2_manifest_fields_validate():
    hashes = phase2_runtime_hashes(**{name: f"h-{name}" for name in PHASE2_MANIFEST_FIELDS})
    result = validate_phase2_manifest_fields(_manifest(hashes))
    assert result.passed
    missing = validate_phase2_manifest_fields(_manifest({}, include_phase2_statuses=False))
    assert not missing.passed
    assert "genome_program_digest" in missing.missing_hashes
    assert "protocol_statuses.phase2.genome_program_digest.status" in missing.missing_hashes


def test_claim_gate_phase2_labels_and_overclaim_rejection():
    gate = ScientificClaimGate()
    allowed = gate.decide(
        ClaimRequest(
            "variable_genome_supported",
            {"genome_program_digest": True, "structural_mutation_record": True},
        )
    )
    assert allowed.allowed
    rejected = gate.decide(ClaimRequest("semantic_closure", {}))
    assert not rejected.allowed
    oee = gate.decide(ClaimRequest("oee_candidate", {"oee_metrics": True, "shadow_run": False}))
    assert not oee.allowed
    intervention = gate.decide(
        ClaimRequest(
            "intervention_supported",
            {
                "intervention_result_artifact": True,
                "intervention_result_digest": True,
                "baseline_digest": True,
                "treatment_digest": True,
                "intervention_protocol_digest": True,
                "effect_size": True,
                "paired_seed_protocol_digest": True,
                "claim_gate_decision_digest": True,
            },
        )
    )
    assert intervention.allowed
