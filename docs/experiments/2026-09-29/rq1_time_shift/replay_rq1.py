"""One replay command from run_manifest.json that reproduces the summary.

    python replay_rq1.py --from-manifest run_manifest.json

Steps
1. verify every recorded artifact checksum,
2. recompute the stage-0 fixture pack and check its checksum is unchanged,
3. recompute analysis.json from the raw files and check the analysis digest.

Exit code 0 means REPLAY_OK; 2 means a mismatch.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-manifest", default="run_manifest.json")
    args = parser.parse_args()

    manifest_path = OUT / args.from_manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    checksum_failures = []
    for name, meta in (manifest.get("artifacts") or {}).items():
        path = RAW / name if (RAW / name).exists() else OUT / name
        actual = sha256(path)
        if actual != meta.get("sha256"):
            checksum_failures.append(
                {"artifact": name, "expected": meta.get("sha256"), "actual": actual}
            )

    # Recompute the fixture pack (pure function of the repo's classifier).
    fixtures_hash_before = sha256(RAW / "stage0_fixtures.json")
    sys.path.insert(0, str(OUT))
    importlib.import_module("stage0_fixtures_rq1").main()
    fixtures_hash_after = sha256(RAW / "stage0_fixtures.json")
    fixtures_ok = fixtures_hash_before == fixtures_hash_after

    # Recompute the derived summary from raw only.
    analysis = importlib.import_module("analysis_rq1")
    analysis.main()
    recomputed = json.loads((OUT / "analysis.json").read_text(encoding="utf-8"))
    digest_ok = recomputed.get("analysis_digest") == manifest.get("analysis_digest")

    ok = not checksum_failures and fixtures_ok and digest_ok
    summary = {
        "replay": "REPLAY_OK" if ok else "REPLAY_MISMATCH",
        "manifest": args.from_manifest,
        "checksums_ok": not checksum_failures,
        "checksum_failures": checksum_failures,
        "fixtures_reproduced": fixtures_ok,
        "analysis_digest_ok": digest_ok,
        "decision": recomputed.get("decision"),
        "manifest_decision": manifest.get("decision"),
        "manifest_round": manifest.get("round"),
        "instrument_positive_case": (recomputed.get("flags") or {}).get(
            "instrument_positive_case"
        ),
        "admissible_pi_realised_matrices": (recomputed.get("live_model_attempt") or {}).get(
            "admissible_pi_realised_matrices"
        ),
        "missing_preconditions": (recomputed.get("preconditions") or {}).get("missing"),
    }
    print(json.dumps(summary, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
