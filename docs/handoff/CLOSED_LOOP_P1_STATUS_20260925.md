# Closed-loop P1 status — 2026-09-25

## Verdict
**P1 implement landed locally** (one clock: both roles as `GenesisOrganism` under `step_population`). Dual `HostParasiteGenesisPath.tick` **hard-raises**. Claim ceiling ≤ `candidate_evidence`. `red_queen_proved` untouched.

## Pass 2 consensus applied
- Hook: `PopulationConfigs.closed_loop_hp_life` inside `step_population` (same optional cut as `phase_e` / `materials`), never `engine.py`.
- Data: role-tagged organisms own `genome` + `atp_state`.
- Compat: dual path fail-closed; `engine_bound` alone never greens P1.
- Anti-cheat: accept tests assert no `HostParasiteWorld.tick` / `_birth_role` / `_death_role` in `closed_loop_p1`; secondary genome digest changes; bit-identical replay.

## Files
- `src/codontrace/genesis/host_parasite_life_plugin.py`
- `src/codontrace/genesis/closed_loop_p1.py`
- `src/codontrace/genesis/population.py` (config + hook)
- `src/codontrace/genesis/host_parasite_genesis_path.py` (hard-raise)
- `tests/closed_loop/test_closed_loop_p1_accept.py`
- gate6 retargeted to expect hard-raise

## Next
Adversarial storm ×1 in Closed Loop Storm → Gen fix → then P2 (Smith–Fretwell partition).
