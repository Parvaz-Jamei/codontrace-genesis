"""6187ff4 default-ecology byte-identity check.

Builds build_idea4_engine_spec(ecology="standing") — and, for contrast,
ecology="persistence_safe" — in the live tree and in a pristine checkout of the
parent commit 44a06f4, then compares the canonical spec digests.

Run with:
    set PYTHONPATH=<repo>\\src
    set PYTHONUTF8=1
    python test-runs/verify/check_standing_identity.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

GIT = r"E:\MinGit\cmd\git.exe"
REPO = r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis"
OTHER = r"E:\_ci_verify\at44a06f4"
PARENT = "44a06f4"

SNIPPET = r"""
import json, sys
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (
    build_idea4_engine_spec,
)

out = {}
for seed in (22, 7):
    spec = build_idea4_engine_spec(seed=seed, tick_count=5)
    out[f"standing_seed{seed}_digest"] = spec.digest()
    md = dict(spec.metadata or {})
    out[f"standing_seed{seed}_metadata"] = md
if hasattr(build_idea4_engine_spec, "__call__"):
    try:
        ps = build_idea4_engine_spec(seed=22, tick_count=5, ecology="persistence_safe")
        out["persistence_safe_seed22_digest"] = ps.digest()
    except Exception as exc:  # parent has no such profile
        out["persistence_safe_seed22_digest"] = f"unavailable: {type(exc).__name__}"
print(json.dumps(out, sort_keys=True, default=str))
"""


def run_in(cwd: str, pythonpath: str) -> dict[str, object]:
    env = dict(os.environ)
    env["PYTHONPATH"] = pythonpath
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    script = Path(tempfile.gettempdir()) / "standing_probe.py"
    script.write_text(SNIPPET, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        errors="replace",
    )
    if proc.returncode != 0:
        raise SystemExit(f"probe failed in {cwd}:\n{proc.stdout}\n{proc.stderr}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


env = dict(os.environ)
env["PATH"] = r"E:\MinGit\cmd;" + env["PATH"]

Path(OTHER).mkdir(parents=True, exist_ok=True)
subprocess.run(
    [GIT, "worktree", "add", "--detach", OTHER, PARENT],
    cwd=REPO,
    env=env,
    capture_output=True,
    text=True,
)
if not (Path(OTHER) / "src").is_dir():
    raise SystemExit(f"worktree checkout of {PARENT} not present at {OTHER}")

try:
    live = run_in(REPO, str(Path(REPO) / "src"))
    parent = run_in(OTHER, str(Path(OTHER) / "src"))
finally:
    pass

# The parent has no persistence_safe branch signature; compare only standing.
checks = [
    ("standing_seed22_digest", True),
    ("standing_seed7_digest", True),
    ("standing_seed22_metadata", True),
    ("standing_seed7_metadata", True),
]
failures = []
for key, _ in checks:
    same = live.get(key) == parent.get(key)
    print(f"{'PASS' if same else 'FAIL'}  {key}: live={live.get(key)!r}")
    if not same:
        print(f"      parent({PARENT})={parent.get(key)!r}")
        failures.append(key)

print(f"\nparent manifest: persistence_safe = {parent.get('persistence_safe_seed22_digest')!r}")
print(f"live   manifest: persistence_safe = {live.get('persistence_safe_seed22_digest')!r}")
print("\n=== STANDING DEFAULT IDENTITY:", "PASS" if not failures else f"FAIL {failures}", "===")
print("worktree to remove:", OTHER)
sys.exit(1 if failures else 0)
