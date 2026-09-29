# task-10 — independent verification of `40138c9` (RNG migration) and `913f18e` (fork restoration)

Verifier: teammate `ci-green` (independent; no repo writes, write scope `test-runs/verify` only).
Tree under test: **`913f18e`** (code) with `HEAD=02cc725`, whose only delta over `913f18e` is two
docs files (`docs/ci/CI_REPAIR_AND_TEST_STATUS_2026-09-29.md`,
`docs/campaigns/discovery_questions_20260928/TESTS_DONE_STATUS_2026-09-29.md`) — `git diff --stat
913f18e HEAD` shows 2 files, 89 insertions, **no source change**. Working tree clean.

Environment for every command: `PYTHONPATH=<tree>\src`, `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`,
captured with `cmd.exe /c "... > file 2>&1"`.

**Verdict: ACCEPT**, with one recorded contract regression that does not invalidate the fix (§B4).

---

## A. `40138c9` — RNG migration preserves the stdlib stream bit-for-bit

### A1. Static gate

```
python -m pytest tests/test_rng.py -q     ->  ....  [100%], exit=0   (4 passed)
```

Offender list computed by me from the same rule as
`tests/test_rng.py::test_no_direct_random_usage_outside_rng_module`
(`forbidden = ("import random", "from random", "random.", "Random(", "pickle")`, `rng.py` exempt):

```
test-runs/verify/scan_rng_offenders.py
scanned=321 files under src\codontrace
exempt=rng.py
offenders=0
```

Raw: `task10_A1_test_rng.txt`, `task10_A1_offenders.txt`. Offender list is **empty** (18 → 0).

### A2. Re-ran the author's proof script into my own output file

```
python test-runs/ci_repair/prove_rng_equality.py test-runs/verify/task10_A2_author_equality.json
-> exit=0 ; stdout ends "ALL_EQUAL"
```

`all_equal = True`; keys `all_equal, checks, draws_per_site, ledger_op_schedule_equal, ledger_ops,
scaffold_digests, unseeded_path`. Raw: `task10_A2_author_equality.txt`, `task10_A2_author_equality.json`.

### A3. My own bit-for-bit reconstruction of the pre-commit stream

I did **not** use the author's harness for this. `test-runs/verify/check_rng_equality.py` extracts the
pre-commit module with
`git show 40138c9^:src/codontrace/life_loop/contact_atp_ledger.py` into
`test-runs/verify/_old_contact_atp_ledger.py`, loads it under a distinct module name with
`importlib.util.spec_from_file_location`, and drives old and new in lockstep:

```
python test-runs/verify/check_rng_equality.py   -> exit=0
extracted pre-commit module -> test-runs/verify/_old_contact_atp_ledger.py
pre-commit source sha256 = <printed>
=== RNG EQUALITY SUMMARY ===
failures: none
```

Coverage — **512 draws per call site**, mixed methods (`random`, `randrange(stop)`,
`randrange(start, stop)`, `choice`, `shuffle`, `sample`), six seeds:

| Path | Seeds | Draws/call site | Result |
| --- | --- | --- | --- |
| `random.Random(s)` vs `StdlibSeedRNG(seed=s)` | 0, 1, 7, 11, 401, 5501, 2147483647 | 512 × 6 call sites | all equal |
| `__post_init__` re-seeded path `int(rng_seed)` | 0, 3, 401 | 512 × 6 call sites | all equal |
| unseeded `Random(None)` vs `StdlibSeedRNG(seed=None)` (state forced, then compared) | — | 64 × 6 call sites | all equal |
| ledger RNG re-seed drain (`ledger._rng = ...(seed=99)`) | 0, 7, 401 | 512 `random()` | all equal |

Real ledger operations that consume the stream, both modules lockstep — `scramble_contacts`
(degree-preserving **and** free), `reallocate_contact_budget`, `matched_random_edge`,
`reward_explore_eps`, `sham_cue_predphase`, `update_reactive_ledger` — produced identical return
values and identical post-schedule `snapshot()`/`digest()` for seeds 0/7/401. Every scaffold builder
(`build_engine_scaffold_ledger`, `build_idea1/2/3/5/6_{scaffold,smoke}_ledger`, `build_smoke_ledger`)
matched byte-for-byte at seeds 0 and 7.

### A4. No recorded campaign number moved

```
git diff --name-only 40138c9~1 913f18e -- docs tests outputs   -> (empty)
git diff --name-only 40138c9~1 913f18e                          -> 8 source files only
```

The two commits touch `src/codontrace/engine_runtime.py`, `src/codontrace/rng.py`,
`src/codontrace/life_loop/contact_atp_ledger.py` and the five
`src/codontrace/genesis/campaigns/discovery_q_20260928_idea{1,2,3,5,6}.py`. **No doc, no test, no
recorded outputs file changed**, so no recorded campaign number moved. (The owner-approved
`vt_spatial_factorial` re-lock `6c979f5` is a separate, earlier, documented change; the 12/12 pin
identity check in B3 confirms the current values.)

---

## B. `913f18e` — fork state restoration

### B1. Identity cells at `913f18e` — 6/6 PASS

`test-runs/verify/check_fork_identity.py` (seed 31), K ∈ {0, 3} × N ∈ {1, 2, 5}, comparing the
`from_fork` continuation against the original engine's tail on four axes:

```
python test-runs/verify/check_fork_identity.py --tree 913f18e   -> exit=0
=== identity cells 6/6 PASS ===
  K=0 N=1 index=True tick=True gen=True pop=True
  K=0 N=2 index=True tick=True gen=True pop=True
  K=0 N=5 index=True tick=True gen=True pop=True
  K=3 N=1 index=True tick=True gen=True pop=True
  K=3 N=2 index=True tick=True gen=True pop=True
  K=3 N=5 index=True tick=True gen=True pop=True
```

Raw: `task10_B1_identity_913f18e.txt`. All four axes on all six cells.

### B2. UNPATCHED negative control — run by me, 0/6

I extracted a pristine tree at the parent commit and ran the **same** script against it:

```
git worktree add --detach E:\_ci_verify\neg40138c9 40138c9
set PYTHONPATH=E:\_ci_verify\neg40138c9\src
python test-runs/verify/check_fork_identity.py --tree 40138c9_UNPATCHED  -> exit=1
=== identity cells 0/6 PASS ===
  K=0 N=1 index=True  tick=False gen=False pop=False
  K=0 N=2 index=True  tick=False gen=False pop=False
  K=0 N=5 index=True  tick=False gen=False pop=False
  K=3 N=1 index=True  tick=False gen=False pop=False
  K=3 N=2 index=True  tick=False gen=False pop=False
  K=3 N=5 index=True  tick=False gen=False pop=False
```

Raw: `task10_B2_identity_40138c9_negctrl.txt`. This is the falsifier: the defect is real and
`913f18e` is what closes it. Note the index axis passes even unpatched (that was `44a06f4`) — only
tick/generation/population digests fail on all six cells, exactly the four un-restored object families.
The scratch worktree was removed afterwards (`git worktree list` shows only the main checkout).

### B3. Locked pin / replay / manifest suites — byte-identical

```
python -m pytest -q tests/platform/pin tests/test_host_parasite_phase25.py \
  tests/test_host_parasite_hard_regressions.py::test_hc5_he_hp_locked_pack_schema_integrity
-> ........  [100%], exit=0

python -m pytest -q tests/test_replay.py tests/test_replay_hash.py \
  tests/test_replay_snapshot_continuity.py tests/test_timeline_replay.py \
  tests/test_export_import.py tests/test_genesis_phase_j_replay_ci.py \
  tests/test_genesis_phase2_manifest_validation_strict.py \
  tests/genesis_gates/test_run_manifest_replay_bundle.py \
  tests/genesis_gates/test_post_review_manifest_replay_review_rule_contracts.py tests/test_rng.py
-> .........................................  [100%], exit=0   (41 passed)

python test-runs/verify/check_pins_vs_434bbd1.py   -> exit=0, "=== PINS: 12/12 PASS ===", failures: none
```

Raw: `task10_B3_pins.txt`, `task10_B3_replay_manifest.txt`, `task10_B3_pin_identity.txt`.
12/12 pinned artifacts (the three BAIC pins, `locked_campaign_digests.json`, HE01 prereg +
amendments 02–05 + LOCK, HE02 results/contrasts) are LF-normalised byte-identical to `434bbd1` and
still match their committed constants. **No locked pin moved and none was re-locked by these commits.**

`ruff check src tests` → exit 0 "All checks passed!"; `compileall -q src tests` → exit 0
(`task10_C_ruff.txt`, `task10_C_compile.txt`).

### B4. Documented residual — probed honestly, plus one contract regression I found

`test-runs/verify/check_fork_isolation_residual.py` (raw `task10_B4_fork_isolation.txt`), one captured
payload, two arms built from it:

```json
{
  "payload_json_safe": false,
  "payload_json_error": "TypeError: Object of type PopulationState is not JSON serializable",
  "payload_has_live_objects_key": true,
  "fork_isolation": {"element_grid": "shared_reference", "nexus_layer": "deepcopy",
                     "population": "shared_reference", "world": "deepcopy"},
  "fork_state_exact": false,
  "arm_a_population_is_arm_b_population": true,
  "arm_a_population_is_parent_population": true,
  "arm_a_element_grid_is_arm_b_element_grid": true,
  "arm_a_world_is_arm_b_world": false,
  "arm_a_population_moved_after_its_tick": true,
  "arm_b_population_moved_when_arm_a_advanced": false,
  "arm_a_matches_original_tail": true,
  "arm_b_matches_original_tail": true
}
```

Read-out, stated plainly:

* **`fork_state_exact = false`, and the map is accurate.** `population` (and `element_grid`) are
  *shared references* — both arms and the parent engine point at the same Python object. `world` and
  `nexus_layer` are genuinely deep-copied. The commit message claims exactly this; my probe confirms
  it and does not overstate it.
* **The sharing is inert under the intended workflow.** `run_ticks` rebinds `runner.population` to a
  fresh `PopulationState` each generation (via `step_generation`), so advancing arm A does **not**
  move arm B: `arm_b_population_moved_when_arm_a_advanced = false`, and both arms still reproduce the
  original tail exactly. In-place mutation of the shared `PopulationState` itself would still leak —
  which is why the manager's `fork_isolation` / `fork_state_exact` disclosure is the right mitigation
  and why D-2 must assert isolation operationally.
* **Contract regression, new finding:** `capture_fork()` is annotated `-> dict[str, JsonValue]` and
  previously returned a JSON-serialisable payload. Since `913f18e` it embeds live objects
  (`live_objects`), and `json.dumps(payload)` now raises
  `TypeError: Object of type PopulationState is not JSON serializable`. Nothing in the repo serialises
  a fork payload today (the only two references are the definitions in `engine_runtime.py:297,342`),
  so no test is red and no recorded number moves — but any audit/disk hand-off of a fork payload will
  break. The honest options are (a) record the in-memory-only nature in the docstring instead of
  claiming a `JsonValue` return (smallest, no code change), or (b) keep a serialisable reduced
  payload alongside `live_objects` for audit. `fork_isolation` / `fork_state_exact` are also only set
  on the live-object path, so a reduced-payload fork has neither attribute.

**Practical consequence for D-2.** The fork machinery now reproduces the original continuation exactly
(6/6 cells), so D-2 can branch arms from one checkpoint and compare them against the same reference
stream — the identity requirement D-2 needs is met. But because arms *share* the population and
`element_grid` objects, D-2 must not assume memory-level isolation: each arm has to be measured by its
own captured results (as the manager states), any code that mutates a `PopulationState`/`ElementGrid`
in place must do so per arm, and fork payloads must stay in-process unless option (b) above is taken.
The identity fix is sound; the isolation claim is deliberately not made, and my probe agrees.

---

## Verdict

**ACCEPT.**

* `40138c9`: pre-commit and post-commit streams are bit-identical over 512 draws per call site across
  six seeds, the mixed-method battery, the unseeded path, the re-seeded `__post_init__` path, the
  stream-consuming ledger operations and every scaffold builder; the static RNG gate is green with an
  empty offender list; no documented or recorded number changed.
* `913f18e`: the six identity cells pass 6/6 at `913f18e` and fail 0/6 on the unpatched negative
  control I ran myself, so the fix is load-bearing and not a no-op.
* Locked pin/replay/manifest suites green; 12/12 pins LF-byte-identical to `434bbd1`; no pin re-locked;
  ruff and compileall clean.
* Residual recorded, not fixed (no repo write): `fork_state_exact = false` with `population` /
  `element_grid` shared by reference, plus the new observation that `capture_fork()` is no longer
  JSON-serialisable despite its `dict[str, JsonValue]` annotation. Neither invalidates the fix; the
  second is the one item I recommend the manager address before any fork payload is written to disk.

No push performed. Repository untouched (`HEAD=02cc725`, clean tree, scratch worktree removed).
