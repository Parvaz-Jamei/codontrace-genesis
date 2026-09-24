# Closed-loop P1 status — 2026-09-25 (post-adversarial fix)

## Verdict
**P1 re-landed after adversarial ×1.** Scope hard-locked: **unify + engine-mutate scaffold** under one `step_population` clock. Not Morran-ready. Not P2 energy-partition. Not P4 dual-arm.

Tip: see `git log -1 --oneline` on `main`.

## Adversarial fixes applied
1. **Hook cut** — `apply_closed_loop_hp_life` moved to **post-ATP settle / pre-birth** (after basal+hazard debit, before nexus/reproduce) in `population.py`.
2. **Engine mutation** — plugin calls `mutate_genome(..., rng=stream.fork(...))`; no parallel `Mutation.point` schedule; `MutationConfig.bit_flip_rate > 0`.
3. **Live stream** — forks the generation `stream`, never `RNGManager(seed=seed)` side tree.
4. **Opaque roles** — `role_by_id` map on config; `role_of(id)` without map returns `None` (no id-prefix parse).
5. **Caller booleans dropped** — summary has measured `p1_scope`, `clock_api`, `hp_world_tick_calls`, `atp_moved` — no `one_clock` / `dual_path_used`.
6. **`assert_single_atp_owner` called** on apply + boot + each tick.
7. **ATP moves** — basal metabolism enabled so energy clock is not idle.
8. **Runtime anti-cheat** — accept patches `HostParasiteWorld.tick` and asserts zero calls.
9. **Hard scope** — reproduction still off; birth/partition = P2. Same-seed replay labeled Gate7-shaped, not P4.
10. Dual `HostParasiteGenesisPath.tick` remains hard-raise.

## Accept
`tests/closed_loop/test_closed_loop_p1_accept.py` + gate6 retired-path test.

## Next
P2 specialist Pass ×2 (Smith–Fretwell energy partition on birth) — only after owner/Gen greenlight.
