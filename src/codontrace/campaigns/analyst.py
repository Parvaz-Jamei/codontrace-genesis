"""Independent reading of a campaign directory.

This module does not trust a scientific flag written by the runner.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from codontrace.campaigns.readiness import ASSESSMENT_WORDS, LEDGER_WORDS, assessments_are_distinct
from codontrace.engine_runtime import checkpoint_from_bytes
from codontrace.errors import ConfigurationError


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"{path} is not an object"
        raise ConfigurationError(msg)
    return payload


def _last_jsonl(path: Path) -> dict[str, Any]:
    last: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            msg = f"{path} has a non-object row"
            raise ConfigurationError(msg)
        last = row
    if last is None:
        msg = f"{path} is empty"
        raise ConfigurationError(msg)
    return last


def control_assessment(payload: dict[str, Any]) -> str:
    """A well-formed positive fixture can show support. A broken one is rejected."""

    required = {"kind", "experiment_id", "predicted", "observed", "matched"}
    if payload.get("synthetic") is not True or payload.get("kind") != "positive":
        return "INVALID_MEASUREMENT"
    if not required <= set(payload) or payload.get("matched") is not True:
        return "INVALID_MEASUREMENT"
    if payload.get("predicted") != payload.get("observed"):
        return "INVALID_MEASUREMENT"
    return "SUPPORTED_IN_THIS_MODEL"


def analyse(campaign: Path) -> dict[str, Any]:
    if assessments_are_distinct("NOT_SUPPORTED", "FALSIFIED_IN_MODEL") is not True:
        msg = "assessment words must stay distinct"
        raise ConfigurationError(msg)
    report: dict[str, Any] = {
        "schema_version": 1,
        "assessment_words": list(ASSESSMENT_WORDS),
        "ledger_words": list(LEDGER_WORDS),
        "engineering_status": "INCOMPLETE",
        "scientific_status": "UNASSESSED",
        "control_assessment": None,
        "synthetic_excluded": True,
        "resume_matched": None,
        "problems": [],
    }
    synthetic = campaign / "SYNTHETIC_CONTROL" / "positive.json"
    if synthetic.is_file():
        report["control_assessment"] = control_assessment(_read_json(synthetic))
        report["synthetic_excluded"] = True
    if not (campaign / "manifest.json").is_file():
        report["problems"].append("missing manifest")
        report["scientific_status"] = "INVALID_MEASUREMENT"
        return report
    arms: dict[str, dict[str, Any]] = {}
    root = campaign / "runs" / "T11"
    if not root.is_dir():
        report["problems"].append("missing T11 runs")
        report["scientific_status"] = "INVALID_MEASUREMENT"
        return report
    for metrics in sorted(root.glob("seed_*/arm_*/metrics.jsonl")):
        arm_dir = metrics.parent
        manifest_path = arm_dir / "artifacts_manifest.json"
        if not manifest_path.is_file():
            report["problems"].append(f"missing hash manifest in {arm_dir.name}")
            report["scientific_status"] = "INVALID_MEASUREMENT"
            return report
        declared = _read_json(manifest_path).get("files")
        if not isinstance(declared, dict):
            report["problems"].append("hash manifest is not an object")
            report["scientific_status"] = "INVALID_MEASUREMENT"
            return report
        for relative, expected in declared.items():
            target = arm_dir / str(relative)
            if not target.is_file():
                report["problems"].append(f"missing {relative}")
                report["scientific_status"] = "INVALID_MEASUREMENT"
                return report
            actual = _sha256(target)
            if actual != expected:
                report["problems"].append(f"forged or stale hash for {relative}")
                report["scientific_status"] = "INVALID_MEASUREMENT"
                return report
        row = _last_jsonl(metrics)
        checkpoint = arm_dir / "checkpoints" / "end.bin"
        try:
            loaded = checkpoint_from_bytes(checkpoint.read_bytes())
        except (ConfigurationError, OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            report["problems"].append(f"unreadable checkpoint: {exc}")
            report["scientific_status"] = "INVALID_MEASUREMENT"
            return report
        if str(loaded.get("state_digest")) != str(row.get("state_digest")):
            report["problems"].append("metrics digest does not match the checkpoint")
            report["scientific_status"] = "INVALID_MEASUREMENT"
            return report
        completion = _read_json(arm_dir / "completion.json")
        # A runner flag, even a flattering one, is not the result.
        completion.pop("scientific_status", None)
        arms[str(row.get("arm"))] = {
            "tick": row.get("tick"),
            "state_digest": row.get("state_digest"),
            "completion": completion,
        }
    left = arms.get("uninterrupted")
    right = arms.get("resume")
    if left is None or right is None:
        report["problems"].append("both arms are required")
        report["engineering_status"] = "INCOMPLETE"
        return report
    if left["tick"] != right["tick"]:
        report["problems"].append("horizons differ")
        report["scientific_status"] = "INVALID_MEASUREMENT"
        return report
    report["resume_matched"] = left["state_digest"] == right["state_digest"]
    report["engineering_status"] = "COMPLETE" if report["resume_matched"] else "COMPLETE_MISMATCH"
    report["scientific_status"] = "UNASSESSED"
    return report
