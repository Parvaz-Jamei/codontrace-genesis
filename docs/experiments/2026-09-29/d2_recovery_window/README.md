# D2 Recovery Window - experiment record, 2026-09-29

This directory is the archived experiment record: design, protocol, raw data and result together.
All paths below are relative to `docs/experiments/2026-09-29/d2_recovery_window/`.

**Files in this record:** 202 (excluding any tarball listed as excluded).
**Raw-data manifest:** `evidence_files.sha256` (one `sha256  size  path` line per file).

## Excluded large artifacts (sha256 recorded, not imported)

* `docs/experiments/2026-09-29/d2_recovery_window/provenance/tip.tar` - `e4ba113bbc5858f90f579309cc5c7510771d1c25e221b06d96e01f0043926c7e`
* `docs/experiments/2026-09-29/verification/full44a06f4.tar` - `a20845bca785959d7849a6bf9e4d4e4daf33e8d6945b763682033367fbff1cbe`
* `docs/experiments/2026-09-29/verification/full6187ff4.tar` - `416fae0f4af225e1f6029c881c49612ab10f45a6dd9f49612c5b00823ff80a82`
* `docs/experiments/2026-09-29/verification/base49750b1.tar` - `236de879e12c7c020588d0e1f46bebb969856d35914012f91659adb766870075`

## Question and hypothesis

Does contact structure causally mediate recovery of the rare-class yield function
(`FI-RARECLASS-CONTACT-YIELD-V1`) after a named edge is cut, beyond a degree/ATP-matched random cut
and a sham?

## Design

6 independent histories (seeds 5501, 5502 x checkpoints t = 10, 20, 30); arms
`cut_named_scaffold`, `cut_matched_random`, `sham`; horizon 40 boundaries; 18 arm runs. Round 4
builds each arm by independent re-simulation (`from_spec` per arm). Locked endpoint: yield >= 1.25x
baseline for >= 3 consecutive boundaries within T = 40; `delta_P` margin 0.20; both pre-derived and
unchanged.

## Protocol and provenance

`run_manifest.json`, `analysis_round3.json`, `analysis_round4.json`, `raw/round3/`, `raw/round4/`.
Fork diagnostic and identity proof: `logs/task7_*`. The 20 MB provenance tarball
`docs/experiments/2026-09-29/d2_recovery_window/provenance/tip.tar` is **excluded** from this archive by the size rule; its sha256 is
recorded below.

## What was executed

36 runs in round 3 (inadmissible: shared population reference) and 18 runs in round 4 with
per-arm independent re-simulation (isolation passes).

## Raw data

Full sha256 manifest: `evidence_files.sha256`.

## Analysis

`analysis_round4.json` from `raw/round4/round4_raw.json` only; round 3 retained as superseded.

## Result

`FALSIFIED_IN_MODEL` on the calibration tier: 0 of 18 arms recover, maximum yield ratio 0.573
against the locked 1.25x. Scope: 6 histories cannot exclude a rare recovery.

## What this does NOT show

No recovery window law, no slope, no effect estimate and no claim that recovery is impossible; the
fork is not fully isolated for consumers that need a self-contained serialisable fork
(`fork_audit_payload()` provides the serialisable audit view).

## Replay

`python docs/experiments/2026-09-29/d2_recovery_window/harness/d2_pack.py all`

## References

* Yedid, Ofria & Lenski, *J. Evol. Biol.* 21, 1335-1346 (2008) -
  https://doi.org/10.1111/j.1420-9101.2008.01564.x
* "Environmental change makes robust ecological networks fragile", *Nat. Commun.* 7, 12462 (2016) -
  https://doi.org/10.1038/ncomms12462

