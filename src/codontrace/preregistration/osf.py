"""Section 5: OSF registration of a preregistration manifest.

Follows OSF API v2 (https://developer.osf.io/, spec ``swagger.json`` fetched
2026-10-22) and the osf.io server source it documents:

* ``POST /v2/draft_registrations/`` creates a draft from scratch with a
  ``registration_schema`` relationship (the only required field) and the
  ``osf`` registration provider. The manifest SHA-256 goes into the title and
  description, which the registration freezes.
* ``POST /v2/registrations/`` with ``draft_registration_id`` submits it. That
  attribute name is used from API version 2.19 on
  (``api/base/versioning.py: CREATE_REGISTRATION_FIELD_CHANGE_VERSION``, and
  ``api/registrations/serializers.py: RegistrationCreateSerializer``). The
  client pins ``version=2.20`` in the ``Accept`` header.
* The server answers that POST with a registration that still waits for the
  admins' approval: ``RegistrationCreateSerializer.create`` calls
  ``registration.require_approval(auth.user)`` (``api/registrations/serializers.py``),
  so the reply carries ``pending_registration_approval=true`` and
  ``public=false``. Such a reply is never evidence. Once the registration is
  approved, :meth:`OSFClient.fetch` re-reads it with
  ``GET /v2/registrations/{id}/`` and only that later state can be evidence.

The draft-from-scratch route is used on purpose. OSF stops creating projects
through ``POST /v2/nodes/`` on 2026-11-16 and makes projects read-only on
2027-02-19, while registrations from scratch keep working
(https://help.osf.io/article/744-osf-projects-api-impact). So no file is
uploaded to a project. The frozen registration metadata carries the digest.

An OSF registration cannot be deleted, only withdrawn. :meth:`OSFClient.register`
therefore only submits with ``submit=True``. A draft is private and is not
evidence. Neither is a registration that is still pending approval or
embargoed, because nobody outside can see it yet.

OSF reports ``date_registered`` without a zone. The server stores UTC, so the
client attaches UTC. The token is passed in by the caller and is never stored.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from codontrace.errors import ConfigurationError

from ._network import Transport, require_network, urllib_transport
from .manifest import PlanManifest

__all__ = ["OSFClient", "OSFRegistration"]

PRODUCTION = "https://api.osf.io/v2"
TEST_SERVER = "https://api.test.osf.io/v2"
API_VERSION = "2.20"


@dataclass(frozen=True)
class OSFRegistration:
    draft_id: str
    registration_id: str | None
    submitted: bool
    public: bool
    pending_approval: bool
    embargoed: bool
    html_url: str | None
    registered_at: datetime | None
    description: str
    withdrawn: bool = False
    pending_withdrawal: bool = False
    archiving: bool = False


def _parse_time(value: object) -> datetime:
    if not isinstance(value, str):
        raise ConfigurationError(f"OSF date_registered is not a string: {value!r}")
    try:
        t = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ConfigurationError(f"OSF date_registered is not an ISO-8601 time: {value!r}") from exc
    return t if t.tzinfo is not None else t.replace(tzinfo=UTC)


def _flag(attrs: dict[str, object], key: str) -> bool:
    """A JSON boolean attribute. Absent (OSF hides some fields once withdrawn) is False."""
    value = attrs.get(key)
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ConfigurationError(f"OSF attribute {key} is not a JSON boolean: {value!r}")
    return value


@dataclass
class OSFClient:
    token: str
    base_url: str = TEST_SERVER
    allow_network: bool = False
    transport: Transport | None = None

    def _call(self, method: str, url: str, payload: dict[str, object] | None) -> dict[str, object]:
        transport = self.transport
        if transport is None:
            require_network(self.allow_network, "OSF registration")
            transport = urllib_transport
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/vnd.api+json",
            "Accept": f"application/vnd.api+json; version={API_VERSION}",
        }
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        resp = transport(method, url, body, headers)
        if resp.status not in (200, 201):
            raise ConfigurationError(f"OSF {method} {url.split('?')[0]} answered HTTP {resp.status}")
        doc = json.loads(resp.body.decode("utf-8"))
        data = doc.get("data") if isinstance(doc, dict) else None
        if not isinstance(data, dict) or not isinstance(data.get("attributes"), dict):
            raise ConfigurationError("OSF answered without a JSON:API data object")
        return data

    def register(
        self, manifest: PlanManifest, *, title: str, schema_id: str, submit: bool = False
    ) -> OSFRegistration:
        description = f"Preregistration manifest, SHA-256 {manifest.digest}."
        draft = self._call("POST", f"{self.base_url}/draft_registrations/", {
            "data": {
                "type": "draft_registrations",
                "attributes": {"title": f"{title} [sha256:{manifest.digest}]", "description": description},
                "relationships": {
                    "registration_schema": {"data": {"type": "registration-schemas", "id": schema_id}},
                    "provider": {"data": {"type": "registration-providers", "id": "osf"}},
                },
            }
        })
        draft_id = str(draft.get("id") or "")
        if not draft_id:
            raise ConfigurationError("OSF draft id missing")
        if not submit:
            return OSFRegistration(draft_id, None, False, False, False, False, None, None, description)
        reg = self._call("POST", f"{self.base_url}/registrations/", {
            "data": {"type": "registrations", "attributes": {"draft_registration_id": draft_id}}
        })
        return self._registration(reg, draft_id, manifest)

    def fetch(self, registration_id: str, manifest: PlanManifest, *, draft_id: str = "") -> OSFRegistration:
        """Re-read a submitted registration (``GET /v2/registrations/{id}/``).

        The submit reply is pending approval by design, so this is the call that
        can return an approved, public registration once OSF has approved it.
        """
        if not registration_id or "/" in registration_id:
            raise ConfigurationError("an OSF registration id is required")
        reg = self._call("GET", f"{self.base_url}/registrations/{registration_id}/", None)
        if str(reg.get("id") or "") != registration_id:
            raise ConfigurationError("OSF answered with a different registration")
        return self._registration(reg, draft_id, manifest)

    @staticmethod
    def _registration(reg: dict[str, object], draft_id: str, manifest: PlanManifest) -> OSFRegistration:
        attrs = reg["attributes"]
        assert isinstance(attrs, dict)
        stored = str(attrs.get("description") or "")
        if manifest.digest not in stored:
            raise ConfigurationError("OSF registered a description without the manifest digest")
        links = reg.get("links")
        html = links.get("html") if isinstance(links, dict) else None
        stamp = attrs.get("date_registered")
        return OSFRegistration(
            draft_id=draft_id,
            registration_id=str(reg.get("id")) if reg.get("id") else None,
            submitted=True,
            public=_flag(attrs, "public"),
            pending_approval=_flag(attrs, "pending_registration_approval"),
            embargoed=_flag(attrs, "embargoed") or _flag(attrs, "pending_embargo_approval"),
            html_url=str(html) if html else None,
            registered_at=_parse_time(stamp) if stamp else None,
            description=stored,
            withdrawn=_flag(attrs, "withdrawn"),
            pending_withdrawal=_flag(attrs, "pending_withdrawal"),
            archiving=_flag(attrs, "archiving"),
        )
