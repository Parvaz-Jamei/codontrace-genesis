"""Verify that PROPOSED_CHANGE_rng_backend.patch applies and reproduces the tree.

Steps (no repo writes; works on copies under test-runs/):
  1. copy the provenance baseline to a fresh scratch root;
  2. apply the unified diff hunk-by-hunk with exact context matching (hunks in
     reverse line order, as `git apply` does);
  3. assert the resulting 7 files are byte-identical to the already-verified
     patched tree used for the experiments (test-runs/ci_verify_scratch).

Usage:
    python -B verify_patch_applies.py <baseline_root> <verified_patched_root> <scratch_out> <patch>
"""

from __future__ import annotations

import hashlib
import re
import shutil
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


def apply_patch(patch_text: str, target: Path) -> list[str]:
    text = "".join(
        line for line in patch_text.splitlines(keepends=True) if not line.startswith("diff --git ")
    )
    blocks = list(re.finditer(r"^--- a/(\S+)\n\+\+\+ b/\S+\n", text, flags=re.M))
    applied: list[str] = []
    for block in blocks:
        rel = block.group(1)
        next_block = text.find("--- a/", block.end())
        body = text[block.end() : next_block if next_block != -1 else len(text)]
        hunks = list(re.finditer(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@[^\n]*\n", body, flags=re.M))
        path = target / rel
        content = path.read_text(encoding="utf-8")
        for m in reversed(hunks):
            start = int(m.group(1)) - 1
            next_hunk = re.search(r"^@@ ", body[m.end() :], flags=re.M)
            hunk_text = (
                body[m.end() : m.end() + next_hunk.start()] if next_hunk else body[m.end() :]
            )
            hunk_lines = hunk_text.splitlines(keepends=True)
            old_lines = [line[1:] for line in hunk_lines if line[:1] in (" ", "-")]
            new_lines = [line[1:] for line in hunk_lines if line[:1] in (" ", "+")]
            lines = content.splitlines(keepends=True)
            actual = lines[start : start + len(old_lines)]
            if actual != old_lines:
                raise SystemExit(
                    f"{rel}: context mismatch at line {start + 1}\n"
                    f"  expected: {old_lines[:2]!r}\n  actual:   {actual[:2]!r}"
                )
            lines[start : start + len(old_lines)] = new_lines
            content = "".join(lines)
        path.write_text(content, encoding="utf-8")
        applied.append(rel)
    return applied


def main() -> int:
    baseline = Path(sys.argv[1])
    verified = Path(sys.argv[2])
    scratch = Path(sys.argv[3])
    patch_path = Path(sys.argv[4])
    if scratch.exists():
        shutil.rmtree(scratch)
    shutil.copytree(baseline, scratch)
    applied = apply_patch(patch_path.read_text(encoding="utf-8"), scratch)
    print(f"applied {len(applied)} files")
    ok = True
    for rel in SCOPE:
        same = hashlib.sha256((verified / rel).read_bytes()).hexdigest() == hashlib.sha256(
            (scratch / rel).read_bytes()
        ).hexdigest()
        ok = ok and same
        print(("OK  " if same else "DIFF"), rel)
    print("PATCH_REPRODUCES_TREE:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
