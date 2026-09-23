# Phase 12 review — HGT-analogue + intracellular / free-living pack

Human research review of digital-only HGT-analogue segment copy, noise-transfer
dual-null, intracellular seat constraint, and free-living horizontal inject
under the same `host_parasite` profile. Two critique rounds each name a real
defect, the fix, and the retest.

## What Phase 12 delivers

- `run_hgt_compartment_campaign` in `host_parasite_hgt.py`.
- Arms: `hgt_analogue_segment_copy`, `hgt_analogue_noise_transfer`,
  `intracellular_seat_constraint`, `free_living_horizontal_inject`.
- Segment-transfer digests + `transfer_kind` honesty flags; wet HGT /
  conjugation / CRISPR spacer acquisition always False.
- COU labels `microbe` / `bacterium_analogue`; no new DomainProfile.
- Extended `DECLARED_INTERVENTION_KINDS` with the three digital kinds.
- `attach_hgt_compartment_campaign` (prereg + digest bind; refuses wet claims).
- Tests in `tests/test_host_parasite_phase12.py`.

## Critique round 1

### Flaws found

1. **Entropy-based `diversity_delta` made uniform noise edits look like a
   diversity rise** (all clones identically edited), breaking the dual-null
   contrast against structured segment copy.
2. **Transfer kind was only implicit in digest salts**, so ClaimGate consumers
   could not see structured vs noise vs seat vs free-living without decoding.

### Fixes

- Redefined diversity as unique-genome count + mean Hamming deltas (noise and
  seat stay flat; structured / free-living rise).
- Added explicit `transfer_kind` on each arm outcome.

### Retest

`pytest tests/test_host_parasite_phase12.py` — green; noise ≤ 0; structured > 0;
four distinct arm and transfer digests.

## Critique round 2

### Flaws found

1. **Tests did not assert pairwise-distinct transfer digests** for structured
   vs noise (core dual-null surface).
2. **Attach must refuse wet HGT / CRISPR identity flags** if forged into the
   payload.

### Fixes

- Tests assert four distinct transfer digests and structured ≠ noise.
- Attach checks `wet_hgt_claimed` / `crispr_identity_proved` and forces False
  on the attached record; requires non-empty `failure_reason` when falsified.

### Retest

Phase 12 suite green. BAIC pins unchanged; `engine.py` untouched; still one
`host_parasite` profile.

## Honest limits after Phase 12

- Digital payload / seat / inject analogues only — not wet HGT, conjugation,
  plasmids, or CRISPR spacer acquisition.
- COU microbe/bacterium labels are vocabulary, not taxonomic DomainProfiles.
