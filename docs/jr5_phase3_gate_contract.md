# JR5 phase 3 verified gate record

## Lock status

Final synchronization with the dated preregistration amendment is pending.
The gate currently uses the existing trusted manifest pin in
`LOCKED_PREREG_MANIFEST_DIGEST`; no new manifest or constants value is guessed.
Once the amendment is finalized, merge it normally, update that code pin to
its verified manifest digest, and rerun the complete package tests and CI.
No locked preregistration document is changed by this follow-up.

## Loading and evaluation

`load_e1_gate_spec(root=None)` reads the record and constants once each.
`E1GateSpec.from_prereg_constants(raw: bytes, *, record_raw: bytes)` checks both
the declared and recomputed canonical manifest digest against the code pin,
then checks the constants SHA-256 against the unique manifest entry. It parses
the exact byte sequence that was hashed, not a mapping paired with a supplied
hash. The mapping decoder is private and does not establish provenance.

`evaluate_e1_gate` compares its spec to the trusted loader's complete spec.
It requires the exact Cartesian product of registered sex ratios and reported
host sizes, and every cell requires its exact seed set with no duplicates.
N=50 remains report-only for equivalence, but a cap breach in any cell is an
instrument failure. Excluded early-fixed populations may omit `log_w`; every
kept fit must be finite. The statistical rules and positive acceptance path
are unchanged.

## Interface for the verdict adapter

`E1GateResult.to_record()` emits schema `jr5_e1_gate_v3`:

| Top-level key | JSON type |
| --- | --- |
| schema | string |
| constants_sha256 | string, computed SHA-256 of constants bytes |
| prereg_manifest_digest | string, verified canonical manifest digest |
| spec | object with the complete settings below |
| cells | array of cell objects, all reported sizes included |
| passed | boolean, equivalence/null checks pass at gated N only |
| instrument_failure | boolean, gate failure or any cell over the exclusion cap |
| digest | string, canonical digest of all preceding record fields |

The `spec` object contains:

- `constants_sha256`, `prereg_manifest_digest`, `test`: strings.
- `alpha`, `ci_level`, `relative_margin`, `must_exclude`,
  `must_exclude_ci_level`, `exclusion_cap_fraction`: numbers.
- `early_fixation_generation`, `host_n_gate`, `populations_per_cell`: integers.
- `sex_ratios`: array of numbers; `host_n_reported`: array of integers.
- `seed_split`: object keyed by the string representation of each sex ratio,
  with inclusive `[first_seed, last_seed]` integer pairs.

Each cell adds `seeds`, its sorted array of actual seed integers. Existing
cell fields remain: ratio/size, gated flag, total/used counts, excluded/fixed/
lost seed arrays, cap flag, log/ratio bounds, TOST record, ratio intervals,
log exclusion interval and decision booleans. Excluded seeds remain part of
`seeds`, as exclusion is not permission to remove a registered replicate.

A consumer must compare the full `record["spec"]` to
`load_e1_gate_spec().to_record()`, check the top-level digests agree, and check
all four cells and their seed blocks. The adapter must recompute statistics
from its bound raw evidence; a matching JSON digest or a supplied `passed`
boolean alone is not evidence. `adapter_e1()` still returns only the two gated
ratio-scale summaries for compatibility, not a provenance credential.

This check protects against swapped/tuned files and falsely labeled settings,
not arbitrary hostile code running inside the analysis process. The records
are not signed. The original preregistration's external timing/evidence
requirements remain separate from this loader's content verification.
