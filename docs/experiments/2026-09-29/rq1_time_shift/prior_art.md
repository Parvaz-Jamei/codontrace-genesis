# RQ-1 prior art

**Search date:** 2026-09-29 (live web search, this session).
**Scope of the search:** time-shift assays in host–parasite coevolution; digital
evolution host–parasite systems; common-versus-rare host genotype advantage;
re-evolution of digital traits.

## Nearest work

| # | Work | Relation to RQ-1 |
|---|---|---|
| 1 | [Decaestecker et al., *Nature* 450, 870–873 (2007)](https://www.nature.com/articles/nature06291) — host–parasite Red Queen dynamics archived in pond sediment | The original time-shift design: a past antagonist is assayed against present versus past hosts. RQ-1's time-shift assay is this design. |
| 2 | [Gaba & Ebert, *TREE* 24(4), 226–232 (2009)](https://hal.inrae.fr/hal-02667425v1/dc) — time-shift experiments as a tool to study antagonistic coevolution | Reviews the method, its controls and its interpretation limits. Confirms a 3×3 cross-time matrix is a standard instrument, not a novelty. |
| 3 | [Gibson et al., *Biology Letters* (2020), doi:10.1098/rsbl.2020.0210](https://pmc.ncbi.nlm.nih.gov/articles/PMC7423043/) — experimental test of parasite adaptation to common versus rare host genotypes | Rare-host-advantage is already tested empirically; RQ-1's "recently common host" framing is the same question. |
| 4 | [Buckingham & Ashby, *J. Evol. Biol.* 35, 205–224 (2022), doi:10.1111/jeb.13981](https://doi.org/10.1111/jeb.13981) | Coevolutionary theory of hosts and parasites; short time-shift windows can look directional under fluctuating selection. This is why RQ-1 demands the interaction contrast rather than a single sign. |
| 5 | [Fortuna et al., *Nature Communications* 7, 12462 (2016)](https://www.nature.com/articles/ncomms12462) — environmental change makes robust ecological networks fragile (Avida) | Host–parasite digital networks already exist in Avida; a digital host–antagonist contact matrix is not new. |
| 6 | [Zaman, PhD thesis (2014) — host–symbiont coevolution in digital and microbial systems](http://diyhpl.us/~bryan/papers2/Host-symbiont%20coevolution%20in%20digital%20and%20microbial%20systems%20-%20Zaman%20-%20thesis%20-%202014.pdf) | Digital-system host–parasite coevolution with archived lineages; closest digital precedent for cross-temporal comparison. |
| 7 | [Yedid, Ofria & Lenski (2008), *Am. Nat.*](https://pubmed.ncbi.nlm.nih.gov/18564346/) — re-evolution of a complex digital trait | Re-evolution of a digital trait is already published. |
| 8 | [Blount, Lenski & Losos, *Science* 362, eaam5979 (2018)](https://doi.org/10.1126/science.aam5979) — contingency and determinism: replaying life's tape | Frames the replay/fork requirement RQ-1 inherits. |

## Negative / cautionary results already on record

* The repository's own sealed stage-0 record (`DISCOVERY_PROGRAM_STAGE0_20260929.md`)
  already issues `BLOCKED_MEASUREMENT` for RQ-1 on the live model and states that
  a hand matrix with a contemporary peak is not fluctuating selection in this
  model.
* The earlier time-shift work in the repository (`open_problem_20260925_time_shift.py`)
  reports that a panel which passes on a mechanism built to cycle only tests the
  **detector**; the live demography alone does not license FRQ/ERQ discrimination.
* The repository's causal-tape record reports that coevolution does not maintain
  costly sex in that model, and that antagonist turnover does not raise the
  critical cost — a negative result that stays negative.

## Testable difference claimed here

**None that is a novelty claim.** RQ-1's design is the standard time-shift assay
(items 1–2). What this pack tests is narrower and is *not* claimed as new:

1. the primary quantity is the **interaction contrast** of `π_realised` across
   host time × antagonist time, with the frequency histogram explicitly excluded
   from the estimand (`histogram_used=false`, `class_frequency_used=false`), and
2. the negative control is a **random permutation of the time labels**, which must
   remove the pattern.

Both are measurement-hygiene requirements, not a scientific first. The live
model currently cannot run the assay at all, so no distinct prediction can be
evaluated yet (see `decision.md`).

## Non-claims

* A passing fixture on a mechanism built to cycle tests the detector only.
* An injected positive is not a discovery.
* A 2026-09-29 search result gives no right to a "first in the world" claim.
