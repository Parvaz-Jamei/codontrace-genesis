# Closed-loop P1 status — 2026-09-25

## Verdict
P1 landed: both roles as `GenesisOrganism` under one `step_population` clock.
Scope hard-locked to **unify + engine-mutate scaffold**. Not Morran-ready.
Not P2 energy-partition. Not P4 dual-arm.

Tip: `git log --oneline --grep='closed-loop' -5` on `main`.

## Implementation notes
1. Hook cut — HP life plugin at **post-ATP settle / pre-birth** in `population.py`.
2. Engine mutation via `mutate_genome` + live generation `stream` (no parallel point schedule).
3. Opaque `role_by_id` map (no id-prefix role parse).
4. Summary uses measured fields only (`p1_scope`, `clock_api`, `hp_world_tick_calls`, `atp_moved`) — no caller-boolean clocks.
5. `assert_single_atp_owner` called on apply/boot/tick; basal metabolism so ATP moves.
6. Accept patches `HostParasiteWorld.tick` and asserts zero calls under the session.
7. Reproduction remains off in P1 (birth/partition = P2).
8. Dual `HostParasiteGenesisPath.tick` remains hard-raise.
9. `engine.py` stays domain-free (no infection vocabulary).
10. Claim ceiling ≤ `candidate_evidence`; `red_queen_proved` stays false.

## Accept
`tests/closed_loop/test_closed_loop_p1_accept.py` (+ gate6 retired-path test).

## Next
P2: Smith–Fretwell energy partition on birth (engine reproduction on).
