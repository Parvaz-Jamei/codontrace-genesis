"""Hash-before-run preregistration: offline tests on recorded TSA responses.

fixtures/freetsa_response.tsr and fixtures/record_fixture.tsr were recorded
from https://freetsa.org/tsr on 2026-10-21 (see fixtures/README.md). The
Zenodo replies below follow the documented response bodies at
https://developers.zenodo.org/ (they are not recordings: publishing needs an
account token).
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.preregistration import (
    PreregistrationRecord,
    TimestampEvidence,
    build_request,
    hash_plan,
    parse_response,
    request_timestamp,
    rfc3161,
    verify_before_run,
)
from codontrace.preregistration.__main__ import main as cli
from codontrace.preregistration._network import HttpResponse
from codontrace.preregistration.zenodo import ZenodoClient

FIX = Path(__file__).parent / "fixtures"
PLAN = (FIX / "plan_fixture.md").read_bytes()
PLAN_SHA = hashlib.sha256(PLAN).hexdigest()


def test_request_der_is_byte_identical_to_openssl():
    # freetsa_request.tsq was produced by `openssl ts -query -sha256 -cert`.
    recorded = (FIX / "freetsa_request.tsq").read_bytes()
    nonce = parse_response((FIX / "freetsa_response.tsr").read_bytes(), expected_sha256=PLAN_SHA).nonce
    assert build_request(PLAN_SHA, nonce=nonce) == recorded


def test_recorded_response_parses_and_checks_imprint():
    tok = parse_response((FIX / "freetsa_response.tsr").read_bytes(), expected_sha256=PLAN_SHA)
    assert tok.status == 0
    assert tok.gen_time == datetime(2026, 10, 21, 20, 41, 54, tzinfo=UTC)
    with pytest.raises(ConfigurationError, match="imprint"):
        parse_response((FIX / "freetsa_response.tsr").read_bytes(), expected_sha256="00" * 32)
    with pytest.raises(ConfigurationError, match="nonce"):
        parse_response((FIX / "freetsa_response.tsr").read_bytes(), expected_sha256=PLAN_SHA, expected_nonce=1)


def test_truncated_response_is_rejected():
    der = (FIX / "freetsa_response.tsr").read_bytes()
    with pytest.raises(ConfigurationError):
        parse_response(der[:-10], expected_sha256=PLAN_SHA)


@pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl not installed")
def test_signature_verification_with_openssl():
    tok = parse_response((FIX / "freetsa_response.tsr").read_bytes(), expected_sha256=PLAN_SHA)
    ca, crt = FIX / "freetsa_cacert.pem", FIX / "freetsa_tsa.crt"
    assert rfc3161.verify_signature(tok, PLAN, ca_file=ca, untrusted=crt)
    assert not rfc3161.verify_signature(tok, PLAN + b"tampered", ca_file=ca, untrusted=crt)


def test_network_is_opt_in(monkeypatch):
    monkeypatch.delenv("CODONTRACE_ALLOW_NETWORK", raising=False)
    with pytest.raises(ConfigurationError, match="allow_network"):
        request_timestamp(PLAN_SHA, "https://freetsa.org/tsr", created_at="x")
    with pytest.raises(ConfigurationError, match="allow_network"):
        ZenodoClient(token="t").deposit(hash_plan(["plan_fixture.md"], root=FIX), title="t", creators=[])


def test_request_timestamp_replays_recorded_exchange(monkeypatch):
    der = (FIX / "freetsa_response.tsr").read_bytes()
    nonce = parse_response(der, expected_sha256=PLAN_SHA).nonce
    monkeypatch.setattr(rfc3161, "derive_nonce", lambda *_: nonce)
    sent = []

    def replay(method, url, body, headers):
        sent.append((method, url, body, headers["Content-Type"]))
        return HttpResponse(200, der, {})

    tok = request_timestamp(PLAN_SHA, "https://freetsa.org/tsr", created_at="x", transport=replay)
    assert sent == [("POST", "https://freetsa.org/tsr", (FIX / "freetsa_request.tsq").read_bytes(),
                     "application/timestamp-query")]
    assert tok.serial == 156712342


def _copy_plan(tmp_path):
    shutil.copy(FIX / "plan_fixture.md", tmp_path / "plan_fixture.md")
    return PreregistrationRecord.from_json((FIX / "record_fixture.json").read_text())


def test_record_fixture_matches_its_token():
    rec = PreregistrationRecord.from_json((FIX / "record_fixture.json").read_text())
    tok = parse_response((FIX / "record_fixture.tsr").read_bytes(), expected_sha256=rec.manifest.digest)
    assert rec.evidence[0].time == tok.gen_time
    assert rec.manifest == hash_plan(["plan_fixture.md"], root=FIX, title=rec.manifest.title)


def test_hash_before_run_passes_and_fails_honestly(tmp_path):
    rec = _copy_plan(tmp_path)
    stamped = rec.evidence[0].time
    ok = verify_before_run(rec, root=tmp_path, run_started_at=stamped + timedelta(hours=1), require_signature=True)
    assert ok.ok and ok.earliest_external == stamped
    late = verify_before_run(rec, root=tmp_path, run_started_at=stamped - timedelta(seconds=1))
    assert not late.ok and "before the run" in late.reasons[0]
    (tmp_path / "plan_fixture.md").write_text("edited after registration\n")
    changed = verify_before_run(rec, root=tmp_path, run_started_at=stamped + timedelta(hours=1))
    assert not changed.ok and "plan changed" in changed.reasons[0]


def test_self_attested_record_without_external_evidence_fails(tmp_path):
    rec = _copy_plan(tmp_path)
    bare = PreregistrationRecord(rec.manifest)
    res = verify_before_run(bare, root=tmp_path, run_started_at=datetime(2030, 1, 1, tzinfo=UTC))
    assert not res.ok


def test_evidence_for_another_manifest_is_refused(tmp_path):
    rec = _copy_plan(tmp_path)
    other = TimestampEvidence("rfc3161", "x", datetime(2026, 1, 1, tzinfo=UTC), "ab" * 32, "serial:1")
    with pytest.raises(ConfigurationError):
        rec.with_evidence(other)


def _zenodo_replay(manifest, publish_ok=True):
    blob = json.dumps(manifest.to_dict(), indent=2, sort_keys=True).encode()
    md5 = "md5:" + hashlib.md5(blob, usedforsecurity=False).hexdigest()
    base = "https://sandbox.zenodo.org/api"
    draft = {"id": 542201, "state": "unsubmitted", "submitted": False, "created": "2026-10-21T20:00:00+00:00",
             "links": {"bucket": f"{base}/files/568377dd", "publish": f"{base}/deposit/depositions/542201/actions/publish"}}
    published = {**draft, "state": "done", "submitted": True, "doi": "10.5072/zenodo.542201",
                 "record_url": "https://sandbox.zenodo.org/records/542201", "modified": "2026-10-21T20:01:00+00:00"}
    calls = []

    def replay(method, url, body, headers):
        calls.append((method, url))
        assert headers["Authorization"] == "Bearer tok"
        if url.endswith("/deposit/depositions"):
            return HttpResponse(201, json.dumps(draft).encode(), {})
        if "/files/" in url:
            assert body == blob
            return HttpResponse(201, json.dumps({"key": "prereg_manifest.json", "checksum": md5}).encode(), {})
        if url.endswith("/publish"):
            return HttpResponse(202, json.dumps(published).encode(), {})
        raise AssertionError(url)

    return replay, calls


def test_zenodo_draft_is_not_evidence_and_publish_is_explicit():
    manifest = hash_plan(["plan_fixture.md"], root=FIX)
    replay, calls = _zenodo_replay(manifest)
    draft = ZenodoClient("tok", transport=replay).deposit(manifest, title="t", creators=[{"name": "Jamei, Parvaz"}])
    assert not draft.submitted and [m for m, _ in calls] == ["POST", "PUT"]
    with pytest.raises(ConfigurationError, match="unpublished"):
        TimestampEvidence.from_zenodo(draft, manifest)
    replay, calls = _zenodo_replay(manifest)
    pub = ZenodoClient("tok", transport=replay).deposit(manifest, title="t", creators=[], publish=True)
    ev = TimestampEvidence.from_zenodo(pub, manifest)
    assert ev.reference == "doi:10.5072/zenodo.542201" and ev.time.tzinfo is not None
    assert [m for m, _ in calls] == ["POST", "PUT", "POST"]


def test_cli_hash_and_check(tmp_path, capsys):
    shutil.copy(FIX / "plan_fixture.md", tmp_path / "plan_fixture.md")
    rec_path = tmp_path / "rec.json"
    assert cli(["hash", str(rec_path), "plan_fixture.md", "--root", str(tmp_path), "--title", "codontrace prereg fixture"]) == 0
    fixture = PreregistrationRecord.from_json((FIX / "record_fixture.json").read_text())
    assert PreregistrationRecord.from_json(rec_path.read_text()).manifest == fixture.manifest
    rec_path.write_text(fixture.to_json())
    assert cli(["check", str(rec_path), "--root", str(tmp_path), "--run-started-at", "2030-01-01T00:00:00+00:00"]) == 0
    assert cli(["check", str(rec_path), "--root", str(tmp_path), "--run-started-at", "2020-01-01T00:00:00+00:00"]) == 1
