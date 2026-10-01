# Phase 5 lock — limited confirmatory campaign was not opened

**Date:** 2026-10-02. **Verdict:** `BLOCKED_MEASUREMENT`.
**Flags:** `hypothesis_supported = false`, `red_queen_proved = false`.
Source of the standing labels: [`VERDICT_LEDGER_V1.json`](VERDICT_LEDGER_V1.json).

No biological innovation is claimed. The nearest published frames stay the ones
already cited in each record (Hamilton 1980 and Otto & Nuismer 2004 for the
cost of sex; Yedid, Ofria & Lenski 2008 for recovery after loss; a noise-free
`do` on a mutation draw for CausalTape). This phase does not add a new
prediction.

## Locked before any new seed

| Test | Aim | Data mechanism | Estimand | Analysis | Performance rule | Effect bound | Stop |
|---|---|---|---|---|---|---|---|
| RQ-1 | time-shift interaction | archived population JSON | class-balanced cell, not abundance pressure | paired interval on seeds | support label and sign | not re-fit | stop: archive incomplete |
| RQ-3 | information-path cut | antagonist roster | common-window share | paired seeds | interval excludes 0 | not re-fit | stop: cited seeds have no raw |
| D-2 | contact-mediated recovery | engine transfer, not name order | paid ATP on an identified contact | seed is the replicate | positive control must be able to move | locked 1.25× is historical only | stop: control cannot reach it |
| sex cost | where costly sex is lost | the archived 2,100-run grid | sexual frequency and extinction | the grid's own intervals | bracket only inside that grid | `(1.1, 1.2]` is not exported | no new sweep |

Development, pilot and confirmatory seeds stay in the bands already written in
each design file. Seeds that appear in a README are spent. They are not unseen.

## Two short runs on this machine

Python 3.11, one generation, three arms, no files written. Seeds 21001 and
21011 are already in the published raw tree.

| Seed | Wall clock | Per arm |
|---|---|---|
| 21001 | 1.159 s including import | about 0.096–0.099 s |
| 21011 | 1.125 s including import | about 0.098–0.102 s |

A 40-generation, three-arm, three-seed continuation would be on the order of
half a minute of stepping. Time is not why the campaign stays closed. It stays
closed because the gates above failed. The first attempt also failed in 0.9 s:
the archived runner called `_passage_update` with a positional RNG, and the
current method takes that argument by keyword. The call was corrected. The
personal `E:\` import path was replaced with the checkout root. Neither change
opens a confirmatory tier or rewrites a result.

## What a clean checkout can and cannot rebuild

The verdict ledger test is a required CI gate. The mypy job is optional
(`continue-on-error: true`); a green workflow does not mean mypy passed.
`rq3_harness.py` is an archive runner, not a substitute for `tests/`.
