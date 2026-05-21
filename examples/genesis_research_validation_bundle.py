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
from codontrace.genesis import ValidationBundle, ValidationRunRecord, ValidationScenario

scenario = ValidationScenario(
    scenario_id="d0_qd_smoke",
    description="Evidence bundle smoke object; no runner and no report.",
    required_components=("d0", "qd"),
    config_digest="cfg:d0_qd_smoke",
    expected_evidence=("trace_digest", "behavior_digest"),
    non_claims=("no_open_ended_discovery_proof",),
)
record = ValidationRunRecord(
    run_id="run:1",
    scenario_id=scenario.scenario_id,
    seed=1,
    trace_digest="trace:1",
    behavior_digest="behavior:1",
    qd_archive_digest="qd:1",
    limitations=("synthetic_smoke_only",),
)
bundle = ValidationBundle(
    bundle_id="bundle:smoke",
    version=__version__,
    scenarios=(scenario,),
    run_records=(record,),
    evidence_digests=(record.trace_digest, record.behavior_digest),
    claim_limitations=("evidence_scaffold_not_proof",),
)
print({"bundle_id": bundle.bundle_id, "digest": bundle.digest()[:12]})
