# Three-arm ecology path and digest-backed frequency clocks

Revision `hp-arm01-20260926`. Branched from `closed-loop/pearl-pair-spc`
(`d3cea0c`), which itself sits on tip `610f46f` (`codontrace==0.3.0b10`).
Sealed confirmatory seeds 101–108 on that tip remain an honest FAIL
(0/8 separate, 0/8 mixed). Both `red_queen_proved` and
`biological_red_queen_proved` stayed false. ClaimGate still refuses
`red_queen_proved` on the `host_parasite` profile. The P7 preregistration
was not edited after that run. `engine.py` was not edited. BAIC pins were
not touched.

## Why this note exists

Morran et al. (Science 333:216–218, 2011, doi:10.1126/science.1206360) and
Slowinski et al. (Evolution 70:2632–2639, 2016, doi:10.1111/evo.13048) used
control, fixed-parasite, and copassaged regimes when asking whether sex is
maintained under coevolution. The closed-loop ledger already names the
matching tip passages. This slice maps the ecology labels without collapsing
`absent` into `frozen` or into pure zero-debit / `costless` (Pearl,
Biometrika 82:669–688, 1995, doi:10.1093/biomet/82.4.669).

| Ecology arm | Tip passage | Meaning |
|---|---|---|
| `avirulent` | `absent` | Antagonist removal; not a Pearl zero-debit cut |
| `fixed` | `frozen` | Update off, debit on |
| `copassaged` | `coevolve` | Update on, debit on |

`costless` stays a Pearl debit knockout for measurement clauses. It is not
an ecology arm on this path.

## Frequency clocks

Required fields, not caller-booleans:

1. **Genotype** — recognition-window frequency tables, digest-backed.
2. **Mating-mode** — outcross / selfing headcounts, digest-backed.
3. **Match-class** — paid match vs unmatched hosts per generation,
   digest-backed.

A clock digest does not write `red_queen_proved`. Missing series fail
closed.

## Primary ecology accept path

Slowinski-style invasion / mating-mode frequency contrast: terminal selfing
frequency under `copassaged` must be strictly below both `avirulent` and
`fixed`. Short scaffolding runs may honestly fail that contrast; the miss
is recorded. Pearl `frozen`+`costless` knockouts and debit-stream capability
gates from the Pearl-pair harness may attach as thin measurement clauses
only after the three clocks exist. They are not the ecology accept path.

## Claim posture

| Item | Status |
|---|---|
| Sealed 101–108 | honest FAIL; not reopened |
| `red_queen_proved` | false; not promoted |
| `biological_red_queen_proved` | false |
| ClaimGate refuse | holds |
| Ceiling while scaffolding | `runtime_observation` |
| Max ceiling once clocks + treatment/control exist | `candidate_evidence` |
| `absent` vs Pearl pair | documented distinct |

## Optional Holling handling-time (HP env only)

`HostParasiteEnv.handling_time` gates further inject attempts while busy and
scales steal magnitude by `1/(1+Th)`. Ablation digests with handling off vs
on must differ. Type III shapes and infection language in `engine.py` stay
out of scope.

## Code

- Additive module: `src/codontrace/genesis/closed_loop_hp_arm01.py`
- Thin env knob: `handling_time` on `host_parasite_env.py`
- Accept tests: `tests/closed_loop/test_closed_loop_hp_arm01.py`

## Branch base

Stacked on the Pearl-pair gates branch so frequency clocks can reuse Pearl
measurement helpers after clocks land. Ordinary dependency on that draft
pull request.

## Out of scope here

Goldsby×HP, MA↔GFG continuum, time-shift / finite-N / Ashby factorial,
Type III Holling, MFA / CRN / R2R / ATP carryover / queue-timing stacks,
reopening sealed 101–108, loosening ClaimGate, promoting either Red Queen
flag.
