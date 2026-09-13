# HARD_EXPERIMENT_01 preregistration — Amendment 01 (Wave 1c, assay validity)

Product: **CodonTrace Genesis** (package `codontrace`).
Experiment id: `hard_experiment_01_capsule_source_bias`.
Schema after this amendment: `hard_experiment_01_v3`.
Identity: `0.3.0b4.dev0`. Not a new Phase letter. Not a tag or PyPI release.

This amendment is frozen **before** any analysis seed (11–40) is run under
the v3 design. The campaign payload records both `prereg_digest` (original
plan, unchanged bytes) and `prereg_amendment_digest` (SHA-256 of this file).
Pilot seeds 1000–1009 were used for calibration only and are excluded from
inference.

**Blocked claims (unchanged):** `intelligence`, `collective_intelligence`,
`proved_collective_intelligence`, `agi`, `tokyo_type1_passed`,
`avida_replacement`. ClaimGate is not loosened.

---

## 1. Why an amendment (what v2 got wrong)

The v2 campaign (`docs/hard_experiment_01/results_v2.json`) returned an
**invalid assay**, not an interpretable null. Three defects were found by
code inspection and reproduced on pilot seed 1000:

1. **DAG edge e2 did not exist in the engine.** `adopt_causal_capsule` only
   added a node/edge to the receiver's `CausalGraph`; nothing in
   `GenesisOrganism.step` read that graph when choosing an action. Adopted
   capsules were behaviourally inert, so `source_bias_on`,
   `source_bias_off` and `capsules_shuffled` produced identical traces.
2. **No variation in source quality.** A single emitter (index 0) meant the
   `min_source_fitness` gate had nothing to select on; the dose ladder was a
   ladder over an empty set.
3. **Food was not renewable under an organism.** Legacy respawn never
   placed Lumen on an occupied cell, so `EAT_LUMEN` was a one-shot; a
   "good" payload could not be good in expectation.

A negative-control/manipulation-check layer was absent, so the pipeline
labelled the identical arms an "interpretable null". Wave 1b/2 relabelled it
`assay_invalid`; this amendment fixes the design so the assay can be valid.

---

## 2. What changes (design), what does not (estimand)

**Unchanged:** the question (source-fitness gating vs ablated gate vs
channel off vs scrambled content), the four analysis arms, the paired-seed
design, seeds 11–40 (n = 30), 40 ticks × 16 organisms, Cohen's d_z with BCa
bootstrap (10 000), exact paired permutation, Holm over the three primary
contrasts, α = 0.05, replay of first and last seeds for every arm, and the
ClaimGate ceiling rule (`intervention_supported` only if every decision rule
passes; otherwise `runtime_observation`).

**Changed (all overlay-only; Phase A–E digest pins are unchanged):**

| Item | v2 | v3 (this amendment) | Rationale |
|---|---|---|---|
| Edge e2 (adopted capsule → action) | absent | `CapsuleTransferConfig.adoption_effect_action=True`, `adoption_substitutable_actions=("WAIT",)`; the adopted payload replaces `WAIT` in the receiver and pays that action's codon cost | manipulation must be able to act |
| Capsule payload | `("EMIT_NEXUS",)` | `("EMIT_NEXUS", <emitter's last executed non-signalling action>)` (only when the knob is on) | content must carry behaviour so a content scramble is meaningful |
| Population roles | 1 emitter, 10 eaters, 5 waiters | index % 4: 0 → good emitter `EAT_LUMEN,EMIT_NEXUS,WAIT`; 1 → poor emitter `SENSE_DANGER,EMIT_NEXUS,WAIT`; 2,3 → receiver `WAIT×3` | source quality must vary |
| Food | even cells, 12 ATP, refill never under organisms | every cell, 2 ATP, `respawn_under_organisms=True`, `respawn_draws_per_tick=population` | `EAT_LUMEN` sustainably +1.2/tick; `WAIT` −0.1; `SENSE_DANGER` −0.4 |
| Primary outcome | last-tick composite selection fitness | **receiver mean terminal runtime ATP** (`receiver_mean_terminal_runtime_atp`) | the DAG's ATP node, on the treated units; the composite score is kept as a secondary descriptive field (`legacy_terminal_selection_fitness`) |
| Treatment threshold | 2.0 | **1.5** (between poor 1.0 and good 3.0 per-tick source fitness, pilot 1000–1009) | gate must bind |
| Dose ladder | {0,1,2,4}, monotone Spearman | {0.0, 1.5, 4.0}, **pattern test** (see §4) | source fitness is discrete on this substrate; monotonicity is the wrong prediction above the top source |
| Positive control | none | `oracle_capsule` arm: poor emitters replaced by good emitters, gate off | shows the channel *can* move the outcome |
| Manipulation check | none | §3 | a null without it is `assay_invalid` |

`max_adoptions_per_organism` is 1 per tick (a receiver's bias is the last
adopted payload). `accept_provisional_source_fitness` stays `True`: on this
substrate emitted capsules carry `LAST_KNOWN` fitness from the previous
tick, and provisional values are computed from the real trace, not
defaulted to zero; the threshold applies to them identically.

---

## 3. Manipulation check (assay validity, evaluated before any p-value)

All conditions must hold or the campaign is `assay_invalid` and ClaimGate
stays at `runtime_observation`:

- `source_bias_on`: mean bias-applied events per seed > 0; mean adoptions
  rejected with `source_fitness_below_threshold` > 0; adopted payload set
  ⊆ {`EAT_LUMEN`}.
- `source_bias_off`: adopted payload set contains `SENSE_DANGER`.
- `capsules_off`: adoptions = 0 and bias-applied events = 0.
- `capsules_shuffled`: adoptions > 0.
- `oracle_capsule` mean outcome > `capsules_off` mean outcome.
- Not all seeds have bitwise-identical result digests for
  `source_bias_on` vs `source_bias_off`.
- Existing v2 checks remain: treatment adoptions > 0; treatment extinction
  rate < 1.

---

## 4. Hypotheses (restated on the v3 outcome)

**Primary H1.** `source_bias_on` > `source_bias_off` on receiver mean
terminal runtime ATP (paired by seed).

**Auxiliary H1.** `source_bias_on` > `capsules_shuffled`, and
`capsules_shuffled` does **not** beat `capsules_off` (lower 95 % BCa bound
of the paired delta `shuffled − off` ≤ 0). v2 predicted equivalence; under
v3 a scrambled payload is a real, costly action, so the correct
negative-control prediction is "scrambled content does not help", not
"scrambled content is neutral". `shuffled < off` is an allowed outcome.

**Dose H1 (pattern, Grimm et al. 2005 pattern-oriented).** With
`FITNESS_WEIGHTED` adoption and thresholds t ∈ {0.0, 1.5, 4.0}:
outcome(1.5) > outcome(0.0) **and** outcome(1.5) > outcome(4.0).
Statistic S = (m₁.₅ − m₀) + (m₁.₅ − m₄); one-sided p from 10 000
within-seed level permutations (seed 20260911); supported if the pattern
holds descriptively and p < 0.05.

**Decision rule for `intervention_supported`** (all required):
research scale (n = 30, 40 × 16); tier `research_grade_benchmark_candidate`;
replay matched; assay valid (§3); H1 vs `source_bias_off` CI excludes 0 and
Holm p < 0.05; H1 vs `capsules_shuffled` CI excludes 0 and Holm p < 0.05;
`capsules_shuffled` vs `capsules_off` lower CI bound ≤ 0; dose pattern
supported.

---

## 5. What a positive result would and would not mean

A positive result means: *in this designed overlay, gating capsule
adoption on emitter fitness causally raised receiver energy through the
adopted action.* Roles, payloads and food are designed, not evolved. It is
not knowledge transfer, communication intelligence, collective
intelligence, OEE, Tokyo Type 1, or Avida parity. Ceiling:
`intervention_supported` (CLAIMS.md §5 level 3) at most.

---

## 6. References

- Okasha S., Otsuka J. (2020) The Price equation and the causal analysis of
  evolutionary change. *Phil. Trans. R. Soc. B* 375:20190365.
- Goldsby H.J., Dornhaus A., Kerr B., Ofria C. (2012) Task-switching costs
  promote the evolution of division of labor and shifts in individuality.
  *PNAS* 109(34):13686–13691. (isolation test / negative control logic)
- Grimm V. et al. (2005) Pattern-oriented modeling of agent-based complex
  systems. *Science* 310:987–991.
- Nosek B.A., Ebersole C.R., DeHaven A.C., Mellor D.T. (2018) The
  preregistration revolution. *PNAS* 115(11):2600–2606. (transparent,
  pre-analysis amendments)
- Lakens D. (2017) Equivalence tests. *Soc. Psychol. Personal. Sci.*
  8(4):355–362. (why the v2 "≈ by CI-includes-0" rule was weak and is
  replaced by a one-sided non-superiority bound here)

Smoke scale for CI is 12 seeds × 8 ticks × 8 organisms (was 6 × 4): the
smallest overlay on which every §3 check can pass. Smoke stays
`exploratory_only`.
