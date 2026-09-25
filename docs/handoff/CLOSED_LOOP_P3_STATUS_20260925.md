# Closed-loop P3 status — 2026-09-25

## Verdict
P3 landed: scalar genetic harm/help (κ) via life-loop `EnergyCoupling` on
`atp_state`. Fixed bit-window decode on a mutable genome locus (both roles).
Post-f(κ) clamp 0.8 is **not** a gene default. Ablate κ→0 kills
`|net_transfer|` and ATP skew. Claim ceiling `candidate_evidence`.

Tip: `git log --oneline --grep='P3' -3` on `main`.

## Hard scope (do not over-claim)
| In scope | Out of scope |
|---|---|
| κ ∈ [-1,+1] fixed bit-window decode | Morran / Red Queen proved |
| Transfer via EnergyCoupling → atp_state | `HostParasiteEnv.steal_fraction` |
| Clamp 0.8 post-f(κ) only | Profile `coupling_amount` path |
| Ablation kill of transfer + skew | Dual-arm elicit/ablate replay (P4) |
| P2 birth conservation ±ε under κ | Infection physics in `engine.py` |
| Measured witnesses only | Caller-boolean `genetic_harm_ok` |

## Binding checklist
1. κ decoded from fixed locus (`KAPPA_BIT_START` / `KAPPA_BIT_WIDTH`); both roles.
2. Transfer magnitude `|f(κ)|×available` then clamp to `0.8×donor` — clamp outside decode.
3. Pairing via `AttachmentSlot`; transfer via `EnergyCoupling` mirrored to `atp_state`.
4. Under κ-on closed-loop path: zero reads of `steal_fraction` / `coupling_amount`.
5. Ablate κ→0 ⇒ `|net_transfer|→0`; peak ATP skew collapses vs κ-on.
6. P2 partition conservation still measured under κ transfers.
7. Summary witnesses: `mean_kappa_*`, `net_transfer`, `peak_abs_atp_skew`, ablation Δ.
8. ClaimGate: ceiling `candidate_evidence`; `red_queen_proved=False`.
9. Runtime: zero `HostParasiteWorld.tick` / `_birth_role` under accept.
10. `engine.py` stays domain-free (no steal/κ/infection vocabulary).

## Deliverables
- `src/codontrace/genesis/closed_loop_p3.py`
- `src/codontrace/genesis/host_parasite_life_plugin.py` (κ helpers + config flags)
- `tests/closed_loop/test_closed_loop_p3_accept.py`
- This status note

## Accept
```bash
uv run pytest tests/closed_loop/test_closed_loop_p3_accept.py \
  tests/closed_loop/test_closed_loop_p2_accept.py \
  tests/closed_loop/test_closed_loop_p1_accept.py -q
```
