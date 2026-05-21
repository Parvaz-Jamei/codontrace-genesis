"""Small Phase-B final evidence smoke.

Writes deterministic sample artifacts for Phase-B release wiring.  This example
is intentionally small and descriptive; it does not claim strong discovery/OEE.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from codontrace.genesis import GenesisEngine
from codontrace.genesis.runtime_profiles import GenesisRuntimeProfile


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run a small deterministic Phase-B final evidence smoke.")
    parser.add_argument("--out", default="artifacts/phase_b_final_smoke", help="Output directory for Phase-B smoke artifacts.")
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    result = GenesisEngine.from_spec(GenesisRuntimeProfile.toolchain_pilot_world(seed=13, tick_count=3)).run_ticks()
    phase_b = result.phase_b_scientific_maturity_report
    manifest = result.evidence_manifest
    (out / "phase_b_scientific_maturity_report.json").write_text(json.dumps(phase_b.to_dict(), sort_keys=True, indent=2), encoding="utf-8")
    (out / "phase_b_evidence_manifest.json").write_text(json.dumps(manifest.to_dict(), sort_keys=True, indent=2), encoding="utf-8")
    (out / "phase_b_release_pack_sample.json").write_text(json.dumps(phase_b.release_packs[0].to_dict(), sort_keys=True, indent=2), encoding="utf-8")
    (out / "phase_b_smoke_index.json").write_text(json.dumps({
        "schema_version": "phase_b_smoke_index_v1",
        "phase_b_report_digest": phase_b.digest(),
        "manifest_digest": manifest.digest(),
        "release_pack_digest": phase_b.release_packs[0].digest(),
        "strong_claim_status": "downgraded_single_seed_smoke",
    }, sort_keys=True, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(out), "phase_b_report_digest": phase_b.digest()}, sort_keys=True))


if __name__ == "__main__":
    main()
