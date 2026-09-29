# task-6 — independent verification of the tick-index fix

Verifier: teammate `ci-green` (independent; no repo writes, write scope `test-runs/verify` only).
Repo: `codontrace-genesis` at **HEAD `6187ff4`**, clean working tree.
Environment for every command: `PYTHONPATH=<repo>\src`, `PYTHONIOENCODING=utf-8`,
`PYTHONUTF8=1`, output captured with `cmd.exe /c "... > file 2>&1"` and read back.

**Verdict: ACCEPT.**

---

## 1. Live-repo contract test — PASS

```
cd codontrace-genesis
python -m pytest -q tests/genesis_gates/test_post_review_manifest_replay_review_rule_contracts.py
```

```
.......                                                                  [100%]
exit=0
```

Raw output: `test-runs/verify/check1_gates.txt` (7 passed, whole file green).

## 2. Adversarial probes — PASS

Script: `test-runs/verify/probe_tick_index.py`
Raw output: `test-runs/verify/probe_out.txt`, machine-readable `test-runs/verify/probe_report.json`.

```
python test-runs/verify/probe_tick_index.py
exit=0
asserted failures: none
```

**2a. `batch(N)` vs `N × run_ticks(1)`** — six matrix cells, all `index_ok=true` and
`tick_digest_identical=true`:

| spec | N | batch indices | single indices | seeds implied | tick digests |
| --- | --- | --- | --- | --- | --- |
| seed 22, `tick_count=0` | 1 | `[0]` | `[0]` | `[22]` | identical |
| seed 22, `tick_count=0` | 5 | `[0..4]` | `[0..4]` | `[22..26]` | identical |
| seed 22, `tick_count=0` | 17 | `[0..16]` | `[0..16]` | `[22..38]` | identical |
| seed 7, `tick_count=5` | 1 | `[0]` | `[0]` | `[7]` | identical |
| seed 7, `tick_count=5` | 5 | `[0..4]` | `[0..4]` | `[7..11]` | identical |
| seed 7, `tick_count=5` | 17 | `[0..16]` | `[0..16]` | `[7..23]` | identical |

**2b. Falsifier — is the fix a lazy revert that ignores the index?** No.
`recorded_seed_schedule(seed=22, N=17)`: `engine_used_index_driven_seeds = true`. The engine's
per-tick digests are distinguishable from a runner driven with a constant seed, so the schedule is
genuinely index-driven; a revert to `base + len(self._tick_results)` would have produced the
constant-seed sequence and failed 2a.

**2c. `from_fork` honours `_tick_offset`** — PASS.

| case | `fork["tick_index"]` | child indices | child seeds | expected seeds | `fork_honours_tick_offset` |
| --- | --- | --- | --- | --- | --- |
| seed 31, pre=3, post=2 | 3 | `[3, 4]` | `[34, 35]` | `[34, 35]` | **true** (not `[0, 1]`) |
| seed 7, pre=4, post=3 | 4 | `[4, 5, 6]` | `[11, 12, 13]` | `[11, 12, 13]` | **true** |

`index_ok`, `seeds_ok` and `continuation_index_identical` are all `true`: the continuation's index
sequence equals the original engine's tail at the same absolute indices.

## 3. Pins byte-identical to HEAD `434bbd1` — PASS, 12/12, no pin moved

Script `test-runs/verify/check_pins_vs_434bbd1.py`, raw output `test-runs/verify/check3_pin_identity.txt`
(`exit=0`), plus the live suites in `test-runs/verify/check3_pins.txt`:

```
python -m pytest -q tests/platform/pin tests/test_host_parasite_phase9.py \
  tests/test_host_parasite_phase18.py tests/test_host_parasite_phase24.py \
  tests/test_host_parasite_phase25.py tests/test_host_parasite_phase26.py \
  tests/test_host_parasite_hard_regressions.py::test_hc5_he_hp_locked_pack_schema_integrity \
  tests/test_host_parasite_world_phase6.py
...........................................                              [100%]
exit=0
```

Per-pin result (`SAME` = LF-normalised bytes equal the `434bbd1` blob **and** the committed
constant still matches the live file):

| Pin (committed constant) | vs `434bbd1` |
| --- | --- |
| `docs/hard_experiment_01/results_v7.json` `35bb5936…cbd6` | PASS |
| `docs/claimgate/risk_bar.json` `4dbe4aa3…1cd7` | PASS |
| `docs/claimgate/biomedical_study.json` `9685f2fb…ddce` | PASS |
| `docs/hard_experiment_hp/locked_campaign_digests.json` (`locked_digest 62fec73f…7349`, 4 campaigns) | PASS |
| `docs/HARD_EXPERIMENT_01_PREREG.md` `cb4643a3…fc40` | PASS |
| amendment `02` `14c111af…2f2f` | PASS |
| amendment `03` `3a9d4fd4…7058` | PASS |
| amendment `04` `6a1facb0…fd60` | PASS |
| amendment `05` `d363533b…e6d7` | PASS |
| amendment `LOCK` `818b4efe…159c` | PASS |
| `docs/hard_experiment_02/results_v1.json` `58fd4566…6418` | PASS |
| `docs/hard_experiment_02/analysis_v1b_contrasts.json` `0572e106…cf58` | PASS |

`=== PINS: 12/12 PASS ===`, `failures: none`. No pin moved, so no re-lock was proposed.
(The live working tree is CRLF while the blobs are LF, exactly as `.gitattributes` `* text=auto`
implies; the graded comparison is the LF digest plus the committed constant, and both agree.)

## 4. Lint and bytecode — PASS

```
python -m ruff check src tests        -> exit=0, "All checks passed!"
python -m compileall -q src tests examples tools -> exit=0, no output
```

Raw: `test-runs/verify/check4_ruff.txt`, `test-runs/verify/check4_compileall.txt`.

## 5. Commit inspection — PASS, no unrelated edits

```
git show --stat 44a06f4   ->  src/codontrace/engine_runtime.py | 2 +-   (1 insertion, 1 deletion)
git show --stat 6187ff4   ->  src/codontrace/genesis/campaigns/discovery_q_20260928_idea4_engine.py | 22 +++-- (20 insertions, 2 deletions)
```

* `44a06f4` is exactly the one-line change
  `index=base + len(self._tick_results)` → `index=base + index` inside `run_ticks`, at
  `src/codontrace/engine_runtime.py:283`. Nothing else in the commit. No unrelated edit.
* `6187ff4` touches one file only. `ecology: str = "standing"` is the default, and I verified the
  default path is **byte-identical** to the parent `44a06f4` by building the spec in a pristine
  `git worktree` checkout of `44a06f4` and in the live tree
  (`test-runs/verify/check_standing_identity.py`, raw output `test-runs/verify/check5_standing.txt`,
  `exit=0`):

  | probe | live `6187ff4` | parent `44a06f4` | result |
  | --- | --- | --- | --- |
  | `standing` digest, seed 22, tick 5 | `ac7911ede50b25f12994a77d1278235518d06a9b91f556a0d465106f97e35db6` | identical | PASS |
  | `standing` digest, seed 7, tick 5 | `c00f8c49a4d603d3fe1ec316cbc06b93649a0b44085c2fe5a733fdf4b67e9374` | identical | PASS |
  | `standing` metadata, both seeds | full dict | identical | PASS |
  | `persistence_safe`, seed 22 | `34753504d501b04b9e9f8414511be019c36e8e27533ec9825882349e7a320888` | `TypeError` (profile absent) | opt-in only, as claimed |

  `=== STANDING DEFAULT IDENTITY: PASS ===`. The temporary worktree was removed
  (`git worktree list` shows only the main checkout); the repo is untouched by this verification.

## 6. Recorded, not fixed — the manager's extra check really does FAIL

`from_fork` continuation is **not** byte-identical to the original engine's continuation. My own
independent reproduction agrees (different seeds/offsets than the manager's, same outcome):

* `fork seed=31 pre=3 post=2`: `continuation_index_identical = true` but
  `continuation_digest_identical = **false**`
  * child (restored) indices `[3, 4]` → `664a80777fb993759db3bddc41f188e79a8eab4629a279c4c74a882e67f14e4b`,
    `d5725bc0970aa3fb76f5aa9c67184ee5f34773da5ffe10abc084e5e63b6d6c44`
  * original engine indices `[3, 4]` → `385d017de1f645afb718a989af0cab7b1f75ef1d5edf87dfe5ce9279f39781af`,
    `9d0b0184d18bd4a59342b68b849442256d8ebb4c75746eea5bae85d77c7f1cc4`
* `fork seed=7 pre=4 post=3`: `continuation_digest_identical = false` likewise.

This is **not** an index defect — the index/seed invariant Job A requires holds in both cases — it
is incompleteness of the captured fork state. It is out of task-6's scope and is owned by
`mechanism-test`; recorded here as instructed, not fixed, and not counted against the verdict.

---

## Verdict

**ACCEPT.** Checks 1–5 all pass on `6187ff4` with raw evidence above; the pins are byte-identical to
`434bbd1` (12/12, none moved); the fix is the intended one-line change and is not a lazy revert
(`from_fork` still honours `_tick_offset`); the `6187ff4` opt-in addition leaves the standing default
byte-identical. The only outstanding defect is the pre-existing fork-continuation
incompleteness, which is recorded for `mechanism-test` and is not a regression from these commits.
No push performed.
