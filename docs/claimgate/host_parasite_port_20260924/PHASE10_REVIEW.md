# Phase 10 review — genome-aware dual digests on Zaman arms

Human research review of layered host+parasite `SemanticGenome.digest()`
trajectories on freeze / replay / reciprocal arms, schedule-bound digest-of-
trajectory, repertoire continuity, and ClaimGate attach honesty. Two critique
rounds each name a real defect, the fix, and the retest.

## What Phase 10 delivers

- `run_genome_zaman_campaign` in `host_parasite_genome_zaman.py`.
- Dual-genome summaries: host/parasite digests + trajectories +
  `parasite_schedule_digest`; optional secondary `GenomeProgram` identity.
- Explicit arm-mode flags: `parasite_genome_frozen`,
  `parasite_schedule_predetermined`, `reciprocal_genome_update`.
- Repertoire summaries layered from Phase 7 Zaman (continuity).
- `attach_genome_zaman_campaign` (prereg + digest bind required);
  complexity / Red Queen unproved; ceiling max `candidate_evidence`.
- Tests in `tests/test_host_parasite_phase10.py`.
- Wave-3 design lock: `DEPTH_BRAINSTORM_WAVE3.md` (two innovation rounds).

## Critique round 1

### Flaws found

1. **Arm semantics were digest-only without declared mode flags.** A flat
   parasite digest trajectory could be misread as coincidental equality rather
   than intentional freeze; ClaimGate consumers had no boolean honesty surface.
2. **`GenomeProgram` was initially constructed with an invalid `genome=`
   kwarg** (API is `bits` + `codon_width`); caught in smoke before attach.

### Fixes

- Added `parasite_genome_frozen` / `parasite_schedule_predetermined` /
  `reciprocal_genome_update` on `DualGenomeSummary` and asserted in tests.
- Construct `GenomeProgram(bits=..., codon_width=...)` for secondary identity
  only; primary surface remains `SemanticGenome.digest()`.

### Retest

`pytest tests/test_host_parasite_phase10.py` — green; freeze singleton parasite
trajectory + host movement; three distinct schedule digests.

## Critique round 2

### Flaws found

1. **Attach omitted preregistration digest binding.** Unlike Phase 9 Cornish,
   a genome Zaman campaign could attach under a mismatched QOI/COU prereg.
2. **Schema not checked on attach**, so a renamed/forged payload could slip
   into `extra["genome_zaman_campaign"]`.

### Fixes

- `attach_genome_zaman_campaign` requires bundle prereg digest and records it
  on the attached payload; refuses schema ≠
  `host_parasite_genome_zaman_campaign_v1`.
- Tests assert attached `preregistration_digest` matches prereg record.

### Retest

Phase 10 suite green; prior HP suites remain green. BAIC pins unchanged;
`engine.py` untouched; `population/` untracked.

## Honest limits after Phase 10

- Digital genotype freeze/replay/reciprocal analogues only; not wet Zaman
  contingency loci and not a complexity-emergence proof.
- `GenomeProgram` identity is secondary provenance, not infection physics.
- Repertoire richness remains task-set cardinality; genome digests are layered
  observables under the same `host_parasite` profile.
