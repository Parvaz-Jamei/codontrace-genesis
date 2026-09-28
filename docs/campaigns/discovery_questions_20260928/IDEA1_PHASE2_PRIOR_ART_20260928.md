# Idea 1 — Phase 2 prior-art report: costly causal experimentation vs reactive learning

**Date:** 2026-09-28 (Asia/Tehran)  
**Campaign:** CodonTrace Genesis discovery — Idea 1, Track C  
**Repo context:** `Parvaz-Jamei/codontrace-genesis` (box path `/workspace/codontrace-genesis`)  
**Phase-1 anchor:** `docs/campaigns/discovery_questions_20260928/IDEA1_PHASE1_PROBLEM_BOUNDARY.md`  
**Claim ceiling:** `phase2_design` / prior-art only — **not** a discovery claim; **not** a first-in-world claim  
**Search mode:** live WebSearch + Crossref API DOI verification (2026-09-28)  
**Primary estimand (phase 1):** survival share to horizon T (run-level)

**Locked question (phase 1):** When do lineages evolve costly selective interventions that discriminate rival explanations (active causal experimentation), vs reactive learning / pattern memory, under survival/reproduction/resource limits and a changing world? Boundary of transition from learned reaction to costly causal search.

**Standing locks respected:** domain-free ledger (contact/ATP); no infection physics in `engine.py`; no Euler-in-loop; no Avida steal into engine; no second population engine; sealed seeds `801–816` untouched; runners off; EvoSCM deferred preprint watch only; reward exploration ≠ rival-hypothesis discrimination.

---

## 1. Bottom line

**Closest published designs** fall into three ingredient clusters, not one assembly:

1. **Evolved reactive / associative learning under change** — digital and theoretical lineages evolve learning rules, memory/exploration parameters, or associative modules when environments vary across generations but are relatively stable within a lifetime (Giannakakis et al. 2024; Pontes et al. 2020; Ferguson & Ofria 2023; Arehart & Adler 2023; Kozielska & Weissing 2024; Eliassen et al. 2007; Turner et al. 2024). Selective value is typically reward / intake / task success, not discrimination of locked rival world-explanations.
2. **Engineered active / interventional causal design** — optimal or amortized policies choose interventions to recover causal structure or maximize information about graphs (Zhang et al. 2023; Zemplenyi & Miller 2023; Gong et al. 2023; Bramley et al. 2015; Fox & Ghosh 2024; Jiang & Lucas 2024). These assume an experimenter or trained design policy; they do not ask when **evolution** pays survival cost for discrimination under lifespan and world-change constraints.
3. **Intrinsic motivation / curiosity / open-ended exploration** — competence-progress, novelty, and POET-style coevolution of challenges drive exploration without external task reward (Oudeyer et al. 2007; Laversanne-Finot et al. 2021; Wang et al. 2019 POET; Enhanced POET 2020 PMLR). Exploration is usually for skill coverage or novelty, not for scoring which of two pre-registered causal accounts is true on a survival ledger.

**Joint surface — NOT found:** We are not aware of a published precedent for a **pre-registered evolutionary invasion regime** in which lineages pay survival-cost interventions whose selective value is measured by **discrimination of rival world-explanations** (not reward gain alone), with run-level survival-share replication, explicit reactive and reward-exploration rival arms, and an honest non-emergence outcome when a named selective barrier (cost / lifespan / change-rate) holds.

**Joint surface — FOUND as separate ingredients:** learning-cost × lifespan × environmental change; evolved associative learning in digital organisms; interventional experiment selection for causal structure; curiosity-driven exploration. The **assembly** (discrimination assay + costly evolutionary arm + reactive/reward controls + run-level invasion margin + barrier reporting) is the live gap for phase-2 design.

**Already solved?** **NO** — not as the phase-1/2 assembly. **Caveat:** absence of a hit in this search is **not** proof of uniqueness. Gap wording stays “we are not aware of a published precedent for …”. Claim ceiling remains `phase2_design` / prior-art; ceiling for subsequent empirical work is `phase2_design` (not discovery).

---

## 2. Verified closest works table

Every DOI below was queried live against `https://api.crossref.org/works/{DOI}` on 2026-09-28 unless marked FAIL / deferred. Preprints are flagged and not used as locked journal precedent.

| # | Citation | DOI | Crossref | What it does | What it does NOT cover |
|---|---|---|---|---|---|
| 1 | Giannakakis, Khajehabdollahi & Levina 2024 *Artif. Life* — Network bottlenecks and task structure control the evolution of interpretable learning rules in a foraging agent | `10.1162/artl_a_00458` | **OK** (2024) | Evolved learning rules in an ALife foraging agent; task/network structure shapes interpretable update rules. | No rival-explanation discrimination interventions; no survival-share invasion of costly causal search vs reactive arms. |
| 2 | Arehart & Adler 2023 *Proc. R. Soc. B* — A minimal model of learning: cost and benefit in changing environments | `10.1098/rspb.2023.1084` | **OK** (2023) | Correlational memory (α) + exploration (ε) vs fixed strategies; fitness benefit depends on change regime; explore–exploit cost made explicit. | Abiotic restless resources; reward/intake objective; **not** interventional discrimination of rival causal accounts. |
| 3 | Kozielska & Weissing 2024 *PLOS Comput. Biol.* — Neural network model for evolution of learning in changing environments | `10.1371/journal.pcbi.1011840` | **OK** (2024) | Evolved network learning under frequency/magnitude of change and lifespan; when learning invades vs fixed control. | Reactive / reward learning architectures; no locked rival-hypothesis `do` assay. |
| 4 | Eliassen, Jørgensen, Mangel & Giske 2007 *Oikos* — Exploration or exploitation: life expectancy changes the value of learning | `10.1111/j.2006.0030-1299.15462.x` | **OK** (2007) | Shorter life expectancy shifts foragers toward exploitation; sampling early season trades intake for information. | Information for patch quality, not causal-structure discrimination under lineage invasion. |
| 5 | Turner, Morgan & Griffiths 2024 *Proc. R. Soc. B* — Environmental complexity and regularity shape the evolution of cognition | `10.1098/rspb.2024.1524` | **OK** (2024) | Environmental complexity/regularity regimes that favour evolved cognition. | Cognition as general capacity; not costly selective interventions that separate rival explanations. |
| 6 | Pontes, Mobley, Ofria, Adami & Dyer 2020 *Am. Nat.* — The evolutionary origin of associative learning | `10.1086/706252` | **OK** (2020) | Associative learning evolves by selection in digital organisms when environments vary across generations but are stable within a lifetime; modular stepwise origin from reflexes. | **Reactive associative learning only** — strong H1-adjacent negative precedent; no interventionist rival-hypothesis tests. |
| 7 | Ferguson & Ofria 2023 *ALIFE* — Potentiating mutations facilitate the evolution of associative learning in digital organisms | `10.1162/isal_a_00684` | **OK** (2023) | Lineage replays isolate potentiating mutations for associative learning. | Potentiation of **associative** learning, not evolved costly causal experimentation. |
| 8 | Zhang, Cammarata, Squires, Sapsis & Uhler 2023 *Nat. Mach. Intell.* — Active learning for optimal intervention design in causal models | `10.1038/s42256-023-00719-0` | **OK** (2023) | Optimal active selection of interventions for causal models / design. | Engineered design policy; not evolutionary invasion under survival cost, lifespan, world-change. |
| 9 | Zemplenyi & Miller 2023 *Bayesian Anal.* — Bayesian optimal experimental design for inferring causal structure | `10.1214/22-ba1335` | **OK** (2023) | Bayesian OED for causal-structure inference. | Experimenter-side design; no lineage fitness / survival-share estimand. |
| 10 | Gong, Gerstenberg, Mayrhofer & Bramley 2023 *Cogn. Psychol.* — Active causal structure learning in continuous time | `10.1016/j.cogpsych.2022.101542` | **OK** (2023) | Humans choose continuous-time interventions balancing information vs inferential complexity. | Human experiment selection; not evolved under resource/survival limits in digital lineages. |
| 11 | Bramley, Lagnado & Speekenbrink 2015 *JEP:LMC* — Conservative forgetful scholars: learning causal structure through interventions | `10.1037/xlm0000061` | **OK** (2015) | People learn causal structure via sequences of interventions with conservative/forgetful updating. | Cognitive science of intervention sequences; not evolutionary selection of costly discrimination. |
| 12 | Jiang & Lucas 2024 *Comput. Brain Behav.* — Actively learning to learn causal relationships | `10.1007/s42113-023-00195-0` | **OK** (2024) | Transfer of abstract causal overhypotheses improves future experiment selection. | Meta-learning of experiment policies in cognition/ML; not lineage invasion on a survival ledger. |
| 13 | Fox & Ghosh 2024 *Mach. Learn. Sci. Technol.* — Active causal learning for decoding chemical complexities with targeted interventions | `10.1088/2632-2153/ad6feb` | **OK** (2024) | Active causal sampling + interventions in chemical design space (QM9 dipole). | Domain chemistry design loop; not evolutionary biology / ALife invasion under ATP cost. |
| 14 | Oudeyer, Kaplan & Hafner 2007 *IEEE TEVC* — Intrinsic motivation systems for autonomous mental development | `10.1109/tevc.2006.890271` | **OK** (2007) | Learning-progress intrinsic motivation drives staged exploration. | Curiosity / competence progress ≠ rival-explanation discrimination; not survival-share evolutionary invasion. |
| 15 | Laversanne-Finot, Péré & Oudeyer 2021 *Front. Neurorobot.* — Intrinsically motivated exploration of learned goal spaces | `10.3389/fnbot.2020.555271` | **OK** (2021) | Intrinsic exploration over learned goal spaces. | Goal competence, not locked rival causal accounts on a ledger. |
| 16 | Wang, Lehman, Clune & Stanley 2019 GECCO — POET (Paired Open-Ended Trailblazer) | `10.1145/3321707.3321799` | **OK** (2019) | Coevolution of environments and agents for open-ended challenge invention. | Open-ended skill/challenge coverage; not discrimination of rival world-explanations under ATP cost. |
| 17 | Wang, Lehman, Rawal, Zhi, Li, Clune & Stanley 2020 — Enhanced POET (ICML / PMLR v119:9940–9951) | PMLR proceedings (no Crossref DOI resolved this session) | **Unchecked Crossref** — verified via live PMLR page `proceedings.mlr.press/v119/wang20l.html` | Unbounded invention of learning challenges + solutions; PATA-EC diversity. | Same gap as POET: not evolutionary costly causal discrimination vs reactive arms. |
| 18 | Lehman & Stanley 2011 *Evol. Comput.* — Abandoning objectives: evolution through novelty alone | `10.1162/evco_a_00025` | **OK** (2011) | Novelty search as evolutionary exploration without objectives. | Behavioral novelty ≠ causal-account discrimination; no survival-cost intervention assay. |
| 19 | Liefting, Rohmann, Le Lann & Ellers 2019 *Anim. Cogn.* — Costs of learning in a parasitoid wasp | `10.1007/s10071-019-01281-2` | **OK** (2019) | Empirical constitutive costs of fast associative learning; modest trade-offs. | Physiological cost of associative speed, not interventional causal search. |
| 20 | Giron et al. 2023 *Nat. Hum. Behav.* — Developmental changes in exploration resemble stochastic optimization | `10.1038/s41562-023-01662-1` | **OK** (2023) | Human developmental shift explore → exploit as cooling schedule. | Developmental psychology; not lineage evolution of costly causal interventions. |
| 21 | Pelz & Kidd 2020 *Phil. Trans. R. Soc. B* — The elaboration of exploratory play | `10.1098/rstb.2019.0503` | **OK** (2020) | Exploratory play as information-seeking elaboration. | Play/exploration framing; not evolutionary invasion under resource limits with discrimination assay. |

### Deferred / preprint-only (not locked journal precedent)

| Item | ID | Status | Why adjacent, not lock |
|---|---|---|---|
| **EvoSCM** — Scientific Belief Revision Through Causal Model Evolution and Experimentation | arXiv:`2609.01526` | Live arXiv page **OK** (2026-09-01 preprint). Crossref `10.48550/arXiv.2609.01526` → **FAIL** (HTTP 404 this session). | Maintains a **population of rival SCM hypotheses** and selects interventions that **maximally discriminate** among them — closest *mechanism language* to phase-1 discrimination. But: engineered scientific-agent loop on DiscoverPhysics-style worlds; **not** evolutionary selection under survival/ATP cost, lifespan, and world-change with run-level invasion. **Deferred literature watch only** (phase-1 lock). |
| CausalEvolve — causal scratchpad guiding evolutionary search | arXiv:`2603.14575` | Preprint; Crossref DataCite DOI **FAIL** this session. | Evolutionary program/search guided by causal factors; not ecological lineage invasion of costly discrimination. Deferred. |
| CAASL — Amortized Active Causal Induction (deep RL) | arXiv:`2405.16718` | Preprint; Crossref DataCite DOI **FAIL** this session. | Amortized intervention policy for structure learning; engineered, not evolved under survival share. Deferred. |
| IMGEP Forestier et al. 2022 *JMLR* 23(152) | JMLR (often no Crossref DOI) | Verified via live JMLR page; Crossref DOI not used as lock. | Autotelic goal exploration / curriculum; competence progress ≠ rival-explanation discrimination under ATP survival. Adjacent curiosity cluster. |

**Phase-1 cite check (all still OK):** Giannakakis `10.1162/artl_a_00458`; Arehart & Adler `10.1098/rspb.2023.1084`; Kozielska & Weissing `10.1371/journal.pcbi.1011840`; Zhang et al. `10.1038/s42256-023-00719-0`; Zemplenyi & Miller `10.1214/22-ba1335`; Turner et al. `10.1098/rspb.2024.1524`. EvoSCM remains deferred preprint (Crossref DataCite unresolved; arXiv live).

---

## 3. Kill-criteria searches run

Kill criterion for **gap-closing hit:** a single published study that jointly (i) evolves lineages that may pay **costly interventions**, (ii) scores selective value by **discrimination of rival world-explanations** (not reward alone), (iii) includes **reactive learning and/or reward-exploration** rival arms, (iv) varies **cost / lifespan / world-change**, and (v) reports invasion or honest non-emergence on a **run-level survival** (or equivalent fitness-share) estimand.

| # | Query string (cluster) | What it hit | Gap-closing? |
|---|---|---|---|
| Q1 | `active causal learning interventionist exploration evolutionary biology ALife` | CausalEvolve; CAASL; Fox & Ghosh chemistry active causal; amortized intervention design | **No** — engineered / chemistry / agent design, not evolutionary invasion under survival cost |
| Q2 | `costly information exploration exploitation evolution lifespan environmental change Arehart Adler` | Arehart & Adler 2023; Eliassen et al. 2007; Kozielska & Weissing 2024 | **No** — learning costs under change/lifespan, but correlational / reward learning |
| Q3 | `evolvable curiosity intrinsic motivation experiment selection digital evolution` | POET / Enhanced POET; Curious POET; IMGEP; Oudeyer intrinsic motivation; open-ended ER | **No** — curiosity/novelty/competence; not rival-explanation discrimination |
| Q4 | `EvoSCM evolutionary structural causal models` | EvoSCM arXiv:2609.01526 (discriminative interventions among SCM hypotheses) | **No** — closest *language*; preprint agent scientific loop; deferred |
| Q5 | `"no evolved experimentation" OR "reactive only" digital organisms learning evolution` | Sparse exact-phrase hits; related Avida associative-learning / division-of-labor literature | **No** exact kill title; see Q9–Q10 for reactive-learning positives |
| Q6 | `evolution of active experimentation OR "causal intervention" OR "hypothesis testing" learning biology lifespan` | Developmental human explore→exploit (Giron); exploratory play (Pelz & Kidd); constructivist active inference | **No** — developmental/cognitive, not digital-lineage invasion |
| Q7 | `reactive learning evolution "digital organisms" OR Avida OR "artificial life" exploration cost intervention` | Avida associative learning / DoL / task-switching cost literature | **No** joint discrimination arm |
| Q8 | `"life expectancy" OR lifespan exploration exploitation learning foraging Eliassen` | Eliassen 2007 confirmed | Ingredient only |
| Q9 | `"associative learning" evolves OR evolved Avida OR "digital organisms"` | **Pontes et al. 2020** *Am. Nat.* `10.1086/706252`; Ferguson & Ofria 2023 | Strong **H1-adjacent** precedent: reactive associative learning evolves **without** interventionist causal experimentation |
| Q10 | `"learning does not evolve" OR "fixed strategy" preferred exploration cost environmental change` | Arehart–Adler regimes where learning underperforms fixed rules; Kozielska lifespan/change cells where learning fails to invade | Supports **H0/H1 barrier** language; not a discrimination-arm design |
| Q11 | `"discriminat" OR "rival" OR "competing hypotheses" intervention evolution learning cost survival` | EvoSCM discriminative interventions; learning-cost trade-off papers; no evolutionary survival-share discrimination invasion | **No** joint hit |
| Q12 | `"experiment selection" OR "discriminative intervention" OR "rival hypotheses" evolution learning cost ALife OR "digital evolution"` | Replay / potentiating-event methods; CodonTrace-adjacent tooling; EvoSCM | Methods / preprint; **not** phase-1 assembly |

**Result of kill searches:** no gap-closing hit. Near-misses either (a) evolve **reactive** learning, (b) engineer **active causal design** without evolution under survival cost, or (c) drive **curiosity/novelty** without a locked rival-explanation assay.

---

## 4. Interdisciplinary Combos A–E (phase-2 mechanism surface)

All combos respect standing locks: domain-free **contact/ATP ledger**; interventions as ledger-visible actions with real cost; generation timing via `GenerationBoundaryObserver`; **no** infection physics in `engine.py`; **no** Euler-in-loop; **no** Avida steal into engine; **no** second population engine. Falsifiable predictions are for design-digest pre-registration, not current claims.

### Combo A — Restless learning-cost schedule + locked rival-discrimination assay

- **Inspiration:** Arehart & Adler explore–exploit (α, ε); Zhang / Zemplenyi OED intervention value.
- **Mechanism:** Three arms on one ledger — (R) reactive update from observed contact/ATP outcomes; (E) reward exploration (ε-style actions that improve short-horizon ATP without a rival contrast); (D) costly `do` set whose outcome distributions are constructed so two locked world-explanations make different ledger predictions.
- **Falsifiable prediction:** In intermediate change-rate ρ and moderate cost c, arm D clears ≥ 0.15 survival-share vs best of {R, E} **only if** the discrimination assay passes. If D wins survival without assay pass → H2 FAIL (read as H1 / design FAIL). If no cell clears margin → favour H0 with named barrier (c, L, ρ).

### Combo B — Lifespan × world-change gate (Eliassen / Kozielska map)

- **Inspiration:** Eliassen life-expectancy shifts exploration value; Kozielska lifespan × change regimes for learning invasion.
- **Mechanism:** Pre-register a grid over lifespan L (generation-boundary units) and world-change rate ρ (turnover of rival-relevant ledger structure). Cost c fixed in a mid cell. Same R / E / D arms as Combo A.
- **Falsifiable prediction:** D invades only in a contiguous mid band of (L, ρ): too short L → exploration never recovers cost (H0); too fast ρ → discrimination info obsolete before use (H0); stable world → R or E suffices (H1). Outside the band, survival-share margin < 0.15 for D.

### Combo C — Evolvable curiosity propensity vs discrimination-gated curiosity

- **Inspiration:** Oudeyer learning-progress IM; IMGEP competence progress; novelty search / POET diversity drives.
- **Mechanism:** Arm C0 evolves an intrinsic “novelty / competence-progress” propensity that spends ATP on exploratory actions **without** a rival-explanation schema. Arm C1 may spend the same ATP budget only on actions that are pre-registered as discrimination interventions (schema non-empty). Compare to R and E.
- **Falsifiable prediction:** If C0 matches or beats C1 on survival-share while failing the discrimination assay, curiosity/novelty is **not** causal experimentation (H1). C1 must both clear 0.15 **and** pass discrimination to support H2. Empty schema at run time → freeze reopen.

### Combo D — EvoSCM-style disagreement-maximising `do` (deferred tech, ledger-mapped)

- **Inspiration:** EvoSCM population disagreement for discriminative interventions (preprint watch only); Bramley / Gong human intervention sequences.
- **Mechanism:** Maintain a **small finite set** of ledger-visible rival explanations (not a second population engine — hypotheses are state on the lineage, not a parallel ecology). Select allowed `do` to maximise predicted disagreement between rivals, paying ATP cost c. Update which explanation is retained after the outcome. Compare to a myopic reward `do` policy (E) and to no-`do` reactive update (R).
- **Falsifiable prediction:** Disagreement-maximising D beats myopic E in cells where cue–outcome confounding makes reward exploration systematically mis-rank actions; E beats D when rivals are already separated by observation alone (V_causal low). If D’s advantage vanishes when disagreement scoring is ablated but ATP spend is matched → discrimination criterion was doing the work (positive control). **Do not** treat EvoSCM preprint metrics as locked precedent.

### Combo E — Pontes-style associative module as explicit H1 control

- **Inspiration:** Pontes et al. 2020 evolutionary origin of associative learning; Ferguson & Ofria potentiating mutations for associative learning; phase-1 reject equating associative update with rival-hypothesis discrimination.
- **Mechanism:** Arm A evolves an associative cue→action map (reactive pattern memory) under the same (c, L, ρ) grid and ATP accounting. Arm D is the costly discrimination intervention arm. Arm E is unstructured reward exploration. No arm may silently issue discrimination interventions unless registered.
- **Falsifiable prediction:** Under within-lifetime stability + across-generation change (Pontes regime), A invades and D does not (H1). Under regimes where cues are confounded with the true ledger parent of ATP drain, A collapses and D clears ≥ 0.15 **iff** assay passes (H2). If D wins without assay pass → design FAIL.

**Shared operational locks for all combos (must be filled in design digest before any run):** rival explanation pair + distinct ledger predictions; allowed intervention set, cost bound, generation-boundary timing; discrimination scoring rule; inheritance/persistence of experimentation propensity; real ATP/survival cost (not cosmetic); N = runs; invasion margin ≥ 0.15 vs best rival over ≥ 6 runs when execution is later allowed.

---

## 5. Suggested Round-1 critique questions

1. Does the discrimination assay force **different** predictions from at least two locked world-explanations on ledger observables, or can reward gain alone satisfy the scorer?
2. Can arms R and E be implemented so they are **forbidden** from silently issuing discrimination interventions (design digest check)?
3. Is cost c ledger-visible and survival-coupled (ATP / mortality), or only a cosmetic counter?
4. For Combo B: is the (L, ρ) grid spaced so that H0 / H1 / H2 cells are each **reachable**, with pre-registered barrier names if D never invades?
5. Does any proposed mechanism add infection physics, domain RNG branches, Euler integration in the life loop, Avida code paths, or a second population engine? If yes → reject.
6. How is “invasion” scored strictly as **run-level survival share to T**, not Δ growth of contact pairs?
7. If D wins survival without assay pass, is the pre-registered reading **H2 FAIL → H1 / design FAIL** (not soft success)?
8. Is EvoSCM (or any preprint) cited only as deferred watch, never as journal precedent or result claim?
9. What is the minimal finite rival set (size 2?) that still makes disagreement-maximising `do` (Combo D) identifiable without smuggling a second ecology?
10. Against Pontes-style associative evolution (Combo E), what confounding structure on the ledger is required so that associative learning is predicted to **fail** while discrimination remains valuable?
11. Are sealed seeds `801–816` and `red_queen_proved = false` untouched by this design?
12. What honest non-emergence report looks like (named barrier in c / L / ρ) if no cell clears 0.15?

---

## 6. Claim ceiling reminder

- This file is **prior-art / phase2_design support only**.
- It does **not** authorise runners, pilots, or campaigns.
- It does **not** claim discovery, law, uniqueness, or “first”.
- Gap wording only: **“we are not aware of a published precedent for …”**
- Search gap ≠ uniqueness.
- Empirical ceiling after a design digest remains `phase2_design` until a later phase explicitly raises it.
- EvoSCM arXiv:2609.01526 stays **deferred preprint watch**.

---

## Appendix A — Crossref verification log (2026-09-28)

| DOI | HTTP | Notes |
|---|---|---|
| `10.1162/artl_a_00458` | 200 | Giannakakis et al. 2024 |
| `10.1098/rspb.2023.1084` | 200 | Arehart & Adler 2023 |
| `10.1371/journal.pcbi.1011840` | 200 | Kozielska & Weissing 2024 |
| `10.1038/s42256-023-00719-0` | 200 | Zhang et al. 2023 |
| `10.1214/22-ba1335` | 200 | Zemplenyi & Miller 2023 |
| `10.1098/rspb.2024.1524` | 200 | Turner et al. 2024 |
| `10.1111/j.2006.0030-1299.15462.x` | 200 | Eliassen et al. 2007 |
| `10.1086/706252` | 200 | Pontes et al. 2020 |
| `10.1162/isal_a_00684` | 200 | Ferguson & Ofria 2023 |
| `10.1016/j.cogpsych.2022.101542` | 200 | Gong et al. 2023 |
| `10.1037/xlm0000061` | 200 | Bramley et al. 2015 |
| `10.1007/s42113-023-00195-0` | 200 | Jiang & Lucas 2024 |
| `10.1088/2632-2153/ad6feb` | 200 | Fox & Ghosh 2024 |
| `10.1109/tevc.2006.890271` | 200 | Oudeyer et al. 2007 |
| `10.3389/fnbot.2020.555271` | 200 | Laversanne-Finot et al. 2021 |
| `10.1145/3321707.3321799` | 200 | Wang et al. POET 2019 |
| `10.1162/evco_a_00025` | 200 | Lehman & Stanley 2011 |
| `10.1007/s10071-019-01281-2` | 200 | Liefting et al. 2019 |
| `10.1038/s41562-023-01662-1` | 200 | Giron et al. 2023 |
| `10.1098/rstb.2019.0503` | 200 | Pelz & Kidd 2020 |
| `10.48550/arXiv.2609.01526` | **404 FAIL** | EvoSCM — cite arXiv:2609.01526 [PREPRINT]; arXiv abs page live |
| Enhanced POET PMLR v119 | No Crossref DOI this session | Verified via `proceedings.mlr.press/v119/wang20l.html` — mark **unchecked Crossref** |

---

## Appendix B — Search protocol summary

- **Clusters:** active causal / interventionist ALife; costly information × lifespan × change; evolvable curiosity / IM / experiment selection; EvoSCM; negative reactive-only / no-experimentation; associative-learning digital organisms; discriminative / rival hypotheses + survival cost.
- **Verification:** Crossref works API for every locked DOI; arXiv abs for deferred preprints; PMLR page for Enhanced POET.
- **Negatives:** Pontes associative learning (reactive evolves); Arehart/Kozielska cells where learning fails to invade (barrier language); curiosity/POET without discrimination assay.
