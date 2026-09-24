# Closed-loop P2 status — 2026-09-25

## Verdict
**P2 landed:** Smith–Fretwell **N=1 asexual** birth ATP partition under one
`PopulationRunner.step_generation` clock. Engine `ReproductionConfig` ON.
Child endowment **Iy = Ip × offspring_atp_fraction** after `parent_atp_cost`
(cost dissipated). Zero-endowment live births blocked (`offspring_atp_zero`).

Tip: see `git log -1 --oneline` on `main`.

## Hard scope (do not over-claim)
| In scope | Out of scope |
|---|---|
| N=1 asexual partition via engine `reproduce()` | Morran coevolution / Red Queen proved |
| Both roles birth as GenesisOrganisms | Genetic-harm coupling (P3) |
| Measured conservation ±ε≈1e-9 | P4 dual-arm elicit/ablate |
| Opaque `role_by_id` inheritance on birth | SF optimal Iy* search |
| Gate7 same-seed bit-identical | Multi-child N=⌊Ip/Iy⌋ |
| Claim ceiling `candidate_evidence` | Infection physics in `engine.py` |
| | `HostParasiteWorld.tick` / `_birth_role` demography |

## Binding checklist
1. P1 post-ATP / pre-birth plugin hook **kept** where it is.
2. Engine reproduction ON in P2; reuses `offspring_atp_fraction` + `parent_atp_cost`.
3. N=1 asexual only; Ip = parent runtime at `reproduce()` entry after basal settle,
   after `parent_atp_cost` debit for the Iy formula.
4. Birth blocked at Iy=0 (`can_reproduce` + `reproduce` + chamber cost helper).
5. Child runtime ATP == measured Iy; `learning_atp` on child = 0; conservation
   `parent_after + child == parent_before - parent_atp_cost` (±ε).
6. No fresh flat `initial_runtime_atp` / HP `initial_energy` as birth life source;
   P2 accept path does not use `skip_parent_costs` / `offspring_runtime_atp_override`.
7. Child inherits opaque role from parent (map growth via `with_inherited_birth_roles`);
   secondary founders encode COPY_SELF like primary.
8. Summary witnesses measured: `births`, `mean_child_atp` / `mean_Iy`,
   `partition_conserved` / `_count` / `_checks` — never hardcoded True.
9. Gate7 = same-seed only — not P4.
10. Runtime anti-cheat: zero `HostParasiteWorld.tick` / `_birth_role` under accept.
11. ClaimGate: `claim_ceiling=candidate_evidence`; `red_queen_proved=False`;
    no caller-boolean `smith_fretwell_ok` / `one_clock` / `partition_ok`.

## Deliverables
- `src/codontrace/genesis/closed_loop_p2.py` — `ClosedLoopP2Session`
- `src/codontrace/genesis/host_parasite_life_plugin.py` — role inheritance helpers
- `src/codontrace/genesis/population.py` — Iy=0 birth block (domain-free)
- `tests/closed_loop/test_closed_loop_p2_accept.py`
- This status note

## Accept
```bash
uv run pytest tests/closed_loop/test_closed_loop_p2_accept.py \
  tests/closed_loop/test_closed_loop_p1_accept.py -q
```

## Soft risks
- High `bit_flip_rate` can mutate COPY_SELF off founders before birth; accept uses low rate.
- `ticks_per_generation=3` needed so EAT/COPY/WAIT cycle hits COPY_SELF each generation.
- Chamber/sexual paths still exist in engine but are unused by P2 session (asexual default).

## Next
P3 (genetic harm / interaction→fitness) only after owner/Gen greenlight. Do not start P3 here.
