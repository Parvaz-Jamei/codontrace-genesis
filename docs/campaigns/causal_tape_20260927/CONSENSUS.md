# Causal tape campaign — design consensus (stage 1)

**Date:** 2026-09-27 · **Status:** consensus recorded before implementation
**Related:** `docs/architecture/PHASE_BUILD_PROTOCOL.md`, `docs/CAUSAL_VALIDATION_PROTOCOL.md`,
`docs/CLAIMS.md`

## Purpose

Three questions were selected for this campaign. Each one is answerable only
because the life loop is deterministic and its random draws can be replayed
without re-keying the stream, so a counterfactual arm can be run that differs
from the factual arm in exactly one intervention.

1. **Estimator benchmark.** When the exact interventional effect of a single
   substitution is computable, how wrong are the estimators normally applied to
   observational lineages — naive conditioning and regression adjustment?
2. **Two-fold cost of sex.** Does coevolution with an antagonist maintain sexual
   reproduction when Maynard Smith's cost is charged as an explicit energy debit
   in a conserved ledger?
3. **Biotic versus abiotic turnover.** In a two-factor design, what share of
   genotype turnover is attributable to a coevolving antagonist and what share to
   an abiotic resource pulse, on one generation clock?

## Evidence brought to the design

The literature review for round 1 produced four conclusions that shaped the
brief and are carried into the text as concessions rather than as novelty.

| Finding | Source | Consequence for this campaign |
|---|---|---|
| Conditioning on the absence of a mutation is not an intervention and gives incorrect predictions for accumulation models | Díaz-Uriarte, Ríos-Arroyo & Johnston (2026), arXiv:2606.12597 | The benchmark measures the size of that error; it does not claim to discover it |
| The naive-versus-treated decomposition is standard selection-bias theory | Heckman (1979), *Econometrica* 47:153 | The `naive = ATT + selection bias` identity is presented as textbook, not new |
| Selection bias in mutation-effect estimation has been quantified and corrected in mutation-accumulation work | Wahl & Agashe (2022), *Evolution* 76:1189 | The contribution is the exact instrument, not the phenomenon |
| Noise-free paired counterfactuals require draws to be keyed to events, not to positions in a stateful stream | Klein et al. (2024), arXiv:2409.02086; Buffalo et al. (2026), arXiv:2603.11084 | The intervention is defined as suppressing a drawn event while leaving the stream untouched; this is the published remedy, applied |
| Non-commutativity of substitutions is a named, separately estimable quantity | Bajić et al. (2018), *PNAS* 115:11286 | Order dependence is reported under that name; the paper does not claim to have found order sensitivity |
| A digital host–parasite factorial over biotic and abiotic factors is published | Acosta & Zaman (2022), *Front. Ecol. Evol.* 9:750772 | Question 3 is framed as a measurement with a drift-calibrated turnover statistic and a uniform-tax control, not as a first comparison |
| Realised two-fold cost can vanish under resource limitation | Yasui (2026), *J. Evol. Biol.* 39:1154 | The primary outcome for question 2 is genotype frequency and extinction time, never equilibrium realised fitness |

Two further sources fixed the instrumentation rather than the claim: Powell &
Mariscal (2015), *Interface Focus* 5:20150040, who treat the replay question as a
modal one for which a deterministic engine is the appropriate instrument, and
Marshall & Galea (2015), *Am. J. Epidemiol.* 181:92, who require that the
estimand be stated and that ergodicity or its failure be characterised.

## Adopted, deferred, rejected

**Adopted.** Exact paired counterfactuals with the draw stream untouched; a
closed-form ground truth for the additive case that must be recovered to machine
precision; a rechargeable ledger with a deliberate leak as an audit control; a
frequency-weighted turnover statistic with a drift null built on the effective
number of breeders; a genotype-blind uniform-tax control; per-run datasets so
estimators can be recomputed without re-simulating.

**Deferred.** A matched-schedule arrival-order intervention against a permuted
multiset is implemented, but the number of independent coupling draws is too
small for its environment-level claim; it is reported descriptively.

**Rejected.** Renaming existing quantities as new ones; presenting a digital
landscape written for the experiment as a biological result; treating a
bit-reproducible stream as evidence of anything beyond reproducibility;
softening a threshold to convert an honest negative into a positive.
