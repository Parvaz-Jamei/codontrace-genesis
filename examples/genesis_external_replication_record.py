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
from codontrace.genesis import ExternalReplicationRecord

record = ExternalReplicationRecord(
    replication_id="external-demo",
    external_environment="owner-ci-or-lab",
    library_version=__version__,
    scenario_digest="scenario",
    seed_count=3,
    evidence_digest="evidence",
    differences=("hardware/environment not modeled",),
    limitations=("External validation record only.",),
)
print({"replication": record.replication_id, "seeds": record.seed_count})
