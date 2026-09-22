# ASME V&V 40 and ClaimGate

Coordinator literature search: 2026-09-12; biomedical wrapper: 2026-09-22.

ASME V&V 40-2018, *Assessing Credibility of Computational Modeling through
Verification and Validation: Application to Medical Devices*, treats model
credibility as **context-of-use (COU)** and **risk-informed**. There is no
universal numeric “validation score” that a simulator either passes or fails.
Model risk is assembled from *model influence* and *decision consequence*.
Credibility activities (code verification, calculation verification,
validation comparator, applicability) must be commensurate with that risk.

ClaimGate is complementary, not a substitute:

- V&V 40 asks whether a model is credible *for a stated use and risk*.
- ClaimGate asks whether a **claim** is licensed *by the evidence in hand*
  (CLAIMS.md §5 + §8).

The standalone auditor therefore returns a public 0–5 **claim grade**, not a
COU credibility number. A high ClaimGate level still needs an explicit context
of use before it is a V&V 40 argument. A low ClaimGate level is not a V&V 40
failure — it is missing claim evidence.

The biomedical adapter (`claimgate.adapters.biomedical`) only records QOI,
COU, and user-declared influence/consequence on the bundle. It does **not**
implement the V&V 40 process, issue a regulatory opinion, or certify SaMD.

See [`CLAIMGATE_STANDALONE.md`](../CLAIMGATE_STANDALONE.md) and
[`BIOMEDICAL_ENGINEERING.md`](../BIOMEDICAL_ENGINEERING.md).
