# Phase 6 review — factorial, network digests, preregistration

Human research review of abiotic×biotic factorial campaigns, adaptive-origin
gate, interaction-network digests, and mandatory preregistration before
campaign attach. Two critique rounds each name a real defect, the fix, and
the retest.

## What Phase 6 delivers

- `run_abiotic_biotic_factorial` — 2×2 abiotic productivity × biotic
  presence/absence cells with per-cell campaign digests.
- `adaptive_origin_gate` — Fortuna 2017-inspired digital control flag
  (`wet_claim=False`).
- `summarize_interaction_network` — edge count, strength heterogeneity,
  canonical digest.
- `host_parasite_preregistration` + attach; **required** before
  `attach_host_parasite_campaign`.
- Evidence notes under `docs/claimgate/host_parasite_port_20260924/evidence/`
  with DOIs (digital comparator scope only).
- Tests in `tests/test_host_parasite_phase6.py`.

## Critique round 1

### Flaws found

1. **Prereg gate broke Phase 4 attach tests silently.** After requiring
   preregistration, attach failures all reported “preregistration required”
   and never reached overwrite / missing-`requested_claim` / falsification
   checks — masking those contracts.
2. **Empty `forbidden_claims=()` could skip clinical bans** before merge if
   validation allowed an empty sequence through.

### Fixes

- Phase 4 attach tests now attach a valid preregistration first, then assert
  the original refuse paths.
- `host_parasite_preregistration` rejects empty `forbidden_claims` and always
  unions the core clinical / overclaim ban set.

### Retest

`pytest tests/test_host_parasite_campaign_phase4.py tests/test_host_parasite_phase6.py`
— green.

## Critique round 2

### Flaws found

1. **Abiotic factor was label-only.** Low/high productivity cells under biotic
   presence shared the same steal and therefore the same mean scores/digests,
   so the factorial could not challenge one-sided biotic stories.
2. **Snapshot/docs risked overclaiming wet adaptive origin.** Gate text needed
   an explicit `wet_claim=False` / digital-control-only note.

### Fixes

- Biotic-present cells set `steal_fraction = min(1.0, 0.8 / productivity)` so
  high productivity retains more CPU (Lopez Pascua resource analogy); absent
  cells stay at score 1.0 with shared digest (honest: no parasite).
- Adaptive-origin gate payload includes `wet_claim=False`,
  `raises_claim_ladder=False`, and Fortuna-2017 digital-control source tag.

### Retest

Full host–parasite Phase 1–6 suites green. BAIC pins unchanged; `engine.py`
untouched; `population/` untracked.

## Honest limits after Phase 6

- Factorial + network digests audit digital campaigns; they do not prove Red
  Queen dynamics, major transitions, CRISPR identity, phage therapy, vaccine
  effect, epidemic forecast, or BSL.
- Preregistration records intent; it does not raise the public ClaimGate ladder.
- Evidence notes are literature comparators, not clinical certificates.
