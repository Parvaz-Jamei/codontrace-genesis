# NOVELTY VERDICT — claim-by-claim verification for CausalTape Tests 1–3

**Author:** teammate `prior-art` (novelty-verification member)
**Date of search:** 2026-09-27 (Asia/Tehran)
**Subject:** the three experiments in `causal-tape-experiment/` on `codontrace-genesis` @ `5a161081`
**Scope:** verification only. No new experiments were run.

**Method.** `web_search` is broken in this environment (as reported by the prior audits), so every
lookup was done against primary APIs: Crossref REST (`api.crossref.org`), OpenAlex REST, the arXiv
Atom API, NCBI E-utilities (PubMed), and `doi.org` via record fetches. Fetched content was treated
strictly as data. Verification labels used below: **[VERIFIED]** = the DOI resolves in Crossref and
the title/authors/venue were read this session; **[PREPRINT]** = preprint, not peer-reviewed;
**[NOT READ IN FULL]** = record verified but only abstract/metadata read, not the methods section.

**Honesty constraint applied throughout.** No sentence below says "first in the world". The strongest
permitted form — "we are not aware of a published precedent for X" — is used verbatim.

---

## 0. Local files read (and one instruction discrepancy)

Read in full or in the relevant sections:

* `causal-tape-experiment/RESULTS3.md`, `RESULTS4.md`, `PREREG.md`
* `codontrace_scm_novelty_audit.md` (workspace root)
* `contingency_replay_state_of_art.md` (workspace root)
* `order-effect-literature-verdict.md` (workspace root)
* `codontrace-genesis-main-snapshot/docs/claimgate/host_parasite_port_20260924/TWO_FOLD_COST_LITERATURE_AND_DESIGN_20260927.md`
* `codontrace-genesis/CLAIMS.md`, `codontrace-genesis/BACKLOG.md`
* the evidence notes under `codontrace-genesis-main-snapshot/docs/claimgate/host_parasite_port_20260924/evidence/`

**Discrepancy to record.** The brief says "the two literature reports inside
`…/host_parasite_port_20260924/` (filenames contain TWO_FOLD_COST and/or 20260927)". Only **one**
file in that directory matches either token:

* `TWO_FOLD_COST_LITERATURE_AND_DESIGN_20260927.md`

The other three prior audits are elsewhere: `codontrace_scm_novelty_audit.md`,
`contingency_replay_state_of_art.md`, `order-effect-literature-verdict.md` — all in the workspace
root. No file matching those tokens exists elsewhere in the tree (checked by glob over the whole
workspace and by grepping the full glob spill lists). If the brief expected a second in-directory
report (e.g. a Red-Queen/Court-Jester literature report), **it was never written** and that gap is
listed in §5.

---

## 1. The repository's own claims — verified by reading the files

### 1.1 `TWO_FOLD_COST_SEX` is advertised in the repo

`codontrace-genesis/CLAIMS.md:94` (quoted verbatim, one row of the claim table):

> | Sexual recombination substrate | Explicit `ReproductionMode.SEXUAL_CROSSOVER` / `life_loop_world(reproduction_mode=...)` runs a CodonTrace Genesis birth chamber (pairing queue, wait/capacity policy) plus positional continuous corresponding crossover (`CONT_REC_REGS` / `CORESPOND_REC_REGS` semantics), then mutation. Dual-parent lineage and recombination records are digest-backed and replayable. Knobs mirror `avida.cfg` `RECOMBINATION_GROUP` (`RECOMBINATION_PROB`, `SAME_LENGTH_SEX`, **`TWO_FOLD_COST_SEX`**, `MAX_BIRTH_WAIT_TIME`). Opt-in `diploid_meiosis` is an Aevol-style homolog-reduction analog before chamber crossover (default off). Research defaults remain asexual. Grounded in Misevic, Ofria, Lenski 2006 Proc B. | Allowed as software capability / runtime observation. Do not claim sexual selection, evolved instinct, intelligence, Aevol-grade meiosis, biological diploidy, or Avida-replacement status. |

`codontrace-genesis/BACKLOG.md:8`:

> 4. Phase B (implemented, opt-in): Sexual recombination substrate — CodonTrace birth chamber + positional continuous corresponding recombination, digest-backed dual-parent records, opt-in `diploid_meiosis` homolog-reduction analog and **`TWO_FOLD_COST_SEX`** (optional knobs peer-compatible with `avida.cfg` `RECOMBINATION_GROUP`). Research defaults stay asexual. Mating types / lekking remain stubs.

`codontrace-genesis-main-snapshot/CHANGELOG.md:595`:

> (Avida `TWO_FOLD_COST_SEX` already placed one recombinant product).

**Verdict on the earlier audit's report: CONFIRMED.** The repo does advertise `TWO_FOLD_COST_SEX`,
and it advertises it as *"software capability / runtime observation"* — **not** as a result and
**not** as an audited energy charge. The allowed-claim ceiling on that row explicitly forbids
stronger readings.

### 1.2 What `TWO_FOLD_COST_SEX` actually does in the code

`TWO_FOLD_COST_LITERATURE_AND_DESIGN_20260927.md:53` (local audit, reading the engine):

> `two_fold_cost_sex` ("Avida `TWO_FOLD_COST_SEX`") sets `needed = 1 if two_fold_cost_sex else 2` and
> then keeps `products[:1]` — i.e. **one offspring placed per mated pair instead of two**
> (`src/codontrace/genesis/population.py:5286`, `:5325–5327`; `src/codontrace/genesis/birth.py:162`).
> That is a **demographic / fecundity-halving cost, explicitly not an ATP debit.**

This matters for C1: the repo's own knob is the *demographic* form of the two-fold cost. Charging the
same 2× as an ATP debit inside a conserved ledger is therefore not merely "already in the repo"; if
the maths is the same fecundity halving, a reviewer will say it is algebraically identical
(the audit says exactly this at lines 212–214 and 462–470).

### 1.3 ClaimGate state the new results do **not** change

`red_queen_proved` is a ClaimGate *refusal* flag and is `false` across the tree — 245 matching lines
in `codontrace-genesis/**/*.md`; representative mandatory lines include
`codontrace-genesis/docs/handoff/CLOSED_LOOP_P5_STATUS_20260925.md:27`
("Not Morran 2011 (doi:10.1126/science.1206360). No control / evolution / coevolution arms.
`red_queen_proved` is false.") and
`codontrace-genesis/docs/handoff/CLOSED_LOOP_HP_ARM01_RQ_EARN_CONFIRM_RESULTS_20260926.md:16`
("| `red_queen_proved` | **false** |").

`PREREG.md:29` states for this run: "`red_queen_proved` and every other ClaimGate refusal stay false
and untouched by this run." There is **no `CLAIMS.md` row for the TEST 2 / TEST 3 results** — the
three new experiments live outside the repo's claim registry, which is consistent with that.

---

## 2. Verdict table C1–C4

| # | Candidate claim | Verdict | Closest prior art (verified) | Defensible sentence |
|---|---|---|---|---|
| **C1** | First to charge Maynard Smith's two-fold cost as an explicit irreversible dissipation delta inside a conserved/audited energy ledger, with an injected-leak audit control | **PARTIALLY OCCUPIED** — every component is published; the exact combination was not found | **Misevic, Ofria & Lenski 2006**, *Proc. R. Soc. B* 273:457–464, [10.1098/rspb.2005.3338](https://doi.org/10.1098/rspb.2005.3338) **[VERIFIED]** (Avida sexual vs asexual digital organisms; cost demographic, energy scaled by genome length) · **Misevic, Ofria & Lenski 2010**, *J. Heredity* 101(S1):S46–S54, [10.1093/jhered/esq017](https://doi.org/10.1093/jhered/esq017) **[VERIFIED]** (sex dominates only under rapid environmental change; no audited ledger) · **Goyal, Flamholz, Petroff & Murugan 2023**, *PNAS* 120(52):e2309387120, [10.1073/pnas.2309387120](https://doi.org/10.1073/pnas.2309387120) **[VERIFIED]** (rigorous closed-ecosystem energy-budget/closure precedent) · **Yasui & Hasegawa 2024**, Research Square preprint [10.21203/rs.3.rs-4360051/v1](https://doi.org/10.21203/rs.3.rs-4360051/v1) **[VERIFIED][PREPRINT]** and **Yasui 2026**, *J. Evol. Biol.* 39(9):1154–1168, [10.1093/jeb/voag069](https://doi.org/10.1093/jeb/voag069) **[VERIFIED]** (resource limitation / carrying capacity removes the *realised* two-fold cost) | "We are not aware of a published precedent for charging the two-fold cost of sex as an explicit, irreversible ATP debit — a per-mating dissipation δ with no counterpart ledger entry — inside a conserved energy ledger whose closure is audited every generation with an injected-leak negative control. The closest precedents charge the cost demographically (Avida's `TWO_FOLD_COST_SEX`; Misevic et al. 2006, 2010), frame closure energetically without a sex cost (Goyal et al. 2023), or argue that resource limitation removes the realised cost altogether (Yasui & Hasegawa 2024)." |
| **C2** | First exact (noise-free) decomposition of the bias of mutation-effect estimators using a bit-reproducible simulator whose do-operator leaves the random stream untouched | **PARTIALLY OCCUPIED** — the estimand identity is textbook; three of four components are published; the specific packaging was not found | **Heckman 1979**, *Econometrica* 47(1):153–161, [10.2307/1912352](https://doi.org/10.2307/1912352) **[VERIFIED]** (selection bias as a specification error; the naive-vs-ATT decomposition) · **Díaz-Uriarte, Ríos-Arroyo & Johnston 2026**, arXiv:2606.12597, [10.48550/arXiv.2606.12597](https://doi.org/10.48550/arXiv.2606.12597) **[VERIFIED][PREPRINT]** ("A simple approach of conditioning on the absence of a mutation gives incorrect predictions") · **Wahl & Agashe 2022**, *Evolution*, [10.1111/evo.14430](https://doi.org/10.1111/evo.14430) **[VERIFIED]** (quantifies and corrects selection bias in mutation-accumulation DFE estimation; simulated MA with known true DFE) · **Klein, Abeysuriya, Stuart & Kerr 2024**, arXiv:2409.02086, [10.48550/arXiv.2409.02086](https://doi.org/10.48550/arXiv.2409.02086) **[VERIFIED][PREPRINT]** (noise-free paired counterfactuals in ABMs by aligning random-number realisations) · **Buffalo, Pearson & Klein 2026**, arXiv:2603.11084, [10.48550/arXiv.2603.11084](https://doi.org/10.48550/arXiv.2603.11084) **[VERIFIED][PREPRINT]** (formalises the SCM incoherence of execution-path-dependent draw indexing) · **Marshall & Galea 2015**, *Am. J. Epidemiol.* 181(2):92–99, [10.1093/aje/kwu274](https://doi.org/10.1093/aje/kwu274) **[VERIFIED]** (exchangeability free by construction; ergodicity/specification carry the weight) | "We are not aware of a published precedent for an exact, noise-free decomposition `naive = ATT + selection_bias` computed per lineage for a single mutation inside a bit-reproducible digital-evolution simulator whose `do()` suppresses the drawn event without rewinding or re-keying the random stream. Every ingredient is published separately: the decomposition is standard selection-bias theory (Heckman 1979), conditioning on mutation absence is shown to be incorrect by Díaz-Uriarte et al. (2026), selection bias in mutation-effect estimation is quantified and corrected by Wahl & Agashe (2022), and noise-free paired counterfactuals via common random numbers are established by Klein et al. (2024) and Buffalo et al. (2026)." |
| **C3** | First matched-multiset arrival-order permutation intervention with a per-arm schedule digest on a deterministic simulator | **PARTIALLY OCCUPIED** — the digest/event-keying mechanism and the determinism-failure mode are published; the permutation intervention itself was not found on a matched multiset | **Buffalo, Pearson & Klein 2026**, arXiv:2603.11084, [10.48550/arXiv.2603.11084](https://doi.org/10.48550/arXiv.2603.11084) **[VERIFIED][PREPRINT]** (event-keyed hashing with counter-based RNGs; the published remedy whose failure mode the per-arm digest detects) · **Klein et al. 2024**, arXiv:2409.02086, [10.48550/arXiv.2409.02086](https://doi.org/10.48550/arXiv.2409.02086) **[VERIFIED][PREPRINT]** (matched random-number realisations across scenarios) · **Schruben & Margolin 1978**, *JASA* 73(363):504–514, [10.1080/01621459.1978.10480044](https://doi.org/10.1080/01621459.1978.10480044) **[VERIFIED]** (common-random-numbers assignment; the classical precedent) · **Teimouri & Kolomeisky 2021**, *Phys. Biol.* 18(5), [10.1088/1478-3975/ac0b7e](https://doi.org/10.1088/1478-3975/ac0b7e) **[VERIFIED]** (explicit comparison of two alternative mutation sequences in a first-passage model of cancer initiation — an order intervention without a matched-multiset digest) · **Bajić, Vila, Blount & Sánchez 2018**, *PNAS* 115(44):11286–11291, [10.1073/pnas.1808485115](https://doi.org/10.1073/pnas.1808485115) **[VERIFIED]** (noncommutative epistasis δ as a separately estimable quantity) · **Salverda et al. 2011**, *PLoS Genet.* 7(3):e1001321, [10.1371/journal.pgen.1001321](https://doi.org/10.1371/journal.pgen.1001321) **[VERIFIED]** (observed, not intervened, order dependence) | "We are not aware of a published precedent for a matched-multiset arrival-order permutation intervention on a deterministic simulator in which a per-arm schedule digest certifies that both arms consumed the same proposal multiset. The digest is motivated by published work on execution-path-dependent draw indexing (Buffalo et al. 2026) and by common-random-numbers pairing (Klein et al. 2024; Schruben & Margolin 1978); order dependence itself is a published quantity (Bajić et al. 2018; Salverda et al. 2011; Teimouri & Kolomeisky 2021)." |
| **C4** | First 2×2 factorial partitioning genotype turnover between a coevolving antagonist and an abiotic resource shock with an Ne-based drift null and a genotype-blind uniform-tax control | **PARTIALLY OCCUPIED (strongly)** — the biotic × abiotic factorial in a *digital* host–parasite system is published; biotic-vs-abiotic partitioning has multiple precedents; the specific turnover metric + Ne null + uniform-tax control were not found | **Acosta & Zaman 2022**, *Front. Ecol. Evol.* 9:750772, [10.3389/fevo.2021.750772](https://doi.org/10.3389/fevo.2021.750772) **[VERIFIED]** (digital host–parasite communities; biotic × abiotic factorial; "ecological opportunity and necessity"; diversification metric, not turnover) · **Scanlan et al. 2015**, *Mol. Biol. Evol.* 32(6):1425–1435, [10.1093/molbev/msv032](https://doi.org/10.1093/molbev/msv032) **[VERIFIED]** (coevolution vs abiotic-beneficial mutations — wet two-factor design) · **Lopez Pascua et al. 2014**, *Ecol. Lett.* 17(11):1380–1388, [10.1111/ele.12337](https://doi.org/10.1111/ele.12337) **[VERIFIED]** (resource level × host–parasite coevolution) · **Ezard, Aze, Pearson & Purvis 2011**, *Science* 332(6027):349–351, [10.1126/science.1203060](https://doi.org/10.1126/science.1203060) **[VERIFIED]** (partitioning biotic ecology × abiotic climate on macroevolutionary dynamics) · **Lively & Wade 2022**, *Ecol. Evol.* 12(8):e9136, [10.1002/ece3.9136](https://doi.org/10.1002/ece3.9136) **[VERIFIED]** (coupled Price equations partitioning natural selection vs environmental change in host–parasite coevolution) · **Barnosky 2001**, *J. Vert. Paleontol.* 21(1):172–185, [10.1671/0272-4634(2001)021[0172:DTEOTR]2.0.CO;2](https://doi.org/10.1671/0272-4634(2001)021%5B0172:DTEOTR%5D2.0.CO;2) **[VERIFIED]**; **Benton 2009**, *Science* 323(5915):728–732, [10.1126/science.1157719](https://doi.org/10.1126/science.1157719) **[VERIFIED]**; **Voje et al. 2015**, *Proc. R. Soc. B* 282(1809):20150186, [10.1098/rspb.2015.0186](https://doi.org/10.1098/rspb.2015.0186) **[VERIFIED]** (Red Queen / Court Jester framing) · **Zaman et al. 2014**, *PLoS Biol.* 12(12):e1002023, [10.1371/journal.pbio.1002023](https://doi.org/10.1371/journal.pbio.1002023) **[VERIFIED]** (digital host–parasite coevolution, biotic only) · **Misevic et al. 2010**, [10.1093/jhered/esq017](https://doi.org/10.1093/jhered/esq017) **[VERIFIED]** (digital organisms, abiotic environmental change only) | "We are not aware of a published precedent that partitions genotype turnover in a digital host–parasite system using a 2×2 factorial (coevolving antagonist × aperiodic abiotic resource shock) scored by a temporal F_st(w) against a closed-form Wright–Fisher drift null built from an Ne estimate, with a genotype-blind uniform-tax control. Biotic × abiotic factorial designs are published for digital host–parasite communities (Acosta & Zaman 2022) and for wet coevolution (Scanlan et al. 2015; Lopez Pascua et al. 2014), and biotic-vs-abiotic partitioning has strong precedent (Ezard et al. 2011; Lively & Wade 2022), but those use diversity, genomic-change, or Price-variance currencies rather than a drift-null-scaled turnover statistic." |

**Read the verdicts as "no evidence of an exact precedent found", not as proof of absence.**

---

## 3. Prior art that MUST be cited

Grouped by the claim it constrains. All URLs are DOI links verified this session.

### C1 — two-fold cost / digital sex / energy budgets
1. **Maynard Smith 1978**, *The Evolution of Sex* (Cambridge UP) — the two-fold cost itself.
2. **Williams 1975**, *Sex and Evolution* (Princeton UP) — cost of meiosis.
3. **Hamilton 1980**, *Oikos* 35(2):282–290, [10.2307/3544435](https://doi.org/10.2307/3544435) — parasite-driven maintenance hypothesis.
4. **Misevic, Ofria & Lenski 2006**, *Proc. R. Soc. B* 273:457–464, [10.1098/rspb.2005.3338](https://doi.org/10.1098/rspb.2005.3338) — **the direct digital-organism sex-cost precedent**; Avida's cost is demographic, energy scales with genome length.
5. **Misevic, Ofria & Lenski 2010**, *J. Heredity* 101(S1):S46–S54, [10.1093/jhered/esq017](https://doi.org/10.1093/jhered/esq017) — sex dominates only under rapid environmental change; maintaining is easier than invading.
6. **Otto & Nuismer 2004**, *Science* 304(5673):1018–1020, [10.1126/science.1094072](https://doi.org/10.1126/science.1094072) — interactions "typically select against sex"; Red Queen alone does not explain sex.
7. **Agrawal 2009**, *Evolution* 63(8):2131–2141, [10.1111/j.1558-5646.2009.00695.x](https://doi.org/10.1111/j.1558-5646.2009.00695.x) — selection on sex vs recombination differ.
8. **Salathé, Kouyos, Regoes & Bonhoeffer 2008**, *Evolution* 62(2):295–300, [10.1111/j.1558-5646.2007.00265.x](https://doi.org/10.1111/j.1558-5646.2007.00265.x) — the main pro-sex simulation result (severe cost to non-infecting parasites).
9. **Zaman et al. 2014**, *PLoS Biol.* 12(12):e1002023, [10.1371/journal.pbio.1002023](https://doi.org/10.1371/journal.pbio.1002023) — digital host–parasite coevolution platform precedent.
10. **Goyal et al. 2023**, *PNAS* 120(52):e2309387120, [10.1073/pnas.2309387120](https://doi.org/10.1073/pnas.2309387120) — closed-ecosystem energy/closure framing.
11. **Yasui & Hasegawa 2024**, [10.21203/rs.3.rs-4360051/v1](https://doi.org/10.21203/rs.3.rs-4360051/v1) **[PREPRINT]** and **Yasui 2026**, *J. Evol. Biol.* 39(9):1154–1168, [10.1093/jeb/voag069](https://doi.org/10.1093/jeb/voag069) — **the most dangerous citation**: resource limitation removes the realised two-fold cost; a closed ledger is by construction resource-limited, so the estimand must be biomass share / time-to-fixation, not equilibrium per-capita fitness.
12. **Gibson, Delph & Lively 2017**, *Evol. Lett.* 1(1):6–15, [10.1002/evl3.1](https://doi.org/10.1002/evl3.1) — the closest *measured* two-fold cost (frequency-change currency).
13. **Slowinski et al. 2016**, *Evolution* 70(11):2632–2639, [10.1111/evo.13048](https://doi.org/10.1111/evo.13048) — the coevolving / fixed / avirulent three-treatment structure TEST 2 copies.

### C2 — estimator bias, exact decomposition, noise-free replay
14. **Heckman 1979**, *Econometrica* 47(1):153–161, [10.2307/1912352](https://doi.org/10.2307/1912352) — selection bias as a specification error; the naive-vs-ATT decomposition.
15. **Marshall & Galea 2015**, *Am. J. Epidemiol.* 181(2):92–99, [10.1093/aje/kwu274](https://doi.org/10.1093/aje/kwu274) — ABM causal inference; exchangeability is free, identifiability rests on ergodicity + specification.
16. **Díaz-Uriarte, Ríos-Arroyo & Johnston 2026**, arXiv:2606.12597, [10.48550/arXiv.2606.12597](https://doi.org/10.48550/arXiv.2606.12597) **[PREPRINT]** — **forecloses any "new application of the do-operator" framing**; conditioning on mutation absence gives incorrect predictions.
17. **Wahl & Agashe 2022**, *Evolution*, [10.1111/evo.14430](https://doi.org/10.1111/evo.14430) — selection bias in mutation accumulation, quantified and corrected, with simulated MA against a known true DFE. **The closest single precedent for C2's estimand.**
18. **Klein, Abeysuriya, Stuart & Kerr 2024**, arXiv:2409.02086, [10.48550/arXiv.2409.02086](https://doi.org/10.48550/arXiv.2409.02086) **[PREPRINT]** — noise-free paired comparison by aligned random-number realisations.
19. **Buffalo, Pearson & Klein 2026**, arXiv:2603.11084, [10.48550/arXiv.2603.11084](https://doi.org/10.48550/arXiv.2603.11084) **[PREPRINT]** — SCM-level argument that stateful PRNGs make paired counterfactuals causally incoherent; remedy = counter-based RNG + event identifiers. **Load-bearing for both C2 and C3.**
20. **Cornish, Faaiz Taufiq, Doucet & Holmes 2026**, *JMLR* (arXiv:2301.07210, [10.48550/arXiv.2301.07210](https://doi.org/10.48550/arXiv.2301.07210)) **[VERIFIED][PREPRINT-OF-JMLR]** — causal falsification of simulation-based "digital twins"; observational match cannot certify an intervention.
21. **Poinsot et al. 2025**, ICML position paper, [hal-05066031](https://hal.science/hal-05066031v2/file/icml2025_causal_profiler_position.pdf) — synthetic experiments must not be built to confirm the author's own claim (the circularity objection).
22. **Li & Kim 2026**, arXiv:2609.10954, [10.48550/arXiv.2609.10954](https://doi.org/10.48550/arXiv.2609.10954) **[PREPRINT]** — "fork ledger": matched update/hold continuations under common random numbers with a recorded per-fork delta. Methodologically adjacent to the exact paired counterfactual design.

### C3 — arrival order, matched schedules, digests
23. **Schruben & Margolin 1978**, *JASA* 73(363):504–514, [10.1080/01621459.1978.10480044](https://doi.org/10.1080/01621459.1978.10480044) — classical common-random-numbers assignment.
24. **Buffalo et al. 2026** — see #19 (the digest's theoretical justification).
25. **Klein et al. 2024** — see #18.
26. **Bajić et al. 2018**, *PNAS* 115(44):11286–11291, [10.1073/pnas.1808485115](https://doi.org/10.1073/pnas.1808485115) — noncommutative epistasis δ; the published name for the quantity; 1% / 10% effect floors come from here.
27. **Weinreich, Delaney, DePristo & Hartl 2006**, *Science* 312(5770):111–114, [10.1126/science.1123539](https://doi.org/10.1126/science.1123539); **Weinreich, Watson & Chao 2005**, *Evolution* 59(6):1165–1174, [10.1111/j.0014-3820.2005.tb01768.x](https://doi.org/10.1111/j.0014-3820.2005.tb01768.x) — sign epistasis / few accessible paths.
28. **Sailer & Harms 2017**, *PLoS Comput. Biol.* 13(5):e1005541, [10.1371/journal.pcbi.1005541](https://doi.org/10.1371/journal.pcbi.1005541) — Walsh–Hadamard separation of pairwise from higher-order epistasis (the analysis that defuses "order is just epistasis").
29. **Salverda et al. 2011**, *PLoS Genet.* 7(3):e1001321, [10.1371/journal.pgen.1001321](https://doi.org/10.1371/journal.pgen.1001321) — observed first-mutation order effects.
30. **Teimouri & Kolomeisky 2021**, *Phys. Biol.* 18(5), [10.1088/1478-3975/ac0b7e](https://doi.org/10.1088/1478-3975/ac0b7e) — explicit two-sequence (order) comparison in a stochastic model.
31. **Ortiz-Barrientos et al.** — not applicable; instead **"Order Matters: The Order of Somatic Mutations Influences Cancer Evolution" 2017**, *CSH Perspect. Med.*, [10.1101/cshperspect.a027060](https://doi.org/10.1101/cshperspect.a027060) — evidence that "mutation order" is an occupied term in the biomedical literature (expect reviewers to read order claims through this lens).
32. **Kryazhimskiy, Rice, Jerison & Desai 2014**, *Science* 344(6191):1519–1522, [10.1126/science.1250939](https://doi.org/10.1126/science.1250939) — global epistasis makes adaptation predictable despite sequence-level stochasticity (the strongest counter-evidence to any large order-effect claim).

### C4 — biotic × abiotic partitioning, drift nulls
33. **Acosta & Zaman 2022**, *Front. Ecol. Evol.* 9:750772, [10.3389/fevo.2021.750772](https://doi.org/10.3389/fevo.2021.750772) — **the closest digital prior art**: Avida host–parasite communities, biotic × abiotic drivers of diversification.
34. **Scanlan et al. 2015**, *Mol. Biol. Evol.* 32(6):1425–1435, [10.1093/molbev/msv032](https://doi.org/10.1093/molbev/msv032) — coevolution × abiotic-beneficial mutations.
35. **Lopez Pascua et al. 2014**, *Ecol. Lett.* 17(11):1380–1388, [10.1111/ele.12337](https://doi.org/10.1111/ele.12337) — resources × host–parasite coevolution.
36. **Ezard et al. 2011**, *Science* 332(6027):349–351, [10.1126/science.1203060](https://doi.org/10.1126/science.1203060) — biotic ecology × abiotic climate partitioning.
37. **Lively & Wade 2022**, *Ecol. Evol.* 12(8):e9136, [10.1002/ece3.9136](https://doi.org/10.1002/ece3.9136) — coupled Price equations partitioning selection vs environmental change in host–parasite coevolution.
38. **Barnosky 2001**, [10.1671/0272-4634(2001)021[0172:DTEOTR]2.0.CO;2](https://doi.org/10.1671/0272-4634(2001)021%5B0172:DTEOTR%5D2.0.CO;2); **Benton 2009**, [10.1126/science.1157719](https://doi.org/10.1126/science.1157719); **Voje et al. 2015**, [10.1098/rspb.2015.0186](https://doi.org/10.1098/rspb.2015.0186) — Red Queen vs Court Jester framing and its critique.
39. **FST / drift-null apparatus (the metric is standard; cite the sources, claim none of it):** Wright's F-statistics and the Wright–Fisher diffusion; **Weir & Cockerham 1984**, *Ann. Hum. Genet.* 48(2):173–186, [10.1111/j.1469-1809.1984.tb00852.x](https://doi.org/10.1111/j.1469-1809.1984.tb00852.x); **Nei & Tajima 1981**; **Waples 1989**, *J. Hered.* 80(4):277–280; **Jorde & Ryman 2007**, *Mol. Ecol.* 16(6):1099–1106, [10.1111/j.1365-294X.2007.03383.x](https://doi.org/10.1111/j.1365-294X.2007.03383.x). The branch-count Ne formula `(Σk)²/Σk²` is the standard effective number of parents (Wright 1938; Crow & Kimura 1970; Hill 1972) — cite it as standard, not as novel.
40. **Convergence/contingency framing (if the tape-of-life framing survives):** **Blount, Lenski & Losos 2018**, *Science* 362(6415):eaam5979, [10.1126/science.aam5979](https://doi.org/10.1126/science.aam5979) **[VERIFIED]**; **Powell & Mariscal 2015**, *Interface Focus* 5(6):20150040, [10.1098/rsfs.2015.0040](https://doi.org/10.1098/rsfs.2015.0040) **[VERIFIED]**.

---

## 4. What each verdict means operationally

* **C1 must not be written as a first.** The honest move is to (a) name the Avida
  `TWO_FOLD_COST_SEX` convention and state in one sentence why the ATP-debit form is not
  algebraically identical, and (b) state the estimand as biomass share / time-to-extinction, not
  equilibrium fitness (Yasui). The "irreversible dissipation δ with no counterpart entry" is the
  only genuinely novel ingredient, and it only survives if the audit trail shows the destroyed
  energy as a ledger entry with no matching transfer.
* **C2 must not claim the decomposition.** Cite Heckman (1979) for the identity and
  Díaz-Uriarte et al. (2026) and Wahl & Agashe (2022) for the evolutionary instances, then claim
  only the *instrument*: exact per-lineage ground truth in a bit-reproducible simulator, with the
  RNG-stream-preserving `do()` argued explicitly against Buffalo et al. (2026).
* **C3 is the strongest of the four.** The digest is the falsifiable mechanism, and the prior art
  it must engage (Buffalo 2026) *supports* rather than undercuts it: it is the published articulation
  of the failure mode the digest detects. Keep the claim to the design, never to order dependence itself.
* **C4 must not be written as "first to compare biotic and abiotic"** — that framing is occupied
  (Acosta & Zaman 2022, Scanlan 2015, Lopez Pascua 2014, Ezard 2011, Lively & Wade 2022). The claim
  can only be about the *statistic and its controls*: temporal F_st(w) with a closed-form
  Wright–Fisher drift null from an Ne estimate, plus a genotype-blind uniform-tax control that shows
  the biotic effect is not a uniform tax.

---

## 5. Still open — searches that could not be completed (so they can be redone)

1. **OpenAlex full-text search was rate-limited for the whole session.** Every
   `api.openalex.org/works?search=…` and `filter=title_and_abstract.search:…` call returned
   `HTTP 429 {"error":"Rate limit exceeded", "retryAfter": 31–40}` — including with a `mailto`
   parameter in the polite pool. Only two early OpenAlex calls succeeded. **Redo with a free
   OpenAlex API key** (or off-peak) the four full-text searches: (a) `"twofold cost of sex"` AND
   energy/ATP/ledger; (b) mutation-effect estimator bias AND exact/ground-truth simulator;
   (c) arrival-order/permutation intervention AND matched schedule; (d) `"Court Jester"` OR
   `"Red Queen"` AND turnover AND factorial.
2. **No second in-directory literature report exists.** If a Red-Queen/Court-Jester-focused
   literature report was expected under `…/host_parasite_port_20260924/` (C4's dedicated audit), it
   was not written; C4's audit therefore rests on this document only.
3. **The exhaustive "intervened order-permutation designs" check remains unrun.** It is explicitly
   listed as an uncompleted delegation stream at the end of `order-effect-literature-verdict.md`
   ("Delegation unavailable… an exhaustive check specifically for *intervened* order-permutation
   designs"). C3's "no precedent found" is therefore the weakest-supported of the four negatives.
   Redo with Google Scholar / Scopus / Web of Science, which are unavailable here.
4. **Full texts not read for the four most load-bearing negatives.** Verification was
   record-and-abstract level for: Acosta & Zaman 2022 (C4's closest digital prior art — its methods
   must be read before claiming the metric combination is new); Ezard et al. 2011 (abstract only,
   but the claim is well-established); Misevic et al. 2006/2010 (abstract/PMC account only);
   Otto & Nuismer 2004 (abstract). **Paywalled full texts (ScienceDirect, IOP, Frontiers methods)
   were not accessible.**
5. **Europe PMC and Semantic Scholar were not attempted** (the earlier audits report Europe PMC
   REST failures and Semantic Scholar 403; Semantic Scholar would independently cover the C1–C3
   negatives).
6. **Search-engine coverage gap.** `web_search` is broken and Google/Bing/Google Scholar were
   unavailable, so *grey* prior art (workshop papers, blog/software documentation, unpublished
   digital-evolution platforms) is systematically under-covered. Absence of a hit here is
   evidence about the indexed literature, not about all literature.
7. **`TWO_FOLD_COST_SEX` in the Avida source itself was not read** (only via the local audit's
   quote of `population.py` / `birth.py`). A one-line verification against `avida.cfg` 2.14.0
   `RECOMBINATION_GROUP` documentation would close the strongest reviewer objection to C1.

---

## 6. Bottom line

| Claim | Verdict |
|---|---|
| C1 two-fold cost as audited energy debit | **PARTIALLY OCCUPIED** — combination not found; each component is published; one component (resource limitation removes the realised cost) actively threatens the premise |
| C2 exact noise-free bias decomposition via RNG-preserving `do()` | **PARTIALLY OCCUPIED** — decomposition is textbook; three of four ingredients are published; the specific instrument not found |
| C3 matched-multiset order permutation + per-arm schedule digest | **PARTIALLY OCCUPIED** — the digest mechanism's theory is published; the matched-multiset permutation itself was not found (weakest negative, §5.3) |
| C4 2×2 biotic × abiotic turnover with Ne drift null + uniform-tax control | **PARTIALLY OCCUPIED (strongly)** — the digital biotic × abiotic factorial is published (Acosta & Zaman 2022); only the statistic and controls are unoccupied |

**No claim below survives in its "first to…" form. All four survive in the
"we are not aware of a published precedent for X" form given in §2**, provided the prior art in §3
is cited and the C1 estimand is restated as biomass share / time-to-fixation.
