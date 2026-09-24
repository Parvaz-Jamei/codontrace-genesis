"""Check the BAIC pin digests under both hashing methods.

The project note docs/claimgate/WINDOWS_TEXT_DIGEST.md requires the LF-normalising
text digest; raw byte hashing is expected to differ on a CRLF checkout.

Usage: python tools/check_pin_methods.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codontrace.genesis.text_digest import sha256_text_file  # noqa: E402

PINS = {
    "docs/hard_experiment_01/results_v7.json": (
        "35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6"
    ),
    "docs/claimgate/risk_bar.json": (
        "4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7"
    ),
    "docs/claimgate/biomedical_study.json": (
        "9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce"
    ),
}


def main() -> int:
    print(f"{'file':45s} {'raw_bytes':11s} {'text_digest':11s}")
    bad = 0
    for rel, pin in PINS.items():
        path = REPO / rel
        raw = hashlib.sha256(path.read_bytes()).hexdigest()
        txt = sha256_text_file(path)
        raw_ok = raw == pin
        txt_ok = txt == pin
        if not txt_ok:
            bad += 1
        print(f"{rel:45s} {'MATCH' if raw_ok else 'MISMATCH':11s} "
              f"{'MATCH' if txt_ok else 'MISMATCH':11s}")
        print(f"   pin : {pin[:20]}...")
        print(f"   raw : {raw[:20]}...")
        print(f"   text: {txt[:20]}...")
    print()
    print("text-digest failures:", bad)
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
