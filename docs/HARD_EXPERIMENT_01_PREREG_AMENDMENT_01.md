# HARD_EXPERIMENT_01 preregistration amendment 01

Product: **CodonTrace Genesis** (package `codontrace`).
Experiment id: `hard_experiment_01_capsule_source_bias`.
Schema after this amendment: `hard_experiment_01_v3`.
Identity: `0.3.0b4.dev0`. Dated: **2026-09-12**.

This file is a **transparent dated amendment** to
[`HARD_EXPERIMENT_01_PREREG.md`](HARD_EXPERIMENT_01_PREREG.md) (v2).
The original preregistration file is **not** rewritten. Confirmatory
campaigns store both `prereg_digest` (SHA-256 of the frozen v2 prereg
UTF-8 bytes) and `amendment_digest` (SHA-256 of this file’s UTF-8
bytes). Do not reuse the v2 prereg alone for the changed design.

Literature for the amendment practice: dated protocol amendments before
confirmatory analysis are expected (trial-amendment / preregistration
norms). Manipulation checks verify that the intervention changed the
intended construct; identical-arm outcomes are not a scientific null
(manipulation-check / ITT literature). Sham / positive controls
distinguish assay death from a true null (ALife sham-control practice).

**Blocked claims (unchanged):** `intelligence`,
`collective_intelligence`, `proved_collective_intelligence`, `agi`,
`tokyo_type1_passed`, `avida_replacement`, and ClaimGate aliases of
those labels. ClaimGate is not loosened. Forbidden claims are
unchanged. Phase A–E pins must not change.

---

## Why this amendment exists

HARD_EXPERIMENT_01 research v2 is **`assay_invalid`**, not an
interpretable null. All four primary arms produced bitwise-identical
mean fitness `0.164375`, adoptions `169 / 169 / 0 / 169`, dz = 0,
CI = `[0, 0]`. Causes already in the v2 code:

1. `accept_provisional_source_fitness=True` bypassed
   `min_source_fitness=2.0` (adoptions on = off).
2. The absolute threshold 2.0 never bites fitness ≈ 0.16.
3. Calibration genomes `EAT, EMIT, WAIT` had no `COPY` → births = 0 →
   next-generation fitness from the prereg is undefined.
4. Capsule content on `life_loop_world` only recorded; it did not
   change action / ATP. DAG edge `content → action` was missing, so
   the estimand was unanswerable on that substrate.

---

## Deviations from `HARD_EXPERIMENT_01_PREREG.md`

### A. Substrate (confirmatory runs)

**Was:** Phase A `life_loop_world` overlay.

**Now:** confirmatory runs use
`GenesisRuntimeProfile.phase_e_substrate_world()` (CLAIMS.md: capsule
slots change subsequent action / ATP there). Overlay still does **not**
mutate default Phase A–E preset digests.

- Primary arms: `enable_capsule_memory=True`,
  `seed_preferred_action=""` (no seed prior that would make arms
  identical), `write_actions=()` so only **adopted** capsule content
  writes slots, `inherit_lineage=True` so next-generation organisms
  can carry adopted slots.
- Adopted nexus capsules write an unconstrained Phase E slot
  (`source="adopted_capsule"`). That is the missing
  `which_capsule_is_adopted → action` edge.
- Capsule emission may encode the source’s fitness-relevant action
  (`encode_source_action_in_content=True`) so shuffled content can
  differ from on.

### B. Source-fitness gate

**Was:** treatment `min_source_fitness=2.0` (absolute) and
`accept_provisional_source_fitness=True`.

**Now:**

- Treatment (and shuffled / matching dose) uses
  `accept_provisional_source_fitness=False`.
- Absolute 2.0 is replaced by a **same-tick source-fitness quantile**.
  Treatment uses the **median** (`source_fitness_quantile=0.5`) of
  last-known organism fitnesses and readable capsule source fitnesses
  in that tick. Capsules below the tick median are rejected
  (`source_fitness_below_threshold` or
  `source_fitness_provisional_not_accepted`).
- `source_bias_off` keeps the channel on with the gate ablated
  (`min_source_fitness=0.0`, `source_fitness_quantile` unset,
  `THRESHOLD`).

### C. Dose ladder

**Was:** absolute `min_source_fitness ∈ {0, 1, 2, 4}`.

**Now:** quantile levels `{0.0, 0.25, 0.50, 0.75}` under
`FITNESS_WEIGHTED`. Dose `0.50` matches treatment. Dose `0.0` is the
minimum of the same-tick pool (not `source_bias_off`).

### D. Genomes / reproduction

**Was:** calibration emitter `EAT, EMIT, WAIT` (no `COPY`).

**Now:** every calibration genome includes `COPY_SELF` (or equivalent)
so `births > 0` is possible. Births are reported in Results tables.
`births > 0` is a **validity condition** when the claim concerns
next-generation fitness.

| Role | Bits | Actions |
|---|---|---|
| Emitter (index 0) | `101110111` | `EAT_LUMEN`, `EMIT_NEXUS`, `COPY_SELF` |
| Eater | `101111000` | `EAT_LUMEN`, `COPY_SELF`, `WAIT` |
| Waiter | `111000000` | `COPY_SELF`, `WAIT`, `WAIT` |

Survival / energy / food overlay knobs from Wave 1b remain overlay-only.

### E. Seed separation

**Was:** calibration and confirmatory both used analysis seeds `11`…`40`.

**Now:**

- Survival / calibration / pilot only on seeds `1000`–`1009`.
- Analysis seeds `11`–`40` must not run until this overlay is
  **locked** (`CONFIG_LOCKED=True` after this amendment is the frozen
  design). Smoke after lock may use `11`…`22`. Research after lock
  uses `11`…`40`.

### F. Positive control arm `oracle_capsule`

**New.** Fifth measured arm. Payload that **directly** increases
fitness on the same Phase E content→action→ATP path: seed
`preferred_action="EAT_LUMEN"` with elevated `atp_bonus` (4.0 vs 0.5)
and unconstrained cue match. Reported in the arm table. **Not**
included in the three primary Holm contrasts. If oracle vs
`capsules_off` also yields dz ≈ 0 (bitwise-identical outcomes), the
assay is dead.

### G. Mandatory manipulation check (per seed)

For each analysis / smoke seed, all of the following must hold or the
seed fails with `assay_failed: manipulation_not_realized`:

1. Set of content digests of adopted capsules: `on ≠ off`.
2. Shuffled adopted content digests `≠ on`.
3. `capsules_off` adoptions = 0.
4. `rejected_by_source_fitness` count in `on` > 0.

If outcomes are bitwise-identical across primary arms in ≥ 90% of
seeds → warning `arms_bitwise_identical` (not a scientific null).

### H. ClaimGate auditor (before public level ≥ 2)

For HE01-shaped bundles, require `manipulation_check_passed`,
`positive_control_detected` (or a documented waiver string),
within-arm outcome variance > 0, and `births > 0` when the claim is
about next-generation fitness. Else public ceiling = level 1 with
label `assay_invalid`. Existing HE01 v2 artifact grading stays
`assay_invalid`. ClaimGate is never loosened.

### I. Valid confirmatory outcomes (v3)

After validity passes, a scientific reading is either a **real
effect** or a **null with** manipulation check passed **and**
positive control positive. Wave 3 is not this amendment.

---

## Unchanged

Question, DAG nodes/edges, three primary contrasts, Holm family size 3,
BCa / sign-flip / inferential seed `20260911`, α = 0.05, missing
outcomes dropped (never zero-filled), replay of first and last seeds,
forbidden claims, Phase A–E pins:

- `life_loop_world(seed=7, tick_count=12, population=6)` spec
  `7d199ae51345872215dbbb0c45cf8f141aacfb4c31d6537eda6de246c0cb7aac`
- snapshot
  `76a5e62cb0123b20a089adde25acd1cfb6dc460bdfab52f33ee460533d76f43a`
