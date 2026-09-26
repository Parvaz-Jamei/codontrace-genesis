# Demography-only Stage 0 results (HP-ARM01-RQ-EARN-DEMOGRAPHY-TUNE), 2026-09-26

This file records outcomes for the lock in
`WAVE7_DEMOGRAPHY_TUNE_PREREG_20260926.md` (also mirrored as the Stage 0
slice ahead of `WAVE7_RQ_EARN_CONFIRM_PREREG_20260926.md`). The
preregistration was not edited after seeing outcomes. Soft carrying
capacity \(K\) and the demographic floor were not relaxed after peeking.
Polymorphism hold, lagged negative frequency-dependent selection (NFDS),
and Red Queen Dynamics (RQD) were **not** scored on this slice.

| Pin | Commit |
|---|---|
| Demography Stage 0 runner | `ecd474978782d90f15caa2c705eb81bc1d80c6de` |
| Winner pin into RQ-earn confirm prereg §2 | `291019d` (tip lineage of Stage 0 follow-up) |
| Lagged-NFDS / RQ-earn scaffold (prior, not scored here) | `fa69913` |

Sealed Slowinski prereg `214df20`, persistence ledger `91ab0c6`, mating
ledger `7171d19`, and sealed structural confirm seeds **701–708**
(`CLOSED_LOOP_HP_ARM01_STRUCTURAL_RQ_CONFIRM_RESULTS_20260926.md`) were
not touched and were not reused.

Nosek et al. (Proc. Natl. Acad. Sci. USA 115:2600–2606, 2018,
doi:10.1073/pnas.1708274114) and Simmons, Nelson, and Simonsohn
(Psychol. Sci. 22:1359–1366, 2011, doi:10.1177/0956797611417632)
motivate writing seeds, grid cells, and pass rules before outcomes.
Kriegeskorte et al. (Nat. Neurosci. 12:535–540, 2009, doi:10.1038/nn.2303)
forbid selecting the analysis on the confirming data. Ashby (J. Evol.
Biol. 33:1795–1805, 2020, doi:10.1111/jeb.13718) separates sex-maintenance
claims from Red Queen Dynamics; this Stage 0 estimand is neither — it is
**debit-arm demographic readability under antagonist load** only.

## Why this slice existed

The sealed structural confirmatory campaign (seeds 701–708) returned one
typed `regime_hostile_ne` (seed 702): hold-class PASS was still true
(7/8), but a demographic crash can burn confirmatory seeds before
frequency clocks speak. Gokhale and Traulsen (Sci. Rep. 3:3180, 2013,
doi:10.1038/srep03180) stress that finite-\(N\) host–parasite games are
sensitive to demographic envelope. Elena and Lenski (Nat. Rev. Genet.
4:457–469, 2003, doi:10.1038/nrg1088) treat feast–famine refill under load
as a separate experimental control from evolutionary readouts. Owner
critique after 701–708 therefore required a **demography-only** tune
(separate estimand) before locking bolus × patches for the RQ-earn
confirm (seeds 801–816).

## Locked inputs (unchanged after inspection)

| Knob | Lock |
|---|---|
| Seeds | **751–758** (n=8); never reuse 601–603, 701–708, 801+ |
| Horizon / windows | **500**; floor checked at **125 / 250 / 500** |
| Soft \(K\) | **64** (fixed; raising \(K\) as an \(N_e\) fix forbidden) |
| min_viable floor | **12** (fixed; floor cut forbidden) |
| Host / parasite \(N\); founders; bit-flip | 64 / 64; 16 distinct; 0.02 |
| Sub-loci | 3×2 graded feature-overlap (AND-exact refused) |
| \(\kappa\) / p-mut / vir / steal | 0.5 / 0.25 / 8.0 / 0.15 |
| Primary success | Both debit arms (`fixed`, `copassaged`) census ≥ 12 at every locked window |
| Cell PASS | ≥ **6/8** `demography_ok` |
| Bolus × patches grid (≤3 cells, pre-registered) | **(24, 20)**, **(28, 20)**, **(24, 24)** |
| Unscored here | \(R_{\min}\)/\(\varepsilon\), polymorphism, lagged NFDS, Pearl, RQ flags |

Ecology debit arms follow the Morran–Slowinski-style contrast used in this
closed loop (Morran et al., Nature 464:275–278, 2010,
doi:10.1038/nature08840; Slowinski et al., Evolution 70:1550–1561, 2016,
doi:10.1111/evo.12915), scored **only** for floor survival — not for
selfing invasion, not for RQD.

## Campaign outcome

| Item | Value |
|---|---|
| Stage 0 PASS (≥6/8 on a winning cell) | **True** |
| (24.0 × 20) `demography_ok` | **8 / 8** |
| (28.0 × 20) `demography_ok` | **8 / 8** |
| (24.0 × 24) `demography_ok` | **8 / 8** |
| `regime_hostile_ne` (any cell) | **0** |
| `parasite_extinct` / `horizon_insufficient` | **0 / 0** |
| Winner (tie-break: lower bolus, then fewer patches) | **24.0 × 20** |
| Claim ceiling | `runtime_observation` |
| `red_queen_proved` | **false** |
| `biological_red_queen_proved` | **false** |
| Workers / wall | 6 parallel; ≈5786 s (≈96 min Asia/Tehran) |
| `engine.py` domain-token scan | clean (no infection / virulence / parasite physics) |

Winner-cell design digest:
`hp_arm01_demography_tune_design:2567bc8229880c14329d980d2b8132b241b8344cd7d29f991aefc23a06004c37`

Winner-cell report digest:
`34515c7bd72219690889fd56ed9d61f987424c2e2960cc34211c2a55769bab55`

## Winner cell seed table (24.0 × 20)

Living host census at locked windows on debit arms (pass iff every entry ≥ 12):

| Seed | typed | fixed@125 | fixed@250 | fixed@500 | cop@125 | cop@250 | cop@500 |
|---|---|---:|---:|---:|---:|---:|---:|
| 751 | demography_ok | 41 | 36 | 49 | 30 | 36 | 43 |
| 752 | demography_ok | 44 | 54 | 62 | 34 | 48 | 44 |
| 753 | demography_ok | 48 | 57 | 54 | 26 | 49 | 48 |
| 754 | demography_ok | 46 | 29 | 43 | 51 | 35 | 38 |
| 755 | demography_ok | 33 | 30 | 33 | 58 | 56 | 46 |
| 756 | demography_ok | 32 | 46 | 58 | 28 | 55 | 61 |
| 757 | demography_ok | 23 | 25 | 61 | 39 | 54 | 61 |
| 758 | demography_ok | 33 | 47 | 48 | 33 | 39 | 57 |

Terminal censuses stayed well above the floor of 12; the tightest locked
window on the winner cell was fixed@125 for seed 757 (census 23), still
nearly 2× min_viable.

## Analysis (what this does and does not buy)

1. **Demographic envelope is readable.** Across three pre-registered
   feast–famine cells, every seed kept both debit arms above the floor at
   every locked window. The `regime_hostile_ne` failure mode seen on
   structural confirm seed 702 did not recur under this Stage 0 design.
2. **Bolus × patches is no longer a free knob.** All three cells hit 8/8,
   so the pre-registered tie-break selected the landed structural defaults
   **(24.0, 20)** rather than escalating resource. That pin was copied
   verbatim into `WAVE7_RQ_EARN_CONFIRM_PREREG_20260926.md` §2 before
   Stage 1 outcomes.
3. **Not RQD, not sex-by-RQ.** Ashby (2020): polymorphism / cycle
   candidacy ≠ Red Queen Dynamics; sex maintained by parasites is a
   separate claim. Dybdahl and Lively (Evolution 52:907–915, 1998,
   doi:10.1111/j.1558-5646.1998.tb01833.x) lagged tracking is the Stage 1
   clock, not this slice. Stage 0 deliberately left lagged NFDS, Pearl
   freeze≠absent passages, and ClaimGate `red_queen_proved` unscored /
   false.
4. **Power still belongs to Stage 1.** n=8 here is only a demography
   gate. The RQ-earn confirmatory design uses fresh seeds **801–816**
   (n=16) with SUCCESS iff `rq_earn_seed_pass` ≥ 12/16 under conjunctive
   floor + hold + lagged NFDS + true Pearl contrasts — after Critic P4
   review before any allowlist change.
5. **Honest limits.** Soft \(K=64\) remains a modelling soft cap, not an
   effective-population-size certificate (Gokhale & Traulsen 2013). Floor
   survival does not imply antagonist-driven oscillating selection.
   Decaestecker et al. (Nature 450:870–873, 2007, doi:10.1038/nature06291)
   and Papkou et al. (BMC Biol. 14:81–94, 2016, doi:10.1186/s12915-016-0304-z)
   remain the empirical benchmarks Stage 1 must approach with clocks, not
   with census alone.

## Explicit non-claims

- No `red_queen_proved` / `biological_red_queen_proved`.
- No rewrite of sealed 701–708 hold-class PASS into an RQ claim.
- No packaging of Stage 0 PASS as evidence of lagged NFDS or sex
  maintenance.
- No post-peek floor cut, \(K\) raise, or new grid cells.

## Handoff

Stage 0 **PASS**. Stage 1 RQ-earn confirmatory campaign (seeds 801–816) is
authorized under bolus × patches = **24.0 × 20** and the locks in
`WAVE7_RQ_EARN_CONFIRM_PREREG_20260926.md`. Local evidence pack:
`evidence_wave7_demography_20260926/` (live metrics JSONL, per-cell
reports, campaign summary).

## References

1. Ashby B. 2020. When should sex and dispersal be linked? *J. Evol. Biol.*
   33:1795–1805. doi:10.1111/jeb.13718
2. Decaestecker E, Gaba S, Raeymaekers JAM, et al. 2007. Host–parasite
   ‘Red Queen’ dynamics archived in pond sediment. *Nature* 450:870–873.
   doi:10.1038/nature06291
3. Dybdahl MF, Lively CM. 1998. Host-parasite coevolution: evidence for
   rare advantage and time-lagged selection. *Evolution* 52:907–915.
   doi:10.1111/j.1558-5646.1998.tb01833.x
4. Elena SF, Lenski RE. 2003. Evolution experiments with microorganisms:
   the dynamics and genetic bases of adaptation. *Nat. Rev. Genet.*
   4:457–469. doi:10.1038/nrg1088
5. Gokhale CS, Traulsen A. 2013. Evolutionary games in the multiverse.
   *Sci. Rep.* 3:3180. doi:10.1038/srep03180
6. Kriegeskorte N, Simmons WK, Bellgowan PSF, Baker CI. 2009.
   Circular analysis in systems neuroscience: the dangers of double
   dipping. *Nat. Neurosci.* 12:535–540. doi:10.1038/nn.2303
7. Morran LT, Schmidt OG, Gelarden IA, Parrish RC II, Lively CM. 2010.
   Running with the Red Queen: host-parasite coevolution selects for
   biparental sex. *Nature* 464:275–278. doi:10.1038/nature08840
8. Nosek BA, Ebersole CR, DeHaven AC, Mellor DT. 2018. The preregistration
   revolution. *Proc. Natl. Acad. Sci. USA* 115:2600–2606.
   doi:10.1073/pnas.1708274114
9. Papkou A, Gokhale CS, Traulsen A, Schulenburg H. 2016. Host–parasite
   coevolution: why changing population size matters. *BMC Biol.*
   14:81–94. doi:10.1186/s12915-016-0304-z
10. Simmons JP, Nelson LD, Simonsohn U. 2011. False-positive psychology.
    *Psychol. Sci.* 22:1359–1366. doi:10.1177/0956797611417632
11. Slowinski JB, Morran LT, Parrish RC II, et al. 2016. Coevolutionary
    interactions with parasites constrain the spread of self-fertilization.
    *Evolution* 70:1550–1561. doi:10.1111/evo.12915
