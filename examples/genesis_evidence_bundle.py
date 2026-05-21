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
from codontrace.genesis import EvidenceBundle, EvidenceRecord, validate_evidence_bundle

record = EvidenceRecord(
    evidence_id="e1",
    evidence_type="trace",
    source_component="d0",
    seed=1,
    config_digest="cfg",
    trace_digest="trace",
    limitation_ids=("lim_alpha",),
)
bundle = EvidenceBundle("bundle", __version__, (record,), claim_limitations=("no proof",))
result = validate_evidence_bundle(bundle)
print({"bundle_digest": bundle.digest(), "succeeded": result.succeeded})
