"""CLI: ``python -m codontrace.preregistration {hash,stamp,check}``.

``stamp`` contacts a TSA and therefore requires ``--allow-network``.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from .manifest import hash_plan
from .record import PreregistrationRecord, TimestampEvidence, verify_before_run
from .rfc3161 import request_timestamp, verify_signature


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m codontrace.preregistration")
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hash", help="write a record for the plan files")
    h.add_argument("record")
    h.add_argument("files", nargs="+")
    h.add_argument("--root", default=".")
    h.add_argument("--title", default="")
    s = sub.add_parser("stamp", help="add an RFC 3161 time-stamp to a record")
    s.add_argument("record")
    s.add_argument("--tsa", default="https://freetsa.org/tsr")
    s.add_argument("--ca-file")
    s.add_argument("--untrusted")
    s.add_argument("--allow-network", action="store_true")
    c = sub.add_parser("check", help="verify the plan is unchanged and stamped before a run start")
    c.add_argument("record")
    c.add_argument("--root", default=".")
    c.add_argument("--run-started-at", required=True, help="ISO 8601 with time zone")
    c.add_argument("--require-signature", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "hash":
        rec = PreregistrationRecord(hash_plan(a.files, root=a.root, title=a.title))
        Path(a.record).write_text(rec.to_json())
        print(rec.manifest.digest)
        return 0
    rec = PreregistrationRecord.from_json(Path(a.record).read_text())
    if a.cmd == "stamp":
        created = datetime.now(UTC).isoformat()
        tok = request_timestamp(rec.manifest.digest, a.tsa, created_at=created, allow_network=a.allow_network)
        verified = bool(a.ca_file) and verify_signature(
            tok, rec.manifest.canonical_bytes(), ca_file=a.ca_file, untrusted=a.untrusted
        )
        rec = rec.with_evidence(TimestampEvidence.from_rfc3161(tok, a.tsa, signature_verified=verified))
        Path(a.record).write_text(rec.to_json())
        Path(a.record).with_suffix(".tsr").write_bytes(tok.response_der)
        print(tok.gen_time.isoformat(), "signature_verified" if verified else "signature_not_verified")
        return 0
    res = verify_before_run(
        rec, root=a.root, run_started_at=datetime.fromisoformat(a.run_started_at),
        require_signature=a.require_signature,
    )
    print("OK" if res.ok else "FAIL", *res.reasons, sep="\n")
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
