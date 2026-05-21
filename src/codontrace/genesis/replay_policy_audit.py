"""Integration replay policy coverage helpers."""

from __future__ import annotations

from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.replay_integrity import replay_digest_class_policies


def audit_replay_policy_coverage(required_class_paths: tuple[str, ...]) -> dict[str, JsonValue]:
    present = {item.class_path for item in replay_digest_class_policies()}
    missing = sorted(path for path in required_class_paths if path not in present)
    payload: dict[str, JsonValue] = {
        "schema_version": "integration_replay_policy_audit_v1",
        "passed": not missing,
        "missing": missing,
        "checked_count": len(required_class_paths),
    }
    payload["audit_digest"] = canonical_digest(payload, prefix="integration_replay_policy")
    return payload
