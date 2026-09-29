# Task-7 report — `capture_fork`/`from_fork` continuation was not byte-identical

**Agent:** mechanism-test (D-2) · **Date:** 2026-09-29 · **Verdict:** root cause found, minimal fix
delivered, fix proven with a discriminating test **and** a negative control.
**Patch:** `docs/experiments/2026-09-29/d2_recovery_window/PROPOSED_CHANGE_fork.patch` — 68 diff lines, sha256 prefix `9d7e070d90aaf5d2`
**Raw evidence:** `docs/experiments/2026-09-29/d2_recovery_window/logs/task7_fork_identity.json`, `logs/task7_fork_proof.json`,
`logs/task7_probe.txt`, `logs/fork_patch_proof.txt`
**Generators:** `harness/d2_make_fork_patch.py` (patch text and the code exercised by the proof are
the same source strings), `probes/task7_fork_identity.py`

## 1. Falsifying observation (confirms both witnesses)

Seed 31, `GenesisExperimentSpec(tick_count=0)`. Original engine advanced to tick 3, fork captured,
original continued 2 ticks: tick digests `b08885d7a4b1`, `36e2a715fb40`. `from_fork` + 2 ticks:
`13fb2cf7e2fa`, `1b432e538781`. Tick **index** identity holds (`base = _tick_offset + len(...)`);
digest identity does not. Reproduced for K ∈ {0, 3} × N ∈ {1, 2, 5}: **all six cells mismatch** on
both the tick digest and the generation digest (`logs/task7_fork_identity.json`).

## 2. Root cause — five state objects are rebuilt instead of restored

`from_fork` built a fresh engine with `cls.from_spec(...)` and then overwrote only
`runner.population` (from `PopulationState.from_dict`) and `runner.world` (from `World2D.from_dict`).
Bisect at K = 3 (`logs/task7_fork_identity.json → bisect`):

| object | state at fork vs restored | effect |
|---|---|---|
| `engine.qd_archive` | digest `dfbb2e32…` vs `d712008f…` — **fresh archive** | `_apply_qd_parent_feedback` reorders parents differently → different generation result |
| `runner.nexus_layer` | digest `cb4b46bd…` vs `fa61b715…` — **fresh layer** | stigmergy state lost |
| `runner.population` | `to_dict()` compares equal, but the rebuilt organism differs in 3 attributes: `action_runtime_config`, `causal_graph`, `ribosome` | per-organism execution state lost |
| `runner.world` | rebuilt via `from_dict`; replaced by the live object in the repair | world bookkeeping |
| `element_grid` | rebuilt | substrate mirror state |

Repair bisect (runtime, no repo edit; same K = 3, N = 2):

| repair applied after `from_fork` | tick digests equal to original |
|---|---|
| none | no (`13fb2cf7e2fa`, `1b432e538781`) |
| `nexus_layer` + `qd_archive` + `element_grid` | no (`3c5a5602bfbb`, `74c47d6c0263`) |
| `population` object only | no (`28e9b22f911e`, `2112dca034e8`) |
| `population` + `world` + `nexus_layer` + `qd_archive` | **yes** (`b08885d7a4b1`, `36e2a715fb40`) |

So the checkpoint was missing *all* of: QD archive, stigmergy layer, world object, and the
per-organism fields that `PopulationState.to_dict()` does not carry.

## 3. Minimal fix (patch)

`src/codontrace/engine_runtime.py`:

* `capture_fork()` (line 297) — add a `"live_objects"` block carrying the live `population`,
  `world`, `nexus_layer`, `qd_archive`, `element_grid` and `"exact_state": True`.
* `from_fork()` (line 328) — when `live_objects` is present, attach them instead of rebuilding;
  each object is `copy.deepcopy`-ed **per restore** so two arms branched from one payload cannot
  alias each other, and an `isolation` map records `deepcopy` vs `shared_reference` per object.
  The serialisable payload path is retained as a documented **lossy** fallback.

No threshold, seed or recorded number changes.

## 4. Discriminating test — proof and negative control

`logs/task7_fork_proof.json`:

* **negative control (unpatched tree, same test):** every cell of K ∈ {0,3} × N ∈ {1,2,5} fails
  (`tick_digests_equal = false`, `generation_digests_equal = false`) → the test discriminates.
* **patched:** all six cells pass on `tick_index_equal`, `tick_digests_equal`,
  `generation_digests_equal` **and** `population_digest_equal`.
* **multi-arm branching:** two arms restored from **one** fork payload each match the original
  continuation, and they match each other. The worst case for shared references — arms advanced
  **interleaved, one tick each** — also matches the original at K ∈ {0,3}, 3 ticks each.

Isolation map for the exact path: `world`, `nexus_layer`, `qd_archive` → `deepcopy`;
`population` and `element_grid` → `shared_reference` (deepcopy is blocked by `mappingproxy` inside
the organism graph). This is safe in the measured cases because `PopulationRunner.step_generation`
derives a new population object each tick, so the shared pre-fork object is only read.

## 5. Consequences for D-2

* The D-2 checkpoint fork is now state-complete for the tested range (K ∈ {0,3}, N ∈ {1,2,5}) and
  arms branched from one payload are independent on the tested horizon.
* **Remaining watchdog, not a relaxation request:** if a D-2 arm horizon extends far enough that
  `step_generation` ever mutates the shared pre-fork `population`/`element_grid` in place before
  another arm reads them, isolation would break. The patch records `fork_isolation` on every
  restored engine and sets `fork_state_exact` false when any object is shared, so the runner can
  refuse to credit a multi-arm contrast on such a fork rather than silently confound it. I will
  make D-2 assert `fork_isolation["population"] == "deepcopy"` or fail loudly per arm.
* Because the shared-reference objects were proven non-isolating only by the interleaved test and
  not by construction, D-2's forked contrasts stay **conditional** on that assertion; the arms
  themselves are not blocked once the assertion passes.

## 6. Non-claims

No threshold, seed or parameter was tuned to obtain byte-identity. Byte-identity here is obtained
by restoring state, not by re-running from tick 0, so it is valid with mutating observers (the
idea-4 coupler), which a replay-based fork would not be.
