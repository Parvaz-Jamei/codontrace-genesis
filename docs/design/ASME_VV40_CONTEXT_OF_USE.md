# ASME V&V 40 and ClaimGate

Coordinator literature search: 2026-09-12.

ASME V&V 40 treats model credibility as **context-of-use (COU)** and
**risk-informed**. There is no universal numeric “validation score”
that a simulator either passes or fails.

ClaimGate is complementary, not a substitute:

- V&V 40 asks whether a model is credible *for a stated use and risk*.
- ClaimGate asks whether a **claim** is licensed *by the evidence in
  hand* (CLAIMS.md §5 + §8).

The standalone auditor therefore returns a public 0–5 **claim grade**,
not a COU credibility number. A high ClaimGate level still needs an
explicit context of use before it is a V&V 40 argument. A low ClaimGate
level is not a V&V 40 failure — it is missing claim evidence.

See [`CLAIMGATE_STANDALONE.md`](../CLAIMGATE_STANDALONE.md).
