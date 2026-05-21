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
    EvidenceBundle,
    EvidenceRecord,
    ScientificEvidencePack,
    audit_claim_text,
    score_evidence_quality,
)

pack = ScientificEvidencePack("demo-pack", __version__, claim_audit_digest="claim")
bundle = EvidenceBundle(
    "demo-bundle",
    __version__,
    (EvidenceRecord("e1", "trace", "trace", 1, "cfg", "trace"),),
    claim_limitations=("demo limitation",),
)
score = score_evidence_quality(
    pack, bundle, (), audit_claim_text("library-first research scaffold")
)
print({"quality_score": round(score.score_0_to_1, 3), "not_proof": score.warnings[0]})
