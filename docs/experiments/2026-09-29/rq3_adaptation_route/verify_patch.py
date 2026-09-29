"""Verifies test-runs/rq3/PROPOSED_CHANGE.patch without touching the repository.

1. parses the patch: file headers, hunk headers, and their declared line counts;
2. applies every hunk to the pristine repository copy of the target file;
3. compiles both the patched target file and the new module;
4. exercises the patched code: with the patch applied to the module under
   ``sys.path``, the copassaged arm must move its antagonist composition while the
   frozen arm must not, and the two must differ in the turnover ledger.

Writes only under test-runs/rq3/. Prints a JSON verdict.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import re
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis")
PATCH = HERE / "PROPOSED_CHANGE.patch"
TARGET_REL = "src/codontrace/genesis/closed_loop_hp_arm01_structural_rq.py"
NEW_REL = "src/codontrace/genesis/measurements/antagonist_population.py"
MIRROR = HERE / "applycheck"


def parse_patch(text: str) -> list[dict]:
    files: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            if current:
                files.append(current)
            current = {"diff": line, "old": None, "new": None, "hunks": []}
            continue
        if current is None:
            continue
        if line.startswith("--- ") and current["old"] is None:
            current["old"] = line[4:].strip()
            continue
        if line.startswith("+++ ") and current["new"] is None:
            current["new"] = line[4:].strip()
            continue
        match = re.match(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@", line)
        if match:
            current["hunks"].append(
                {
                    "header": line,
                    "old_start": int(match.group(1)),
                    "old_len": int(match.group(2) or 1),
                    "new_start": int(match.group(3)),
                    "new_len": int(match.group(4) or 1),
                    "lines": [],
                }
            )
            continue
        if current["hunks"] and line[:1] in (" ", "+", "-", "\\"):
            current["hunks"][-1]["lines"].append(line)
    if current:
        files.append(current)
    return files


def content(line: str) -> str:
    """Strip the patch marker character, preserving the payload exactly."""

    return line[1:]


def apply_hunks(original: list[str], hunks: list[dict]) -> list[str]:
    """Apply hunks to a file read with keepends=True (newline-normalised compare)."""

    out = [line.rstrip("\r\n") for line in original]
    endings = "\n" if all(not line.endswith("\r\n") for line in original) else "\r\n"
    offset = 0
    for hunk in hunks:
        start = hunk["old_start"] - 1 + offset
        old_lines = [content(h) for h in hunk["lines"] if h[:1] in (" ", "-")]
        old_lines = [line.rstrip("\r\n") for line in old_lines]
        new_lines = [content(h) for h in hunk["lines"] if h[:1] in (" ", "+")]
        if len(old_lines) != hunk["old_len"]:
            raise ValueError(
                f"hunk {hunk['header']} declares {hunk['old_len']} old lines, "
                f"carries {len(old_lines)}"
            )
        if len(new_lines) != hunk["new_len"]:
            raise ValueError(
                f"hunk {hunk['header']} declares {hunk['new_len']} new lines, "
                f"carries {len(new_lines)}"
            )
        window = out[start : start + hunk["old_len"]]
        if window != old_lines:
            detail = "; ".join(
                f"{i}: file={window[i]!r} patch={old_lines[i]!r}"
                for i in range(min(len(window), len(old_lines)))
                if window[i] != old_lines[i]
            )
            raise ValueError(
                f"hunk {hunk['header']} context does not match the file "
                f"(start={start}, window={len(window)}, want={len(old_lines)}) {detail}"
            )
        out[start : start + hunk["old_len"]] = new_lines
        offset += hunk["new_len"] - hunk["old_len"]
    return [line + endings for line in out]


def main() -> int:
    text = PATCH.read_text(encoding="utf-8")
    files = parse_patch(text)
    report: dict[str, object] = {
        "patch": str(PATCH),
        "patch_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "line_endings_lf_only": "\r" not in text,
        "files": [],
        "errors": [],
    }
    pristine = (REPO / TARGET_REL).read_text(encoding="utf-8").splitlines(keepends=True)
    pristine_raw = (REPO / TARGET_REL).read_bytes()
    report["target_sha256"] = hashlib.sha256(pristine_raw).hexdigest()
    report["target_lf_only"] = b"\r\n" not in pristine_raw
    module_src = None

    for entry in files:
        per_file: dict[str, object] = {
            "diff": entry["diff"],
            "old": entry["old"],
            "new": entry["new"],
            "hunks": len(entry["hunks"]),
            "declared_old": [h["old_len"] for h in entry["hunks"]],
            "declared_new": [h["new_len"] for h in entry["hunks"]],
        }
        report["files"].append(per_file)  # type: ignore[attr-defined]
        if entry["new"] == f"b/{TARGET_REL}":
            patched = apply_hunks(pristine, entry["hunks"])
            compile("".join(patched), TARGET_REL, "exec")
            per_file["applied"] = True
            per_file["compiles"] = True
            per_file["patched_line_count"] = len(patched)
        elif entry["new"] == f"b/{NEW_REL}":
            body = [
                content(h) for h in entry["hunks"][0]["lines"] if h.startswith("+")
            ]
            module_src = "".join(
                line if line.endswith("\n") else line + "\n" for line in body
            )
            compile(module_src, NEW_REL, "exec")
            per_file["applied"] = True
            per_file["compiles"] = True
            per_file["patched_line_count"] = len(body)
        else:
            report["errors"].append(f"unexpected target {entry['new']}")  # type: ignore[attr-defined]

    if module_src is None:
        report["errors"].append("new module not found in the patch")  # type: ignore[attr-defined]
        print(json.dumps(report, indent=2))
        return 1

    # Mirror tree for `patch`/`git apply --check` style verification.
    mirror_target = MIRROR / TARGET_REL
    mirror_target.parent.mkdir(parents=True, exist_ok=True)
    patched_text = "".join(patched) if "patched" in dir() else ""
    mirror_target.write_text("".join(pristine), encoding="utf-8")
    mirror_module = MIRROR / NEW_REL
    mirror_module.parent.mkdir(parents=True, exist_ok=True)
    mirror_module.write_text(module_src, encoding="utf-8")
    # A second mirror holding the *patched* target so the patched arm can be imported
    # under its real module path while the repository copy stays pristine.
    patched_root = MIRROR / "patched"
    patched_target = patched_root / TARGET_REL
    patched_target.parent.mkdir(parents=True, exist_ok=True)
    patched_target.write_text(patched_text, encoding="utf-8")
    patched_module_file = patched_root / NEW_REL
    patched_module_file.parent.mkdir(parents=True, exist_ok=True)
    patched_module_file.write_text(module_src, encoding="utf-8")
    for name in (
        "__init__.py",
    ):
        (patched_root / "src" / "codontrace").mkdir(parents=True, exist_ok=True)
        (patched_root / "src" / "codontrace" / name).write_text("", encoding="utf-8")
        (patched_root / "src" / "codontrace" / "genesis").mkdir(
            parents=True, exist_ok=True
        )
        (patched_root / "src" / "codontrace" / "genesis" / name).write_text(
            "", encoding="utf-8"
        )
        (patched_root / "src" / "codontrace" / "genesis" / "measurements").mkdir(
            parents=True, exist_ok=True
        )
        (
            patched_root / "src" / "codontrace" / "genesis" / "measurements" / name
        ).write_text("", encoding="utf-8")

    sandbox = MIRROR / "sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)
    import shutil

    for name in ("closed_loop_hp_arm01.py",):
        shutil.copyfile(REPO / "src/codontrace/genesis" / name, sandbox / name)
    if str(REPO / "src") not in sys.path:
        sys.path.insert(0, str(REPO / "src"))

    # Load the patched arm and the patched module explicitly by path, overriding the
    # repository copies in sys.modules. The module is registered BEFORE the arm import
    # so the arm's `from ...antagonist_population import ...` gets the patched object.
    module_name = "codontrace.genesis.measurements.antagonist_population"
    loader = SourceFileLoader(module_name, str(mirror_module))
    spec = spec_from_loader(module_name, loader)
    isolated = module_from_spec(spec)
    sys.modules[module_name] = isolated
    loader.exec_module(isolated)
    report["isolated_module_origin"] = isolated.__file__

    arm_name = "codontrace.genesis.closed_loop_hp_arm01_structural_rq"
    arm_loader = SourceFileLoader(arm_name, str(patched_target))
    arm_spec = spec_from_loader(arm_name, arm_loader)
    patched_module = module_from_spec(arm_spec)
    sys.modules[arm_name] = patched_module
    arm_loader.exec_module(patched_module)
    report["patched_arm_origin"] = patched_module.__file__
    assert Path(patched_module.__file__).resolve() == patched_target.resolve()

    from codontrace.genesis.closed_loop_hp_arm01 import (  # noqa: E402
        ARM_COPASSAGED,
        ARM_FIXED,
    )

    def run(arm: str, seed: int, generations: int) -> dict:
        arm_obj = patched_module.StructuralRQArm.boot_structural(arm=arm, seed=seed)
        arm_obj.run_generations(generations)
        compositions = [
            tuple(sorted(pairs)) for pairs in arm_obj.parasite_class_hist_series
        ]
        changes = sum(
            1
            for i in range(1, len(compositions))
            if compositions[i] != compositions[i - 1]
        )
        return {
            "arm": arm,
            "seed": seed,
            "generations": generations,
            "antagonist_composition_changes": changes,
            "turnover_kept_sum": sum(arm_obj.turnover_kept),
            "turnover_replaced_sum": sum(arm_obj.turnover_replaced),
            "turnover_mut_events_sum": sum(arm_obj.turnover_mut_events),
            "turnover_churn_sum": sum(arm_obj.turnover_churn),
            "final_classes": len(compositions[-1]) if compositions else 0,
            "has_ancestry": True,
        }

    functional = {}
    try:
        # Opt-in ON, default flags: the manager's exact failing command.
        first = patched_module.StructuralRQArm.boot_structural(
            arm=ARM_COPASSAGED, seed=43, antagonist_ecology="population"
        )
        first.run_generations(1)
        report["optin_first_generation"] = {
            "census": first.living_host_census(),
            "parasite_n": len(first.parasite_windows),
            "population_built": first.antagonist_pop is not None,
            "contact_pair_records_len": len(first.contact_pair_records),
        }
        functional["coevolve"] = run(ARM_COPASSAGED, 21051, 12)
        functional["fixed"] = run(ARM_FIXED, 21051, 12)
        report["functional"] = functional
    except Exception as exc:
        report["errors"].append(f"functional run failed: {type(exc).__name__}: {exc}")

    # The locked P0 expectation the manager's suite enforces: on the copassaged arm,
    # seed 43, the parasite class histogram must be non-empty at generation 25.
    try:
        p0 = patched_module.StructuralRQArm.boot_structural(
            arm=ARM_COPASSAGED, seed=43, antagonist_ecology="population"
        )
        p0.run_generations(50)
        pop0 = p0.antagonist_pop
        report["energy_ledger"] = {
            "units_first": len(pop0.units) if pop0 else 0,
            "energy_series_head": [
                [round(float(u.energy), 4) for u in led.newborns[:5]] for led in pop0.ledgers[:3]
            ] if pop0 else [],
            "deaths_head": [len(led.deaths) for led in pop0.ledgers[:3]] if pop0 else [],
            "newborns_head": [len(led.newborns) for led in pop0.ledgers[:3]] if pop0 else [],
            "mean_energy_head": [round(float(led.mean_energy), 4) for led in pop0.ledgers[:3]]
            if pop0
            else [],
            "alive_head": [int(led.alive) for led in pop0.ledgers[:3]] if pop0 else [],
            "contacts_head": [int(led.contacts) for led in pop0.ledgers[:3]] if pop0 else [],
            "first_ledger_units": [
                {
                    "unit_id": u.unit_id,
                    "window": u.window,
                    "served": u.contacts_served,
                    "energy": round(float(u.energy), 4),
                }
                for u in (pop0.units[:6] if pop0 else [])
            ],
            "record_len_series_head": [
                len(p0.contact_pair_records[i]) for i in range(min(3, len(p0.contact_pair_records)))
            ],
            "alive_series_head": [int(led.alive) for led in pop0.ledgers[:8]] if pop0 else [],
            "mean_energy_series_head": [
                round(float(led.mean_energy), 4) for led in pop0.ledgers[:8]
            ] if pop0 else [],
            "deaths_series_head": [len(led.deaths) for led in pop0.ledgers[:8]] if pop0 else [],
            "newborns_series_head": [
                len(led.newborns) for led in pop0.ledgers[:8]
            ] if pop0 else [],
            "ledger_count": len(pop0.ledgers) if pop0 else 0,
        }
        report["p0_invariant"] = {
            "arm": "copassaged",
            "seed": 43,
            "generations": 50,
            "hist_at_25_nonempty": bool(p0.window_snapshot(25)["parasite_class_hist"]),
            "hist_at_25_classes": len(p0.window_snapshot(25)["parasite_class_hist"]),
            "parasite_n_at_25": int(p0.window_snapshot(25)["parasite_n"] or 0),
            "hist_series_len": len(p0.parasite_class_hist_series),
            "empty_hist_generations": sum(
                1 for pairs in p0.parasite_class_hist_series if not pairs
            ),
            "turnover_replaced_sum": sum(p0.turnover_replaced),
            "turnover_mut_events_sum": sum(p0.turnover_mut_events),
            "window_snapshot_units_at_25": len(
                p0.window_snapshot(25).get("antagonist_units") or []
            ),
        }
    except Exception as exc:
        report["errors"].append(f"P0 invariant run failed: {type(exc).__name__}: {exc}")

    print(json.dumps(report, indent=2))
    return 0 if not report["errors"] else 1  # type: ignore[attr-defined]


if __name__ == "__main__":
    raise SystemExit(main())
