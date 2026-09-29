"""Byte-identity of every frozen pin vs HEAD 434bbd1 (the pre-fix tip).

Run with:
    set PYTHONPATH=<repo>\\src
    set PYTHONUTF8=1
    python test-runs/verify/check_pins_vs_434bbd1.py
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys

GIT = r"E:\MinGit\cmd\git.exe"
BASE = "434bbd1"
REPO = r"E:\مقاله پزشکی شبیه سازی ویروس\codontrace-genesis"

# The three BAIC pins plus every other frozen artifact asserted by the suite.
ARTIFACTS = [
    "docs/hard_experiment_01/results_v7.json",
    "docs/claimgate/risk_bar.json",
    "docs/claimgate/biomedical_study.json",
    "docs/hard_experiment_hp/locked_campaign_digests.json",
    "docs/HARD_EXPERIMENT_01_PREREG.md",
    "docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_02.md",
    "docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_03.md",
    "docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_04.md",
    "docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_05.md",
    "docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_LOCK.md",
    "docs/hard_experiment_02/results_v1.json",
    "docs/hard_experiment_02/analysis_v1b_contrasts.json",
]

# Values the repository commits to (read from the live code, not hard-coded here).
from codontrace.genesis.host_parasite_he_hp_refresh import SCHEMA as _HP_SCHEMA  # noqa: F401
from codontrace.genesis.host_parasite_world import _BAIC_PINS
from codontrace.genesis.hard_experiment_01 import (
    hard_experiment_01_prereg_amendment_02_digest,
    hard_experiment_01_prereg_amendment_03_digest,
    hard_experiment_01_prereg_amendment_04_digest,
    hard_experiment_01_prereg_amendment_05_digest,
    hard_experiment_01_prereg_amendment_lock_digest,
    hard_experiment_01_prereg_digest,
)

COMMITTED = {rel: expected for rel, expected in _BAIC_PINS}
COMMITTED["docs/HARD_EXPERIMENT_01_PREREG.md"] = hard_experiment_01_prereg_digest()
COMMITTED["docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_02.md"] = (
    hard_experiment_01_prereg_amendment_02_digest()
)
COMMITTED["docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_03.md"] = (
    hard_experiment_01_prereg_amendment_03_digest()
)
COMMITTED["docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_04.md"] = (
    hard_experiment_01_prereg_amendment_04_digest()
)
COMMITTED["docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_05.md"] = (
    hard_experiment_01_prereg_amendment_05_digest()
)
COMMITTED["docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_LOCK.md"] = (
    hard_experiment_01_prereg_amendment_lock_digest()
)


def sha256_lf(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def blob(rev: str, path: str) -> bytes:
    return subprocess.run(
        [GIT, "show", f"{rev}:{path}"], capture_output=True, cwd=REPO
    ).stdout


env = dict(os.environ)
env["PATH"] = r"E:\MinGit\cmd;" + env["PATH"]

failures: list[str] = []
for rel in ARTIFACTS:
    live = open(os.path.join(REPO, rel), "rb").read()
    base = blob(BASE, rel)
    live_lf, base_lf = sha256_lf(live), sha256_lf(base)
    # Raw-byte equality is only meaningful after removing the checkout's CRLF:
    # in the live repo the working tree is CRLF while the blob is LF, so the
    # graded comparison is the LF digest plus the committed constant.
    same_bytes = live.replace(b"\r\n", b"\n") == base.replace(b"\r\n", b"\n")
    same_lf = live_lf == base_lf
    committed = COMMITTED.get(rel)
    pin_ok = committed is None or live_lf == committed
    status = "PASS" if (same_bytes and same_lf and pin_ok) else "FAIL"
    if status == "FAIL":
        failures.append(rel)
    print(f"{status}  {rel}")
    print(f"      LF-normalised bytes == {BASE}    : {same_bytes}")
    print(f"      LF digest now                  : {live_lf}")
    print(f"      LF digest at {BASE}            : {base_lf}")
    print(f"      committed constant matches     : {pin_ok}"
          + ("" if committed is None else f" ({committed})"))

print(f"\n=== PINS: {len(ARTIFACTS) - len(failures)}/{len(ARTIFACTS)} PASS ===")
print("failures:", failures if failures else "none")
sys.exit(1 if failures else 0)
