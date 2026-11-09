# JR5 phase 3 verified gate record

## Lock status

The gate pins the locked plan digest (every `record.json` file except
`DEVIATIONS.md`), as named in the deviations log:

- `LOCKED_PREREG_MANIFEST_DIGEST` / `LOCKED_PREREG_PLAN_DIGEST` =
  `577bd4ac643c02da6ab53976afbdbc216cacce95b5c68ba2a348c24cd226c382`.
  The gate-record key stays `prereg_manifest_digest`.
- `LOCKED_PREREG_CONSTANTS_SHA256` =
  `e27d3d9eae739097b6fa712ba6ae4f12f568c3479197c67db27bef7439fab026`,
  the sha256 of `jr5_prereg_constants.json` and its entry in that manifest.

`record.json` `manifest.digest` still covers `DEVIATIONS.md` and is checked
for freshness (declared digest matches the file list; every listed file's
bytes match). The append-only deviations log is verified separately: entries
chain, and the last entry's new digest equals the plan pin. Logging a new
deviation therefore does not disable the gate; editing a locked plan file
still refuses. A record at the earlier lock (`a4f76d60…`, constants
`608ccdea…`) is refused.

## Loading and evaluation

`load_e1_gate_spec(root=None)` re-hashes every plan file under `root`, checks
the plan digest and the deviations log, then reads the constants once.
`E1GateSpec.from_prereg_constants(raw: bytes, *, record_raw: bytes,
deviations_text=None)` checks the plan digest (and the log when text is
supplied) against the code pin, then checks the constants SHA-256 against the
unique manifest entry. It parses the exact byte sequence that was hashed, not
a mapping paired with a supplied hash. The mapping decoder is private and does
not establish provenance.

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
| prereg_manifest_digest | string, verified locked plan digest (excludes DEVIATIONS.md) |
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
