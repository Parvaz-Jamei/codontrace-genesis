# Closed-loop P2 status — 2026-09-25

## Verdict
P2 landed: Smith–Fretwell **N=1 asexual** birth ATP partition under one
population clock. Engine `ReproductionConfig` ON. Child endowment
`Iy = Ip × offspring_atp_fraction` after `parent_atp_cost` (cost dissipated).
Zero-endowment live births blocked.

Tip: `git log --oneline --grep='P2' -3` on `main`.

## Hard scope (do not over-claim)
| In scope | Out of scope |
|---|---|
| N=1 asexual partition via engine `reproduce()` | Morran / Red Queen proved |
| Both roles birth as GenesisOrganisms | Genetic harm/help coupling (P3) |
| Measured conservation ±ε | Dual-arm elicit/ablate replay (P4) |
| Opaque role inheritance on birth | SF optimal Iy* search |
| Same-seed bit-identical short replay | Multi-child N=⌊Ip/Iy⌋ |
| Claim ceiling `candidate_evidence` | Infection physics in `engine.py` |
| | `HostParasiteWorld.tick` / `_birth_role` demography |

## Binding checklist
1. P1 post-ATP / pre-birth plugin hook kept.
2. Engine reproduction ON; reuses `offspring_atp_fraction` + `parent_atp_cost`.
3. N=1 asexual only; Ip after basal settle and after `parent_atp_cost`.
4. Birth blocked at Iy=0.
5. Child runtime ATP == measured Iy; child `learning_atp` = 0; conservation
   `parent_after + child == parent_before - parent_atp_cost` (±ε).
6. No fresh flat birth endowment; no `skip_parent_costs` / override on accept path.
7. Child inherits opaque role from parent; both roles can birth.
8. Summary witnesses measured: `births`, `mean_child_atp` / `mean_Iy`,
   partition conservation counts — never hardcoded true.
9. Same-seed replay only — not dual-arm protocol.
10. Runtime: zero `HostParasiteWorld.tick` / `_birth_role` under accept.
11. ClaimGate: ceiling `candidate_evidence`; `red_queen_proved=False`;
    no caller-boolean `smith_fretwell_ok` / `one_clock` / `partition_ok`.

## Deliverables
- `src/codontrace/genesis/closed_loop_p2.py`
- `src/codontrace/genesis/host_parasite_life_plugin.py` (role inheritance)
- `src/codontrace/genesis/population.py` (Iy=0 birth block)
- `tests/closed_loop/test_closed_loop_p2_accept.py`
- This status note

## Accept
```bash
uv run pytest tests/closed_loop/test_closed_loop_p2_accept.py \
  tests/closed_loop/test_closed_loop_p1_accept.py -q
```

## Soft risks
- High bit-flip rate can mutate COPY_SELF off before birth; accept uses a low rate.
- `ticks_per_generation=3` so EAT/COPY/WAIT hits COPY within a generation.
- Parent-after witnesses can drift inside multi-tick generations; session uses frozen gate + birth_event values.

## Next
P3: scalar genetic harm/help (kill threshold fixed); P4: mutation-stream schedule lock + dual-arm bit replay.
