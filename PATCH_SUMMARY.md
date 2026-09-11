# Patch summary — CodonTrace Genesis

Package: `codontrace` `0.3.0b2` (no version bump in this patch)

This file is a current-state honesty note after Phase F+#9 and Phase G+#10.
It is not a release, tag, or PyPI event.

## What this patch does

Reconcile full-suite tests and release docs with live ClaimGate ceilings:

- Official default memory delayed-reward fixture remains
  `pilot_fixture_not_strong_memory_claim` (`claim_allowed_for_strong_memory=False`).
- Official default capsule-usefulness fixture remains
  `no_positive_behavioral_utility` (`claim_allowed_for_capsule_usefulness=False`).
- Release evidence lists example-generated official pilot JSON names.
  Those files are produced by `examples/genesis_*_pilot.py`. They are not
  committed fake payloads and are not a substitute for ClaimGate.
- Restore the legacy `World2D.resources` amount-only semantics note.
  Phase G named materials are a separate overlay and do not mutate that field.
- Align the license metadata test with `AGPL-3.0-or-later`.

## What was not weakened

ClaimGate still blocks `intelligence`, `collective_intelligence`, `AGI`,
`wet_lab_equivalent`, `realistic_chemistry_proved`, `avida_replacement`,
and the other forbidden aliases. Phase A–E default digest pins are unchanged.
No tag, no release, no PyPI publish.
