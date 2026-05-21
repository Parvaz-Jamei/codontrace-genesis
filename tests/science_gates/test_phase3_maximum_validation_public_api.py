
import pytest
from codontrace.genesis import (
    RELEASE_LABEL, RELEASE_ARTIFACT_NAME,
    Phase3SeedPlan, Phase3MetricSpec, Phase3ControlPlan, Phase3ScenarioSpec,
    Phase3CampaignSpec, Phase3CampaignResult,
    EvidenceLineageNode, EvidenceLineageEdge, EvidenceLineageDAG, EvidenceLineageValidator,
    ReplayBundleManifest, ReplayBundleV2, ReplayEquivalenceReport,
    PreregisteredMetric, SeedSweepPlan, PairedComparisonResult, MultipleComparisonAudit,
    BenchmarkScenarioCatalog, QDScoreReport, CoverageReport, ParetoObjectiveVector,
    ADFCompressionReport, InterventionSpec, InterventionExecutor, build_causal_evidence_report,
    SocialClaimLadder, SwarmResilienceReport, NoveltyTrajectory, LearnabilityReport,
    GenesisPluginSpec, PluginValidationReport, ResourceBudgetPolicy, ScaleBenchmarkSpec,
    FinalClaimManifest, ReleaseEvidencePack, canonical_digest,
)
from codontrace.errors import ConfigurationError, PluginError


def D(name: str) -> str:
    return canonical_digest({"test_digest": name})


def test_phase3_release_identity_public():
    assert "phase3" in RELEASE_LABEL
    assert RELEASE_ARTIFACT_NAME.endswith(".zip")


def test_phase3_campaign_spec_public_api_and_empty_result_status():
    seed=Phase3SeedPlan((1,2,3))
    metric=Phase3MetricSpec("fitness", "task score")
    scenario=Phase3ScenarioSpec("qd_selection_pressure", "qd-small", D("cfg"), D("world"))
    spec=Phase3CampaignSpec("camp", RELEASE_LABEL, seed, Phase3ControlPlan(("pos",),("neg",)), (scenario,), (metric,))
    result=Phase3CampaignResult(spec)
    assert result.status == "empty_but_available"
    assert result.manifest.campaign_spec_digest == spec.digest()
    assert result.digest() == Phase3CampaignResult(spec).digest()


def test_campaign_spec_rejects_nondeterministic_seed_policy():
    with pytest.raises(ValueError):
        Phase3SeedPlan((1,2), deterministic_policy="random_clock")


def test_evidence_lineage_dag_rejects_cycle_and_requires_path():
    cfg=EvidenceLineageNode("cfg","config",D("d1"))
    run=EvidenceLineageNode("run","run_record",D("d2"))
    claim=EvidenceLineageNode("claim","claim_decision",D("d3"))
    dag=EvidenceLineageDAG((cfg,run,claim),(EvidenceLineageEdge("cfg","run","produces"), EvidenceLineageEdge("run","claim","supports")))
    assert EvidenceLineageValidator().validate(dag).succeeded
    with pytest.raises(ConfigurationError):
        EvidenceLineageDAG((cfg,run),(EvidenceLineageEdge("cfg","run","x"), EvidenceLineageEdge("run","cfg","x")))


def test_replay_bundle_manifest_rejects_missing_artifact_digest_and_reports_mismatch():
    with pytest.raises(ValueError):
        ReplayBundleManifest("cfg","seed","src",("",),"env")
    m=ReplayBundleManifest(D("cfg"),D("seed"),D("src"),(D("a"),D("b")),D("env"))
    assert ReplayBundleV2(m).digest() == ReplayBundleV2(m).digest()
    r=ReplayEquivalenceReport(D("a"),D("b"),False,"manifest.runtime_hashes.x")
    assert not r.equivalent and r.mismatch_field_path


def test_preregistered_statistics_require_finite_and_multiple_audit():
    metric=PreregisteredMetric("reward","task")
    plan=SeedSweepPlan((1,2,3))
    comp=PairedComparisonResult(metric,D("base"),D("treat"),plan.digest(),1.0,3,0.2,1.8)
    assert not comp.claim_downgraded
    assert MultipleComparisonAudit(3).digest()
    with pytest.raises(ConfigurationError):
        PairedComparisonResult(metric,D("b"),D("t"),plan.digest(),float("nan"),3,0,1)


def test_benchmark_catalog_has_required_families_and_public_api_only():
    catalog=BenchmarkScenarioCatalog.phase3_default()
    families={c.scenario_family for c in catalog.contracts}
    assert "collective_coordination" in families
    assert "oee_discovery_curriculum" in families
    assert all(c.public_api_only for c in catalog.contracts)
    assert catalog.digest() == BenchmarkScenarioCatalog.phase3_default().digest()


def test_qd_reports_and_pareto_reject_non_finite():
    report=QDScoreReport(D("archive"),10.0,2,"selection_pressure",True)
    assert report.functional_claim_eligible
    cov=CoverageReport(D("archive"),2,4,"behavior_descriptor_v1")
    assert cov.coverage == 0.5
    with pytest.raises(ConfigurationError):
        ParetoObjectiveVector(float("inf"),1,1,1,1,1)


def test_adf_compression_requires_source_reuse_and_compression():
    weak=ADFCompressionReport("ADF_X",D("source"),1,0.0,D("runtime"))
    assert not weak.claim_eligible
    strong=ADFCompressionReport("ADF_X",D("source"),2,0.5,D("runtime"))
    assert strong.claim_eligible


def test_causal_executor_requires_intervention_pair_and_effect_report():
    spec=InterventionSpec("i","factor",D("base"),D("treat"),D("seed"))
    pair=InterventionExecutor().execute(spec, baseline_metric=1.0, treatment_metric=2.0)
    report=build_causal_evidence_report((pair,))
    assert report.claim_eligible


def test_social_collective_swarm_oee_ladders_are_evidence_gated():
    assert SocialClaimLadder(capsule_transfer=True).level == "social_interaction_observed"
    assert SocialClaimLadder(non_capsule_cooperation=True, heldout_partner=True).level == "social_intelligence_candidate"
    swarm=SwarmResilienceReport(1.0,0.8,D("dropout"),D("control"))
    assert swarm.claim_eligible
    novelty=NoveltyTrajectory((0.1,0.2))
    learn=LearnabilityReport(1.0,D("heldout"),D("replay"))
    assert novelty.persistent and learn.claim_eligible


def test_plugin_scale_and_final_claim_manifest_contracts():
    plugin=GenesisPluginSpec("p","action_primitive","1.0",("action",))
    assert PluginValidationReport(plugin.digest(), True, ("ok",)).passed
    assert ResourceBudgetPolicy(100).digest()
    assert ScaleBenchmarkSpec(8,20).digest()
    with pytest.raises(Exception):
        GenesisPluginSpec("p","bad","1.0",("x",))
    claim=FinalClaimManifest("c","claim","control_supported",True,("e",),("e",),(),D("replay"),D("gate"),(D("cfg"),D("run"),D("claim")),1.0,0.1,2.0)
    pack=ReleaseEvidencePack(RELEASE_LABEL,(claim,),D("replay_index"),D("ablation"))
    assert pack.digest()
    denied = FinalClaimManifest("c","claim","control_supported",True,("e",),(),("e",),D("replay"),D("gate"),(),0,0,0)
    assert not denied.allowed
    assert "missing_required_evidence" in denied.validation_reasons
    assert "missing_evidence_lineage_path" in denied.validation_reasons
