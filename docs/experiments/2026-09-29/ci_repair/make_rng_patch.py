"""Generate the git-appliable unified patch for the RNG backend migration.

Compares the provenance baseline (default: test-runs/verify/full6187ff4) with
the patched scratch tree (default: test-runs/ci_verify_scratch) for the 8 files
in scope and writes a `git apply -p1`-compatible diff.

Usage:
    python -B make_rng_patch.py <baseline_root> <patched_root> <out.patch>
"""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

SCOPE = (
    "src/codontrace/rng.py",
    "src/codontrace/life_loop/contact_atp_ledger.py",
    "src/codontrace/genesis/campaigns/discovery_q_20260928_idea1.py",
    "src/codontrace/genesis/campaigns/discovery_q_20260928_idea2.py",
    "src/codontrace/genesis/campaigns/discovery_q_20260928_idea3.py",
    "src/codontrace/genesis/campaigns/discovery_q_20260928_idea5.py",
    "src/codontrace/genesis/campaigns/discovery_q_20260928_idea6.py",
)


def main() -> int:
    baseline = Path(sys.argv[1])
    patched = Path(sys.argv[2])
    out = Path(sys.argv[3])
    chunks: list[str] = []
    changed: list[str] = []
    for rel in SCOPE:
        old = (baseline / rel).read_text(encoding="utf-8").splitlines(keepends=True)
        new = (patched / rel).read_text(encoding="utf-8").splitlines(keepends=True)
        if old == new:
            continue
        changed.append(rel)
        diff = difflib.unified_diff(
            old,
            new,
            fromfile=f"a/{rel}",
            tofile=f"b/{rel}",
            n=3,
        )
        chunks.append(f"diff --git a/{rel} b/{rel}\n")
        chunks.extend(diff)
    out.write_text("".join(chunks), encoding="utf-8")
    print(f"wrote {out} with {len(changed)} changed files")
    for rel in changed:
        print(f"  {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
