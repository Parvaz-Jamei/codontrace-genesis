# Closed-loop P4 status — 2026-09-25

## Verdict
P4 landed: mutation-stream lock via `mutation_stream_lock_roles` in the
post-ATP plugin, plus dual-arm elicit/ablate bit replay under one master seed.
Birth/death stay ON. Measured effect kill first; digests second. Claim ceiling
`candidate_evidence`.

Tip: `git log --oneline --grep='P4' -3` on `main`.

## Hard scope (do not over-claim)
| In scope | Out of scope |
|---|---|
| Mut-freeze via plugin `mutation_stream_lock_roles` | Bag `ScheduleLock.freeze` green path |
| Birth/death remain ON | Gate7 / P2 same-seed theater |
| Dual-arm: κ-on elicit vs ablate/lock kill | Morran / Red Queen proved |
| Bit-identical self-replay both arms | Digests-alone as “effect died” |
| Digests: genomes + ATP + κ | Infection physics in `engine.py` |
| Measured `|net_transfer|` kill | Caller-boolean `effect_died` |

## Binding checklist
1. Locked roles skip `mutate_genome` in post-ATP plugin.
2. When locks active, engine `MutationConfig.bit_flip_rate=0` so birth cannot bypass.
3. Unlocked roles still mutate via plugin `plugin_bit_flip_rate`.
4. Arm A: κ-on → `|net_transfer|_A > ε` (measured elicit).
5. Arm B: ablate κ and/or lock stream → `|net_transfer|_B ≤ ε` (measured kill).
6. Self-replay both arms bit-identical; digests include genomes + ATP + κ.
7. Digests alone do not constitute kill — elicit/kill numbers come first.
8. AST/runtime bans: no `ScheduleLock.freeze` on accept path; no HP world demography.
9. ClaimGate: ceiling `candidate_evidence`; `red_queen_proved=False`.
10. `engine.py` stays domain-free.

## Deliverables
- `src/codontrace/genesis/closed_loop_p4.py`
- `src/codontrace/genesis/host_parasite_life_plugin.py` (lock fields)
- `tests/closed_loop/test_closed_loop_p4_accept.py`
- This status note

## Accept
```bash
uv run pytest tests/closed_loop/ -q
```


## Adversarial fix (2026-09-25)

- Dual-arm default kill is κ-ablate (`kill_mechanism`); mutation-stream lock is a separate witness.
- Do not treat dual-arm as Morran static-genome / lock-kill.
