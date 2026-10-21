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

OSF is not implemented; its registrations are an alternative to Zenodo.

## References

* RFC 3161, Internet X.509 PKI Time-Stamp Protocol (2001); RFC 5816 (ESSCertIDv2 update, 2010).
* RFC 5652, Cryptographic Message Syntax (2009).
* Nosek, B. A., et al. (2018). The preregistration revolution. PNAS 115(11):2600-2606.
* Zenodo REST API documentation, https://developers.zenodo.org/.
