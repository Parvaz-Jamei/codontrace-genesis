# CLOSED_LOOP_DESIGN_STORM — 2026-09-25

**Repo tip:** `343a51250f59fe07fc74b8a29c40440eaaab370a`  
**Mode:** DESIGN ONLY — no implementation, no new meters, no open-problem SF tests.  
**Storm:** ×6 rounds · 4 personas (LoopArchitect, EcoEvo, CausalHonesty, XFieldInnov)  
**Local stamp:** 2026-09-25 00:44 +0330 (Asia/Tehran)

---

## 0. Executive verdict

### EN — why tip `343a512` is a **skeleton**, not a closed loop

Prior «8 gates green» (`docs/handoff/ENGINE_COMPLETE_GATES.md`, `ENGINE_COMPLETE_STATUS.md`) is an **overclaim** for *scientific closed-loop* readiness. Those gates check plumbing (birth/death counters fire, ATP ledger is called, InheritAttached is invoked, digests replay). They do **not** establish:

1. **One life-loop.** `HostParasiteGenesisPath` advances `HostParasiteWorld.tick()` then optionally `GenesisEngine.run_ticks(1)` — two clocks side-by-side. HP registry members are **not** `GenesisEngine` organisms (`host_parasite_genesis_path.py:60–67`, `engine.py` / `GenesisEngine` organism spine).
2. **Selection-from-interaction.** Birth/death are mostly coin-flip profile probabilities (+ optional fixed `birth_energy_cost` / `basal_energy_cost`). Offspring get a **fresh** `ATPAccount(initial_energy)`; parent residual energy is **explicitly not partitioned** (`host_parasite_world.py:1127–1129`). Fitness is not earned from coupling outcomes.
3. **Genetic harm/help.** Coupling amount is a **profile float** (`coupling_amount`, default `0.1`), not decoded from mutable genome loci (`host_parasite_world.py:211–212, 952–957`). Legacy steal defaults remain fixed `0.8` in phenotype-coupling campaigns (`host_parasite_infection_phenotype_coupling.py:25`). Fixed transfer ≠ science.
4. **Freeze one side.** `ScheduleLock` freeze snapshots opaque `state_bags` only (`schedule_lock.py:429–430`; applied at `host_parasite_world.py:1233–1238`). Mutate / birth / death **still run** on the locked role in the same tick (`1257–1295`). Freeze-as-causal-arm is incomplete.
5. **Ablation that kills the effect.** Existing `ablation_preset` clears template bags once (`839–851`); there is no gene-locus ablation of a coupling kernel that must nullify measured energy flow under seed-replay.
6. **SF_TS1 is fake-green for open FRQ.** `run_mechanism_archive(..., mechanism="match_linked_cycle")` **writes** `type_id = (tick // period) % loci` into both pops each tick (`time_shift_assay.py:635–649`). That is clock-written type cycling, **not** evolved FRQ from a closed HP life-loop. Reject as open-problem green.

**Closed loop (definition binding before any problem campaign):** both populations are real organisms inside the GenesisEngine life-loop; energy moves through engine ATP accounts; harm/help comes from mutable genes; freeze one side works; bit-identical replay holds; ablating that gene kills the effect under seed-replay of both runs.

### FA — حکم اجرایی

نوک `343a512` اسکلت لولهٔ فیزیکی است، نه حلقهٔ بستهٔ علمی. ادّعای «۸ دروازه سبز» برای آمادگی مسئلهٔ باز **رد** می‌شود: دو ساعت جدا، تولد/مرگ سکه‌ای، انرژی فرزند تازه نه تقسیم والد، جفت‌سازی از پارامتر ثابت نه ژن جهش‌پذیر، فریز فقط کیف حالت، و SF_TS1 چرخهٔ تایپ با ساعت نوشته‌شده — نه FRQ تکاملی. تا حلقهٔ بسته با دروازه‌های ابطال‌پذیر (ablation + replay) قبول نشود، هیچ کمپین مسئلهٔ باز مجاز نیست.

---

## 1. Evidence from code (file:line)

| Gap | Evidence |
|-----|----------|
| Two clocks / HP ≠ Genesis organisms | `src/codontrace/genesis/host_parasite_genesis_path.py:60–67` — `world.tick()` then `engine.run_ticks(1)`; docstring `:11–12` admits “alongside”. `GenesisEngine` builds `GenesisOrganism` list in `src/codontrace/engine.py` (~2207+); HP members live only in `PopulationRegistry` inside `HostParasiteWorld`. |
| Coin-flip demography | `host_parasite_world.py:227–230` defaults birth/death probs `0.0`; `_birth_role` `:1094` `birth_rng.random() >= birth_prob`; `_death_role` `:1199` coin-flip OR starvation only if `basal_energy_cost > 0`. |
| Fresh energy bag; no partition | `:1127–1129` comment + `ATPAccount(float(self.profile.initial_energy))`. Core `ATPAccount` in `src/codontrace/energy.py:71–163` has debit/credit; no birth-partition API used by HP. |
| Profile coupling ≠ genetic | `:211–212` `coupling_amount` / `coupling_loss_fraction`; `_couple_attached_pairs` `:952–957` builds `EnergyCoupling(..., amount=self.profile.coupling_amount)`. Genomes mutate (`:1056–1070`) but **do not** set coupling amount. |
| Fixed 0.8 steal (legacy) | `host_parasite_infection_phenotype_coupling.py:25` `DEFAULT_STEAL = 0.8`. |
| Freeze bags only | `life_loop/schedule_lock.py:429–430`; HP tick `:1233–1238` restores bags then still mutates/births/deaths `:1257–1295`. |
| Ablation = bag preset, not gene→effect kill | `:839–851` `apply_ablation` on `state_bags`; no “zero coupling gene → zero net transfer” accept gate in `tests/engine_complete/`. |
| Bit-identical HP replay (plumbing OK) | `tests/engine_complete/test_engine_complete_gates.py:242–263` — digests match; necessary but **not** sufficient for closed-loop science. |
| SF_TS1 clock-written cycle | `life_loop/time_shift_assay.py:635–649` `type_id = (tick // period) % loci`; campaign `open_problem_20260925_time_shift.py` scores that mechanism as SF_TS1 PASS. Owner: **reject as fake-green**. |
| Sexual recombination exists on Genesis pop API, unused by HP tick | `genesis/population.py` sexual/recombine paths (~1544+, ~2317+); HP `_birth_role` is asexual copy + optional point mutation only. |
| Prior gate doc overclaim | `docs/handoff/ENGINE_COMPLETE_GATES.md` marks gates 1–8 PASS; `ENGINE_COMPLETE_STATUS.md` claims engine-complete. Owner correction binds: reject as closed-loop ready. |

---

## 2. Mandatory external search (citations)

| Topic | Finding | Cite |
|-------|---------|------|
| Morran sex maintenance | Coevolving *S. marcescens* maintains outcrossing in *C. elegans*; obligate selfing extinct under coevolution. DOI **resolves**. | Morran et al. 2011 *Science* [10.1126/science.1206360](https://doi.org/10.1126/science.1206360) |
| Virulence–transmission | Trade-off hypothesis; plant-virus evidence thin/mixed; Alizon–Froissart line. DOI **resolves**. | Froissart et al. 2010 *Phil. Trans. R. Soc. B* [10.1098/rstb.2010.0068](https://doi.org/10.1098/rstb.2010.0068); Doumayrou et al. 2013 *Evolution* [10.1111/j.1558-5646.2012.01780.x](https://doi.org/10.1111/j.1558-5646.2012.01780.x) |
| Decaestecker time-shift / FRQ | Pond-sediment time-shift; Red Queen archive. DOI cited in-repo and literature. | Decaestecker et al. 2007 *Nature* [10.1038/nature06291](https://doi.org/10.1038/nature06291); Brockhurst et al. 2014 [10.1098/rspb.2014.1382](https://doi.org/10.1098/rspb.2014.1382) |
| Symbulation causal levers | Host & symbiont **interaction values** ∈ [−1,+1], **mutate** each reproduction (Gaussian σ≈0.002); VT rate, spatial structure, partner-choice tags as experimental ablations/manipulations — not denser sim alone. | [Symbulation overview](https://symbulation.readthedocs.io/en/latest/QuickStartGuides/0-Overview.html); Vostinar & Ofria 2019 *Artif. Life* [pubmed 30681912](https://pubmed.ncbi.nlm.nih.gov/30681912/); ALIFE partner-choice [10.1162/isal.a.885](https://doi.org/10.1162/isal.a.885); review [10.3389/fevo.2021.739047](https://doi.org/10.3389/fevo.2021.739047) |
| Avida genetic virulence / energy at birth | `PARASITE_VIRULENCE`, `VIRULENCE_SOURCE` (config / inherited / host-controlled) + mut rate; `ENERGY_GIVEN_AT_BIRTH`, `FRAC_PARENT_ENERGY_GIVEN_TO_ORG_AT_BIRTH`. | [avida.cfg](https://github.com/devosoft/avida/blob/master/avida-core/support/config/avida.cfg); Dolson virulence mut patch; Zaman et al. PLoS Biol [10.1371/journal.pbio.1002023](https://doi.org/10.1371/journal.pbio.1002023) |

**Advantage vs Symbulation (owner binding):** effect → ablate cause → effect dies → seed-replay **both** runs. Not “denser simulation.”

---

## 3. Six storm rounds

### R1 — LoopArchitect: unify populations into GenesisEngine organisms

**Persona aim:** one clock, one organism type, HP as thin profile.

**Minutes**

- Today’s bridge is honest about being a **side-by-side orchestrator** (`HostParasiteGenesisPath`), not unification. Calling that “registry participates in GenesisEngine life-loop” (gate 6) confuses *lockstep ticking* with *shared organismhood*.
- Target architecture (domain-free primitives; HP thin):
  1. Every demographic individual is a `GenesisOrganism` (or thin wrapper) owned by `GenesisEngine` / population runner.
  2. Roles `primary`/`secondary` are **opaque tags** / schedule partitions on the same organism table — not a second world class with its own birth RNG.
  3. Attachment / match / energy-coupling stay in `life_loop/*` as callable primitives; `engine.py` remains free of infection vocabulary (keep BAIC/ClaimGate pins).
  4. `HostParasiteWorld` shrinks to a **profile + wiring** that registers two partitions, slot book, and phenotype map — tick order is engine life-loop phases, not a parallel `HostParasiteWorld.tick` sovereign loop.
- Minimal migrate path: (a) map registry member_ids → organism ids 1:1; (b) move birth/death/mutation hooks into engine reproduction schedule; (c) delete dual `run_ticks` coupling or reduce to “engine only.”

**Search cite:** Symbiosis-in-digital-evolution review — platforms that matter put host & symbiont in one evolutionary loop ([10.3389/fevo.2021.739047](https://doi.org/10.3389/fevo.2021.739047)).

**Verdict R1:** Unification is the load-bearing prerequisite; gate-6 “path” is scaffolding, not closed loop.

---

### R2 — EcoEvo: what closed loop enables for problem 1 first (Morran)

**Persona aim:** after loop, Morran sex-maintenance is first problem — design mention only.

**Minutes**

- Morran needs: (i) mixed-mating hosts with evolvable outcrossing rate; (ii) coevolving parasites that impose fluctuating epistatic selection; (iii) comparison arms: coevolving vs non-coevolving (frozen/non-adapting) pathogen; (iv) extinction of obligate selfing under coevolution as falsifiable signature ([10.1126/science.1206360](https://doi.org/10.1126/science.1206360)).
- Current tip cannot host this honestly: HP birth is asexual coin-flip; sexual recombination exists on Genesis population API but is **not** wired into HP tick; freeze does not stop parasite evolution; coupling is non-genetic.
- Closed loop enables problem 1 by making **outcrossing rate a mutable host gene** whose fitness advantage appears only when parasite genotypes track host types via genetic coupling + real demography — not via clock-written match cycles (reject SF_TS1 pattern for this claim).

**Search cite:** Morran 2011; follow-ups on selfing invasion under coevolution (PMC5088054).

**Verdict R2:** Problem 1 is blocked until loop accept; design roadmap places it first *after* accept, not before.

---

### R3 — CausalHonesty: accept gates that reject fake-green

**Persona aim:** ablation + replay or it did not happen.

**Minutes**

- Accept gates must be **falsifiable**:
  1. **Gene→effect:** enable genetic coupling; measure net energy flow / fitness skew attributable to coupling gene.
  2. **Ablate gene** (force allele to null / delete locus / clamp decode to 0); **same seed** replay; effect metric must collapse within ε.
  3. **Freeze secondary** (true schedule freeze: no mut/birth/death/gene update on frozen partition); primary continues; digests diverge from reciprocal coevo; frozen genomes bit-stable.
  4. **Bit-identical replay** of full intact run (already partial via gate 7) **and** of ablated run.
  5. Reject any SF that writes phenotypes from `(tick // period)` (`time_shift_assay.py:636`) while labeling FRQ/ERQ “evolved.”
- Symbulation-style advantage is **causal levers** (VT, spatial, interaction-value mutation), not particle count ([Symbulation docs](https://symbulation.readthedocs.io/en/latest/); [10.1101/393868](https://doi.org/10.1101/393868) preprint of spatial VT study).

**Verdict R3:** Prior engine-complete PASSes are engineering greens. Scientific accept = effect dies under ablation + dual seed-replay.

---

### R4 — XFieldInnov: interdisciplinary mechanisms that change the loop

**Persona aim:** only innovations that alter loop mechanics (not decorative meters).

**Minutes — four binding mechanism upgrades**

| Mechanism | Cross-field source | Loop change |
|-----------|-------------------|-------------|
| **Energy partition on birth** | Avida `FRAC_PARENT_ENERGY_GIVEN_TO_ORG_AT_BIRTH` / `ENERGY_GIVEN_AT_BIRTH` | Child endowment = f(parent residual, gene); selection can act on energy economy from interaction, not fresh bags. |
| **Selection-from-interaction** | Symbulation resources→reproduce-at-threshold; Avida CPU steal | Birth eligibility / death hazard derived from ATP trajectory & match outcomes, not independent Bernoulli. |
| **Genetic coupling kernel** | Symbulation mutable interaction value ∈ [−1,+1]; Avida `VIRULENCE_SOURCE` inherited+mut | Decode harm/help (and optional loss) from genome loci of one or both partners; mutate with core `Mutation`. Defaults may be zero when optional dynamics off. |
| **True freeze** | Zaman-style frozen partner assays; schedule lock semantics | Freeze partition: skip mut + demography + gene decode updates; bags **and** genomes held; bit-identical frozen side across ticks. |

**Non-innovations (refuse):** denser grids, new β₁ meters, handmade skyline FRQ, vaccine/phage/CRISPR/human-disease modules, “better than Avida” claims.

**Search cite:** Avida virulence inheritance patch; Symbulation interaction-value mutation API (`Symbiont::Mutate` / `SetIntVal`).

**Verdict R4:** Four primitives above are the minimal X-field set that turns skeleton into closed loop.

---

### R5 — Adversarial critique of R1–R4 (all four voices)

**LoopArchitect on EcoEvo:** “You cannot schedule Morran before organism unification — sex on a side clock is theater.”  
**EcoEvo on LoopArchitect:** “Unification without genetic coupling still cannot maintain sex; don’t ship empty organism ids.”  
**CausalHonesty on both:** “Gate docs already greenwashed plumbing. Any ‘unified tick’ without ablation-kills-effect is another fake-green.”  
**XFieldInnov on CausalHonesty:** “Ablation gates without energy partition will still show coin-flip demography ‘effects’ — ablate a gene that never caused birth.”  
**All four agree:** SF_TS1 clock cycle must stay labeled **mechanism toy**, never open-problem solved. Defaults-zero for optional dynamics is fine; **when enabled**, dynamics must be real (owner point 7).  
**Risk:** “Thin HP profile” rhetoric used to leave sovereign `HostParasiteWorld.tick` forever — adversarial reject.

---

### R6 — Consensus design: minimal implementable plan + accept gates + NON-goals

See §§4–7 below (single consensus artifact).

---

## 4. Consensus CLOSED LOOP design (domain-free primitives; HP thin)

### 4.1 Primitives (life_loop / engine — domain-free)

1. **Organism table (single):** ids, genomes (`SemanticGenome`), `ATPAccount`, optional attachment seats, opaque role/partition tags.
2. **GeneticCouplingKernel:** decode `(source_genome, target_genome) → (signed_transfer, loss_frac)` from declared loci; mutate via core `Mutation`; default decode **0** when loci absent / feature off.
3. **BirthEnergyPartition:** on birth, debit parent, credit child per partition gene/config (`frac_parent`, `floor`, `cap`); refuse silent fresh-bag when partition mode enabled.
4. **InteractionSelection:** birth hazard / death hazard / reproduce-threshold functions of ATP + recent coupling outcomes (composable; Bernoulli only as disabled baseline).
5. **ScheduleFreeze:** partition-level freeze skips mutation, demography, and gene-decode updates; guarantees bit-stable genomes for frozen members.
6. **AblationHook:** nullify named loci / clamp kernel to 0; first-class in replay harness.
7. **ReplayHarness:** seed+profile → bit-identical digests for intact and ablated runs.

### 4.2 HP thin profile

- Maps “host/parasite” labels → partition tags + phenotype match rule + slot book.
- **No** infection physics in `engine.py`; **no** steal_fraction in kernel types.
- Campaigns call primitives; they do not embed clock-written type cycling as “evolved FRQ.”

### 4.3 Minimal implementable plan (ordered; design-only here)

| Step | Work | Exit |
|------|------|------|
| CL0 | Owner approve this storm | Written approve |
| CL1 | Organism unification sketch → member_id ≡ organism_id; single tick owner | Architecture lock doc + failing accept tests (tests may be added only after approve — **out of scope this task**) |
| CL2 | GeneticCouplingKernel + wire to ATP debit/credit | Ablation kills transfer |
| CL3 | BirthEnergyPartition + InteractionSelection (enable flags; default off OK) | Fitness tracks coupling when enabled |
| CL4 | ScheduleFreeze true semantics | Frozen genomes invariant; coevo≠freeze |
| CL5 | Dual seed-replay accept suite (intact vs ablate) | All accept gates green |
| CL6 | Only then: problem roadmap campaigns | Morran first |

---

## 5. Accept gates (falsifiable; ablation must kill effect)

| ID | Gate | FAIL if |
|----|------|---------|
| AG1 | **Single clock:** all HP individuals are engine organisms; one tick advances both partitions | Dual `HostParasiteWorld.tick` + `engine.run_ticks` remains the demographic authority |
| AG2 | **Genetic coupling on:** decode from mutable loci; mutation changes transfer distribution (n≥30 seeds) | Transfer still equals profile constant after genome mutation |
| AG3 | **Ablation kills effect:** clamp/delete coupling loci → net coupling energy ≈ 0 and fitness skew collapses; **seed-replay both** intact & ablated | Effect remains after ablation |
| AG4 | **Energy partition on (when enabled):** child ATP derives from parent residual; ledger conserved within ε | Child always `initial_energy` while partition mode on |
| AG5 | **Selection-from-interaction (when enabled):** birth/death rates respond to coupling outcomes vs matched null (shuffle partners / zero kernel) | Demography identical under null |
| AG6 | **Freeze one side:** frozen partition genomes+bags invariant across K ticks; unfrozen evolves; reciprocal≠freeze digests | Freeze only rewrites bags while mut/birth continue |
| AG7 | **Bit-identical replay:** intact and ablated runs each self-replay | Digest drift |
| AG8 | **Anti-fake-green:** any FRQ/ERQ claim must not use clock-assigned `type_id=(tick//period)%loci` as the evolving state | SF_TS1-style PASS reused as open-problem solved |

**Defaults:** optional dynamics may default **off** (zero). Closed loop means: **when enabled, gates AG2–AG6 hold.**

---

## 6. Ordered problem roadmap AFTER accept

1. **Morran sex maintenance** — [10.1126/science.1206360](https://doi.org/10.1126/science.1206360) (outcrossing gene + coevo vs freeze pathogen; selfing extinction signature).  
2. **Virulence–transmission** — Alizon/Froissart line [10.1098/rstb.2010.0068](https://doi.org/10.1098/rstb.2010.0068) (genetic virulence ↔ transmission trade-off signatures; claim ceiling `candidate_evidence`).  
3. **FRQ vs arms race** — Decaestecker time-shift **signatures only** [10.1038/nature06291](https://doi.org/10.1038/nature06291); evolved archives from closed loop — **not** clock-written SF_TS1.  
4. **Diversity from parasite content vs crowding** — content ablation vs density controls.  
5. **Novelty exhaustion** — methods-paper ceiling; refuse “solved open problem / best-in-world.”

---

## 7. What NOT to build

- Vaccine / phage therapy / CRISPR / human clinical disease modules.  
- “Better than Avida / Symbulation” marketing claims.  
- New innovation meters, β₁-on-handmade-graphs, Fisher-on-fake-maps as substitutes for loop.  
- Open-problem SF tests before AG1–AG8.  
- Infection vocabulary inside `engine.py`.  
- Softening ClaimGate refuses (`red_queen_proved`, `arms_race_proved`, etc.).  
- Treating SF_TS1 / `match_linked_cycle` as evolved FRQ.  
- Raising claim ladder above `runtime_observation` / `candidate_evidence` without wet bridge.  
- Code changes in this storm task (docs only).

---

## 8. Ask owner

**Approve implement of CL1–CL5 (closed-loop consensus) before any problem campaign?**

- Reply: **APPROVE_CLOSED_LOOP_IMPLEMENT** or **REJECT / revise**.  
- No code lands until that approve. This document is design-only handoff.

---

## 9. Storm metadata

| Field | Value |
|-------|-------|
| Personas | LoopArchitect, EcoEvo, CausalHonesty, XFieldInnov |
| Rounds | R1–R6 |
| Tip audited | `343a512` |
| Prior 8-gates | **Rejected** as closed-loop ready |
| Deliverable path | `docs/handoff/CLOSED_LOOP_DESIGN_STORM_20260925.md` |
