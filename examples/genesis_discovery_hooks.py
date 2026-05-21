"""Show typed D0/Discovery planning hooks without making a discovery claim."""

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

from codontrace.genesis import D0BaselineConfig, DiscoveryClaimLevel, DiscoveryWitnessStub


def main() -> None:
    config = D0BaselineConfig(behavior_descriptor_bins={"survival_ticks": 4})
    witness = DiscoveryWitnessStub(
        witness_id="stub",
        claim_level=DiscoveryClaimLevel.NONE,
        behavior_digest="behavior",
        graph_digest="graph",
        vocabulary_digest="vocabulary",
        capsule_store_digest="capsules",
        required_evidence=("d0_baseline", "ablation", "multi_seed_replication"),
    )
    print("d0_enabled", config.enabled)
    print("claim_level", witness.claim_level.value)
    print("no_discovery_claim", True)


if __name__ == "__main__":
    main()
