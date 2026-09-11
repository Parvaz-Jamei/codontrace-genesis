# Why CodonTrace Genesis is not intelligence yet

This note maps **world-authority literature** onto **what CodonTrace Genesis
actually implements**. It is an honesty document for Phase A–G plus Phase H
RAG and CI-pathway scaffolding, Phase I evidence harnesses, and Phase J
replay-verified candidate packs. It does **not**
argue that the project is close to AGI, consciousness, proved open-ended
evolution, Tokyo Type 1 *passed*, or literature-grade collective intelligence.

**Claim ceiling:** software capability / `runtime_observation` /
`oee_measurement_only` / `tokyo_type1_measurement_only` /
`collective_intelligence_candidate` (candidate only, never auto-promoted).

**Blocked by `ScientificClaimGate`:** `agi`, `open_ended_intelligence`,
`tokyo_type1_passed`, `proved_open_endedness`, `collective_intelligence`,
`proved_collective_intelligence`, `avida_replacement`, and related aliases.

ClaimGate remains the authority. Do not cite this file as evidence that
CodonTrace Genesis is “almost” intelligent. Phase H/I/J continue as
**measurement, literature RAG, and substrate engineering**, not as an
intelligence countdown.

Cross-links: [`CLAIMS.md`](../CLAIMS.md),
[`SCIENTIFIC_AUTHORITIES_2026.md`](SCIENTIFIC_AUTHORITIES_2026.md),
[`PHASE_D_LITERATURE.md`](PHASE_D_LITERATURE.md),
[`PHASE_E_LITERATURE.md`](PHASE_E_LITERATURE.md),
[`PHASE_H_CI_AI_PATH.md`](PHASE_H_CI_AI_PATH.md),
[`PHASE_I_CI_EVIDENCE.md`](PHASE_I_CI_EVIDENCE.md),
[`PHASE_J_REPLAY_CI.md`](PHASE_J_REPLAY_CI.md),
[`rag/README.md`](rag/README.md),
[`SOCIAL_COLLECTIVE_INTELLIGENCE_PROTOCOL.md`](SOCIAL_COLLECTIVE_INTELLIGENCE_PROTOCOL.md).

---

## 0. What this file is for

Digital-evolution libraries accumulate impressive *instrumentation*. That is
not the same as accumulating *intelligence*. The authorities below describe
structural barriers that current evolutionary computation and ALife systems
typically fail. CodonTrace Genesis has first-class replay, digests, and
claim gates so those failures cannot be papered over with vocabulary.

The honest sentence is:

> CodonTrace Genesis is a deterministic, replay/audit-first Python research
> library for Avida-like ecology experiments. It is **not close to AGI**.
> Measuring a barrier is not crossing it.

Phase F/H work (collective/deme payoff campaigns, group-vs-individual
contrasts and effect sizes, division-of-labor *metrics*, communication
ablation *harnesses*, literature RAG) continues under that sentence. Those
measurements remain group fitness, not intelligence.

Name the project **CodonTrace Genesis** in docs, PRs, and papers. Do not
drop the Genesis qualifier. The PyPI/import package remains `codontrace`.

---

## 1. Barrier map (literature vs CodonTrace Genesis)

Status key: **has** = callable, tested library surface; **partial** = analog
or subset; **lacks** = not present at literature grade; **blocked** = ClaimGate
forbids the corresponding claim.

| Barrier (authority) | What the literature requires | What CodonTrace Genesis has | What it lacks | Claim |
|---|---|---|---|---|
| Small pop / strong selection (Nature MI 2021) | Large *N*, weaker selection, drift/neutrality so diversity can persist | Life-loop capacity can exceed founders; fitness-proportional selection; opt-in QD | Default presets remain small-*N* research smokes; no biological-scale population + weak-selection campaign | `runtime_observation` only |
| Direct genotype→phenotype map (Nature MI 2021) | Developmental / regulatory G→P with neutrality and many-to-one mappings | Semantic/instruction genomes; translation-profile *proxy*; variable-genome tokens | No evolved developmental encoding; no major G→P complexity transition | `adaptive_gp_map_proxy` is a proxy, not biology |
| No major transitions (Nature MI 2021; Szathmáry & Maynard Smith; Michod) | New levels of individuality (cells→organisms→societies) with export-of-fitness | Deme containers, germline/soma *tags*, replicate-on-mean-fitness events | No evolved transition in individuality; tags are assigned, not discovered | `collective_intelligence` **blocked** |
| OEE necessary conditions (Soros & Stanley / Chromaria) | Nontrivial minimal criterion for birth; new opportunities to satisfy it; agent-directed interaction; unbounded phenotypic potential | AliveGate + ATP birth gates; spatial eat/survive/reproduce; Phase C fluctuating env | Chromaria-grade tests of all four conditions; unbounded phenotype; self-generated opportunity landscapes | `oee_measurement_only`; OEE **not proved** |
| Open-endedness as creative-intelligence component (Stanley) | Ongoing generation of interesting novelty, not a fixed objective | MODES/Bedau measurement; Channon step vocabulary; QD archives | Creative intelligence; unbounded adaptive novelty as a *result* | `open_ended_intelligence` **blocked** |
| Tokyo Type 1 procedure (Channon 2024) | Multi-step *test* of ongoing adaptive novelty, including shadow/normalization and multi-replicate decision | `TokyoType1MeasurementProtocol`, multi-seed campaign, opt-in shadow digest, window-sweep suite | A Type 1 **pass**. Measurement steps ≠ pass | `tokyo_type1_measurement_only`; `tokyo_type1_passed` **blocked** |
| Vocabulary gap (arXiv 2607.09560) | Invent and *stabilize* new representational primitives that change the search space | ADF/macro *proposals*, codon-table extensions as auditable metadata | Endogenous vocabulary that alters the search frame and is reused because it pays | Not open-ended intelligence |
| Verifier gap (arXiv 2607.09560) | Evaluate new primitives when payoff is only visible after future reuse; verifier may need to co-evolve | ClaimGate, contribution ledger, delayed-reward traces, instinct ablation hooks | A self-extending evaluator; future-reuse credit that is not an attribution estimate | Ledger is **not** causal proof |
| Culture/tech vs ecology (JaxLife 2024) | Embodied NN agents accumulating culture/tech while abstracting physics/chemistry | Avida-like instruction ecology + audit/replay/ClaimGate | JaxLife NN agents, culture/tech accumulation, CLIP/ASAL OE search | Complementary; **not** a port; `avida_replacement` **blocked** |
| Collective intelligence (Goldsby; GECCO 2008; demes; major transitions) | Division of labor, multilevel selection, group-over-individual payoff, heldout partners, communication ablation | Messaging buffer, role gates, deme payoff + ledger, Phase F campaign metrics, Phase H ablation/effect-size *harnesses* + RAG corpus | Literature-grade multilevel experiments and heldout generalization as default evidence | Group fitness = `runtime_observation`; `collective_intelligence` **blocked** |

None of these rows is a claim that CodonTrace Genesis is close to crossing
the barrier. Phase F adds **more honest instrumentation**, not a pass.

---

## 2. Nature MI 2021 — biological perspective on evolutionary computation

**Cite:** Miikkulainen & Forrest, *Nature Machine Intelligence* **3**, 9–15
(2021), [doi:10.1038/s42256-020-00278-8](https://doi.org/10.1038/s42256-020-00278-8),
“A biological perspective on evolutionary computation.” The paper evaluates
how evolutionary computation diverges from biological evolution. It sits with
the longer computational-evolution agenda (Banzhaf et al., *Nature Reviews
Genetics* 2006, “From artificial evolution to computational evolution”).

Three divergences named in the 2021 perspective:

1. **Small populations and strong selection** — biology retains diversity under
   weaker selection and drift; typical EC uses small *N* and intense selection.
2. **Direct genotype→phenotype maps** — biology uses complex, often neutral
   developmental maps; typical EC decodes genomes almost directly into
   behavior or fitness.
3. **No major organizational transitions** — biology discovers new levels of
   individuality; typical EC stays at one organizational level.

**CodonTrace Genesis has:** a spatial eat/survive/reproduce life-loop;
capacity that can exceed initial *N* so births are not immediately blocked;
fitness-proportional (and optional QD) selection; semantic genomes rather than
a single float genome; dual-parent sexual recombination as an opt-in analog;
Phase D trajectories that *measure* fitness/behavior change.

**CodonTrace Genesis lacks:** biological-scale *N*; systematically weak
selection plus neutrality/drift as the research default; an evolved
developmental G→P; any demonstrated major transition in individuality.

Default `life_loop_world(seed=7, tick_count=12, population=6)` is a **digest
pin**, not a biological population. Scaling *N* in a smoke test does not
satisfy the 2021 critique.

---

## 3. Soros & Stanley — Chromaria necessary conditions for OEE

**Cite:** Soros & Stanley, “Identifying Necessary Conditions for Open-Ended
Evolution through the Artificial Life World of Chromaria,” ALIFE 14 (2014).
Follow-up empirical work (Soros dissertation / OEE workshops) tests four
hypothesized necessary conditions:

1. A **nontrivial minimal criterion (MC)** for reproduction; the seed itself
   must meet it.
2. Evolution of new individuals should **create novel opportunities** to
   satisfy the MC.
3. **Individuals decide** how and where they interact with the world.
4. Potential **phenotypic size/complexity is in principle unbounded**.

**CodonTrace Genesis has:** AliveGate + runtime-ATP gates so not every
organism copies (an MC analog, but a *library* gate, not a Chromaria MC);
spatial interaction (eat, wait, copy, optional sense-react); Phase C
environments that change the resource landscape; variable-genome tokens as a
bounded complexity hook.

**CodonTrace Genesis lacks:** a Chromaria-style controlled test that
removing any one condition causes stagnation; self-generated opportunity
landscapes (condition 2 is not shown); unbounded phenotypic potential
(condition 4 is not true of fixed codon-width instruction genomes);
agent-directed interaction at Chromaria depth (condition 3 is a small action
set on a 2D grid).

Passing an MC analog is not OEE. Phase D MODES/Bedau numbers after a
persistence window are **descriptive**.

---

## 4. Stanley — open-endedness as a component of creative intelligence

**Cite:** Kenneth O. Stanley, “Open-endedness: The last grand challenge you’ve
never heard of” (O’Reilly Radar, 2017), building on Lehman & Stanley novelty
search and the OEE workshop tradition (Packard et al. 2019 Tokyo types).
Open-endedness is framed as a **necessary component of creative
intelligence**, not a metric you check once.

**CodonTrace Genesis has:** novelty-aware QD archives; Bedau activity;
persistence-filtered MODES axes; Channon 2024 *measurement steps*; explicit
refusal to promote those steps to intelligence.

**CodonTrace Genesis lacks:** creative intelligence; a process that keeps
generating adaptive novelty without a researcher-supplied objective and
without bound. Stanley’s point is directional: if you have not got
open-endedness, you have not got that component of creative intelligence.
CodonTrace Genesis has **not** got open-endedness as a result.

`open_ended_intelligence` stays forbidden. Do not paraphrase MODES novelty
as creativity.

---

## 5. Channon 2024 — Tokyo Type 1 measurement is not a pass

**Cite:** Alastair Channon, “A Procedure for Testing for Tokyo Type 1
Open-Ended Evolution,” *Artificial Life* (2024). Packard et al. 2019 supply
the Tokyo-type taxonomy (Type 1 ≈ ongoing generation of adaptive novelty).

CodonTrace Genesis implements the **procedure’s step vocabulary**:

| Step | Library surface | Pass? |
|---|---|---|
| Activity components | Bedau / MODES presence sets | never |
| Evolutionary activity | novelty / diversity / cumulative series | never |
| Adaptive novelty | persistence-filtered change (`persistence_window_t`) | never |
| Shadow / normalization | opt-in Python Empirical-style `shadow_digest` | never |
| Multi-seed aggregation | `TokyoType1MeasurementCampaign` (`seed_count≥2`) | never |
| Claim gate | ceiling `tokyo_type1_measurement_only` | `tokyo_type1_passed` **blocked** |

A researcher can run every step and still must not say Type 1 passed.
Multi-seed does not unlock a pass. A real shadow digest does not unlock a
pass. Phase F does not unlock a pass.

---

## 6. Vocabulary gap and verifier gap (arXiv 2607.09560)

**Cite:** “Beyond Fixed Representations: The Vocabulary and Verifier Gaps in
Open-Ended AI,” arXiv:2607.09560. Modern systems mostly search **inside** a
fixed representational frame. Two gaps:

- **Vocabulary gap:** inventing and *stabilizing* new primitives that change
  the space being searched, rather than recombining supplied tokens.
- **Verifier gap:** judging a new primitive when its payoff is visible only
  after future reuse, possibly requiring the evaluator itself to change.

**CodonTrace Genesis has:** an instruction/codon vocabulary supplied by the
library; ADF/macro *proposal* objects with ATP-gated accounting; contribution
ledgers that *attribute* local reward; ClaimGate as an **external** verifier
that refuses overclaim; delayed-reward and ablation hooks.

**CodonTrace Genesis lacks:** organisms that invent new representational
primitives which then become the search frame; a verifier that co-evolves
with those primitives; future-reuse credit that is more than an attribution
estimate (`caveat: attribution_estimate_not_causal_proof`).

ADF macros and capsule slots are **intra-space** operations in the arXiv
2607.09560 sense until a primitive changes what can be expressed *and* a
downstream evaluator can prefer it for reasons the current fitness function
cannot yet state. That has not happened here. It is not a near-term AGI
ingredient sitting one flag flip away.

---

## 7. JaxLife 2024 — complementary, not a race

**Cite:** JaxLife (arXiv 2409.00853, 2024). The system **deliberately
abstracts physics/chemistry** and uses embodied neural-network agents that
seek culture/tech accumulation.

**CodonTrace Genesis is the other cut:** instruction/genome ecology in the
Avida tradition, plus a first-class **audit / replay / ClaimGate** evidence
layer. Basal energy-budget *inspiration* is landed on the life-loop preset.
JaxLife-style culture/tech NN agents are **not** ported and are not a Phase F
goal for core.

Complementary means: a JaxLife culture result is not a CodonTrace Genesis
intelligence result, and a CodonTrace Genesis digest is not a JaxLife
embodiment result. ASAL / CLIP foundation-model open-ended search
(arXiv 2412.17799) remains out of the dependency-free core.

---

## 8. Collective intelligence — first-class scientific gap (Phase F/H/I)

This is the gap CodonTrace Genesis treats as **first-class** for Phase F/H/I
engineering, still without promoting it to a proved result. Group fitness,
messaging counts, and role shares are allowed as `runtime_observation`.
Proved `collective_intelligence` stays **BLOCKED**. Phase H adds runnable
ablation and effect-size harnesses plus a literature RAG; Phase I adds
heldout-partner, evolved-DoL, and MLS-outcome harnesses. Neither phase
auto-sets ClaimGate flags from smokes.

### 8.1 Literature

- **Goldsby et al.** — coordination instructions in Avida
  (`send_message` / `retrieve_message` / `broadcast_message` /
  `block_propagation`); division-of-labor / task-switching experiments; and
  GermlineReplication (deme-level copy of a germline/propagule when mean
  fitness clears a threshold). Messaging here is a buffer + gate, not those
  evolved coordination instructions paying off.
- **GECCO 2008 digital germlines / cooperative networks** — soma vs germline
  eligibility; cooperative networks that export fitness through a germline.
  Role tags here are eligibility gates, not evolved cooperative networks.
- **`devosoft/avida` demes wiki / `avida.cfg` `DEME_GROUP`** — multilevel
  selection (`DEMES_GROUP_REPLICATE`, germline copy, `GERMLINE`). Phase E
  `DemeConfig.replicate_on_mean_fitness` is an analog, not a C++ port.
- **Major transitions in individuality** — Szathmáry & Maynard Smith 1995
  lineage; Michod’s export-of-fitness / evolutionary transitions in
  individuality. A new Darwinian individual is not a tagged deme.

### 8.2 Distinguish two ceilings

| Observation | Allowed label | Forbidden label |
|---|---|---|
| Deme mean fitness, replication events, contribution shares, role counts, group-vs-individual *delta*, message counts | `runtime_observation` | `collective_intelligence` |
| Group-over-individual improvement **with** communication ablation, role complementarity, heldout unfamiliar partners, multi-seed effect size, replay | `collective_intelligence_candidate` (only if ClaimGate flags are complete) | `collective_intelligence`, `proved_collective_intelligence` |

Mean fitness of a deme is **group fitness**, not collective intelligence.
A contribution ledger is **attribution**, not causal proof of cooperation.
A rank table with `top_k` selected is **not** a multilevel-selection
experiment. A positive group-vs-individual delta in the Phase F smoke still
leaves `collective_intelligence` **BLOCKED**.

`ScientificClaimGate` for `collective_intelligence_candidate` still requires
the full flag set: `real_partner_event`, `non_capsule_cooperation`,
`role_complementarity`, `collective_coordination`, heldout familiar/unfamiliar
protocols, `ablation_result`, `collective_report_digest`,
`replay_verification`. The Phase F campaign **does not set those flags**.
Phase J can earn `replay_verification` from independent digest re-execution
at research scale when captured and replayed campaign digests match. Smoke
still never earns.

### 8.3 What CodonTrace Genesis has (substrate + metrics)

| Surface | What it records | Literature analog | Honesty |
|---|---|---|---|
| Deme messaging buffer | send / retrieve / broadcast / block_propagation events | Goldsby coordination instructions | Gate + inbox, not evolved language |
| Role / germline / soma tags | eligibility for copy or messaging | GECCO 2008 digital germlines | Assigned or round-robin, not evolved DoL |
| Deme containers + `replicate_on_mean_fitness` | extra target deme preserved after refresh; replication events | `DEME_GROUP` / GermlineReplication | Analog; not Avida C++ |
| Contribution ledger | member fitness shares on replication | multi-agent credit / germline contribution | Attribution estimate, not causal proof |
| `CollectiveDemePayoffPack` | replicate-on-mean-fitness + ledger digest | deme payoff bookkeeping | `runtime_observation` |
| `rank_demes_by_mean_fitness` | observational ranking; `top_k` marked selected | multi-deme selection *record* | Ranking ≠ MLS experiment |
| `build_deme_division_of_labor_observation` | role counts × fitness shares | Goldsby DoL metrics | Assigned tags, not evolved DoL |
| `GroupVsIndividualContrast` | paired deme-on vs organism-only mean fitness, selected vs unselected deme means, message count, ledger digest | group-vs-individual payoff coupling *hook* | Delta is group fitness, not intelligence |
| `run_collective_deme_payoff_campaign` | ≥2 seeds of the above | multi-replicate measurement | Gap flags stay `not_run` / `scaffold_only` |
| Phase H `run_communication_ablation_experiment` | messaging on vs off, multi-seed, Cohen's *d* | Goldsby: communication must pay | `measured_runtime_observation`; ClaimGate `ablation_result` **not** set |
| Phase H `run_group_vs_individual_effect_size_campaign` | configurable `seed_count` (default 12; smoke 2) + effect-size fields | group-vs-individual payoff | Delta is still group fitness |
| Phase H `TaskSwitchingCostConfig` | reweights DoL fitness shares by action-switch counts | Goldsby 2012 analog | Not evolved DoL; not 50 replicates |
| Literature RAG (`search_corpus`) | citable digests + deterministic TF-IDF | experiment design map | Retrieval is not evidence |
| Phase J `verify_digest_replay` / `build_replay_verified_ci_candidate_pack` | independent campaign digest re-execution | replay_verification honesty | Smoke never earns; same-object replay rejected |
| Phase J `run_price_equation_covariance_scaffold` | last-generation MLS1 between/within covariance | Price 1970 / Okasha MLS1 | Snapshot; no transmission term; not a full Price paper |
| `CollectiveIntelligenceEvidenceReport` / heldout-partner objects | protocol scaffolds | social CI protocol | Do not auto-fill from a life-loop smoke |

### 8.4 What is still missing for literature-grade collective intelligence evidence

| Missing experiment | Why it matters | Phase F/H/I status |
|---|---|---|
| Payoff coupling that *changes evolutionary outcome* under deme-level selection vs organism-only selection (controls, ≥12 seeds, effect size) | Goldsby / `DEME_GROUP` / Okasha MLS2: which strategy wins, not a rank table | Phase F `scaffold_only`; Phase H fitness Cohen's *d*; Phase I `run_mls_evolutionary_outcome_experiment` is **runnable** (two-task analog; `measured_runtime_observation`); Phase J Price snapshot is MLS1 bookkeeping, not MLS2 |
| Communication ablation (messaging on vs off) that drops group payoff | Goldsby: coordination instructions must *pay* | Phase F campaign stays `not_run`; Phase H harness is **runnable** and does **not** set ClaimGate `ablation_result` from smoke |
| Heldout partner generalization (unfamiliar partners) | ClaimGate `heldout_protocol` / familiar vs unfamiliar | Phase F `not_run`; Phase I `run_heldout_unfamiliar_partner_experiment` is **runnable**; smoke does not earn flags |
| Evolved division of labor (not round-robin tags) whose ablation drops group payoff | Goldsby / Gorelick NMI | Phase H cost hook on assigned tags; Phase I evolved preference analog + ablation is **runnable** |
| Non-capsule cooperation beating single-agent and no-communication baselines | social protocol / swarm candidate flags | Phase I toy has no capsules; still not Avida instruction cooperation |
| Export-of-fitness / transition in individuality | Michod; Szathmáry & Maynard Smith | Phase I `ExportOfFitnessObservation` scaffold; isolation collapse is payoff construction; `major_transition_in_individuality=False` |
| Literature-scale cooperative-network evolution (GECCO 2008 germlines as a *result*) | soma/germline eligibility must be discovered, not assigned | tags remain gates |

Phase I continues on those missing pieces as **engineering**. ClaimGate
still rejects `collective_intelligence` and `proved_collective_intelligence`
when a researcher only has messaging counts, a ledger digest, a rank table,
a group-vs-individual delta, a RAG hit list, or a Phase I smoke. See
[`PHASE_H_CI_AI_PATH.md`](PHASE_H_CI_AI_PATH.md),
[`PHASE_I_CI_EVIDENCE.md`](PHASE_I_CI_EVIDENCE.md), and
[`PHASE_J_REPLAY_CI.md`](PHASE_J_REPLAY_CI.md).

---

## 9. Phase H/I/J continue — not an intelligence countdown

Phase H/I/J are the next **library** increments after Phase F/G:

- Keep A–E default digest pins stable.
- Ship a literature RAG substrate (citable digests + TF-IDF retriever).
- Make communication ablation and group-vs-individual effect sizes
  *runnable* without auto-promoting ClaimGate flags.
- Add a Goldsby 2012 task-switching cost hook on DoL metrics.
- Print `collective_intelligence_candidate` missing flags; never set them.
- Keep JaxLife NN agents and ASAL CLIP out of core.
- Keep Tokyo Type 1 as measurement-only.

Phase I adds heldout unfamiliar-partner generalization, evolved (not
assigned) DoL, MLS evolutionary-outcome contrast, and an export-of-fitness
scaffold. Smoke never earns ClaimGate flags. See
[`PHASE_I_CI_EVIDENCE.md`](PHASE_I_CI_EVIDENCE.md).

Phase J adds independent digest re-execution so `replay_verification` can
be earned honestly when campaign digests match, plus a Price-equation
covariance snapshot. Research-scale full flags may allow
`collective_intelligence_candidate`. Smoke never earns. See
[`PHASE_J_REPLAY_CI.md`](PHASE_J_REPLAY_CI.md).

Phase H/I/J are **not** “the AGI phase.” There is no evidence in this repository
that CodonTrace Genesis is close to AGI, and this document forbids that
reading.

---

## 10. ClaimGate remainder

Allowed now (when evidence objects actually exist):

- `runtime_observation`
- `oee_measurement_only`
- `tokyo_type1_measurement_only`
- `collective_intelligence_candidate` only with the full flag set in
  `ScientificClaimGate` (multi-agent task, non-capsule cooperation, role
  complementarity, heldout familiar/unfamiliar, ablation, replay). Smoke
  campaigns do not set those flags.

Still forbidden, including after Phase H/I/J instrumentation and RAG retrieval:

- `agi`, `consciousness`
- `tokyo_type1_passed`, `channon_2024_passed`, `proved_open_endedness`
- `open_ended_intelligence`
- `collective_intelligence`, `proved_collective_intelligence`
- `avida_replacement`, `associative_learning_proved`

If a sentence in a PR, README, or paper cannot be mapped to a row in
[`CLAIMS.md`](../CLAIMS.md), do not write it.

---

## 11. References (honesty checklist)

- Miikkulainen, R. & Forrest, S. (2021). A biological perspective on
  evolutionary computation. *Nature Machine Intelligence* 3:9–15.
  doi:10.1038/s42256-020-00278-8. (EC vs biology: small pop / strong
  selection; direct G→P; no major transitions.)
- Banzhaf, W. et al. (2006). From artificial evolution to computational
  evolution: a research agenda. *Nature Reviews Genetics* 7:729–735.
- Soros, L. B. & Stanley, K. O. (2014). Identifying necessary conditions for
  open-ended evolution through the artificial life world of Chromaria.
  *ALIFE 14*.
- Stanley, K. O. (2017). Open-endedness: The last grand challenge you’ve
  never heard of. O’Reilly Radar. (Open-endedness as a component of
  creative intelligence.)
- Packard, N. et al. (2019). Tokyo workshop types of open-ended evolution.
- Channon, A. (2024). A procedure for testing for Tokyo Type 1 open-ended
  evolution. *Artificial Life*. Measurement ≠ pass.
- Beyond Fixed Representations: The Vocabulary and Verifier Gaps in
  Open-Ended AI. arXiv:2607.09560.
- JaxLife (2024). arXiv:2409.00853. Embodied NN culture/tech; abstracts
  physics/chemistry. Complementary to CodonTrace Genesis audit/replay
  ecology.
- Goldsby, H. J. et al. Avida messaging / GermlineReplication / division of
  labor (see `devosoft/avida` wiki and related digital-evolution papers).
- Gorelick, R. et al. (2004). Normalized mutual entropy in biology:
  quantifying diversity and division of labor. *Integrative and Comparative
  Biology* 44:345–352. doi:10.1093/icb/44.5.345.
- Okasha, S. (2006). *Evolution and the Levels of Selection*. Oxford
  University Press.
- Michod, R. E. (2007). Evolution of individuality during the transition
  from unicellular to multicellular life. *PNAS* 104:8613–8618.
  doi:10.1073/pnas.0701482104.
- GECCO 2008 digital germlines / cooperative networks.
- `devosoft/avida` demes introduction; `avida.cfg` `DEME_GROUP` /
  `GERMLINE` (VERSION_ID 2.14.0).
- Szathmáry, E. & Maynard Smith, J. (1995). The major evolutionary
  transitions. *Nature* 374:227–232.
- Michod, R. E. Evolutionary transitions in individuality / export of
  fitness.
- Dolson, E. et al. (2019). MODES. *Artificial Life*.
- Ofria, C. & Wilke, C. O. (2004). Avida. *Artificial Life*.

Print-only reminder: `examples/genesis_scientific_gaps_2026.py`,
`examples/genesis_rag_query.py`, and
`examples/genesis_phase_i_ci_evidence.py` print `agi_allowed False` and
collective-intelligence allowed False.
