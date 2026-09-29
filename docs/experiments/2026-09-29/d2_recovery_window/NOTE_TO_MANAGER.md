# D-2 → manager: unblocking patch `docs/experiments/2026-09-29/d2_recovery_window/PROPOSED_CHANGE.patch`

**From:** D-2 test agent (`mechanism-test`) · **Round:** 1 · **Date:** 2026-09-29
**Patch:** `docs/experiments/2026-09-29/d2_recovery_window/PROPOSED_CHANGE.patch` (231 diff lines, sha256 prefix `1398050ecf16fddd`)
**Evidence:** `docs/experiments/2026-09-29/d2_recovery_window/patch_evidence.json`, `docs/experiments/2026-09-29/d2_recovery_window/logs/make_patch.txt`
**Script that generates both:** `docs/experiments/2026-09-29/d2_recovery_window/harness/d2_make_patch.py` (the patch text and the
code exercised for evidence are the *same source strings*).

The patch touches two files and nothing else. It is additive: no existing constant,
threshold, recorded number or decision branch is modified.

---

## Defect 1 — no full fork at a generation boundary (engine state + RNG + parent/child)

* **File/line:** `src/codontrace/engine_runtime.py`, `GenesisEngine.snapshot` (line 296) and
  the tick-base line `base = len(self._tick_results)` (line 275).
* **Defect:** `snapshot()` returns only `run_id, population, world_digest, qd_archive_digest,
  element_grid_digest, substrate_bridge_mode`; there is **no restore entry point**
  (`[n for n in dir(GenesisEngine) if restore|fork|from_snapshot] == []`) and
  `copy.deepcopy(engine)` raises `TypeError: cannot pickle 'mappingproxy' object`.
  Probe: `docs/experiments/2026-09-29/d2_recovery_window/logs/probe7.txt`, `stage0_report.json → fork_precondition`.
  The unforgeable proxies are in `spec.element_grid.registry._definitions`,
  `spec.population_configs.{alive_gate,fitness}.status_registry._definitions`,
  each organism's `action_registry._handlers`,
  `action_runtime_config.status_registry._definitions`, and
  `ribosome.codon_table._mapping`. D-2 cannot branch three early/middle/late checkpoints
  from one history without a restorable fork, so the verdict is blocked.
* **Root cause of the deepcopy failure:** `mappingproxy` is unpicklable by design, so
  `deepcopy` can never work on this object graph. A *state* fork is the smallest fix.
* **Smallest change (in the patch):**
  1. `base = int(getattr(self, "_tick_offset", 0)) + len(self._tick_results)` and
     `index=base + len(self._tick_results)` — lets a restored engine continue the
     `spec.seed + base + index` RNG schedule instead of restarting it at 0.
  2. `GenesisEngine.capture_fork(parent_snapshot_id=None)` — JSON-safe fork payload:
     `population.to_dict()` (organisms carry id/parent/generation, so parent–child identity
     is preserved), `world.to_dict()`, `tick_index`, the per-tick seed derivation, and an
     explicit `RNGManager.snapshot(include_state=True)` for audit.
  3. `GenesisEngine.from_fork(spec, fork, *, generation_boundary_observers=None)` — rebuilds a
     live engine with `PopulationState.from_dict` and `World2D.from_dict`, sets
     `_tick_offset`, clears `_tick_results/_snapshots`. No pickle, no deepcopy.
* **Evidence the fix works (round 1):**

  | check | result |
  |---|---|
  | `continuation_identical` (original 5 ticks after t=10 vs restored fork + 5 ticks) | **true** |
  | `parent_child_ids_preserved` (ids from the fork payload vs restored population) | **true** |
  | `fork_has_rng_state` / `fork_has_population` | **true / true** |
  | `n_organisms_forked`, `fork_tick_index` | 8, 10 |

  A restored fork reproduces the continuation of the original history **byte-identically**.

## Defect 2 — topology not identified: arms differ only by the coupler's global edge-cost penalty

* **File/line:** `src/codontrace/life_loop/engine_ledger_coupler.py`,
  `_organisms_for_nodes` (line 245, `index % len(ordered)` — the module itself says
  "Not a contact physics claim"), the allocation guard (line 320) and
  `apply_ledger_feedback_to_engine` (line 302, `burden_edge_changes = n_edge_changes * 0.35`
  with a matching `food_from_edge_count` term).
* **Defect (measured, not inferred):** the named-scaffold cut (`E0,E1`) and the degree/ATP
  matched random cut (`E6,E7`) produce **identical burden, identical realised contacts and an
  identical engine population trajectory** under `global_smear`. Raw runs:
  `docs/experiments/2026-09-29/d2_recovery_window/logs/probe4.txt`, `probe6.txt`:
  `control=d3084e8b…`, `cut_named_scaffold=39762884025d7aad`,
  `cut_matched_random=39762884025d7aad`, both `burden=3.2202197309490583`. Every arm
  difference versus control is exactly the fixed count penalty (`n_edge_changes × 0.35`).
  This is the D-2 refusal condition, and it fires.
* **Smallest change (in the patch):**
  1. `bind_nodes_to_organisms(engine, pre_snap, post_snap)` — binds the declared ledger node
     order to the sorted live organisms and returns `{}` (refuses) unless the binding is
     complete; there is no modular fallback.
  2. A new allocation mode `"incident_endpoints_realised"` added to the guard: the debit is the
     **realised ATP of the contact edges that actually changed**, charged to the organisms
     bound to those edges' endpoints. `burden_edge_changes` stays `0.0` in this mode, so the
     global count penalty cannot explain any difference.
  3. Flags are set from the binding: `endpoint_map_is_contact_physics`,
     `contact_structure_effect_identified`, `topology_effect_identified` are `True` **only**
     when every changed edge's endpoints resolved to live organisms. `reciept` includes
     `per_organism_realised_debit` and `unbound_nodes`.
* **Evidence the fix works (round 1):**

  | check | before patch | after patch |
  |---|---|---|
  | named vs matched population path | identical | **different** |
  | count-penalty term | identical | identical **and 0.0** |
  | debited organisms | n/a (global smear) | 3 named vs 3 matched, disjoint |
  | `contact_structure_effect_identified` | false | **true** |

  The difference now comes from *which contact edges were cut and which organisms held them*,
  not from the global penalty.

## Known limitation recorded with the patch (not a blocker for landing)

`bind_nodes_to_organisms` needs `len(live organisms) >= len(ledger nodes)` (8). In this model
the population falls below 8 within ~11 generations, so after a fork the coupler **refuses**
rather than silently falling back (observed in `patch_evidence.json → fork_evidence.branches_differ = false`;
by generation 11 the census is 6). That is the intended refusal behaviour, and it is the same
collapsing-population problem already recorded in `OWNER_MEASUREMENT_BLOCKERS_20260929.md`
(`n_alive_end == 0`, 855/960 records). Fixing population persistence is a separate defect; the
D-2 pack will report it as an opportunity/attrition finding rather than tune it away.

## What to do after landing

1. `git apply docs/experiments/2026-09-29/d2_recovery_window/PROPOSED_CHANGE.patch` (or apply by hand; the two hunks are
   independent).
2. Run `python -c "import codontrace.engine_runtime, codontrace.life_loop.engine_ledger_coupler"`.
3. Tell me it landed. I will re-run `python docs/experiments/2026-09-29/d2_recovery_window/harness/d2_pack.py all` against the
   real files and record `decision.md` with a real verdict, plus `d2_replay.py` from the
   manifest. Round 2 of my budget is reserved for that.

## What the patch deliberately does not do

* It does not change `harvest_rare_class_yield`, the 1.25×/≥3-boundary rule, the 0.15 slope,
  the 0.20 ΔP margin, any seed, or any pre-registered constant.
* It does not make the population persist, and it does not invent an antagonist genotype
  population (still `null` with a stated reason in the raw `population.jsonl`).
