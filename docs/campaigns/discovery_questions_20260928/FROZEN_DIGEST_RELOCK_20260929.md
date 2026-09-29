# Frozen-artifact re-lock — VT × spatial factorial digests (2026-09-29)

**Scope:** `docs/hard_experiment_hp/locked_campaign_digests.json`, cells for the
VT × spatial factorial campaign and its `factorial_digest`.
**Decision owner:** the owner, on the independent verification recorded in
`test-runs/verify/frozen_drift.json` (verdict branch: benign, intended
consequence of `baf0b12`).

## Why the digests moved

`baf0b12` added exactly two keys to the environment snapshot,
`handling_time` and `handling_busy_remaining`. Both are constant `0.0` in every
snapshot, and `host_parasite_continuum.py` folds `env.snapshot()["digest"]` into
each cell, so the two keys widened a digest input without changing any modelled
quantity.

## Verification (not inferred)

* `all_raw_outcomes_identical: true` — the raw cell outcomes are identical at
  `d66f0db` (frozen) and `baf0b12`.
* `added_snapshot_keys.note` — both added keys are constant, so no modelled
  quantity varies.
* `aggregate_cell_digest_narrowed_equals_d66f0db_all: true` — dropping the two
  keys from the `baf0b12` snapshots reproduces the `d66f0db` digest exactly, and
  `factorial_from_narrowed` equals the locked `d94e1826…`.
* The other three campaigns match the lock at both revisions.

## Consequences

The four affected cell digests and `factorial_digest` are re-locked to the
`baf0b12` values. The file keeps its existing digest convention: it is text, so
it is hashed through the LF-normalising helper, never through raw working-tree
bytes.

**Scope of the change:** only the `vt_spatial_factorial` block of
`docs/hard_experiment_hp/locked_campaign_digests.json` changed — its four cell
digests plus `factorial_digest` (now
`e5c43da01e0841e4aab57d2b67a56867b9e4a5a64061247a2aeff1bb78af950c`). The other
three campaign blocks are byte-unchanged, and `host_parasite_env.py` is not
touched: the snapshot keys that widened the digest input stay exactly as
`baf0b12` wrote them.

Note on the failure count: on a CRLF checkout of `baf0b12` the seven BAIC pin
failures (raw-byte hashing) abort the family early and mask this drift; that
hashing defect is already fixed by `cff84cd`. On an LF/CI checkout the drift
alone causes five failures, all naming `vt_spatial_factorial`. No environment
code is repaired to chase the CRLF-only seven.

**No claim and no ceiling changes.** Every claim flag (`hypothesis_supported`,
`red_queen_proved`, and the phase/claim-ladder flags) stays exactly as sealed in
the stage-0 and campaign records; this note records a digest-input widening and
nothing else.
