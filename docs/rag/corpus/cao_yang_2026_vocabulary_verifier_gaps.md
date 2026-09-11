# Beyond Fixed Representations: The Vocabulary and Verifier Gaps in Open-Ended AI

**CodonTrace Genesis literature digest** (not a substitute for the paper).

- **id:** `cao_yang_2026_vocabulary_verifier_gaps`
- **authors:** Yuan Cao, Haiqian Yang
- **year:** 2026
- **venue:** arXiv preprint
- **identifiers:** doi:10.48550/arXiv.2607.09560 · arXiv:2607.09560
- **tags:** vocabulary gap, verifier gap, open-ended AI, representational primitives, ClaimGate, ADF, arXiv 2607.09560, intelligence
- **claim ceiling:** `runtime_observation`

## Digest

Cao and Yang (arXiv 2607.09560, 2026) argue that modern AI mostly searches *inside* a fixed representational frame. Two gaps block open-ended intelligence: the vocabulary gap (inventing and stabilizing new primitives that change the search space, not merely recombining supplied tokens) and the verifier gap (judging a new primitive when payoff is visible only after future reuse, possibly requiring the evaluator to co-evolve). Intra-space transformations are not generative ones. CodonTrace Genesis supplies an instruction/codon vocabulary; ADF/macro proposals extend the table as auditable metadata; contribution ledgers attribute local reward; ClaimGate is an *external* verifier that refuses overclaim. Those are intra-space operations until a primitive changes what can be expressed *and* a downstream evaluator prefers it for reasons the current fitness function cannot yet state. That has not happened. ClaimGate staying strict is aligned with the verifier gap: weakening the gate to unlock intelligence would fake the verifier, not close the gap.

## Key claims

- Vocabulary gap: new primitives must change the search frame and stabilize through reuse.
- Verifier gap: payoff may be invisible until future reuse; the evaluator may need to change.
- External claim gates are not co-evolving verifiers, but they must not be weakened to simulate one.

## What CodonTrace Genesis has

Instruction/codon vocabulary; ADF/macro proposal objects; contribution ledger; delayed-reward traces; ClaimGate as external overclaim refusal.

## What CodonTrace Genesis lacks

Endogenous vocabulary that alters the search frame because it pays; a verifier that co-evolves; future-reuse credit beyond attribution estimates.

## Next experiment

Track ADF macros that are reused in later generations under ablation of the macro table; still do not auto-pass open_ended_intelligence. Keep ClaimGate honest.

Retrieving this digest is not `collective_intelligence` or intelligence evidence.
