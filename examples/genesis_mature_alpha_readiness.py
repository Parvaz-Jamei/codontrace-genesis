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

from codontrace import __version__
from codontrace.genesis import (
    APIAuditResult,
    EvidenceBundle,
    ReleaseCandidateChecklist,
    ReleaseGateRecord,
    ReleaseGateStatus,
    ReleaseReadinessProfile,
    ScientificEvidencePack,
    ScientificEvidenceProfile,
    audit_claim_text,
    evaluate_mature_alpha_readiness,
    evaluate_release_candidate,
    score_evidence_quality,
    validate_scientific_evidence_pack,
)

profile = ReleaseReadinessProfile.mature_alpha()
checklist = ReleaseCandidateChecklist(
    __version__,
    "codontrace-demo.zip",
    tuple(ReleaseGateRecord(name, ReleaseGateStatus.PASS) for name in profile.required_gates),
    api_snapshot_digest="api",
    claim_audit_digest="claim",
    validation_bundle_digest="validation",
    citation_digest="citation",
    limitations_digest="limitations",
)
pack = ScientificEvidencePack("demo", __version__, claim_audit_digest="claim")
claim = audit_claim_text("library-first research scaffold")
readiness = evaluate_mature_alpha_readiness(
    __version__,
    evaluate_release_candidate(checklist, profile),
    validate_scientific_evidence_pack(pack, ScientificEvidenceProfile.prepublic()),
    score_evidence_quality(
        pack, EvidenceBundle("b", __version__, (), claim_limitations=("lim",)), (), claim
    ),
    claim,
    APIAuditResult(True, True, 1),
)
print({"accepted": readiness.accepted, "blockers": len(readiness.blocking_issues)})
