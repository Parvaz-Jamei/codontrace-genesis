# D-2 decision — round 4 (independent re-simulation, isolated design)

**Standing verdict, 2026-10-02:** `BLOCKED_MEASUREMENT`, from
[`VERDICT_LEDGER_V1.json`](../VERDICT_LEDGER_V1.json). The positive control did
not reach the locked 1.25× endpoint, so arm zeros do not falsify an
intervention. The `FALSIFIED_IN_MODEL` heading below is the round-4 record. It
is kept. It is not the standing verdict.

**Agent:** D-2 test agent (`mechanism-test`) · **Date:** 2026-09-29
**Verdict:** `FALSIFIED_IN_MODEL` — the pre-registered retention endpoint is 0/18 in an isolated
design, with the largest yield ratio 0.573 against the locked 1.25×.
**Claim ceiling:** `phase2_design` · `hypothesis_supported = false` · `red_queen_proved = false`

Round 4 supersedes round 3. The Lead's primary instruction was applied: the forked arm
construction was replaced by **independent re-simulation per arm**, so no fork payload and no
shared state are involved.

## Provenance (a real archive this time)

* `git` resolved through the absolute binary
  `C:/Users/parvaz/AppData/Local/GitHubDesktop/app-3.5.12/resources/app/git/cmd/git.exe`
  with `-c safe.directory=*` (no git on PATH).
* Live HEAD: **01ee4a23489a63bc8073a43a82c2037c73b7bbff**, working tree clean.
  Note: the manager named tip `02cc725`; the live HEAD differs, and the run used the live tree.
  Both values are recorded in `run_manifest.json`.
* Archive: `provenance/tip.tar`, 21,032,960 bytes,
  sha256 `e4ba113bbc5858f90f579309cc5c7510771d1c25e221b06d96e01f0043926c7e`.
* Config digest: `20a38187cb61b12e47d3418e4c5609cd`. Wall time 294.85 s, one worker, 18 arm runs.

## Design actually run

Six independent population histories (seeds 5501, 5502 × checkpoints 10, 20, 30) on the
persistence-safe ecology. For every (history, arm) the engine is **rebuilt from scratch** with
`GenesisEngine.from_spec`, advanced from tick 0 to the checkpoint, and then the arm is applied at
the next boundary: `cut_named_scaffold`, `cut_matched_random`, `sham`. Horizon 40 boundaries.
Raw: `raw/round4/round4_raw.json`; analysis from raw only: `analysis_round4.json`.

## Isolation assertion (must pass, and does)

`analysis_round4.json → isolation`:

| Check | Result |
|---|---|
| every arm engine built independently (`fork_used = false`) | true |
| all 18 populations distinct objects | true |
| advancing one arm does not change another arm's digests | true |
| same-arm interleaved engines byte-identical (`x == y`) | true |
| a different arm diverges (`z != x`) | true |

The probe reaches the checkpoint before interleaving, so the arm operation has actually fired
(`x: ed2602ed74a5, 509bb9cabae2, 4471e2ed2c74`; `z: ccf9e19b2bff, c7d49cdc9b04, bf2330f6832b`).
An earlier version of this probe advanced from tick 0 and trivially matched; the defect and its fix
are recorded in `logs/round4_final.txt` and in the harness, and the corrected probe is the one
reported.

## Result table

| Arm | runs | n recover (pre-registered) | P(recover) | P(digest return, exploratory) | max yield / baseline | mean n_alive at T |
|---|---|---|---|---|---|---|
| `cut_named_scaffold` | 6 | 0 | 0.00 | 0.00 | 0.059 | 2.0 |
| `cut_matched_random` | 6 | 0 | 0.00 | 0.00 | 0.573 | 2.0 |
| `sham` | 6 | 0 | 0.00 | 0.00 | 0.570 | 2.0 |

Endpoints are versioned separately (`FI-RARECLASS-CONTACT-YIELD-V1`, 2026-09-28, pre-registered;
`GENOME-DIGEST-LOST-THEN-REGAINED-V1`, 2026-09-29, exploratory) and never pooled.

Two findings stand:

1. **Ecology persistence (positive, recorded as such).** The persistence-safe profile removes the
   extinction artefact: `n_alive_end_zero_rate = 0.00` in every arm, mean 2.0 survivors at T = 40,
   against 100 % extinction in round 2. The recovery opportunity now exists.
2. **The pre-registered endpoint does not move.** 0/18 arm runs reach 1.25× for three consecutive
   boundaries; the largest ratio anywhere is 0.573 (matched rewiring), and the named-versus-matched
   mediation contrast is exactly 0.

## Reading the verdict

`FALSIFIED_IN_MODEL` is recorded for the pre-registered retention endpoint **on this tier**: with
an isolated design, a locked rule and no run approaching the threshold, the endpoint is not
recovered by any contact intervention, and the named-vs-matched mediation contrast that D-2 exists
to measure is zero. The honest scope limit is stated with it: this is the calibration tier
(two development seeds, six histories); it does not exclude a rare recovery event, and the
four-seed pilot would be required to certify a falsification for rare events. No threshold, seed or
parameter was moved to change this reading, and the locked 1.25× rule was not re-baselined.

## Standing locks

* No repository writes by this agent; the residual isolation work is with the manager.
* Sealed seeds `801–816` untouched; `red_queen_proved = false`; no infection physics in `engine.py`.
* Every assigned history and arm is reported; no exclusions.
* Controls: `sham` (same checkpoint, token relocated, nothing else), negative
  `ablate_knowledge_digest` (round 2), injected positive used only as a scorer check and labelled
  `scientific_result = false`.
