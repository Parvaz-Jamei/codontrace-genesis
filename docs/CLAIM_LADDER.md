# Claim ladder (public 0–5)

CodonTrace Genesis has **one public ladder**. Names and minimum evidence
are [`CLAIMS.md`](../CLAIMS.md) §5. Rules for positive evidence are
CLAIMS.md §8. Forbidden aliases are unchanged.

| Level | Name | Minimum evidence |
|---:|---|---|
| 0 | Software capability | Source, API, tests, examples. |
| 1 | Runtime observation | Valid run, version, config, seeds, artifact manifest, non-empty records. |
| 2 | Candidate evidence | Treatment/control, seed list, paired summary, a consistent measured difference, no placeholder evidence. |
| 3 | Mechanism support | Ablation or intervention, negative control, replay audit, effect direction, complete artifacts. |
| 4 | Replicated effect | Level 3 plus effect sizes, a confidence interval, and ≥16 seeds. |
| 5 | Publication-grade scientific claim | Level 4 plus an archived experiment artifact/DOI, documented limitations, statistical and ablation evidence. |

Internal ClaimGate still uses nine named rungs. That is a finer evaluator,
not a second public policy. See [`CLAIM_LADDER_MAP.md`](CLAIM_LADDER_MAP.md).

A null finding is valid. Metrics (including MODES and Channon 2024 Tokyo
Type 1 measurement steps) do **not** auto-grant a pass. ASME V&V 40
credibility is context-of-use / risk-informed — not a universal numeric
score. ClaimGate grades *claims given evidence*.

Standalone auditor: [`CLAIMGATE_STANDALONE.md`](CLAIMGATE_STANDALONE.md).
Historical pages [`SCIENTIFIC_CLAIM_LADDER.md`](SCIENTIFIC_CLAIM_LADDER.md)
and [`PHASE2_SCIENTIFIC_EVIDENCE_LADDER.md`](PHASE2_SCIENTIFIC_EVIDENCE_LADDER.md)
are stubs that point here.
