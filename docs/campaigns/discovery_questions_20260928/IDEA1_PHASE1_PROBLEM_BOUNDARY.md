# Idea 1 — Phase-1 problem boundary: evolutionary selection of costly causal experimentation

**Date:** 2026-09-28  
**Base commit:** `f0d1d50c16707223fcf799007c20f95f47ddea2a` (`f0d1d50`), `main`  
**Campaign folder:** `docs/campaigns/discovery_questions_20260928/`  
**Status:** phase-1 problem boundary only; not a discovery claim  
**Claim ceiling:** `phase1_problem_boundary`  
**Track note:** Ambitious-track phase-1 problem boundary (ideas 1, 3, 5, and 6).

This document fixes the scientific question, the nearest published precedent, the open boundary, competing hypotheses, mandatory operational definitions, locked thresholds, falsifiers, and standing locks. It fixes no empirical result. No runner, pilot, or campaign is authorised by this file.

---

## 1. Standing locks

- The life-loop engine remains domain-free: no infection physics in `engine.py`.
- Sealed campaign seeds `801–816` remain untouched (`ABORT / sealed FAIL`).
- `red_queen_proved` remains false (and related proved-claim flags stay closed).
- Runners stay off until the owner explicitly allows execution.
- Unit of replication = **run**. Generation boundaries are observed via `GenerationBoundaryObserver`. Host–antagonist contact pairs are not N.
- **Reject** equating reward-seeking exploration or reactive memory update with rival-hypothesis discrimination.
- **Defer** EvoSCM (arXiv:2609.01526) to later literature watch; preprint only, not a locked journal precedent or result claim here.

---

## 2. Question

When does evolution select costly interventions that discriminate rival world-explanations, rather than reactive learning or reward-oriented exploration alone?

Under survival cost, limited lifespan, and a changing world on the contact/ATP ledger, do lineages invade that pay for interventions whose primary selective value is to separate rival causal accounts — or does selection stop at reactive update and reward exploration, with a named selective barrier against costly causal discrimination?

The potential discovery is a generalizable relation among exploration cost, lifespan, world-change rate, and the value of causal information for lineage survival — **or** honest non-emergence with a named selective barrier. The claim ceiling for this phase remains `phase1_problem_boundary`.

---

## 3. Prior art (verified DOIs)

| Place in argument | Citation | DOI |
|---|---|---|
| Evolved learning rules / ALife foraging | Giannakakis, Khajehabdollahi & Levina 2024 *Artif. Life* | `10.1162/artl_a_00458` |
| Cost and benefit of learning in changing environments | Arehart & Adler 2023 *Proc. R. Soc. B* | `10.1098/rspb.2023.1084` |
| Evolution of learning under environmental change | Kozielska & Weissing 2024 *PLOS Comput. Biol.* | `10.1371/journal.pcbi.1011840` |
| Active learning for optimal intervention design | Zhang, Cammarata, Squires et al. 2023 *Nat. Mach. Intell.* | `10.1038/s42256-023-00719-0` |
| Bayesian optimal experimental design for causal structure | Zemplenyi & Miller 2023 *Bayesian Anal.* | `10.1214/22-ba1335` |
| Environmental complexity and the evolution of cognition | Turner, Morgan & Griffiths 2024 *Proc. R. Soc. B* | `10.1098/rspb.2024.1524` |

**Deferred (preprint only):** EvoSCM — Scientific Belief Revision Through Causal Model Evolution and Experimentation, arXiv:2609.01526. The Crossref DOI `10.48550/arXiv.2609.01526` did not resolve in this session; cite as arXiv:2609.01526 [PREPRINT]. Deferred comparison only; not used as a result claim or journal precedent lock.

The published record covers evolved learning rules, cost–benefit of learning under change, and engineered active / interventional design for causal models. We are not aware of a published precedent for a **pre-registered evolutionary invasion regime** in which lineages pay survival-cost interventions whose selective value is measured by discrimination of rival world-explanations (not by reward gain alone), with run-level replication and an explicit honest-non-emergence outcome when the selective barrier holds.

---

## 4. Open boundary (gap wording)

We are not aware of a published precedent for mapping a selective boundary
\(P(\text{invade} \mid c, L, \rho, V_{\mathrm{causal}})\)
where \(c\) is exploration / intervention cost, \(L\) is lifespan on the generation boundary, \(\rho\) is world-change rate, \(V_{\mathrm{causal}}\) is the lineage value of discriminating rival explanations, invasion is scored as survival-share of **runs**, and non-emergence is reported as a named selective barrier rather than as a soft null.

Absence of a hit in the present search is not proof of uniqueness. The claim ceiling remains `phase1_problem_boundary`.

---

## 5. Competing hypotheses

| ID | Statement |
|---|---|
| **H0** | Costly causal-discrimination interventions do not invade or persist under the pre-registered cost, lifespan, and change-rate cells; any apparent “experimentation” fails the discrimination criterion or the survival margin. |
| **H1** | Reactive learning / reward exploration accounts for any apparent experimentation: lineages that update from observed outcomes or that explore for immediate reward match or beat the discrimination arm; no selective need for rival-hypothesis tests. |
| **H2** | Lineages that pay for interventions that discriminate rival world-explanations invade when cost / lifespan / change-rate satisfy a pre-registered regime (survival-share margin locked below); falsify H2 if an advantage appears without measurable discrimination of rivals. |

H2 is claimed only if the discrimination arm clears the locked margin **and** passes the discrimination operational test. Advantage without discrimination fails H2 and is read as H1 (or design FAIL if the discrimination assay was empty).

---

## 6. Operational definitions (mandatory; empty = reopen freeze)

These definitions must be filled in the design digest **before any run**. Leaving a required field empty, or filling it only after seeing data, reopens this freeze.

### 6.1 Rival-explanation discrimination

A **rival-explanation discrimination** event is a pre-registered intervention (or small intervention set) on the contact/ATP ledger whose outcome distribution is constructed so that at least two locked world-explanations make **different** predictions, and the lineage’s post-intervention update can be scored as selecting one explanation over the other.

Before any run, the design digest must register:

1. The rival explanation pair (or finite set) and their distinct predictions on ledger observables.
2. The allowed intervention set, cost bound, and generation-boundary timing.
3. The scoring rule that marks a trial as discriminating (not merely collecting reward).
4. That interventions never open domain RNG hacks in `engine.py`.

Empty discrimination schema = reopen freeze. Reward gain alone never counts as discrimination.

### 6.2 Reactive learning / reward exploration arms

- **Reactive learning:** update from observed outcomes without issuing a discrimination intervention.
- **Reward exploration:** explore actions to improve immediate or short-horizon payoff without a locked rival-explanation contrast.

Before any run, the design digest must register how each arm is implemented on the ledger and how it is forbidden from silently issuing discrimination interventions.

### 6.3 Costly causal-experimentation arm

A **costly causal-experimentation** lineage may issue discrimination interventions under a pre-registered survival or ATP cost, with heritability / persistence rules fixed in the digest.

Before any run, the design digest must register:

1. Cost schedule \(c\) (ledger-visible).
2. Lifespan / horizon parameters \(L\) in generation-boundary units.
3. World-change rate \(\rho\) (how fast rival-relevant structure turns over).
4. Inheritance or persistence rule for the experimentation propensity.
5. That cost is real on the survival/ATP ledger (not a cosmetic counter).

Empty cost or change-rate schedule = reopen freeze.

---

## 7. Locked estimand and thresholds (pre-data)

- **Primary estimand:** survival share to horizon T (run-level), not Δ growth alone.
- **Invasion / win:** ≥ 0.15 survival-share versus the best rival arm in the same cell, over ≥ 6 runs when execution is later allowed.
- **H2 support** requires both: (i) the discrimination arm clears the 0.15 margin in a pre-registered \((c, L, \rho)\) cell, and (ii) the discrimination assay passes (rival accounts separated by the locked scoring rule).
- **H2 fails** if survival advantage appears without discrimination of rivals → read as H1 (or design FAIL).
- **H0 favoured** if no arm that pays discrimination costs clears the margin in any pre-registered cell.
- \(N\) = runs. Contact pairs are not N. Series via `GenerationBoundaryObserver`.

---

## 8. Falsifiers

| Outcome | Reading |
|---|---|
| No costly discrimination arm clears 0.15 in any pre-registered cell | Favour H0; report named selective barrier (cost / lifespan / change-rate). |
| Reward exploration or reactive learning matches or beats discrimination without passing the discrimination assay | Favour H1. |
| Survival advantage without measurable rival discrimination | H2 fails; do not claim causal experimentation. |
| Advantage only via infection physics in `engine.py` or domain RNG hacks | Design FAIL; result discarded. |
| Empty discrimination schema at run time | Freeze reopened; results invalid. |

---

## 9. Mechanism surface (domain-free)

Cost, lifespan, world change, and interventions are expressed only as:

- contact / ATP ledger actions and costs,
- resource and survival schedules,
- generation-boundary timing via `GenerationBoundaryObserver`,

using the general engine. No infection physics is added to `engine.py`. Rival explanations are ledger-visible prediction contrasts, not domain RNG branches.

---

## 10. What this phase does not claim

- Not a discovery, law, or “first” claim.
- Not authorisation to start runners, pilots, or campaigns.
- Not a revision of sealed seeds `801–816`.
- EvoSCM (arXiv:2609.01526) remains deferred preprint watch only.
- Reward exploration ≠ rival-hypothesis discrimination; reactive learning ≠ causal experimentation.
