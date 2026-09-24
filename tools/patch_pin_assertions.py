"""Repoint BAIC pin assertions onto the LF-normalising text digest.

Windows checkouts have core.autocrlf=true, so raw working-tree bytes are CRLF and
never match a pin recorded from the repository blob. The project's own note
docs/claimgate/WINDOWS_TEXT_DIGEST.md and codontrace.genesis.text_digest exist for
this. Two test files are skipped on purpose: test_text_digest.py asserts the
difference between the two methods, and test_claimgate_ladder_packs.py already
compares normalised digests.

Usage: python tools/patch_pin_assertions.py [--apply]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TESTS = REPO / "tests"

SKIP = {"test_text_digest.py", "test_claimgate_ladder_packs.py"}

# (compiled pattern, replacement)
RULES = [
    (
        re.compile(
            r'__import__\("hashlib"\)\.sha256\((\w+?)\.read_bytes\(\)\)\.hexdigest\(\)'
        ),
        r"sha256_text_file(\1)",
    ),
    (
        re.compile(
            r'hashlib\.sha256\(\(ROOT / (\w+?)\)\.read_bytes\(\)\)\.hexdigest\(\)'
        ),
        r"sha256_text_file(ROOT / \1)",
    ),
    (
        re.compile(r'hashlib\.sha256\((\w+?)\.read_bytes\(\)\)\.hexdigest\(\)'),
        r"sha256_text_file(\1)",
    ),
]

IMPORT_LINE = "from codontrace.genesis.text_digest import sha256_text_file\n"


def patch(path: Path, apply: bool) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8")
    original = text
    changes = 0
    for pattern, repl in RULES:
        text, n = pattern.subn(repl, text)
        changes += n
    if changes == 0:
        return False, "no raw-byte pin assertion found"

    if "sha256_text_file" not in text.split("def ")[0] or IMPORT_LINE not in text:
        lines = text.splitlines(keepends=True)
        last_import = -1
        depth = 0
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if depth > 0:
                # inside a multi-line import; wait for the closing bracket
                depth += stripped.count("(") - stripped.count(")")
                last_import = idx
                continue
            if stripped.startswith("import ") or stripped.startswith("from "):
                last_import = idx
                depth += stripped.count("(") - stripped.count(")")
                continue
            if stripped.startswith("def ") or stripped.startswith("class "):
                break
        if last_import < 0:
            return False, "could not locate an import block"
        lines.insert(last_import + 1, IMPORT_LINE)
        text = "".join(lines)

    if apply:
        path.write_text(text, encoding="utf-8")
    return True, f"{changes} replacement(s)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    touched = 0
    for path in sorted(TESTS.glob("test_*.py")):
        if path.name in SKIP:
            print(f"SKIP {path.name}")
            continue
        ok, note = patch(path, args.apply)
        if ok:
            touched += 1
            print(f"{'PATCHED' if args.apply else 'WOULD PATCH'} {path.name}: {note}")
    print()
    print(f"{'patched' if args.apply else 'would patch'} {touched} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
