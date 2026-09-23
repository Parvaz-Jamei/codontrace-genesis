# Phase 14 review — mode-completeness hardening

Human research review of transmission-mode contrast digests, declared-menu
registration for the HGT noise-transfer dual-null partner, and the brainstormed
keep-mode registry. Two critique rounds each name a real defect, the fix, and
the retest.

## What Phase 14 delivers

- `run_transmission_mode_contrast` in `host_parasite_mode_contrast.py`.
- Arms: `horizontal`, `vertical`, `mixed` with pairwise-distinct mode digests.
- Mixed mode must record both a successful horizontal inject and a vertical
  transmit in the same run (DEPTH Phase 5 requirement, ClaimGate-backed).
- `hgt_analogue_noise_transfer` added to `DECLARED_INTERVENTION_KINDS`.
- `BRAINSTORMED_KEEP_MODES` registry covering Waves 1–3 keep modes.
- `attach_transmission_mode_contrast` (prereg-bound; ladder unchanged).
- Tests in `tests/test_host_parasite_phase14.py`.

## Critique round 1

### Flaws found

1. **Menu registration omitted the noise-transfer dual-null partner**, so
   declared intervention planning could not name the Phase 12 control arm.
2. **Mixed blend was only unit-tested on the env**, not as a three-mode
   campaign digest surface for ClaimGate attach.

### Fixes

- Added `hgt_analogue_noise_transfer` to `DECLARED_INTERVENTION_KINDS`.
- Implemented transmission-mode contrast campaign with distinct digests and an
  explicit mixed blend assertion.

### Retest

`pytest tests/test_host_parasite_phase14.py` — green; three distinct mode
digests; mixed blend true; menu contains noise-transfer.

## Critique round 2

### Flaws found

1. **Attach without preregistration would have been inconsistent** with Wave 3
   campaign attach discipline.
2. **Registry of brainstormed keep-modes was docs-only** and could drift from
   shipped arms.

### Fixes

- Attach requires prereg digest and refuses already-attached / blocked flags.
- Registry test asserts Wave 1–3 keep modes and checks HGT / Zaman arm surfaces.

### Retest

Phase 14 suite green; Phase 12–13 regression green. BAIC pins unchanged;
`engine.py` untouched; still one `host_parasite` profile.

## Honest limits after Phase 14

- Digital transmission-mode labels only — not wet infection physics.
- Mode contrast does not prove Red Queen, major transition, or human virulence
  optimization.
