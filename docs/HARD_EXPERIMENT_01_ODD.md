# HARD_EXPERIMENT_01 ODD — Genesis life-loop overlay (Wave E6)

Product: **CodonTrace Genesis** (package `codontrace`).
Experiment id: `hard_experiment_01_capsule_source_bias`.
Schema: `hard_experiment_01_v5` (Amendment 03 overlay).
Identity: `0.3.0b4.dev0`. Not a new Phase letter. Not a tag or PyPI release.

This is a Grimm et al. (2020) Overview, Design concepts, and Details (ODD)
description of the **HE01 overlay** on the Phase A `life_loop_world`
substrate. It exists so a reviewer can reimplement the overlay. It does
**not** raise ClaimGate, rewrite Amendment 01 / 02 / 03, or reopen seeds
11–40.

**ODD ≠ intelligence.** An ODD report documents structure and dynamics.
It is not model-validity proof and it is not a ClaimGate unlock. Local
policy: [`ODD_REPORTING.md`](ODD_REPORTING.md) — “ODD reports document a
model.” Honesty pointer: [`WHY_NOT_INTELLIGENCE_YET.md`](WHY_NOT_INTELLIGENCE_YET.md).

**Claim level:** `runtime_observation`. This ODD does not claim
`intervention_supported`. Wave 1d′ research (`results_v5.json`) is assay
PASS and decision-rule FAIL (`shuffled_better_than_capsules_off`). E6
does not “fix” that fail by screening.

**Amd 03 overlay (frozen for confirmatory HE01):** roles are
seed-permuted (`seed_permuted_v3_multiset`); food is every-cell
(coverage 1.0); `respawn_draws_per_tick = max(1, population_size)`.
Coverage and respawn are **not** primary Morris factors.

Grimm 2020 numbering is used below. The words Overview / Design concepts /
Details are comments only.

---

## 1. Purpose and patterns

**Purpose.** Document the HE01 overlay well enough to reimplement it, and
host the pattern criteria already used for fitness-for-purpose of the
confirmatory assay (Amendment 01). The confirmatory *question* remains:

> Does source-fitness-gated capsule transfer raise receiver mean terminal
> runtime ATP relative to (a) the same channel with the gate ablated,
> (b) capsules off, and (c) the channel on with content scrambled?

E6 itself answers a different question: which overlay knobs move
`receiver_mean_terminal_runtime_atp` on the treatment arm
(`source_bias_on`), ranked by Morris μ\* on **held-out** seeds. That
ranking is exploratory. It is not Holm / BCa / dose inference and it is
not a licence to retune Amd 01 on seeds 11–40 (Gelman & Loken 2013;
Nosek et al. 2018).

**Patterns (Amd 01; do not reopen):**

| Pattern | Role | Source |
|---|---|---|
| Manipulation check | Assay validity before any p-value | Amd 01 §3; `evaluate_hard_experiment_01_assay` |
| Dose `step_up_then_saturate` | outcome(1.5) > outcome(0.0) and outcome(1.5) > outcome(4.0) | Amd 01 §4; Grimm et al. 2005 pattern-oriented modelling |
| Non-superiority of shuffled | lower 95 % BCa bound of `shuffled − capsules_off` ≤ 0 | Amd 01 auxiliary H1 |

Wave 1d′ v5 realized the manipulation and the dose pattern on seeds 11–40,
then failed non-superiority of shuffled. E6 records that fact; it does not
screen until shuffled looks worse.

**Code.** `docs/HARD_EXPERIMENT_01_PREREG.md` (frozen bytes);
`docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_01.md` §§3–4;
`src/codontrace/genesis/hard_experiment_01.py`.

---

## 2. Entities, state variables and scales

**Entities** (see also `src/codontrace/genesis/odd.py`):

| Entity | HE01 overlay use |
|---|---|
| Organism (`GenesisOrganism`) | Assigned role: good emitter, poor emitter, or receiver |
| `PopulationState` | Fixed roster; HE01 does not use births / mutation as the estimand |
| `World2D` / ElementGrid | Lattice of Lumen food cells |
| Capsule / Nexus | Local read of emitted payloads (`read_radius`) |
| `CausalGraph` | Present; HE01 does not claim causal discovery |

**State variables (organism):** genome bits; runtime ATP; learning ATP;
position; last-tick fitness used as source fitness; adopted payload
(substitutes `WAIT` when `adoption_effect_action` is on); capsule
adoption / reject records.

**Scales:**

| Scale | Smoke (CI default) | Research (confirmatory HE01) |
|---|---|---|
| Lattice | `max(8, pop) × 4` (`runtime_profiles.life_loop_world`) | 16 × 4 |
| Population | 8 | 16 |
| Ticks | 8 | 40 |
| Initial runtime ATP | 48.0 | 48.0 |
| Role period | 4 (index % 4 → good / poor / receiver / receiver, then permuted) | same |

**Code.** `odd.py` entities; `hard_experiment_01.py` (`SMOKE_*`,
`RESEARCH_*`, `CALIBRATION_*`); `runtime_profiles.py` (`life_loop_world`).

---

## 3. Process overview and scheduling

One HE01-relevant tick on the overlay (mapped to `step_population` in
`population.py` plus capsule transfer in `capsule.py`):

1. **Metabolism.** Each live organism pays basal runtime ATP
   (`CALIBRATION_BASAL_COST`, default 0.4).
2. **Actions.** Each organism executes its genome / adopted payload
   (eat Lumen, emit Nexus, wait, or sense-danger). Codon costs apply.
3. **Capsule emit / adopt.** Emitters with `EMIT_NEXUS` write a capsule.
   Receivers read locally (`read_radius`, overlay default 6) and adopt
   under `CapsuleTransferConfig` (gate, policy, shuffle). Adopted
   payload substitutes `WAIT` (DAG edge e2; Amd 01).
4. **Resource respawn.** `RuntimeResourcePolicy` refills Lumen:
   every-cell layout; `respawn_under_organisms=True`;
   `respawn_draws_per_tick = max(1, population_size)`; amount
   `CALIBRATION_RESOURCE_AMOUNT` (default 2.0).

HE01 does not claim adaptation or learning on receivers. Roles are
assigned, then seed-permuted. There is no evolutionary division of
labour in this overlay.

---

## 4. Design concepts

Grimm 2020 design-concept checklist, HE01-specific:

| Concept | Overlay fact |
|---|---|
| Emergence | None claimed. Assigned roles ≠ evolved organisation. |
| Adaptation / learning | Not claimed for HE01 receivers. |
| Interaction | Local capsule read within `read_radius`. |
| Stochasticity | Role multiset is Fisher–Yates permuted with `RNGManager(seed, namespace="hard_experiment_01/roles")`. Food placement ignores seed (every-cell). E6 Morris draws use a **separate** namespace `hard_experiment_01/morris`. |
| Observation | Primary: `receiver_mean_terminal_runtime_atp` on surviving initial receivers. Missing last-tick outcomes are dropped, never zero-filled. |
| Collectives | Not a group-mind model. Capsule transfer is a channel, not a claim. |
| Prediction | Confirmatory prediction is the Amd 01 decision rule. E6 predicts nothing confirmatory. |
| Sensing | Local lattice resources + local capsules. |
| Interaction topology | Lattice neighbourhood, not a complete graph. |

Determinism: same spec digest + same seed replays (snapshot digest).
Claim gating is a documentation / library control, not an organism trait.

---

## 5. Initialization

For each `(seed, arm)`:

1. Start from `GenesisRuntimeProfile.life_loop_world(seed, tick_count, population)`.
2. Attach `CapsuleTransferConfig` for the arm (`_capsule_for_arm` /
   `_enabled_capsule`: `read_radius=6`, treatment
   `min_source_fitness=1.5`, `FITNESS_WEIGHTED`, shuffle off).
3. Apply survival calibration (`_apply_survival_calibration`):
   - Genomes from the v3 role multiset, **permuted** for `seed`
     (Amd 03 §3.1).
   - Food on **every** lattice cell (Amd 03 §3.2); amount 2.0.
   - Metabolism basal 0.4; initial runtime ATP 48.0.
   - Starvation consecutive ticks = 3.
   - Respawn draws = population (Amd 03 §3.3).

**Role genomes:**

| Role | Bits | Actions |
|---|---|---|
| good emitter | `101110000` | `EAT_LUMEN`, `EMIT_NEXUS`, `WAIT` — payload `EAT_LUMEN` |
| poor emitter | `010110000` | `SENSE_DANGER`, `EMIT_NEXUS`, `WAIT` — payload `SENSE_DANGER` |
| receiver | `000000000` | `WAIT` × 3; `WAIT` is substitutable by an adopted payload |

Oracle arm maps poor → good (positive control only; not a hypothesis arm).

**Code.** `calibration_role_for_index`, `permute_roles_for_seed`,
`_apply_survival_calibration`, `build_hard_experiment_01_spec`.

---

## 6. Input data

None in the simulation hot loop. Genesis already states this
(`odd.py`: “No hidden external provider input in the simulation hot
loop”). Overlay genomes, food, and capsule knobs are generated from
code + seed. Campaign artifacts record digests of the frozen prereg
siblings; those files are documentation, not runtime input.

---

## 7. Submodels

| Submodel | What it does | Code |
|---|---|---|
| Capsule transfer / source-fitness gate | Threshold or fitness-weighted adoption; optional content shuffle | `capsule.py` `CapsuleTransferConfig`; HE01 `_enabled_capsule` |
| Runtime resource policy | Renewable every-cell Lumen; draws = pop | `population.py` `RuntimeResourcePolicy` |
| Metabolism basal | Per-tick runtime ATP drain | `population.py` `MetabolicConfig` |
| HE01 overlay builders | Arms, dose ladder, role permute, food | `hard_experiment_01.py` |
| Assay / decision rule | Manipulation check + Amd 01 clauses | `evaluate_hard_experiment_01_assay`, `_decision_rule_failures` |
| ClaimGate | Library ceiling; E6 must not raise it | `claim_gate.py`; HE01 `CLAIM_CEILING` |

Pins A–E / `life_loop_world` default digests are **unchanged** by the
overlay (overlay-only). No new opcodes.

---

## Assumptions

- Overlay-only: Phase A–E pins stay green; HE01 does not mutate
  `life_loop_world` defaults.
- Assigned roles are a designed multiset, not an evolved organisation.
- Every-cell food + full respawn draws are the Amd 03 confirmatory
  ecology. Amd 02 sparse food remains a failed-calibration trail.
- Primary outcome is receiver terminal runtime ATP, not composite
  selection fitness (kept as `legacy_terminal_selection_fitness`).
- E6 Morris factors are overlay knobs, not a new estimand.
- Named RNG namespaces keep E6 trajectory draws off the HE01 analysis
  stream (`hard_experiment_01/roles`).

---

## Limitations

- **ODD ≠ intelligence.** Completing this document is not evidence of
  mind, agency, or a ClaimGate label above `runtime_observation`.
- v5 decision rule **failed** on `shuffled_better_than_capsules_off`
  (shuffled mean 42.314 vs `capsules_off` 28.000; assay otherwise
  valid). E6 must not treat Morris ranks as a repair of that clause.
- `capsules_off` sd = 0 is **structural** on this substrate: WAIT-only
  receivers never eat; basal 0.4 + WAIT 0.1 over 40 ticks from ATP 48
  → 28 on every seed (Amd 03 §1).
- Capsule adoption is not knowledge transfer. Source-fitness gating is
  not communication. Last-tick ATP is not evolved instinct or open-ended
  evolution.
- Environmental knobs are world parameters (practice as in designed
  resource maps; Ofria & Wilke 2004; Dolson et al. 2017). They are not
  a platform-parity claim.
- Morris μ\* is a qualitative screen (Morris 1991; Campolongo et al.
  2007). It is not Sobol \(S_i/S_{Ti}\), not a p-value, and not a
  ClaimGate input (Saltelli et al. 2008).

---

## Claim level

**`runtime_observation`.**

This field is mandatory in Genesis ODD (`MANDATORY_ODD_SECTIONS` in
`odd.py`). Recording it here does not unlock or raise ClaimGate.

This ODD does not claim `intervention_supported`. A later research
campaign could request that existing label only if every Amd 01
decision-rule clause actually passes on a valid confirmatory run.
v5 did not. E6 cannot change that.

---

## Simulation experiments (Grimm 2020 Supplement S7)

Morris elementary-effects screening is a **sibling** of this ODD, not
part of the confirmatory prereg:

- Design: [`hard_experiment_01/morris_e6_design.md`](hard_experiment_01/morris_e6_design.md)
- Harness: `src/codontrace/genesis/hard_experiment_01_morris.py`
- Optional smoke artifact: [`hard_experiment_01/morris_e6_smoke.json`](hard_experiment_01/morris_e6_smoke.json)

Primary screen \(k=4\): `read_radius`, `min_source_fitness` (treatment
knob, not the confirmatory dose analysis), `basal_runtime_atp_cost`,
`resource_amount`. \(r=10\) trajectories; \(N=r(k+1)=50\) design points
at default research design (each point may average \(n_{\mathrm{seed}}\)
held-out seeds). Default **executable** scale is smoke (8 ticks × 8 pop)
for CI cost.

**Frozen (not in primary \(k=4\)):** food coverage = 1.0;
`respawn_draws_per_tick = max(1, pop)`; role-permutation algorithm;
seeds 11–40; Amd 01 decision rule.

**Seeds:** held-out exploratory set 2000–2009 only. Never 11–40
(analysis). Never 1000–1009 (pilot).

**Outcome \(Y\):** `receiver_mean_terminal_runtime_atp` on
`source_bias_on`. Report \(\mu^*,\mu,\sigma\). Label
`exploratory_only`; ceiling `runtime_observation`.

Optional coverage / respawn factors, if ever run, must be a separate
`exploratory_only` artifact and must not feed ClaimGate or Amd text.

---

## References

1. Grimm, V., Railsback, S. F., Vincenot, C. E., et al. (2020). The ODD
   protocol … second update. *JASSS, 23*(2), 7.
   https://doi.org/10.18564/jasss.4259
2. Grimm, V., Berger, U., DeAngelis, D. L., Polhill, J. G., Giske, J.,
   & Railsback, S. F. (2010). The ODD protocol: A review and first
   update. *Ecological Modelling, 221*(23), 2760–2768.
   https://doi.org/10.1016/j.ecolmodel.2010.08.019
3. Grimm, V., Berger, U., Bastiansen, F., et al. (2006). A standard
   protocol for describing individual-based and agent-based models.
   *Ecological Modelling, 198*, 115–126.
   https://doi.org/10.1016/j.ecolmodel.2006.04.023
4. Grimm, V., et al. (2005). Pattern-oriented modeling of agent-based
   complex systems. *Science, 310*(5750), 987–991.
   https://doi.org/10.1126/science.1116681
5. Morris, M. D. (1991). Factorial sampling plans for preliminary
   computational experiments. *Technometrics, 33*(2), 161–174.
   https://doi.org/10.1080/00401706.1991.10484804
6. Campolongo, F., Cariboni, J., & Saltelli, A. (2007). An effective
   screening design for sensitivity analysis of large models.
   *Environmental Modelling & Software, 22*(10), 1509–1518.
   https://doi.org/10.1016/j.envsoft.2006.10.004
7. Saltelli, A., et al. (2008). *Global Sensitivity Analysis: The
   Primer.* Wiley.
8. Gelman, A., & Loken, E. (2013). The garden of forking paths.
   http://www.stat.columbia.edu/~gelman/research/unpublished/p_hacking.pdf
9. Nosek, B. A., et al. (2018). The preregistration revolution. *PNAS,
   115*(11), 2600–2606. https://doi.org/10.1073/pnas.1708274114
10. Ofria, C., & Wilke, C. O. (2004). Avida: A software platform for
    research in computational evolutionary biology. *Artificial Life,
    10*(2), 191–229. https://doi.org/10.1162/106454604773563612
11. Dolson, E., Pérez, A., Olson, R., & Ofria, C. (2017). Spatial
    resource heterogeneity increases diversity and evolutionary
    potential. https://doi.org/10.1101/148973
12. Ojha, V., Timmis, J., & Nicosia, G. (2022). Assessing ranking and
    effectiveness of evolutionary algorithm hyperparameters using
    global sensitivity analysis methodologies. arXiv:2207.04820.

---

## What this document is not

- Not a ClaimGate raise and not `intervention_supported`.
- Not a rewrite of Amd 01 / 02 / 03 or of `results_v5.json`.
- Not a re-analysis of seeds 11–40.
- Not Sobol / FAST variance decomposition.
- ODD ≠ intelligence.
