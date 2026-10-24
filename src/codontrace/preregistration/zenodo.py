"""Section 3: Zenodo deposit of a preregistration manifest.

Follows the Zenodo REST API (https://developers.zenodo.org/, checked
2026-10-21): ``POST /api/deposit/depositions`` creates a draft, the manifest is
``PUT`` to the draft's ``links.bucket``, and ``POST .../actions/publish`` makes
it public with a DOI. Publishing cannot be undone, so :meth:`deposit` only
publishes when ``publish=True`` is passed. A draft is *not* external evidence
(nobody else can see it); only a published record yields a
:class:`TimestampEvidence`.

The token is read by the caller and passed in; it is never logged or stored.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from codontrace.errors import ConfigurationError

from ._network import Transport, require_network, urllib_transport
from .manifest import PlanManifest

__all__ = ["ZenodoClient", "ZenodoDeposit"]

PRODUCTION = "https://zenodo.org/api"
SANDBOX = "https://sandbox.zenodo.org/api"


@dataclass(frozen=True)
class ZenodoDeposit:
    deposition_id: int
    state: str
    submitted: bool
    doi: str | None
    record_url: str | None
    file_checksum_md5: str
    published_at: datetime | None


@dataclass
class ZenodoClient:
    token: str
    base_url: str = SANDBOX
    allow_network: bool = False
    transport: Transport | None = None

    def _call(self, method: str, url: str, body: bytes | None, content_type: str) -> dict[str, object]:
        transport = self.transport
        if transport is None:
            require_network(self.allow_network, "Zenodo deposit")
            transport = urllib_transport
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": content_type}
        resp = transport(method, url, body, headers)
        if resp.status not in (200, 201, 202):
            raise ConfigurationError(f"Zenodo {method} {url.split('?')[0]} answered HTTP {resp.status}")
        data = json.loads(resp.body.decode("utf-8"))
        if not isinstance(data, dict):
            raise ConfigurationError("Zenodo answered with a non-object")
        return data

    def deposit(
        self, manifest: PlanManifest, *, title: str, creators: list[dict[str, str]], publish: bool = False
    ) -> ZenodoDeposit:
        blob = json.dumps(manifest.to_dict(), indent=2, sort_keys=True).encode("utf-8")
        meta = {
            "metadata": {
                "title": title,
                "upload_type": "other",
                "description": f"Preregistration manifest, SHA-256 {manifest.digest}.",
                "creators": creators,
                "access_right": "open",
                "license": "cc-by-4.0",
            }
        }
        dep = self._call("POST", f"{self.base_url}/deposit/depositions", json.dumps(meta).encode(), "application/json")
        links = dep.get("links")
        if not isinstance(links, dict) or "bucket" not in links:
            raise ConfigurationError("Zenodo draft has no bucket link")
        up = self._call("PUT", f"{links['bucket']}/prereg_manifest.json", blob, "application/octet-stream")
        want = "md5:" + hashlib.md5(blob, usedforsecurity=False).hexdigest()
        if up.get("checksum") != want:
            raise ConfigurationError("Zenodo stored a different file than was sent")
        final = dep
        if publish:
            final = self._call("POST", str(links["publish"]), None, "application/json")
        dep_id = final.get("id")
        if not isinstance(dep_id, int):
            raise ConfigurationError("Zenodo deposition id missing")
        submitted = bool(final.get("submitted"))
        stamp = final.get("modified") if submitted else None
        return ZenodoDeposit(
            deposition_id=dep_id,
            state=str(final.get("state")),
            submitted=submitted,
            doi=str(final["doi"]) if submitted and final.get("doi") else None,
            record_url=str(final.get("record_url")) if submitted and final.get("record_url") else None,
            file_checksum_md5=want,
            published_at=datetime.fromisoformat(str(stamp)) if stamp else None,
        )
