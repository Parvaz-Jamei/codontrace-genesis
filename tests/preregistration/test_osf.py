"""OSF registration client, replayed offline.

The replies follow the documented OSF API v2 bodies (https://developer.osf.io/
swagger.json, draft_registrations POST example, and the registration
attributes in api/registrations/serializers.py). They are not recordings,
because a real OSF registration cannot be deleted.

The POST reply is pending approval and private, as the server's
``RegistrationCreateSerializer.create`` calls ``require_approval``. Only the
later ``GET /v2/registrations/{id}/`` reply, after approval, is public.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.preregistration import hash_plan
from codontrace.preregistration._network import HttpResponse
from codontrace.preregistration.osf import API_VERSION, TEST_SERVER, OSFClient
from codontrace.preregistration.record import PreregistrationRecord, TimestampEvidence, verify_before_run

FIX = Path(__file__).parent / "fixtures"
SCHEMA = "61e02b6c90de34000ae3447a"


def _replay(manifest, *, posted=None, **reg_overrides):
    draft = {"data": {"id": "62716076d90ebe0017f2bf42", "type": "draft_registrations",
                      "attributes": {"registration_responses": {}, "datetime_initiated": "2026-10-21T20:00:00.288542",
                                     "title": "t", "description": ""},
                      "relationships": {"registration_schema": {"data": {"id": SCHEMA, "type": "registration-schemas"}},
                                        "provider": {"data": {"id": "osf", "type": "registration-providers"}}}}}
    reg_attrs = {"title": "t", "description": f"Preregistration manifest, SHA-256 {manifest.digest}.",
                 "date_registered": "2026-10-21T20:01:00.123456", "public": True,
                 "pending_registration_approval": False, "embargoed": False, "pending_embargo_approval": False,
                 "withdrawn": False, **reg_overrides}
    reg = {"data": {"id": "abc12", "type": "registrations", "attributes": reg_attrs,
                    "links": {"html": "https://test.osf.io/abc12/"}}}
    pending_attrs = {**reg_attrs, "public": False, "pending_registration_approval": True, **(posted or {})}
    pending = {"data": {**reg["data"], "attributes": pending_attrs}}
    calls = []

    def replay(method, url, body, headers):
        payload = None if body is None else json.loads(body)
        calls.append((method, url, payload))
        assert headers["Authorization"] == "Bearer tok"
        assert headers["Accept"] == f"application/vnd.api+json; version={API_VERSION}"
        if url == f"{TEST_SERVER}/draft_registrations/":
            return HttpResponse(201, json.dumps(draft).encode(), {})
        if url == f"{TEST_SERVER}/registrations/":
            assert method == "POST"
            return HttpResponse(201, json.dumps(pending).encode(), {})
        if url == f"{TEST_SERVER}/registrations/abc12/":
            assert method == "GET" and body is None
            return HttpResponse(200, json.dumps(reg).encode(), {})
        raise AssertionError(url)

    return replay, calls


def test_network_is_opt_in(monkeypatch):
    monkeypatch.delenv("CODONTRACE_ALLOW_NETWORK", raising=False)
    manifest = hash_plan(["plan_fixture.md"], root=FIX)
    with pytest.raises(ConfigurationError, match="needs the network"):
        OSFClient(token="t").register(manifest, title="t", schema_id=SCHEMA)


def test_draft_is_not_evidence_and_submit_is_explicit():
    manifest = hash_plan(["plan_fixture.md"], root=FIX)
    replay, calls = _replay(manifest)
    draft = OSFClient("tok", transport=replay).register(manifest, title="t", schema_id=SCHEMA)
    assert not draft.submitted and len(calls) == 1
    sent = calls[0][2]["data"]
    assert sent["relationships"]["registration_schema"]["data"]["id"] == SCHEMA
    assert manifest.digest in sent["attributes"]["description"]
    with pytest.raises(ConfigurationError, match="unsubmitted"):
        TimestampEvidence.from_osf(draft, manifest)


def test_submit_reply_is_pending_then_approved_fetch_is_evidence(tmp_path):
    manifest = hash_plan(["plan_fixture.md"], root=FIX)
    replay, calls = _replay(manifest)
    client = OSFClient("tok", transport=replay)
    submitted = client.register(manifest, title="t", schema_id=SCHEMA, submit=True)
    assert calls[1][2]["data"]["attributes"] == {"draft_registration_id": "62716076d90ebe0017f2bf42"}
    assert submitted.pending_approval and not submitted.public
    with pytest.raises(ConfigurationError, match="not yet evidence"):
        TimestampEvidence.from_osf(submitted, manifest)
    reg = client.fetch("abc12", manifest, draft_id=submitted.draft_id)
    assert calls[2][:2] == ("GET", f"{TEST_SERVER}/registrations/abc12/")
    assert reg.draft_id == submitted.draft_id
    ev = TimestampEvidence.from_osf(reg, manifest)
    assert ev.reference == "osf:abc12"
    assert ev.time == datetime(2026, 10, 21, 20, 1, 0, 123456, tzinfo=UTC)
    rec = PreregistrationRecord(manifest).with_evidence(ev)
    back = PreregistrationRecord.from_json(rec.to_json())
    ok = verify_before_run(back, root=FIX, run_started_at=datetime(2026, 10, 22, tzinfo=UTC))
    assert ok.ok, ok.reasons
    late = verify_before_run(back, root=FIX, run_started_at=datetime(2026, 10, 21, 20, 0, tzinfo=UTC))
    assert not late.ok


@pytest.mark.parametrize(
    "override",
    [{"pending_registration_approval": True}, {"embargoed": True}, {"pending_embargo_approval": True},
     {"public": False}],
)
def test_pending_embargoed_or_private_is_not_evidence(override):
    manifest = hash_plan(["plan_fixture.md"], root=FIX)
    replay, _ = _replay(manifest, **override)
    reg = OSFClient("tok", transport=replay).fetch("abc12", manifest)
    with pytest.raises(ConfigurationError, match="not yet evidence"):
        TimestampEvidence.from_osf(reg, manifest)


def test_registration_without_the_digest_is_refused():
    manifest = hash_plan(["plan_fixture.md"], root=FIX)
    replay, _ = _replay(manifest, description="something else", posted={"description": "something else"})
    with pytest.raises(ConfigurationError, match="without the manifest digest"):
        OSFClient("tok", transport=replay).register(manifest, title="t", schema_id=SCHEMA, submit=True)


def test_http_error_is_reported():
    manifest = hash_plan(["plan_fixture.md"], root=FIX)

    def fail(method, url, body, headers):
        return HttpResponse(403, b'{"errors": []}', {})

    with pytest.raises(ConfigurationError, match="HTTP 403"):
        OSFClient("tok", transport=fail).register(manifest, title="t", schema_id=SCHEMA)


def test_fetch_refuses_a_different_registration():
    manifest = hash_plan(["plan_fixture.md"], root=FIX)

    def other(method, url, body, headers):
        return HttpResponse(200, json.dumps({"data": {"id": "zzz99", "attributes": {}}}).encode(), {})

    with pytest.raises(ConfigurationError, match="different registration"):
        OSFClient("tok", transport=other).fetch("abc12", manifest)
