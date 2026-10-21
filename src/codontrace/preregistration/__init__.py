"""Hash-before-run preregistration with external timestamps.

1. :mod:`.manifest`: hash a plan (files) into a canonical manifest digest.
2. :mod:`.rfc3161`: RFC 3161 time-stamp request/response (pure-Python DER),
   with optional signature verification through ``openssl ts -verify``.
3. :mod:`.zenodo`: deposit the manifest as a Zenodo draft (publish only on request).
4. :mod:`.record`: a preregistration record and the ``hash before run`` check.

No network call happens unless the caller passes ``allow_network=True``
(or sets ``CODONTRACE_ALLOW_NETWORK=1``); tests replay recorded responses.
"""

from .manifest import PlanManifest, hash_plan
from .record import PreregistrationRecord, TimestampEvidence, verify_before_run
from .rfc3161 import TimeStampToken, build_request, parse_response, request_timestamp

__all__ = [
    "PlanManifest",
    "PreregistrationRecord",
    "TimeStampToken",
    "TimestampEvidence",
    "build_request",
    "hash_plan",
    "parse_response",
    "request_timestamp",
    "verify_before_run",
]
