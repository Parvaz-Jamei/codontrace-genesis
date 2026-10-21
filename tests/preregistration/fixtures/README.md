# Recorded RFC 3161 fixtures

Recorded on 2026-10-21 from the public Free TSA (https://freetsa.org/tsr).

* `plan_fixture.md`: the hashed file. Not a real plan.
* `freetsa_request.tsq`: `openssl ts -query -data plan_fixture.md -sha256 -cert` (OpenSSL 3).
* `freetsa_response.tsr`: the TSA reply to that request.
* `record_fixture.json`, `record_fixture.tsr`: written by
  `python -m codontrace.preregistration hash` and `stamp --allow-network`
  for a manifest of `plan_fixture.md`.
* `freetsa_cacert.pem`, `freetsa_tsa.crt`: the TSA's published CA and signing
  certificates (https://freetsa.org/files/), used only to test signature
  verification. Trusting them is the test's choice, not a recommendation.
