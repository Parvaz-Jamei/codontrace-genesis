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
from codontrace.genesis import FinalReleaseManifest

manifest = FinalReleaseManifest(
    version=__version__,
    artifact_name="codontrace-current alpha-mature-research-alpha-finalization.zip",
    source_zip_digest="example-source-digest",
    claim_audit_digest="claim-digest",
    scientific_evidence_validation_digest="evidence-digest",
)
print({"version": manifest.version, "digest": manifest.digest()[:12]})
