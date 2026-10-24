# Hash-before-run preregistration with an external timestamp

Git commit times are set by the author, so a lock file in the repository
(for example `docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_LOCK.md`) can only
claim that it was "hashed before the run". `codontrace.preregistration`
gets a third party to attest the time.

```bash
# 1. hash the plan (files are hashed individually, then the canonical manifest)
python -m codontrace.preregistration hash prereg.json docs/MY_PREREG.md analysis.py
# 2. get an RFC 3161 time-stamp on the manifest digest (network, opt-in)
python -m codontrace.preregistration stamp prereg.json --allow-network \
    --tsa https://freetsa.org/tsr --ca-file tsa-ca.pem --untrusted tsa.crt
# 3. before analysing: plan unchanged and stamped before the run started?
python -m codontrace.preregistration check prereg.json --run-started-at 2026-11-01T09:00:00+03:00 --require-signature
```

`check` fails when a plan file changed after registration, when there is no
external stamp of exactly this manifest before `--run-started-at`, or (with
`--require-signature`) when the TSA signature was not verified.

## What is checked, and how

* **Request**: DER `TimeStampReq` v1 with a SHA-256 imprint, a nonce and
  `certReq` (RFC 3161 sec. 2.4.1). The bytes are identical to
  `openssl ts -query -sha256 -cert` (tested).
* **Response**: PKIStatus granted, CMS `SignedData` holding `id-ct-TSTInfo`
  (RFC 5652), imprint equal to the manifest digest, nonce equal to the
  request's, `genTime` in UTC (RFC 3161 sec. 2.4.2).
* **Signature**: `openssl ts -verify` against a CA file the user chooses,
  at the time of signing (`-attime`). Without it the record says
  `signature_verified: false`.
* **Zenodo** (`zenodo.ZenodoClient`): draft, upload to the bucket, MD5 check,
  then publish only with `publish=True` (Zenodo REST API,
  https://developers.zenodo.org/, checked 2026-10-21). A draft is not
  evidence; a published record (DOI) is. Use `SANDBOX` to try it.

No call leaves the machine unless `allow_network=True` or
`CODONTRACE_ALLOW_NETWORK=1`. Tests use responses recorded from Free TSA on
2026-10-21 (`tests/preregistration/fixtures/`).

* **OSF** (`osf.OSFClient`): a draft registration from scratch
  (`POST /v2/draft_registrations/`, with a registration schema id and the
  `osf` provider). The manifest SHA-256 goes into the frozen title and
  description. The draft is submitted with `POST /v2/registrations/` and
  `draft_registration_id`, but only when `submit=True` is passed, because an
  OSF registration cannot be deleted. The client pins API version 2.20 in the
  `Accept` header and checks that the registered description carries the
  digest. A draft is not evidence. A registration that is pending approval,
  embargoed or private is not evidence either. Only a public registration
  counts, with its `date_registered` (stored as UTC). No file is uploaded to an
  OSF project, because OSF stops creating projects through the API on
  2026-11-16 and makes them read-only on 2027-02-19, while registrations keep
  working. `TEST_SERVER` (`api.test.osf.io`) is the default. The OSF tests
  replay bodies that follow the documented responses. They are not
  recordings, because a real registration is permanent.
