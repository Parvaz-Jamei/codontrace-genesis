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
from codontrace.genesis import EvidenceBundle, EvidenceRecord, summarize_reproducibility

bundle = EvidenceBundle(
    "demo-repro",
    __version__,
    (
        EvidenceRecord("e1", "trace", "trace", 1, "cfg", "trace", replay_digest="replay"),
        EvidenceRecord("e2", "trace", "trace", 2, "cfg2", "trace2"),
    ),
    claim_limitations=("demo limitation",),
)
summary = summarize_reproducibility(bundle)
print({"unique_seeds": summary.unique_seed_count, "replay": summary.deterministic_replay_available})
