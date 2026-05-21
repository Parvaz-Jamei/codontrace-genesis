"""Structured analyst input bundle for UI and external review workflows."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, cast

from codontrace._types import JsonValue


@dataclass(frozen=True, slots=True)
class AnalystInputBundle:
    """Evidence, manifest, replay, and notes prepared for an analyst/reviewer."""

    evidence_pack: dict[str, JsonValue]
    manifest: dict[str, JsonValue]
    replay_bundle: dict[str, JsonValue] | None = None
    notes: tuple[str, ...] = ()
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    @classmethod
    def from_objects(
        cls,
        *,
        evidence_pack: object,
        manifest: object,
        replay_bundle: object | None = None,
        notes: tuple[str, ...] = (),
    ) -> AnalystInputBundle:
        return cls(
            evidence_pack=_to_dict(evidence_pack),
            manifest=_to_dict(manifest),
            replay_bundle=None if replay_bundle is None else _to_dict(replay_bundle),
            notes=notes,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "evidence_pack": self.evidence_pack,
            "manifest": self.manifest,
            "replay_bundle": self.replay_bundle,
            "notes": list(self.notes),
            "metadata": dict(sorted(self.metadata.items())),
        }

    def digest(self) -> str:
        encoded = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _to_dict(value: object) -> dict[str, JsonValue]:
    if hasattr(value, "to_dict"):
        return cast(dict[str, JsonValue], cast(Any, value).to_dict())
    if isinstance(value, Mapping):
        return {str(k): cast(JsonValue, v) for k, v in value.items()}
    msg = "value must be mapping-like or expose to_dict()."
    raise TypeError(msg)
