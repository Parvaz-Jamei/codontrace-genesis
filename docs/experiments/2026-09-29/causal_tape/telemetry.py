"""Shared telemetry: live JSONL event logs, per-generation snapshots, manifests, resume.

Every heavy run writes, under ``<root>/<test>/``:

* ``logs/<run_key>.jsonl``      one JSON object per event, flushed immediately
* ``snapshots/<run_key>.npz``   decimated per-generation state arrays
* ``runs/<run_key>.json``       manifest: config, digests, timings, status
* ``done.jsonl``                append-only index of completed runs, used to resume

Nothing is buffered in memory across a process boundary, so killing a run keeps
everything already written and ``completed_keys`` lets a restarted run skip it.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np


def _jsonable(value: Any) -> Any:
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if hasattr(value, "item") and not isinstance(value, (str, bytes, int, float, bool)):
        try:
            return _jsonable(value.item())
        except (ValueError, AttributeError):
            return str(value)
    return value


def config_digest(config: dict) -> str:
    payload = json.dumps(_jsonable(config), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Telemetry:
    def __init__(
        self,
        root: str | Path,
        test: str,
        run_key: str,
        config: dict,
        *,
        snapshot_every: int = 5,
    ) -> None:
        self.test_dir = Path(root) / test
        self.run_key = run_key
        self.snapshot_every = max(1, snapshot_every)
        for sub in ("logs", "snapshots", "runs"):
            (self.test_dir / sub).mkdir(parents=True, exist_ok=True)
        self.log_path = self.test_dir / "logs" / f"{run_key}.jsonl"
        self.snap_path = self.test_dir / "snapshots" / f"{run_key}.npz"
        self.manifest_path = self.test_dir / "runs" / f"{run_key}.json"
        self._log = self.log_path.open("a", encoding="utf-8")
        self._buffer: list[dict] = []
        self._started = time.time()
        self.config = config
        self.manifest = {
            "run_key": run_key,
            "test": test,
            "config": _jsonable(config),
            "config_digest": config_digest(config),
            "started_at": self._started,
            "status": "running",
            "pid": os.getpid(),
        }
        self._write_manifest()

    # -- live event log -----------------------------------------------------
    def event(self, **fields: Any) -> None:
        record = {"t": round(time.time() - self._started, 4), **{k: _jsonable(v) for k, v in fields.items()}}
        self._log.write(json.dumps(record, separators=(",", ":")) + "\n")
        self._log.flush()

    # -- decimated per-generation snapshots ---------------------------------
    def snapshot(self, generation: int, arrays: dict[str, Any], *, force: bool = False) -> None:
        if not force and generation % self.snapshot_every:
            return
        row = {"generation": generation, **{k: _jsonable(v) for k, v in arrays.items()}}
        self._buffer.append(row)
        if len(self._buffer) >= 50:
            self.flush_snapshots()

    def flush_snapshots(self) -> None:
        if not self._buffer:
            return
        existing: dict[str, list] = {}
        if self.snap_path.exists():
            with np.load(self.snap_path, allow_pickle=True) as data:
                existing = {k: list(data[k]) for k in data.files}
        for row in self._buffer:
            generation = row.pop("generation")
            existing.setdefault("generation", []).append(generation)
            for key, value in row.items():
                existing.setdefault(key, []).append(value)
        np.savez_compressed(self.snap_path, **{k: np.array(v) for k, v in existing.items()})
        self._buffer.clear()

    # -- manifest -----------------------------------------------------------
    def _write_manifest(self) -> None:
        tmp = self.manifest_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.manifest, indent=2), encoding="utf-8")
        tmp.replace(self.manifest_path)

    def close(self, summary: dict, *, status: str = "done") -> None:
        self.flush_snapshots()
        self._log.close()
        self.manifest["status"] = status
        self.manifest["seconds"] = round(time.time() - self._started, 3)
        self.manifest["summary"] = _jsonable(summary)
        self.manifest["snapshot_rows"] = int(self._snapshot_rows())
        self._write_manifest()
        with (self.test_dir / "done.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {"run_key": self.run_key, "status": status, "seconds": self.manifest["seconds"],
                     "config_digest": self.manifest["config_digest"]},
                    separators=(",", ":"),
                )
                + "\n"
            )

    def _snapshot_rows(self) -> int:
        if not self.snap_path.exists():
            return 0
        with np.load(self.snap_path, allow_pickle=True) as data:
            return int(len(data["generation"])) if "generation" in data.files else 0


def completed_keys(root: str | Path, test: str) -> set[str]:
    """Run keys that already finished, for resuming a killed batch."""

    path = Path(root) / test / "done.jsonl"
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("status") == "done":
            keys.add(str(record["run_key"]))
    return keys


def iter_missing(keys: Iterable[str], done: set[str]) -> list[str]:
    return [key for key in keys if key not in done]
