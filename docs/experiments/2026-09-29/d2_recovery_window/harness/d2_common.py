"""D-2 (idea 4) population test pack — stage 0 + measurement diagnostic + refusal test.

Owner: teammate ``mechanism-test`` (D-2 test agent).  Write scope: ``test-runs/d2/``.
This pack never writes inside ``codontrace-genesis``.  Code changes needed by the
repository are handed to the manager as ``PROPOSED_CHANGE.patch``.

Protocol applied (``DISCOVERY_TEST_PROGRAM_2026-09-29_FA.md``):

* one worker process; stage 0 first (unit/property tests, hand-computed cases,
  invariants, replay, neutral control, pre-defined positive control, negative
  control);
* calibration ceilings two development seeds x <= 80 generations;
* paired seed-level effect with a cluster bootstrap / randomisation interval;
* raw JSONL appended and flushed per generation, summary every 10, snapshot every 25;
* manifest with commit + dirty flag, config and design hashes, schema version,
  seed and RNG streams, wall/CPU/RAM, stop code, parent snapshot, parameters, arm;
* checksums and a schema validator on every file; a cut run keeps a valid prefix;
* one replay command from the manifest reproduces the summary.

The D-2 refusal is a locked acceptance condition: if the named-scaffold arm and
the degree/ATP-matched random arm have the same realised contacts and the same
population trajectory, or if any arm difference comes only from the coupler's
global edge-cost penalty, the verdict is ``BLOCKED_MEASUREMENT``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:  # POSIX only; Windows has no resource module
    import resource  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - Windows
    resource = None  # type: ignore[assignment]

REPO = Path(__file__).resolve().parents[5]
ROOT = Path(__file__).resolve().parents[6]
D2 = ROOT / "test-runs" / "d2"
RAW = D2 / "raw"
LOGS = D2 / "logs"
HARNESS = D2 / "harness"
sys.path.insert(0, str(REPO / "src"))

from codontrace.engine_runtime import GenesisEngine  # noqa: E402
from codontrace.genesis.campaigns.discovery_q_20260928_idea4 import (  # noqa: E402
    CHECKPOINT_ID,
    COMPETENCE_ID,
    DELTA_P_THRESHOLD,
    HORIZON_T,
    RECOVERY_TOKEN_KEY,
    SCAFFOLD_ID,
    SLOPE_THRESHOLD,
    _apply_ops_cell,
    _score_recover,
    harvest_rare_class_yield,
)
from codontrace.genesis.campaigns.discovery_q_20260928_idea4_engine import (  # noqa: E402
    build_idea4_engine_spec,
)
from codontrace.life_loop.contact_atp_ledger import build_engine_scaffold_ledger  # noqa: E402
from codontrace.life_loop.engine_ledger_coupler import (  # noqa: E402
    EngineCoupledLedgerObserver,
    population_path_fingerprint,
)

SCHEMA_VERSION = "d2-pack-v1"
DEV_SEEDS: tuple[int, ...] = (5501, 5502)
T_GRID: tuple[int, ...] = (10, 20, 30)  # early / middle / late checkpoint
DIAG_HORIZON = 40  # the program ceiling for a diagnostic tier is <= 80 generations
ARMS: tuple[str, ...] = (
    "control",
    "cut_named_scaffold",
    "cut_matched_random",
    "scramble_contacts",
    "ablate_knowledge_digest",
    "sham",
)
POPULATION = 8
SUCCESS_MULTIPLIER = 1.25
SUCCESS_CONSECUTIVE = 3
WALL_CAP_SECONDS = 8 * 60
PACK_CAP_SECONDS = 45 * 60
RAM_SOFT_STOP_BYTES = int(3.5 * 1024**3)
SUMMARY_EVERY = 10
SNAPSHOT_EVERY = 25

EVENT_FIELDS = (
    "run_id",
    "seed",
    "arm",
    "generation",
    "event_id",
    "organism_id",
    "parent_id",
    "genotype_digest",
    "antagonist_digest",
    "contact_edge_id",
    "opportunity",
    "matched",
    "intended_debit",
    "realised_debit",
    "atp_before",
    "atp_after",
    "birth",
    "death",
    "mutation",
    "intervention_id",
)
POP_FIELDS = (
    "run_id",
    "seed",
    "arm",
    "generation",
    "n_alive",
    "class_counts",
    "class_frequencies",
    "genotype_counts",
    "genotype_frequencies",
    "antagonist_frequency",
    "fitness",
    "atp_sum",
    "atp_mean",
    "contact_opportunities",
    "pi_realised",
    "pi_intended",
    "resource_mass",
    "genealogy",
    "population_path_digest",
)
NULL_REASONS = {
    "antagonist_digest": "no antagonist genotype population exists in this model",
    "antagonist_frequency": "no antagonist genotype population exists in this model",
    "opportunity": "the engine has no per-organism contact-opportunity counter exposed",
    "matched": "no per-contact match flag is exposed by the engine life-loop",
    "intended_debit": "ledger feedback is a count penalty, not an intended per-contact debit",
    "pi_realised": "realised conditional pressure is not wired into this model path",
    "pi_intended": "intended conditional pressure is not wired into this model path",
    "contact_opportunities": "no contact-opportunity counter is exposed",
    "fitness": "no fitness score is exposed on the population snapshot",
}


def now() -> float:
    return time.time()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_hash(payload: Any) -> str:
    return sha256_text(json.dumps(payload, sort_keys=True, default=str))


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def git_state() -> dict[str, Any]:
    def _run(args: list[str]) -> str:
        try:
            return subprocess.run(args, cwd=REPO, capture_output=True, text=True, check=False).stdout.strip()
        except OSError:
            return ""

    return {
        "commit": _run(["git", "rev-parse", "HEAD"]),
        "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "dirty": bool(_run(["git", "status", "--porcelain"])),
        "status_porcelain": _run(["git", "status", "--porcelain"]),
    }


class JsonlWriter:
    """Append-only JSONL with a per-record schema check and a flushing writer."""

    def __init__(self, path: Path, required: tuple[str, ...]) -> None:
        self.path = path
        self.required = required
        self.count = 0
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("w", encoding="utf-8")

    def validate(self, record: dict[str, Any]) -> None:
        missing = [k for k in self.required if k not in record]
        if missing:
            raise ValueError(f"{self.path.name}: record missing fields {missing}")
        for key in self.required:
            if isinstance(record[key], float) and record[key] != record[key]:
                raise ValueError(f"{self.path.name}: NaN in {key}")

    def write(self, record: dict[str, Any]) -> None:
        self.validate(record)
        self._fh.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        self._fh.flush()
        self.count += 1

    def close(self) -> None:
        self._fh.close()


def rss_bytes() -> int:
    if resource is not None:
        try:
            return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
        except (ValueError, OSError, AttributeError):
            pass
    try:  # Windows fallback
        import ctypes
        from ctypes import wintypes

        class _ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
        if ok:
            return int(counters.WorkingSetSize)
    except Exception:  # noqa: BLE001 - reporting only
        pass
    return 0


def cpu_seconds() -> float:
    if resource is not None:
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return float(usage.ru_utime + usage.ru_stime)
        except (ValueError, OSError, AttributeError):
            pass
    try:
        return float(time.process_time())
    except Exception:  # noqa: BLE001 - reporting only
        return 0.0
