# Three-arm ecology path: life-loop bind and Slowinski invasion

Revision `hp-arm01-engine-bind-20260926`. Branched from
`closed-loop/pearl-pair-spc` (`d3cea0c`), which itself sits on tip `610f46f`
(`codontrace==0.3.0b10`). Sealed confirmatory seeds 101–108 on that tip remain
an honest FAIL (0/8 separate, 0/8 mixed). Both `red_queen_proved` and
`biological_red_queen_proved` stayed false. ClaimGate still refuses
`red_queen_proved` on the `host_parasite` profile. The P7 preregistration was
not edited after that run. `engine.py` was not edited. BAIC pins were not
touched.

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

`costless` stays a Pearl debit knockout for measurement clauses on new cells.
It is not an ecology arm on this path.

## ENGINE-BIND (life-loop substrate)

Each ecology arm runs on the real CodonTrace life-loop:

1. **Population step** — `PopulationRunner.step_generation` (same inner clock
   as `GenesisEngine.run_ticks`). Domain-free; no host/parasite vocabulary in
   `engine.py`.
2. **Phase B sexual chamber** — `ReproductionMode.SEXUAL_CROSSOVER` with the
   existing outcross locus (mating-effort ATP). Maynard Smith's two-fold cost
   (`SexualRecombinationConfig.two_fold_cost_sex`) remains **unpaid** (default
   off). Mating-effort is not silently equated with Hamilton / two-fold cost.
3. **HostParasiteEnv contact** — recognition-window allele tasks drive
   inject/debit on the **same** env instance the arm owns. Holling
   `handling_time` ablation must use that campaign env path
   (`campaign_handling_ablation_pair`), not a disconnected probe.

The shared-modifier census (`run_shared_modifier`) is **refused** as the
primary campaign substrate. It may still appear in thin Pearl measurement
helpers, not as the ecology accept path.

## Frequency clocks (per-arm)

Required fields, not caller-booleans. Built **per arm** from life-loop
digests — not concatenated across arms; not treatment-only genotype clock:

1. **Genotype** — recognition-window frequency tables, digest-backed.
2. **Mating-mode** — outcross / selfing headcounts, digest-backed.
3. **Match-class** — paid match vs unmatched hosts per generation,
   digest-backed.

Invasion series (also per-arm): **selfing-rate** and **allele-frequency**.
A clock digest does not write `red_queen_proved`. Missing series fail closed.

## Primary ecology accept path (HP-ARM01-SLOWINSKI-INVASION)

Resident obligate-outcross deme + low-frequency selfing-capable introduction.
Accept only when selfing **invades** under `avirulent` and `fixed` (terminal
frequency above introduction) and **stays rare** under `copassaged` (at or
below introduction and strictly below both controls).

Morran outcrossing-maintenance is **secondary**, not a substitute PASS.
Legacy three-frequency terminal inequality is **not** the accept path and
must never be reported as Slowinski PASS for a shared-modifier substrate.

Short scaffolding runs may honestly fail the invasion contrast; the miss is
recorded. The confirmatory invasion horizon is locked in
`CLOSED_LOOP_HP_ARM01_SLOWINSKI_INVASION_PREREG_20260926.md` (48 generations,
virulence 32, parasite mutation 0.5, intro 0.2, seeds 201–208, pass bar 6/8)
before outcomes. Do not soft-green by retuning after inspection.

Pearl `frozen`+`costless` knockouts and SPC/CUSUM/observer predicates may
attach as thin **fail-closed measurement clauses** only after per-arm
frequency clocks exist. They are not the ecology accept path and must not
grant Red Queen flags.

## Claim posture (ClaimCritic harden)

| Item | Status |
|---|---|
| Sealed 101–108 | honest FAIL; not reopened |
| `red_queen_proved` | false; not promoted |
| `biological_red_queen_proved` | false |
| ClaimGate refuse | holds |
| Ceiling while scaffolding / invasion miss | `runtime_observation` |
| Candidate only when | life-loop bind ∧ per-arm clocks ∧ treatment/control ∧ invasion holds |
| Non-empty clock fields alone | do **not** grant `candidate_evidence` |
| Shared-modifier as Slowinski PASS | refused |
| `absent` vs Pearl pair | documented distinct |
| Two-fold cost of sex | unpaid; documented |

## Optional Holling handling-time (HP env only)

`HostParasiteEnv.handling_time` gates further inject attempts while busy and
scales steal magnitude by productivity/(1+Th). Ablation digests with handling
off vs on must differ **on the campaign env path**. Type III shapes and
infection language in `engine.py` stay out of scope.

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
flag, importing ecology vocabulary into `engine.py`.
