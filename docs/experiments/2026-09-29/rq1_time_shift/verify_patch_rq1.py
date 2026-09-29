"""Read-only verification of PROPOSED_CHANGE.patch.

Parses the unified diff, applies every hunk **in memory** (the repository files
are only read, never written), py_compiles the results, and executes the new
contact-pressure law's assertions. Reports PATCH_OK / PATCH_MISMATCH.
"""

from __future__ import annotations

import py_compile
import re
import tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis")
PATCH = OUT / "PROPOSED_CHANGE.patch"


def split_patch(text: str):
    files = []
    current = None
    hunk = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            current = {"header": line, "path": None, "new_file": False, "hunks": []}
            files.append(current)
            hunk = None
        elif line.startswith("new file mode"):
            current["new_file"] = True
        elif line.startswith("--- "):
            current["old"] = line[4:]
        elif line.startswith("+++ "):
            current["path"] = line[4:]
        elif line.startswith("@@"):
            m = re.match(r"@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
            hunk = {
                "old_start": int(m.group(1)),
                "old_len": int(m.group(2) or 1),
                "new_start": int(m.group(3)),
                "new_len": int(m.group(4) or 1),
                "lines": [],
            }
            current["hunks"].append(hunk)
        elif hunk is not None and (line.startswith("+") or line.startswith("-") or line.startswith(" ") or line == ""):
            hunk["lines"].append(line)
    return files


def apply_hunks(original: list[str], hunks) -> tuple[list[str], list[str]]:
    result: list[str] = []
    errors: list[str] = []
    cursor = 0  # 0-based index into original
    for h in hunks:
        start = h["old_start"] - 1
        if start < cursor:
            errors.append(f"hunk at {h['old_start']} overlaps a previous hunk")
        # copy untouched lines
        result.extend(original[cursor:start])
        idx = start
        for line in h["lines"]:
            tag, body = (line[0], line[1:]) if line else (" ", "")
            if tag == " ":
                if idx >= len(original) or original[idx] != body:
                    errors.append(
                        f"context mismatch at line {idx + 1}: file={original[idx]!r} patch={body!r}"
                    )
                result.append(body)
                idx += 1
            elif tag == "-":
                if idx >= len(original) or original[idx] != body:
                    errors.append(
                        f"removal mismatch at line {idx + 1}: file={original[idx]!r} patch={body!r}"
                    )
                idx += 1
            elif tag == "+":
                result.append(body)
        cursor = idx
        # verify the hunk consumed the declared old length
        consumed = sum(1 for line in h["lines"] if line[:1] in (" ", "-") or line == "")
        if consumed != h["old_len"]:
            errors.append(
                f"hunk at {h['old_start']} consumed {consumed} old lines, header says {h['old_len']}"
            )
    result.extend(original[cursor:])
    return result, errors


def main() -> int:
    files = split_patch(PATCH.read_text(encoding="utf-8"))
    report = {"files": [], "errors": []}
    tmp = Path(tempfile.mkdtemp(prefix="rq1_patch_"))
    for f in files:
        rel = f["path"].removeprefix("b/")
        if f.get("new_file"):
            body = []
            for h in f["hunks"]:
                for line in h["lines"]:
                    if line.startswith("+"):
                        body.append(line[1:])
            target = tmp / Path(rel).name
            target.write_text("\n".join(body) + "\n", encoding="utf-8")
            if target.suffix == ".py":
                try:
                    py_compile.compile(str(target), doraise=True)
                    compiled = True
                except py_compile.PyCompileError as exc:
                    compiled = False
                    report["errors"].append(f"{rel}: {exc}")
            else:
                compiled = None
            declared = sum(h["new_len"] for h in f["hunks"])
            report["files"].append(
                {
                    "path": rel,
                    "mode": "new_file",
                    "declared_new_len": declared,
                    "actual_new_len": len(body),
                    "len_matches": declared == len(body),
                    "compiles": compiled,
                }
            )
            if not compiled and compiled is not None or declared != len(body):
                report["errors"].append(
                    f"{rel}: declared {declared} lines, wrote {len(body)}"
                )
            if rel == "src/codontrace/life_loop/contact_pressure.py":
                import importlib.util
                import sys

                sys.path.insert(0, str(REPO / "src"))
                spec = importlib.util.spec_from_file_location("cp_check", target)
                mod = importlib.util.module_from_spec(spec)
                sys.modules["cp_check"] = mod
                spec.loader.exec_module(mod)
                policy = mod.ContactPressurePolicy()
                checks = {
                    "kappa": policy.kappa,
                    "intended_000000_000001": policy.intended_debit("000000", "000001"),
                    "intended_111100_000011": policy.intended_debit("111100", "000011"),
                    "realised_capped": mod.ContactPressurePolicy.realised_debit(1.2, 0.5),
                    "realised_full": mod.ContactPressurePolicy.realised_debit(1.2, 10.0),
                }
                from codontrace.genesis.measurements.rq_frequency_clocks import (
                    reference_graded_affinity,
                )

                mismatch = [
                    (h, a)
                    for h in ("000000", "111100", "010101", "101010")
                    for a in ("000011", "111111", "000001", "110011")
                    if mod.graded_affinity(h, a) != reference_graded_affinity(h, a)
                ]
                report["contact_pressure_checks"] = {
                    "values": checks,
                    "kappa_approx_1_2": abs(policy.kappa - 1.2) < 1e-12,
                    "intended_approx_1_0": abs(checks["intended_000000_000001"] - 1.0)
                    < 1e-12,
                    "zero_affinity": checks["intended_111100_000011"] == 0.0,
                    "cap_ok": abs(checks["realised_capped"] - 0.5) < 1e-12,
                    "affinity_mismatches_vs_reference": mismatch,
                }
                if mismatch or not report["contact_pressure_checks"]["kappa_approx_1_2"]:
                    report["errors"].append("contact_pressure.py value checks failed")
        else:
            original_path = REPO / rel
            original = original_path.read_text(encoding="utf-8").splitlines()
            report.setdefault("debug", {})[rel] = {
                "hunk0_lines": [
                    {"tag": (l[0] if l else " "), "body": (l[1:] if l else "")}
                    for l in f["hunks"][0]["lines"][:8]
                ],
                "original_head": [
                    {"i": i, "line": original[i]} for i in range(9, 16)
                ],
                "hunk_headers": [
                    {"old_start": h["old_start"], "old_len": h["old_len"]}
                    for h in f["hunks"]
                ],
            }
            patched, errs = apply_hunks(original, f["hunks"])
            target = tmp / Path(rel).name
            target.write_text("\n".join(patched) + "\n", encoding="utf-8")
            try:
                py_compile.compile(str(target), doraise=True)
                compiled = True
            except py_compile.PyCompileError as exc:
                compiled = False
                errs.append(str(exc))
            report["files"].append(
                {
                    "path": rel,
                    "mode": "modified",
                    "hunks": len(f["hunks"]),
                    "n_original_lines": len(original),
                    "n_patched_lines": len(patched),
                    "compiles": compiled,
                }
            )
            report["errors"].extend(errs)
            if errs:
                report["errors"].append(f"{rel}: hunk application failed")

    ok = not report["errors"] and all(
        (item.get("compiles") is not False) and item.get("len_matches", True)
        for item in report["files"]
    )
    report["result"] = "PATCH_OK" if ok else "PATCH_MISMATCH"
    import json

    print(json.dumps(report, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
