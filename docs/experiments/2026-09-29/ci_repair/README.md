# CI repair record — 2026-09-29

**Owner draft for import.** Destination in the repository:
`codontrace-genesis/docs/experiments/2026-09-29/ci_repair/README.md`. Paths below
are repository-relative unless stated otherwise; the files this record describes
live in the same directory as this README. The supporting narrative is
`docs/ci/CI_REPAIR_AND_TEST_STATUS_2026-09-29.md` and the regenerated acceptance
transcripts are in `docs/ci/evidence/`.

## 1. What this record is

This is the **maintenance history of a continuous-integration repair**, not a
scientific experiment. It records why the `Full pytest` workflow job had been red
for every visible run, what was changed to fix it, and — the only part with
evidentiary value — the proof that none of the fixes moved a recorded number, a
locked digest or a claim flag.

There is no hypothesis, arm, effect size or interval here. The invariants held
throughout were: `hypothesis_supported` and `red_queen_proved` stay `false`; no
threshold, seed, gate or refusal was relaxed; no locked campaign pin was
re-locked (see §8).

## 2. Inherited state

`Full pytest` (`python -m pytest tests --disable-plugin-autoload`, see
`.github/workflows/ci.yml`) had failed on every visible run of the workflow —
**39 of 39 red** — and was equally red at `49750b1`, `6c979f5` and `434bbd1`, so
the failures predate the repair session. The authoritative pre-fix result quoted
in `docs/ci/CI_REPAIR_AND_TEST_STATUS_2026-09-29.md` §2 is:

```text
commit 434bbd1 — 5 failed / 2334 passed / 1 skipped / 1 xfailed in 2048 s
GitHub Actions run 36569138689, job 109408436292
```

## 3. Root causes (five failing node ids)

| Node id | Root cause | Fixed in |
|---|---|---|
| `tests/genesis_gates/test_post_review_manifest_replay_review_rule_contracts.py::test_run_ticks_batch_seed_schedule_matches_single_steps` | `GenesisEngine.run_ticks` built the tick index as `base + len(self._tick_results)` while `base` already contained `len(self._tick_results)`, so advancing an engine in more than one call produced indices 0, 2, 4, 6, … instead of 0, 1, 2, 3, … . The seed schedule was already correct: generation digests were unchanged, and only `GenesisTickResult.index` and the digests derived from it moved. | `44a06f4` |
| `tests/test_life_loop_attachment_energy.py::test_banned_tokens_absent_from_new_life_loop_modules` | the literal token `infection` in a docstring in `src/codontrace/life_loop/engine_ledger_coupler.py` | `c4d8638` |
| `tests/test_life_loop_contact_inherit.py::test_banned_tokens_absent_from_new_life_loop_modules` | same docstring token | `c4d8638` |
| `tests/test_life_loop_populations.py::test_banned_tokens_absent_from_life_loop_sources` | same docstring token | `c4d8638` |
| `tests/test_rng.py::test_no_direct_random_usage_outside_rng_module` | 20 literal offenders of the static scan (below) | `c4d8638` (2) and `40138c9` (18) |

### The RNG scan in detail

`tests/test_rng.py` scans every `.py` file under `src/codontrace/` **except
`rng.py`** for the literal markers `import random`, `from random`, `random.`,
`Random(` and `pickle`. At the pushed tip there were **20 offender markers in 8
files**: **2 cosmetic** — the word `pickle` inside a docstring in
`src/codontrace/engine_runtime.py` and inside a comment in
`src/codontrace/genesis/campaigns/discovery_q_20260928_jsonl_engine.py` — and
**18 real RNG bypasses**, the standard library's `random.Random` constructed
directly in `src/codontrace/life_loop/contact_atp_ledger.py` (the import plus
three construction sites) and in the five campaign modules
`src/codontrace/genesis/campaigns/discovery_q_20260928_idea{1,2,3,5,6}.py` (a
function-local `import random as _random` plus `_random.Random(...)` each). The
rule being enforced is stated in `src/codontrace/rng.py`: all project randomness
must flow through `codontrace.rng`.

## 4. What was changed, and where

| Commit | Change (files) | Acceptance command | Recorded result |
|---|---|---|---|
| `44a06f4` | tick-index fix, `index=base + index` in `src/codontrace/engine_runtime.py` (1 line) | `python -m pytest tests/genesis_gates/test_post_review_manifest_replay_review_rule_contracts.py -q` | `docs/ci/evidence/tick_index_test_at_1355b60.txt` — 7 passed |
| `c4d8638` | reword the domain tokens flagged by the hygiene gates: `src/codontrace/life_loop/engine_ledger_coupler.py`, `src/codontrace/engine_runtime.py`, `src/codontrace/genesis/campaigns/discovery_q_20260928_jsonl_engine.py` | `python -m pytest tests/test_life_loop_attachment_energy.py tests/test_life_loop_contact_inherit.py tests/test_life_loop_populations.py -q` | `docs/ci/evidence/banned_tokens_at_1355b60.txt` — 3 passed |
| `40138c9` | new `StdlibSeedRNG` in `src/codontrace/rng.py` plus migration of `life_loop/contact_atp_ledger.py` and the five idea modules (7 files, +143/−14) | `python -m pytest tests/test_rng.py -q`; `python -m ruff check src tests` | `docs/ci/evidence/rng_scan_at_1355b60.txt` (4 passed), `rng_offenders_at_1355b60.txt` (`offender_count=0`), `ruff_at_1355b60.txt` (`All checks passed!`) |
| `913f18e` | restore the full fork state in `from_fork` in `src/codontrace/engine_runtime.py`: `qd_archive`, `nexus_layer`, `element_grid` and per-organism `action_runtime_config`, `causal_graph`, `ribosome` | fork identity check over K ∈ {0, 3} × N ∈ {1, 2, 5} | `docs/ci/evidence/fork_identity_cells_at_1355b60.txt` — 6/6 PASS, `CELLS_FAILED=0` |
| `01ee4a2` | make the fork payload contract explicit; add `tests/test_fork_audit_payload.py` | `python -m pytest tests/test_fork_audit_payload.py -q` | `docs/ci/evidence/fork_audit_tests_at_1355b60.txt` — 3 passed |
| `76cbf49` | isolate fork branches and report the branch's actual state; `engine_runtime.py`, `tests/test_fork_audit_payload.py`, new `tests/test_fork_branch_isolation.py` (3 files, +348/−45) | `python -m pytest tests/test_fork_branch_isolation.py tests/test_fork_audit_payload.py -q` | fork-isolation evidence filed with the verification record; the per-file transcripts above are the in-repo copies |

Full-suite and pin evidence for the same tree:
`docs/ci/evidence/pin_replay_manifest_suites_at_1355b60.txt` — 52 passed, 0
failed on the pin / replay / manifest suites;
`docs/ci/evidence/ruff_at_1355b60.txt` — `All checks passed!`;
`docs/ci/evidence/compileall_at_1355b60.txt` — empty, i.e. `compileall` clean.

## 5. The RNG stream-preservation proof

`40138c9` was allowed to land only because it provably does not move a recorded
number. The mechanism is `StdlibSeedRNG` in `src/codontrace/rng.py`: it forwards
the seed **untouched** to the standard library's `random.Random(seed)` and exposes
`random`, `randrange`, `choice`, `shuffle`, `sample`, `fork`, `snapshot`,
`state_digest`, `getstate`/`setstate` and `draw_count`. Namespaced derivation (as
`RNGManager` uses) is deliberately *not* applied, because hashing the seed would
change every draw.

The proof script is `prove_rng_equality.py` in this directory, with raw output in
`rng_equality_out.txt` and `rng_equality_out.json`. Every value is compared by
`repr`, with no tolerance:

* **8 call-site seed expressions × 32 draws each**, in two schedules (a
  `random()`-only schedule and a mixed `random`/`randrange`/`choice`/`shuffle`
  schedule), comparing the pre-patch stream `random.Random(seed)` with the
  post-patch stream `StdlibSeedRNG(seed=seed)`;
* the **real ledger** driven through one fixed op schedule
  (`matched_random_edge`, `matched_random_edge(degree=2)`, `reward_explore_eps`,
  `reallocate_contact_budget`), legacy stream against new stream;
* the scaffold ledger digest for **seeds 0/1/7/11/401/5501**, the unseeded
  default path (`StdlibSeedRNG()` is OS-entropy seeded like `random.Random()`)
  and the re-seeded path.

`rng_equality_out.json` reports `"all_equal": true`, and its content is identical
to `rng_equality_manager.json` — the manager's **independent re-run of the same
script against the patched tree**. End to end, `campaigns_before.json` and
`campaigns_after.json` are the 20 scored cells of the five campaign modules at
seed 401 before and after the migration: byte-equal, SHA-256
`2394fd82f06a0557bbfb4d95adf75e40…` over the sorted cell payload, with equal
ledger digests. `verify_patch_applies_out.txt` records that the proposed patch,
applied to a fresh extraction of the tree, reproduces the verified patched tree
exactly (7/7 files, `PATCH_REPRODUCES_TREE: True`).

## 6. In-repo evidence layout

| File (this directory) | Role |
|---|---|
| `PROPOSED_CHANGE_rng_backend.patch` | appliable unified diff for `40138c9` (7 files); `git apply -p1` from the repository root |
| `INVENTORY.md` | root cause with file/line, design, proofs, acceptance commands |
| `prove_rng_equality.py` | the stream-equality proof; also archived as `docs/experiments/2026-09-29/verification/check_rng_equality.py` |
| `rng_equality_out.json`, `rng_equality_out.txt` | proof output (author) |
| `rng_equality_manager.json` | proof output (manager's independent re-run) |
| `campaigns_before.json`, `campaigns_after.json` | 20 scored campaign cells, before/after the migration |
| `snapshot_campaigns.py` | generator of the before/after campaign snapshots |
| `apply_rng_patch.py`, `make_rng_patch.py` | deterministic generator of the change and of the patch |
| `verify_patch_applies.py`, `verify_patch_applies_out.txt` | patch-application reproducibility check |
| `paatched_scratch_full_pytest.txt` | partial full-suite transcription of the patched tree (filename as produced) |
| `evidence_files.sha256` | `sha256  size  path` manifest for the files above |

The in-repo `evidence_files.sha256` hashes were computed on LF line endings, so a
Windows checkout with CRLF will not match them byte-for-byte without
normalisation; the same convention applies to `docs/ci/evidence/`.

## 7. CI outcome after the repair

On the pushed tips the workflow is green: **Core smoke 12/12 success** (Ubuntu,
macOS and Windows across Python 3.11–3.14) and **Full pytest 4/4 success**
(Ubuntu 3.11, 3.12, 3.13, 3.14). The only red step is **Mypy inside the
continue-on-error lint job**, which `.github/workflows/ci.yml` explicitly allows
to fail. Run and job identifiers for the pre-fix failure and the intermediate tip
`6187ff4` are in `docs/ci/CI_REPAIR_AND_TEST_STATUS_2026-09-29.md` §2 and §6.

## 8. Standing rule on pins

No locked pin was re-locked to make these fixes pass. The only frozen-artifact
change in this campaign is the **previously owner-approved `vt_spatial_factorial`
maintenance re-lock in `6c979f5`**, separate from the CI repair and documented in
`docs/campaigns/discovery_questions_20260928/FROZEN_DIGEST_RELOCK_20260929.md`.

## 9. Replay

Run from the repository root with `PYTHONPATH=src` (dependencies: `ruff`,
`pytest`). The paths are the ones the evidence was produced with; on a clean
checkout substitute this record's own copies under
`docs/experiments/2026-09-29/ci_repair/` for the patch and proof scripts.

```bash
python -m pytest tests/genesis_gates/test_post_review_manifest_replay_review_rule_contracts.py -q   # 1 tick-index contract
python -m pytest tests/test_life_loop_attachment_energy.py tests/test_life_loop_contact_inherit.py tests/test_life_loop_populations.py -q   # 2 banned tokens
python -m pytest tests/test_rng.py -q                                                               # 3 RNG scan: 4 passed, 0 offenders
python -m ruff check src tests && python -m compileall -q src                                        # 4 lint and compile
python -B docs/experiments/2026-09-29/ci_repair/prove_rng_equality.py rng_equality_replay.json      # 5 expect "all_equal": true
python -B docs/experiments/2026-09-29/ci_repair/snapshot_campaigns.py campaigns_replay.json 401      # 6 needs the patch applied
python -B docs/experiments/2026-09-29/ci_repair/verify_patch_applies.py <baseline> <patched> <scratch> docs/experiments/2026-09-29/ci_repair/PROPOSED_CHANGE_rng_backend.patch
```

## 10. What this record does not show

Nothing about the science. It shows only that the CI repair landed, that the
affected suites and gates are green, and that no recorded draw, campaign digest or
locked pin moved as a result. The scientific results are recorded separately
under `docs/experiments/2026-09-29/`.

## References

* Python Software Foundation, *random — Generate pseudo-random numbers* (CPython
  3.14 documentation; Mersenne Twister seeding and the version-stability guarantee
  for `random()`), accessed 2026-09-29. https://docs.python.org/3/library/random.html
* L. Schruben and B. Margolin, "Pseudorandom number assignment in statistically
  designed simulation and distribution sampling experiments", *Journal of the
  American Statistical Association* 73(363):504–514, 1978.
  https://doi.org/10.1080/01621459.1978.10480044 — the classical
  common-random-numbers argument behind preserving the stream across arms.
* Python Software Foundation, *pickle — Python object serialization*, accessed
  2026-09-29. https://docs.python.org/3/library/pickle.html — context for the
  static rule's token ban alongside JSON-safe state snapshots.
* K. Popper, *The Logic of Scientific Discovery*, 1959 — the falsification stance
  this repository applies to its own gates (*not verified in this session*; cited
  as standing practice, not as a source for any number above).
