# CI repair and executed-test status — 2026-09-29

**Owner-facing record.** Every claim below is tied to a commit hash or a file path. The
repository is `codontrace-genesis`, branch `main`, one working tree, no divergent branches and no
stashes at any point. The manager is the single writer; the Lead performs every push.

## 1. Commit chain on `main` and what each fixed

| Commit | Fix |
|---|---|
| `44a06f4` | Tick-index double count: `GenesisEngine.run_ticks` used `index=base + len(self._tick_results)` while `base` already contains `len(self._tick_results)`, so any engine advanced by more than one call produced indices 0, 2, 4, 6, 8 … . Now `index=base + index`; `base` and `capture_fork.tick_index` untouched. |
| `6187ff4` | Opt-in `ecology=persistence_safe` profile in `build_idea4_engine_spec`; the standing default is byte-identical. |
| `c4d8638` | Banned-token hygiene: `life_loop/engine_ledger_coupler.py` docstring "No infection physics" → "No domain-specific transmission physics"; `engine_runtime.py` and `discovery_q_20260928_jsonl_engine.py` reworded to drop the literal `pickle`. |
| `d421104` | RQ-3 arm-level opt-in `antagonist_ecology` (`"standing"` default, `"population"` opt-in) plus the heritable `AntagonistPopulation` with realised per-seat income. |
| `cc675a4` | `AntagonistPopulation.founders(..., maintenance_cost: float | None = None)`; `None` returns the previously built object unchanged. |
| `40138c9` | RNG hygiene: stream-preserving backend in `src/codontrace/rng.py` and migration of the seven direct stdlib-random callers (`life_loop/contact_atp_ledger.py`, `discovery_q_20260928_idea1/2/3/5/6.py`). |
| `913f18e` | `from_fork` state restoration: `qd_archive`, `nexus_layer`, `element_grid` and per-organism `action_runtime_config` / `causal_graph` / `ribosome`. |

Earlier commits in the same chain, already pushed: `d400687` (ruff B007), `cff84cd` (LF-normalising
pin hashing), `49750b1` (RQ-1 route addendum), `6c979f5` (owner-approved `vt_spatial_factorial`
re-lock), `434bbd1` (causal-tape estimator attribution).

## 2. Root cause of the CI red state inherited at the start

The workflow had **39 of 39 visible runs red**. The authoritative full pytest at `434bbd1` was
**5 failed / 2334 passed / 1 skipped / 1 xfailed in 2048 s** (run `36569138689`, job
`109408436292`). The five node ids and their causes:

| Node id | Cause | Fixed by |
|---|---|---|
| `tests/genesis_gates/test_post_review_manifest_replay_review_rule_contracts.py::test_run_ticks_batch_seed_schedule_matches_single_steps` | tick-index double count | `44a06f4` |
| `tests/test_life_loop_attachment_energy.py::test_banned_tokens_absent_from_new_life_loop_modules` | the token `infection` in the `engine_ledger_coupler.py` docstring | `c4d8638` |
| `tests/test_life_loop_contact_inherit.py::test_banned_tokens_absent_from_new_life_loop_modules` | same docstring token | `c4d8638` |
| `tests/test_life_loop_populations.py::test_banned_tokens_absent_from_life_loop_sources` | same docstring token | `c4d8638` |
| `tests/test_rng.py::test_no_direct_random_usage_outside_rng_module` | 20 literal offenders: 2 were comments/docstrings (`engine_runtime.py`, `discovery_q_20260928_jsonl_engine.py`) and 18 were real RNG bypasses in `life_loop/contact_atp_ledger.py` and `discovery_q_20260928_idea1/2/3/5/6.py` | `c4d8638` (2) and `40138c9` (18) |

A separate, real defect found during the repair (not part of that red list): a `from_fork`
continuation diverged from the original engine's continuation because four object families were
not restored; fixed by `913f18e`.

## 3. Evidence file map

| Evidence | File |
|---|---|
| Independent verification and ACCEPT of `44a06f4` (batch(N) == N × `run_ticks(1)` for N = 1, 5, 17; fork offset honoured; 12/12 pins byte-identical) | `test-runs/verify/VERIFICATION_REPORT.md` |
| RNG equality proof (8 call sites × 32 draws, mixed-method sequences, ledger schedule and scaffold digests, `all_equal`) | `test-runs/ci_repair/rng_equality_out.json`; manager re-run `test-runs/ci_repair/rng_equality_manager.json`, `e1_equality.txt` |
| Persistence opt-in measurement (standing `final_n_alive 0`, 11 zero-census boundaries → `persistence_safe` 2, 0) | `test-runs/d2/logs/manager_persistence_probe_20260929.txt` |
| Fork identity proof and its negative control | `test-runs/d2/logs/task7_fork_proof.json`; manager re-run `e3_proof.txt` (6/6 cells, `CELLS_FAILED=0`) |
| Pin/replay byte-identity after the tick-index fix and after the fork fix | `jobA_pins.txt` (66 passed, 0 failed), `e3_suites.txt` (52 passed, 0 failed) |
| Banned-token gates and the exact remaining-offender list | `roundD_banned.txt`, `roundD_offenders.txt`, `e1_rng.txt` |
| RQ-3 opt-in ledger: surplus realised, 50 generations, zero empty rosters | `rd2_on.txt`, `rd2_on50.txt`, `reconcile_on.txt` |
| Canonical LF pin proof | `mgr_pin_verify.txt` |

## 4. Executed-test inventory

* Release-critical set: the four red classes above plus the pin, replay and manifest suites.
* Three banned-token gates: `tests/test_life_loop_attachment_energy.py`,
  `tests/test_life_loop_contact_inherit.py`, `tests/test_life_loop_populations.py` — green after
  `c4d8638`.
* `tests/test_rng.py` — green after `40138c9`, offenders 18 → 0.
* `tests/platform/pin` + HE-HP phase families + HC5 + replay/manifest: 66 passed / 0 failed after
  `44a06f4`; 52 passed / 0 failed after `913f18e`; no locked pin moved in either run.
* `tests/closed_loop` on the RQ-3 opt-in tree: 23 passed / 0 failed with the opt-in OFF.
* Science runs (recorded in their own packs): CausalTape heavy1 with 121500 paired seeds; the RQ-1
  pilot pack; the RQ-1 confirmatory partial with 2 of 8 sealed seeds executed and its effect
  interval as recorded in the RQ-1 pack (`test-runs/rq1/`).

## 5. Status flags that must stay true

* The locked campaign pins were **never re-locked for these CI fixes**. The only frozen artifact
  change in this campaign is the owner-approved `vt_spatial_factorial` re-lock in `6c979f5`,
  which remains separate and is documented in
  `docs/campaigns/discovery_questions_20260928/FROZEN_DIGEST_RELOCK_20260929.md`.
* No threshold, seed, locked decision or claim flag was touched; `hypothesis_supported` and
  `red_queen_proved` stay `false`.
* The Mypy step inside the continue-on-error lint job is still red and is explicitly allowed to
  fail by `.github/workflows/ci.yml`.

## 6. CI run and job identifiers

* `6187ff4` — Core smoke **SUCCESS** on the six finished jobs (macOS 3.11/3.12/3.13/3.14, Windows
  3.12/3.13/3.14); Windows 3.11 still running at the time of writing.
* `913f18e` — run id **pending**; to be filled in by the Lead's final push note.
* Full-pytest run quoted in §2: run `36569138689`, job `109408436292`.
