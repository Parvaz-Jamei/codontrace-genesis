# 2026-09-29 verification record — independent verification of the CI-repair commits

## 1. What this record is

This directory is a **verification history, not an experiment**. It contains no new campaign, no new
measurement and no seed sweep. It records what an independent verifier checked about engine changes
that other members authored, the raw command output behind each check, and the defects the checks
found.

"Independent" has one concrete meaning here: **the verifier did not write the code it judges**. The
changes below were authored by `manager` (and one earlier change by an interval writer); the verifier
(`ci-green`) never held write access to `codontrace-genesis` while verifying. Every verification was
run from a committed tree with its own probes, its own before-state reconstruction from `git`, and —
where a fix was claimed — its own **unpatched negative control**. The author's own harness was never
accepted as evidence; when it is cited, it is cited as a *re-run into a verifier-owned file*, and the
verifier's independent reconstruction is what the verdict rests on. A verification that only
re-runs the author's script proves the script, not the code.

The verification of a change always had three parts: reproduce the claimed behaviour with the
verifier's own probe, falsify it by running the same probe on the tree **before** the fix, and show
that nothing else moved (locked pins, identity cells, lint, byte-compilation).

## 2. Round 1 — task-6: the tick-index fix (`44a06f4`)

Commit `44a06f4` changed one line of `src/codontrace/engine_runtime.py`
(`index=base + len(self._tick_results)` → `index=base + index`) so that an engine advanced by more
than one call no longer produced indices 0, 2, 4, 6, …

Verified and **ACCEPTED**:

* the contract test file
  `tests/genesis_gates/test_post_review_manifest_replay_review_rule_contracts.py` — 7 passed, exit 0
  (`docs/experiments/2026-09-29/verification/check1_gates.txt`);
* the verifier's own probe `docs/experiments/2026-09-29/verification/probe_tick_index.py`: `batch(N)` is identical to
  `N × run_ticks(1)` for N ∈ {1, 5, 17} on two different specs (seed 22 / `tick_count` 0 and seed 7 /
  `tick_count` 5), on tick index **and** tick digest, all six cells
  (`docs/experiments/2026-09-29/verification/probe_report.json`, `probe_out.txt`);
* falsifier for a lazy revert: `engine_used_index_driven_seeds = true`, i.e. the per-tick seed really
  is `spec.seed + absolute_index` and is distinguishable from a constant-seed schedule;
* `from_fork` still honours `_tick_offset` (seed 31, K=3: continuation indices `[3, 4]`, seeds
  `[34, 35]`);
* 12/12 locked pins byte-identical to `434bbd1` (`docs/experiments/2026-09-29/verification/check3_pin_identity.txt`);
* `ruff check src tests` exit 0 and `compileall` clean.

Full record: `docs/experiments/2026-09-29/verification/VERIFICATION_REPORT.md`, sha256
`c095e3069e20f4f25365ea7ec0260c03d0c688175388a62e9540434a80d39096`.

## 3. Round 2 — task-10: the RNG migration (`40138c9`) and fork restoration (`913f18e`)

### 3.1 `40138c9` — the stdlib RNG stream must not move

The commit routed seven direct `random` users (`life_loop/contact_atp_ledger.py` and five
`discovery_q_20260928_idea*` modules) through a new `StdlibSeedRNG` backend in
`src/codontrace/rng.py`, so that `tests/test_rng.py::test_no_direct_random_usage_outside_rng_module`
is satisfied without changing any draw.

Verified and **ACCEPTED**:

* `python -m pytest tests/test_rng.py -q` → 4 passed, exit 0; the verifier's own offender scan
  (`docs/experiments/2026-09-29/verification/scan_rng_offenders.py`, same rule as the test, `rng.py` exempt) reports
  `scanned=321 files, offenders=0` (`docs/experiments/2026-09-29/verification/task10_A1_offenders.txt`);
* the author's equality harness was re-run into a verifier-owned file
  (`docs/experiments/2026-09-29/verification/task10_A2_author_equality.json`, `all_equal = true`) — cited, not trusted;
* the load-bearing evidence is the verifier's **own reconstruction of the pre-commit stream**:
  `docs/experiments/2026-09-29/verification/check_rng_equality.py` extracts the pre-commit module with
  `git show 40138c9^:src/codontrace/life_loop/contact_atp_ledger.py`, loads it under a separate module
  name, and drives old and new in lockstep. **512 draws per call site**, six methods, seven seeds
  (0, 1, 7, 11, 401, 5501, 2³¹−1), the unseeded `random.Random(None)` path, the re-seeded
  `int(rng_seed)` path used by `ContactAtpLedger.__post_init__`, every stream-consuming ledger
  operation and all twelve scaffold builders — all bit-identical
  (`docs/experiments/2026-09-29/verification/check_rng_equality_out.txt`, `failures: none`);
* no recorded campaign number moved: `git diff --name-only 40138c9~1 913f18e -- docs tests outputs`
  is empty, so the two commits touched source only.

### 3.2 `913f18e` — restoring the full fork state

The commit made a `from_fork` continuation byte-identical to the original engine's continuation by
restoring object families that the reduced payload had dropped.

Verified and **ACCEPTED**, including the negative control the author did not run:

* six identity cells at `913f18e` (K ∈ {0, 3} × N ∈ {1, 2, 5}), all four axes (tick index, tick
  digest, generation digest, population digest): **6/6 PASS**
  (`docs/experiments/2026-09-29/verification/task10_B1_identity_913f18e.txt`);
* the **unpatched negative control**, run by the verifier on a pristine tree extracted at `40138c9`:
  the same six cells give **0/6** — index passes, tick/generation/population digests fail on every
  cell (`docs/experiments/2026-09-29/verification/task10_B2_identity_40138c9_negctrl.txt`). The fix is load-bearing;
* locked pin / replay / manifest suites green (8 passed; 41 passed), 12/12 pins LF-byte-identical to
  `434bbd1`, no pin re-locked; ruff and compileall clean;
* the documented residual was probed honestly: `fork_state_exact = false` with `population` and
  `element_grid` reported as `shared_reference`, while an incremental `run_ticks` did not leak between
  arms. That residual is the finding that Round 3 turned into a repair task.

Full record: `docs/experiments/2026-09-29/verification/VERIFICATION_TASK10_REPORT.md`, sha256
`521d8738c78d3be342080cd0e6a4486e22b6cf7d98d26472af1742bfaaacf5f9`.

## 4. Round 3 — task-14: fork branches really isolated, audit no longer false

The external reviewer found that two branches built from one `capture_fork()` payload shared the same
`PopulationState` **and** the same `ElementGrid` (and both were the parent's objects), that the branch
reported `fork_state_exact = False` while `fork_audit_payload()` reported `True`, and that
`tests/test_fork_audit_payload.py` asserted the false value.

Root cause, measured by the verifier (`test-runs/fork_isolation/diag_deepcopy.txt`, sha256
`b80d66a291fbbec960fc4e0bacfb8d21803c74629d83766ac91f8ba56d84b5c5`):

```
FAIL deepcopy population: TypeError: cannot pickle 'mappingproxy' object
FAIL deepcopy element_grid: TypeError: cannot pickle 'mappingproxy' object
  organism.ribosome / action_registry / action_runtime_config / causal_graph
  grid.registry
```

`copy.deepcopy` cannot pickle the read-only `mappingproxy` registries embedded in the organisms and
the grid. The old restore code caught that exception and **returned the parent's live object**, so
the sharing was silent; `capture_fork` in turn recorded a constant `"exact_state": True`, and the
audit converted that constant into `fork_state_exact`. The false report and the aliasing are the same
swallowed exception.

Repair, proposed as `test-runs/fork_isolation/PROPOSED_CHANGE.patch` (sha256
`5551405870104b6bb0739f17979ced79bb71fffc33048fc588d5bc1b6edfa259`, `git apply --check` exit 0 at
`e3eea30`) and landed by the manager as commit **`76cbf49`**
("fix(engine): isolate fork branches and report the branch's actual state"):

* `_immutable_tables()` pre-seeds the deepcopy memo with the reachable read-only mappingproxy tables,
  which are shared deliberately because they are immutable, while `population`, organisms, `world`
  and `element_grid` are copied for real (`_isolated_copy()`);
* `from_fork` now **refuses loudly** — `ConfigurationError("fork isolation refused: ...")` — instead
  of silently returning a shared reference when a copy cannot be made;
* `capture_fork` no longer carries a constant exactness claim; `_fork_isolation_map()` computes the
  isolation map **by trial** from the engine's own live objects, and `fork_audit_payload()` reports
  the branch's actual `fork_isolation` / `fork_state_exact`;
* `tests/test_fork_audit_payload.py` no longer asserts the false report, and the new
  `tests/test_fork_branch_isolation.py` is the discriminating test: distinct population and element
  grid per branch; in-place ATP, `vitae_store` and grid-cell mutation in arm A leaves arm B and the
  parent unchanged and conversely; and a constant-detector forces the copier to fail and requires
  `fork_state_exact is False` plus a loud refusal.

Before / after, same probes (`test-runs/fork_isolation/UNPATCHED_tests.txt`, sha256
`883a59a954845c3ba72ae1c1d95d7677eeef39c2846ea7181397f7b7289af67d`, and `patched_tests.txt`, sha256
`bfce81a920a305e888c2d21f12eb35beb7c515e88d5d692d6df4756a46f89a0e`):

| Observation | unpatched (`e3eea30`) | patched / `76cbf49` |
| --- | --- | --- |
| discriminating tests | 6 failed, 1 passed | 7 passed |
| `arm_a_population_is_arm_b_population` | true | false |
| `arm_a_element_grid_is_arm_b_element_grid` | true | false |
| `arm_a_population_is_parent_population` | true | false |
| isolation map for `population` | `shared_reference` | `deepcopy` |
| `fork_state_exact` | false (audit said true) | true |
| identity cells K∈{0,3} × N∈{1,2,5} | 6/6 | 6/6 |
| locked pins vs `434bbd1` | 12/12 | 12/12 |
| `from_fork` cost (4 organisms, 32 cells) | 19.95 ms | 107.91 ms |

The cost is the honest price of copying the population and grid instead of aliasing them; ~108 ms per
branch is negligible for the handful of arms D-2 needs. The committed `76cbf49` was re-verified
independently at HEAD: `tests/test_fork_audit_payload.py` + `tests/test_fork_branch_isolation.py` →
7 passed (`test-runs/fork_isolation/HEAD76cbf49_tests.txt`), residual flags as above
(`HEAD_residual.txt`), pins 12/12 (`HEAD_pins.txt`).

## 5. Adversarial method (the rules the rounds followed)

1. **Own probes.** Every claim was reproduced with a script written by the verifier, under
   `docs/experiments/2026-09-29/verification/`. Author harnesses were re-run only into verifier-owned files and are labelled
   as such.
2. **Own before-state.** Where "preserves the old stream" was claimed, the old code was extracted
   from git (`git show <sha>^:<path>`) and loaded as a separate module; nothing was taken on trust.
3. **Unpatched negative control.** Where a fix was claimed, the same probe was run on a pristine
   tree before the fix, so a no-op fix could not pass. `913f18e` (0/6 vs 6/6) and task-14
   (6 failed vs 7 passed) both carry this control.
4. **Constant detectors.** A reported flag is only trusted if a test can flip it: the task-14 audit
   test forces the copier to fail and requires the report to change.
5. **Nothing-else-moved.** Locked pin identity (12/12 vs `434bbd1`), identity cells, `ruff` and
   `compileall` were re-run at every stage, plus `git diff --name-only … -- docs tests outputs` to show
   no recorded number moved.

## 6. Raw evidence files and how to re-run

Environment for every command: `PYTHONPATH=<repo>\src`, `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`,
output captured with `cmd.exe /c "... > file 2>&1"`, then read back.

| File | sha256 | Re-run |
| --- | --- | --- |
| `docs/experiments/2026-09-29/verification/check1_gates.txt` | `bfce81a9…89a0e` | `python -m pytest -q tests/genesis_gates/test_post_review_manifest_replay_review_rule_contracts.py` |
| `docs/experiments/2026-09-29/verification/probe_report.json` | `c25f820e…d1b5d0e` | `python docs/experiments/2026-09-29/verification/probe_tick_index.py` |
| `docs/experiments/2026-09-29/verification/check3_pin_identity.txt` | `38a315a1…2765e5` | `python docs/experiments/2026-09-29/verification/check_pins_vs_434bbd1.py` |
| `docs/experiments/2026-09-29/verification/check5_standing.txt` | `10adfdd9…48b4b` | `python docs/experiments/2026-09-29/verification/check_standing_identity.py` |
| `docs/experiments/2026-09-29/verification/check_rng_equality_out.txt` | `1c071563…d89b76` | `python docs/experiments/2026-09-29/verification/check_rng_equality.py` |
| `docs/experiments/2026-09-29/verification/task10_A1_offenders.txt` | `d0c9a2f5…dea8b5` | `python docs/experiments/2026-09-29/verification/scan_rng_offenders.py` |
| `docs/experiments/2026-09-29/verification/task10_A2_author_equality.json` | `016142cf…94aa170` | `python docs/experiments/2026-09-29/ci_repair/prove_rng_equality.py <out>` (author harness, re-run) |
| `docs/experiments/2026-09-29/verification/task10_B1_identity_913f18e.txt` | `393b0fdf…1c5dd` | `python docs/experiments/2026-09-29/verification/check_fork_identity.py --tree 913f18e` |
| `docs/experiments/2026-09-29/verification/task10_B2_identity_40138c9_negctrl.txt` | `799af960…ffcdd5` | same probe with `PYTHONPATH` at a pristine `40138c9` tree |
| `docs/experiments/2026-09-29/verification/task10_B4_fork_isolation.txt` | `2bcd22ee…d827b` | `python docs/experiments/2026-09-29/verification/check_fork_isolation_residual.py` |
| `docs/experiments/2026-09-29/verification/VERIFICATION_REPORT.md` | `c095e306…39096` | record of Round 1 |
| `docs/experiments/2026-09-29/verification/VERIFICATION_TASK10_REPORT.md` | `521d8738…cf5f9` | record of Round 2 |
| `test-runs/fork_isolation/PROPOSED_CHANGE.patch` | `55514058…dfa259` | `git apply --check …` at `e3eea30` (now superseded by `76cbf49`) |
| `test-runs/fork_isolation/diag_deepcopy.txt` | `b80d66a2…4b5c5` | `python test-runs/fork_isolation/diag_deepcopy.py` |
| `test-runs/fork_isolation/UNPATCHED_tests.txt` | `883a59a9…9af67d` | `python -m pytest -q test-runs/fork_isolation/test_fork_branch_isolation.py …` at `e3eea30` |
| `test-runs/fork_isolation/patched_tests.txt` | `bfce81a9…89a0e` | same files on the patched tree |
| `test-runs/fork_isolation/bench_unpatched.txt` / `bench_patched.txt` | `481cddd2…87f59f` / `d5c1a2f2…7ce20` | `python test-runs/fork_isolation/bench_fork.py` on each tree |
| `test-runs/fork_isolation/HEAD76cbf49_tests.txt` | `bfce81a9…89a0e` | `python -m pytest -q tests/test_fork_audit_payload.py tests/test_fork_branch_isolation.py` at HEAD |
| `test-runs/fork_isolation/HEAD_residual.txt` | `4c3f34c5…2b1e3` | `python docs/experiments/2026-09-29/verification/check_fork_isolation_residual.py` at HEAD |
| `test-runs/fork_isolation/HEAD_pins.txt` | `38a315a1…2765e5` | `python docs/experiments/2026-09-29/verification/check_pins_vs_434bbd1.py` at HEAD |

Hashes are of the files as archived beside this README; a re-run on a different commit will
legitimately produce different bytes for the observables and the same PASS/FAIL structure.

## 7. Limits — what was not verified, and what remains open

* **Not verified here:** anything outside the three rounds above — no science gate, no claim ceiling,
  no multi-seed campaign and no D-2 measurement was re-derived; the pin check covers the twelve
  artifacts the suites pin, not every number in the repository.
* **Full-suite gate:** the whole-suite run on the patched/committed state is still in progress at the
  time of writing and is not summarised in this record. The evidence archived here is focused: the
  affected suites, the verifier's probes and the pin identity. The full-suite summary line is the one
  claim in this record that is deliberately left open.
* **Residual flagged, not fixed:** `capture_fork()` returns an **in-memory-only** payload whose
  `live_objects` embed live instances, so `json.dumps(payload)` raises `TypeError`. This is now
  documented in the docstring and the serialisable hand-off is `fork_audit_payload()`, but no test
  enforces that no caller serialises a live payload, and no reduced serialisable state is kept beside
  the live objects.
* **Cost not budgeted:** the isolation fix makes `from_fork` ~5× slower (19.95 ms → 107.91 ms for a
  4-organism, 32-cell state). No per-arm budget was set for D-2, and none should be inferred from this
  record.
* **Shared immutable tables by design:** branches still share the read-only element / action /
  ribosome / causal-graph registries. That sharing is intentional (they are immutable) and is not
  covered by the mutation tests, which exercise mutable state only.
* **Earlier owner-approved relock:** the `vt_spatial_factorial` re-lock (`6c979f5`) predates these
  rounds and was not re-verified here; the pin identity check in each round confirms the locked values
  did not move under the CI repairs.

## Limits recorded from the verification report

These are honest residuals, not defects to hide, and none of them blocks the landed
fixes.

1. **The in-memory-only contract is partly enforced already** (`fork_audit_payload()` since `01ee4a2` is the serialisable hand-off, the docstring states "Not JSON-serialisable", and the live-payload `TypeError` is asserted); what stays open: `fork_audit_payload()` is the serialisable
   hand-off, and `tests/test_fork_audit_payload.py` asserts that the live payload raises
   `TypeError` under `json.dumps`. No reduced serialisable state exists beside the live
   objects, and nothing guards a future caller from trying to serialise the live payload.
2. **`from_fork` cost rose** from about 19.95 ms to about 107.91 ms per branch
   (4 organisms / 32 cells) once real copying replaced aliasing. No per-arm compute
   budget is set for D-2.
3. **Branches still share the read-only `mappingproxy` registries by design.** The
   mutation tests do not cover those tables.
4. **The owner-approved `vt_spatial_factorial` re-lock (`6c979f5`) was independently verified and owner-approved before this round**
   and is documented separately, so it is a cross-reference rather than an open gate. The pin suites confirm those locked values did
   not move, and the re-lock is documented separately in
   `docs/campaigns/discovery_questions_20260928/FROZEN_DIGEST_RELOCK_20260929.md`.

**Content identity of the landed fix.** ci-green confirmed that the landed `76cbf49` is
content-identical to the patch it handed over: `git diff --no-index --numstat` reports no
differences, `src/codontrace/engine_runtime.py` is byte-identical by sha256, and the two
test files differ only in LF versus CRLF line endings under the repository's
`* text=auto`. The reviewer's isolation finding is therefore verified fixed on the pushed
tip, not merely claimed.
