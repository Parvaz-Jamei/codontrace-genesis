"""Section 4: preregistration record and the hash-before-run check."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from codontrace.errors import ConfigurationError

from .manifest import PlanManifest, hash_plan
from .rfc3161 import TimeStampToken
from .zenodo import ZenodoDeposit

__all__ = ["PreregistrationRecord", "TimestampEvidence", "PreregCheck", "verify_before_run"]


@dataclass(frozen=True)
class TimestampEvidence:
    kind: str  # "rfc3161" or "zenodo"
    authority: str
    time: datetime
    manifest_sha256: str
    reference: str
    signature_verified: bool = False

    @classmethod
    def from_rfc3161(cls, token: TimeStampToken, tsa_url: str, *, signature_verified: bool) -> TimestampEvidence:
        return cls("rfc3161", tsa_url, token.gen_time, token.imprint_sha256, f"serial:{token.serial}", signature_verified)

    @classmethod
    def from_zenodo(cls, dep: ZenodoDeposit, manifest: PlanManifest) -> TimestampEvidence:
        if not dep.submitted or dep.published_at is None or not dep.doi:
            raise ConfigurationError("an unpublished Zenodo draft is not external evidence")
        return cls("zenodo", dep.record_url or "zenodo", dep.published_at, manifest.digest, f"doi:{dep.doi}", True)

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind, "authority": self.authority, "time": self.time.isoformat(),
            "manifest_sha256": self.manifest_sha256, "reference": self.reference,
            "signature_verified": self.signature_verified,
        }

    @classmethod
    def from_dict(cls, d: dict[str, object]) -> TimestampEvidence:
        t = datetime.fromisoformat(str(d["time"]))
        if t.tzinfo is None:
            raise ConfigurationError("evidence time must carry a time zone")
        return cls(str(d["kind"]), str(d["authority"]), t, str(d["manifest_sha256"]), str(d["reference"]),
                   bool(d.get("signature_verified", False)))


@dataclass(frozen=True)
class PreregistrationRecord:
    manifest: PlanManifest
    evidence: tuple[TimestampEvidence, ...] = ()

    def with_evidence(self, ev: TimestampEvidence) -> PreregistrationRecord:
        if ev.manifest_sha256 != self.manifest.digest:
            raise ConfigurationError("evidence is for a different manifest")
        return PreregistrationRecord(self.manifest, (*self.evidence, ev))

    def to_json(self) -> str:
        return json.dumps(
            {"manifest": self.manifest.to_dict(), "evidence": [e.to_dict() for e in self.evidence]},
            indent=2, sort_keys=True,
        ) + "\n"

    @classmethod
    def from_json(cls, text: str) -> PreregistrationRecord:
        d = json.loads(text)
        return cls(PlanManifest.from_dict(d["manifest"]),
                   tuple(TimestampEvidence.from_dict(e) for e in d.get("evidence", [])))


@dataclass(frozen=True)
class PreregCheck:
    ok: bool
    reasons: tuple[str, ...] = field(default_factory=tuple)
    earliest_external: datetime | None = None


def verify_before_run(
    record: PreregistrationRecord,
    *,
    root: str | Path,
    run_started_at: datetime,
    require_signature: bool = False,
) -> PreregCheck:
    """True only if the plan is unchanged *and* externally time-stamped before the run.

    A git commit time is author-controlled and never counts. Evidence counts
    only when its digest equals the manifest digest, its time is before
    ``run_started_at`` and (with ``require_signature``) its signature was verified.
    """
    if run_started_at.tzinfo is None:
        raise ConfigurationError("run_started_at must carry a time zone")
    reasons: list[str] = []
    paths: Sequence[str] = [p for p, _ in record.manifest.files]
    try:
        now = hash_plan(paths, root=root, title=record.manifest.title)
    except ConfigurationError as exc:
        return PreregCheck(False, (f"plan files unreadable: {exc}",))
    if now.digest != record.manifest.digest:
        changed = sorted(p for (p, h), (_, h2) in zip(record.manifest.files, now.files, strict=True) if h != h2)
        reasons.append(f"plan changed after registration: {changed}")
    good = [
        e for e in record.evidence
        if e.manifest_sha256 == record.manifest.digest and e.time < run_started_at
        and (e.signature_verified or not require_signature)
    ]
    if not good:
        reasons.append("no external time-stamp of this manifest before the run")
    earliest = min((e.time for e in good), default=None)
    return PreregCheck(not reasons, tuple(reasons), earliest)
