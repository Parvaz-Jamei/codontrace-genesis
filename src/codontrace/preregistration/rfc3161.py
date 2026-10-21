"""Section 2: RFC 3161 time-stamp protocol, pure-Python DER.

Implements the request (``TimeStampReq``, RFC 3161 sec. 2.4.1) and parses the
response (``TimeStampResp``, sec. 2.4.2) down to the ``TSTInfo`` inside the
CMS ``SignedData`` (RFC 5652). The parser checks the PKI status, the message
imprint (SHA-256 of the manifest), the nonce and reads ``genTime``.

The TSA's *signature* is verified only by :func:`verify_signature`, which
calls ``openssl ts -verify`` with a CA file the caller trusts. Without it a
token proves the imprint and time the TSA *claims*, not who signed it; the
record says which level was checked.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from codontrace.errors import ConfigurationError

from ._network import Transport, require_network, urllib_transport

__all__ = [
    "TimeStampToken",
    "build_request",
    "parse_response",
    "request_timestamp",
    "verify_signature",
]

OID_SHA256 = "2.16.840.1.101.3.4.2.1"
OID_SIGNED_DATA = "1.2.840.113549.1.7.2"
OID_TST_INFO = "1.2.840.113549.1.9.16.1.4"
_GRANTED = {0, 1}  # granted, grantedWithMods (RFC 3161 sec. 2.4.2)


# ---- DER encoding --------------------------------------------------------
def _len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _len(len(value)) + value


def _int(n: int) -> bytes:
    b = n.to_bytes(max(1, (n.bit_length() + 8) // 8), "big", signed=True)
    return _tlv(0x02, b)


def _oid(dotted: str) -> bytes:
    parts = [int(p) for p in dotted.split(".")]
    out = bytearray([40 * parts[0] + parts[1]])
    for p in parts[2:]:
        chunk = [p & 0x7F]
        p >>= 7
        while p:
            chunk.append(0x80 | (p & 0x7F))
            p >>= 7
        out.extend(reversed(chunk))
    return _tlv(0x06, bytes(out))


def _seq(*items: bytes) -> bytes:
    return _tlv(0x30, b"".join(items))


def build_request(sha256_hex: str, *, nonce: int | None = None, cert_req: bool = True) -> bytes:
    """DER ``TimeStampReq`` v1 for a SHA-256 imprint."""
    digest = bytes.fromhex(sha256_hex)
    if len(digest) != 32:
        raise ConfigurationError("imprint must be a SHA-256 hex digest")
    imprint = _seq(_seq(_oid(OID_SHA256), b"\x05\x00"), _tlv(0x04, digest))
    parts = [_int(1), imprint]
    if nonce is not None:
        parts.append(_int(nonce))
    if cert_req:
        parts.append(_tlv(0x01, b"\xff"))
    return _seq(*parts)


def derive_nonce(sha256_hex: str, created_at: str) -> int:
    """64-bit nonce from the imprint and request time (unique per request, no RNG)."""
    h = hashlib.sha256(f"{sha256_hex}|{created_at}".encode()).digest()
    return int.from_bytes(h[:8], "big") >> 1


# ---- DER decoding --------------------------------------------------------
@dataclass(frozen=True)
class _Node:
    tag: int
    value: bytes
    raw: bytes

    def children(self) -> list[_Node]:
        if not self.tag & 0x20:
            raise ConfigurationError(f"DER tag {self.tag:#x} is not constructed")
        return _parse_all(self.value)


def _parse_one(buf: bytes, i: int) -> tuple[_Node, int]:
    if i + 2 > len(buf):
        raise ConfigurationError("truncated DER")
    start = i
    tag = buf[i]
    if tag & 0x1F == 0x1F:
        raise ConfigurationError("high-tag-number DER is not supported")
    n = buf[i + 1]
    i += 2
    if n & 0x80:
        k = n & 0x7F
        if k == 0 or k > 4 or i + k > len(buf):
            raise ConfigurationError("bad DER length")
        n = int.from_bytes(buf[i : i + k], "big")
        i += k
    if i + n > len(buf):
        raise ConfigurationError("truncated DER value")
    return _Node(tag, buf[i : i + n], buf[start : i + n]), i + n


def _parse_all(buf: bytes) -> list[_Node]:
    out, i = [], 0
    while i < len(buf):
        node, i = _parse_one(buf, i)
        out.append(node)
    return out


def _decode_oid(v: bytes) -> str:
    first = v[0]
    parts = [first // 40, first % 40]
    acc = 0
    for b in v[1:]:
        acc = (acc << 7) | (b & 0x7F)
        if not b & 0x80:
            parts.append(acc)
            acc = 0
    return ".".join(map(str, parts))


def _gen_time(v: bytes) -> datetime:
    s = v.decode("ascii")
    if not s.endswith("Z"):
        raise ConfigurationError("genTime must be UTC (RFC 3161 sec. 2.4.2)")
    s = s[:-1]
    main, _, frac = s.partition(".")
    dt = datetime.strptime(main, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    if frac:
        dt = dt.replace(microsecond=int((frac + "000000")[:6]))
    return dt


@dataclass(frozen=True)
class TimeStampToken:
    status: int
    imprint_sha256: str
    gen_time: datetime
    serial: int
    nonce: int | None
    policy: str
    response_der: bytes

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "imprint_sha256": self.imprint_sha256,
            "gen_time": self.gen_time.isoformat(),
            "serial": self.serial,
            "nonce": self.nonce,
            "policy": self.policy,
            "response_sha256": hashlib.sha256(self.response_der).hexdigest(),
        }


def parse_response(der: bytes, *, expected_sha256: str, expected_nonce: int | None = None) -> TimeStampToken:
    """Parse a ``TimeStampResp`` and check status, imprint and nonce."""
    top, end = _parse_one(der, 0)
    if end != len(der) or top.tag != 0x30:
        raise ConfigurationError("TimeStampResp must be one DER SEQUENCE")
    items = top.children()
    status_info = items[0].children()
    status = int.from_bytes(status_info[0].value, "big", signed=True)
    if status not in _GRANTED or len(items) < 2:
        raise ConfigurationError(f"TSA refused the request (PKIStatus {status})")
    content_info = items[1].children()
    if _decode_oid(content_info[0].value) != OID_SIGNED_DATA:
        raise ConfigurationError("timeStampToken is not CMS SignedData")
    signed = content_info[1].children()[0].children()
    encap = signed[2].children()
    if _decode_oid(encap[0].value) != OID_TST_INFO:
        raise ConfigurationError("eContentType is not id-ct-TSTInfo")
    octets = encap[1].children()[0]
    tst = _parse_one(octets.value, 0)[0].children()
    policy = _decode_oid(tst[1].value)
    imprint = tst[2].children()
    alg = _decode_oid(imprint[0].children()[0].value)
    if alg != OID_SHA256:
        raise ConfigurationError(f"imprint algorithm {alg} is not SHA-256")
    got = imprint[1].value.hex()
    if got != expected_sha256.lower():
        raise ConfigurationError("time-stamp imprint does not match the manifest digest")
    serial = int.from_bytes(tst[3].value, "big", signed=True)
    gen_time = _gen_time(tst[4].value)
    nonce = None
    for node in tst[5:]:
        if node.tag == 0x02:
            nonce = int.from_bytes(node.value, "big", signed=True)
    if expected_nonce is not None and nonce != expected_nonce:
        raise ConfigurationError("time-stamp nonce does not match the request")
    return TimeStampToken(status, got, gen_time, serial, nonce, policy, der)


def request_timestamp(
    sha256_hex: str,
    tsa_url: str,
    *,
    created_at: str,
    allow_network: bool = False,
    transport: Transport | None = None,
) -> TimeStampToken:
    """Send a ``TimeStampReq`` to ``tsa_url`` (opt-in network) and parse the reply."""
    nonce = derive_nonce(sha256_hex, created_at)
    body = build_request(sha256_hex, nonce=nonce)
    if transport is None:
        require_network(allow_network, "RFC 3161 time-stamping")
        transport = urllib_transport
    resp = transport("POST", tsa_url, body, {"Content-Type": "application/timestamp-query"})
    if resp.status != 200:
        raise ConfigurationError(f"TSA answered HTTP {resp.status}")
    return parse_response(resp.body, expected_sha256=sha256_hex, expected_nonce=nonce)


def verify_signature(
    token: TimeStampToken, data: bytes, *, ca_file: str | Path, untrusted: str | Path | None = None
) -> bool:
    """Verify the TSA signature and chain with ``openssl ts -verify`` (if installed)."""
    exe = shutil.which("openssl")
    if exe is None:
        raise ConfigurationError("openssl is not installed; signature not verified")
    with tempfile.TemporaryDirectory() as tmp:
        tsr = Path(tmp) / "r.tsr"
        dat = Path(tmp) / "d.bin"
        tsr.write_bytes(token.response_der)
        dat.write_bytes(data)
        cmd = [exe, "ts", "-verify", "-data", str(dat), "-in", str(tsr), "-CAfile", str(ca_file),
               # check the chain at signing time, so a later expiry does not void old stamps
               "-attime", str(int(token.gen_time.timestamp()))]
        if untrusted is not None:
            cmd += ["-untrusted", str(untrusted)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603
    return proc.returncode == 0 and "Verification: OK" in proc.stdout
