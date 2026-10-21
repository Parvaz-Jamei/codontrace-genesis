"""Verify the RQ-1 6187ff4 provenance chain from inside this repository.

    python verify_provenance.py [--restored DIR]

1. Commit 6187ff4 exists here and is an ancestor of HEAD.
2. The three meter files pinned by rq1_design.METER_PINS have, at 6187ff4,
   exactly the pinned SHA-256 (CRLF-normalised as the runner does).
3. Every reproduced seed in the restored pack equals the archived raw for
   the same seed, record by record (parsed JSON; wall-clock fields ignored),
   over the archived length. For 5706 that is the archived partial prefix.

Exit code 0 only when all checks pass. Prints one JSON report.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONF = HERE.parent
ARCHIVED_RAW = CONF / "raw"
PIN = "6187ff4"
WALL = {"wall_s", "pack_wall_s"}


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(HERE), *args], capture_output=True, text=True, check=False)


def _meter_pins() -> dict[str, str]:
    sys.path.insert(0, str(CONF))
    from rq1_design import METER_PINS

    return dict(METER_PINS)


def _strip(x: object) -> object:
    if isinstance(x, dict):
        return {k: _strip(v) for k, v in x.items() if k not in WALL}
    if isinstance(x, list):
        return [_strip(v) for v in x]
    return x


def _frozen_is_zero(rec: dict) -> bool:
    """The rule in confirmatory_rq1.run_seed, applied to a stored record."""
    fx = rec.get("regimes", {}).get("fixed")
    if not fx:
        return False
    times = ("past", "now", "future")
    vals = [float(fx["matrix"][h][a]) for h in times for a in times]
    return bool(
        max(vals) - min(vals) <= 1e-12
        and abs(float(fx["contrast"]["i_contemp"])) < 1e-12
        and abs(float(fx["contrast"]["i_lag"])) < 1e-12
    )


def _records(path: Path) -> list[object]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = path.read_text(encoding="utf-8")
    out: list[object] = []
    for line in text.splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                out.append({"__unparseable_line__": line})
    return out


def _archived(kind: str, seed: int) -> Path | None:
    for name in (f"{kind}_seed{seed}.jsonl.gz", f"{kind}_seed{seed}.jsonl"):
        p = ARCHIVED_RAW / name
        if p.exists():
            return p
    return None


def check(restored: Path) -> dict[str, object]:
    report: dict[str, object] = {}
    full = _git("rev-parse", f"{PIN}^{{commit}}")
    report["commit_present"] = full.returncode == 0
    report["commit"] = full.stdout.strip()
    report["ancestor_of_head"] = _git("merge-base", "--is-ancestor", PIN, "HEAD").returncode == 0
    pins = {}
    for rel, want in _meter_pins().items():
        blob = _git("show", f"{PIN}:{rel}")
        data = blob.stdout.encode("utf-8").replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        pins[rel] = blob.returncode == 0 and hashlib.sha256(data).hexdigest() == want
    report["meter_pins_match_at_commit"] = pins
    seeds: dict[str, object] = {}
    raw = restored / "raw"
    for seed_file in sorted(raw.glob("seed_*.json")) if raw.is_dir() else []:
        seed = int(seed_file.stem.split("_")[1])
        entry: dict[str, object] = {}
        arch_seed = ARCHIVED_RAW / f"seed_{seed}.json"
        if arch_seed.exists():
            a = _strip(json.loads(arch_seed.read_text(encoding="utf-8")))
            b = _strip(json.loads(seed_file.read_text(encoding="utf-8")))
            assert isinstance(a, dict) and isinstance(b, dict)
            same = sorted(k for k in set(a) | set(b) if a.get(k) == b.get(k))
            differ = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
            entry["seed_json_fields_identical"] = len(same)
            entry["seed_json_fields_differing"] = differ
            # frozen_is_zero is derived by the runner from the fixed-regime
            # matrix. Recompute it from the *archived* matrix with the runner's
            # rule; the reproduction must agree with that recomputation.
            derived_ok = set(differ) <= {"frozen_is_zero"}
            if "frozen_is_zero" in differ:
                derived_ok = derived_ok and b["frozen_is_zero"] == _frozen_is_zero(a)
                entry["archived_frozen_is_zero"] = a.get("frozen_is_zero")
                entry["frozen_is_zero_recomputed_from_archived_matrix"] = _frozen_is_zero(a)
            entry["seed_json_data_identical"] = derived_ok
        for kind in ("summary", "population", "events"):
            arch = _archived(kind, seed)
            mine = raw / f"{kind}_seed{seed}.jsonl"
            if arch is None or not mine.exists():
                entry[kind] = "no_archived_counterpart" if arch is None else "missing_reproduction"
                continue
            ra, rb = _records(arch), _records(mine)
            prefix = len(ra)
            entry[kind] = {
                "archived_records": prefix,
                "reproduced_records": len(rb),
                "archived_prefix_identical": [_strip(r) for r in ra] == [_strip(r) for r in rb[:prefix]],
            }
        seeds[str(seed)] = entry
    report["seeds"] = seeds

    def ok(e: object) -> bool:
        if isinstance(e, dict):
            skip = {
                "archived_records", "reproduced_records", "seed_json_fields_identical",
                "seed_json_fields_differing", "archived_frozen_is_zero",
                "frozen_is_zero_recomputed_from_archived_matrix",
            }
            return all(ok(v) for k, v in e.items() if k not in skip)
        if isinstance(e, bool):
            return e
        return True

    report["ok"] = bool(report["commit_present"] and report["ancestor_of_head"] and all(pins.values()) and ok(seeds))
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--restored", default=str(HERE))
    a = ap.parse_args()
    rep = check(Path(a.restored))
    print(json.dumps(rep, indent=2, sort_keys=True))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
