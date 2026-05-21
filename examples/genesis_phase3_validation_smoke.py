"""Small public-API Phase 3 validation smoke.

Builds a campaign spec, evidence lineage path, replay manifest and final claim
manifest without private engine internals. This is a smoke artifact, not a heavy
campaign.
"""
from __future__ import annotations

try:
    from ._path_bootstrap import ensure_src_path
except ImportError:
    import sys as _sys
    from pathlib import Path as _Path

    _EXAMPLES_DIR = _Path(__file__).resolve().parent
    if str(_EXAMPLES_DIR) not in _sys.path:
        _sys.path.insert(0, str(_EXAMPLES_DIR))
    from _path_bootstrap import ensure_src_path

ensure_src_path()

from codontrace.genesis import (
    RELEASE_LABEL,
    Phase3SeedPlan, Phase3MetricSpec, Phase3ControlPlan, Phase3ScenarioSpec,
    Phase3CampaignSpec, Phase3CampaignResult,
    EvidenceLineageNode, EvidenceLineageEdge, EvidenceLineageDAG, EvidenceLineageValidator,
    ReplayBundleManifest, ReplayBundleV2,
    FinalClaimManifest, ReleaseEvidencePack, canonical_digest,
)

seed = Phase3SeedPlan((1, 2, 3))
metric = Phase3MetricSpec("qd_score", "quality-diversity score")
scenario = Phase3ScenarioSpec("qd_selection_pressure", "qd-small", canonical_digest({"cfg": "phase3-smoke"}), canonical_digest({"world": "phase3-smoke"}))
spec = Phase3CampaignSpec("phase3-smoke", RELEASE_LABEL, seed, Phase3ControlPlan(("pos",), ("neg",)), (scenario,), (metric,))
result = Phase3CampaignResult(spec)

cfg = EvidenceLineageNode("cfg", "config", spec.digest())
run = EvidenceLineageNode("run", "run_record", result.digest())
gate_digest = canonical_digest({"claim_gate": "phase3-smoke-denied"})
claim_node = EvidenceLineageNode("claim", "claim_decision", gate_digest)
dag = EvidenceLineageDAG((cfg, run, claim_node), (EvidenceLineageEdge("cfg", "run", "executes"), EvidenceLineageEdge("run", "claim", "supports")))
validation = EvidenceLineageValidator().validate(dag)

rbm = ReplayBundleManifest("cfg", seed.digest(), "src", (result.digest(),), "env")
replay = ReplayBundleV2(rbm)
ablation_digest = canonical_digest({"ablation": "not_run_but_explicit_negative_pack"})
claim = FinalClaimManifest(
    "qd-functional-candidate", "QD functional candidate requires selection-pressure evidence", "instrumented_runtime", False,
    ("selection_pressure", "qd_changed_selection"), ("selection_pressure",), ("qd_changed_selection",), replay.digest(), gate_digest, ("cfg", "run", "claim"), 0.0, 0.0, 0.0,
)
pack = ReleaseEvidencePack(RELEASE_LABEL, (claim,), replay.digest(), ablation_digest)
print({"campaign": result.digest()[:12], "lineage_valid": validation.succeeded, "replay": replay.digest()[:12], "pack": pack.digest()[:12]})
