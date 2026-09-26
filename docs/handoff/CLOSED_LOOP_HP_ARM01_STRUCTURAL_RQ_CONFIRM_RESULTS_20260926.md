# Structural Red Queen confirmatory results (HP-ARM01-STRUCTURAL-RQ-CONFIRM), 2026-09-26

This file records outcomes for the lock in
`CLOSED_LOOP_HP_ARM01_STRUCTURAL_RQ_CONFIRM_20260926.md`. The
preregistration / confirmatory design file was not edited after the run.
Parameters were not retuned after seeing outcomes.

| Pin | Commit |
|---|---|
| Confirmatory design lock (pre-outcome) | `7abe12cde3dc6e52d1fcf25fe7c51eba757abff1` |
| Mechanism commit | `b533a721054f725e913b183735b1ab924dd41fbb` |
| Campaign tip (runtime) | `08c601b1e65cdd63423ff9fc21e11c80e753119e` |

Sealed Slowinski prereg `214df20`, persistence ledger `91ab0c6`, and mating
ledger `7171d19` were not touched. Pilot seeds 601–603
(`CLOSED_LOOP_HP_ARM01_STRUCTURAL_RQ_REGIME_RESULTS_20260926.md`) remain
**prior observation only** and were not reused. Mating / Slowinski invasion
remain deferred and unscored this wave.

Nosek et al. (Proc. Natl. Acad. Sci. USA 115:2600–2606, 2018,
doi:10.1073/pnas.1708274114) separate prediction from postdiction. Simmons,
Nelson, and Simonsohn (Psychol. Sci. 22:1359–1366, 2011,
doi:10.1177/0956797611417632) motivate writing seeds and pass rules first.
Kriegeskorte et al. (Nat. Neurosci. 12:535–540, 2009, doi:10.1038/nn.2303)
forbid selecting the analysis on the confirming data. Ashby (J. Evol. Biol.
33:1795–1805, 2020, doi:10.1111/jeb.13718): sex ≠ Red Queen Dynamics;
`polymorphism_hold` ≠ `cycle_candidate` ≠ `red_queen_proved`.

## Locked inputs (unchanged after inspection)

500 generations; locked windows 125, 250, 500; conjunctive hold only
(\(R_{\min}=3\), \(\varepsilon=0.15\)); host \(N=K=64\); parasite \(N=64\);
16 distinct match-state founders; host bit-flip 0.02; 3×2-bit graded
feature-overlap debit (AND-collapse forbidden); \(\kappa=0.5\); parasite
mutation 0.25; virulence 8.0; steal 0.15; birth ATP 48; bolus **24.0** on
**20** patches; min viable census 12 (demographic floor only, not an
\(N_e\) proxy); asexual substrate (mating deferred); fresh seeds **701–708**;
campaign PASS iff hold-class ≥ **6/8**; substrate
`population_runner_phase_b_host_parasite_env`.

Ecology arms follow the Morran–Slowinski-style three-arm contrast used in
this closed loop (Morran et al., Nature 464:275–278, 2010,
doi:10.1038/nature08840; Slowinski et al., Evolution 70:1550–1561, 2016,
doi:10.1111/evo.12915), scored here only for structural polymorphism hold /
cycle candidacy — not for selfing invasion:

| Ecology arm | Tip passage | Role |
|---|---|---|
| `avirulent` | `absent` | No-antagonist control |
| `fixed` | `frozen` | Debit-active score arm |
| `copassaged` | `coevolve` | Debit-active score arm |

## Campaign outcome

| Item | Value |
|---|---|
| Campaign PASS (hold-class ≥ 6/8) | **True** |
| Hold-class (polymorphism_hold + cycle_candidate) | **7 / 8** |
| Typed `polymorphism_hold` (un-upgraded) | 0 / 8 |
| Typed `cycle_candidate` (observation upgrade after hold) | **7 / 8** |
| Typed `regime_hostile_ne` | 1 / 8 |
| Sweep / horizon / parasite-extinct / selfing / Slowinski | 0 |
| Slowinski scored | **no** (deferred) |
| Claim ceiling | `candidate_evidence` |
| `red_queen_proved` | **false** |
| `biological_red_queen_proved` | **false** |
| Workers / wall | 6 parallel workers; ≈3731 s (≈62 min) |

Design digest:
`hp_arm01_structural_rq_confirm_design:b297d40e3b3b1fdab4c2d5d4e8d781ff2e37136586fc63727120e1c2f319ec18`

Document digest:
`b678cfa21a0cc10016b6831114234ff074d0cbe1dbe276a6ad37ee349e4351d1`

Campaign digest:
`66a7725017c5166c20e7191dad7dcb6f9b8ba4ad456804e88069dbc7df8a8823`

## Seed table

Terminal census is living host mating census at generation 500
(avirulent / fixed / copassaged).

| Seed | Typed outcome | Terminal census avi / fixed / copassaged | Notes |
|---|---|---|---|
| 701 | `cycle_candidate` | 64 / 40 / 37 | ceiling `candidate_evidence` |
| 702 | `regime_hostile_ne` | 62 / 55 / 12 | ceiling `runtime_observation`; copassaged at demographic floor |
| 703 | `cycle_candidate` | 64 / 32 / 24 | ceiling `candidate_evidence` |
| 704 | `cycle_candidate` | 64 / 40 / 41 | ceiling `candidate_evidence` |
| 705 | `cycle_candidate` | 64 / 29 / 36 | ceiling `candidate_evidence` |
| 706 | `cycle_candidate` | 63 / 24 / 50 | ceiling `candidate_evidence` |
| 707 | `cycle_candidate` | 64 / 56 / 25 | ceiling `candidate_evidence` |
| 708 | `cycle_candidate` | 64 / 36 / 26 | ceiling `candidate_evidence` |

Per prereg, `cycle_candidate` is recorded only after conjunctive
`polymorphism_hold` criteria hold, plus dominant-class turnover across ≥2
locked windows. Hold-class for the campaign bar therefore counts these seven
seeds. Primary success for ClaimGate packaging remains the hold estimand;
cycle candidacy does **not** authorize `red_queen_proved`.

## Reading against related work

### Large \(N\) and multi-locus structure

Gokhale & Traulsen (BMC Evol. Biol. 13:254, 2013,
doi:10.1186/1471-2148-13-254) show that Red Queen-like cycling is fragile
under small effective population size: stochastic fixation / loss can erase
frequency clocks before a cycle is readable. Engelstädter (Am. Nat. 185:E000,
2015, doi:10.1086/680476) likewise argues that single-locus matching is a
poor substrate for sustained antagonistic coevolution relative to multilocus
architectures. The confirmatory stack was built for that structural gap:
host \(N=K=64\), founder match-state richness 16, and graded multi-sublocus
debit rather than AND-collapse. Relative to the pilot (1/3
`polymorphism_hold`, 2/3 `regime_hostile_ne` at 250 generations), the
confirmatory horizon (500 generations) and conjunctive hold produced
hold-class **7/8**, meeting the pre-registered PASS bar of 6/8.

### Empirical Red Queen and three-arm ecology

Morran et al. (Nature 464:275–278, 2010, doi:10.1038/nature08840) and
Slowinski et al. (Evolution 70:1550–1561, 2016, doi:10.1111/evo.12915)
motivate coevolving versus fixed-antagonist contrasts in host–parasite
systems. Decaestecker et al. (Nature 450:870–873, 2007,
doi:10.1038/nature06291) and Papkou et al. (Proc. R. Soc. B 288:20212269,
2021, doi:10.1098/rspb.2021.2269) document time-lagged adaptation and
allele-frequency change under natural coevolution. Rabajante et al.
(Sci. Rep. 5:10004, 2015, doi:10.1038/srep10004) illustrate how oscillatory
matching can appear when diversity is maintained. In this campaign the
`avirulent` control stayed near soft \(K\) (terminal census 62–64) with zero
match debits, while debit-active arms ran leaner but usually above the
demographic floor — consistent with antagonist pressure that does not
globally extinguish the deme.

### What this PASS is — and is not

Ashby (J. Evol. Biol. 33:1795–1805, 2020, doi:10.1111/jeb.13718) warns against
equating the maintenance of sex, polymorphism, or oscillation candidacy with
proof of Red Queen Dynamics. Here:

- **PASS** means the pre-registered structural hold-class bar was met (7/8).
- Seven seeds show **observation-only** `cycle_candidate` upgrades after hold.
- Seed 702 is typed `regime_hostile_ne` because the `copassaged` arm sat at
  the demographic floor (terminal census 12; earlier windows dipped to ~7),
  so allelic series are not interpretable as hold — a demography gate, not a
  soft-green path to RQ.
- `red_queen_proved` and `biological_red_queen_proved` stay **false**.
- Claim ceiling is `candidate_evidence`.
- Slowinski selfing invasion remains unscored; sealed FAILS are untouched.

Resource scaling (bolus 24.0 × 20 patches) follows the Elena & Lenski
(Nat. Rev. Genet. 4:457–469, 2003, doi:10.1038/nrg1088) spirit of matching
refill density to world / \(N\), as locked before outcomes — not a post-hoc
rescue of typed fails.

### Limits for later work (not applied to this sealed campaign)

Binomial sampling under an illustrative coin-flip null still leaves a
non-negligible chance of ≥6/8 successes at \(n=8\); larger confirmatory \(n\)
(e.g. 16–24 fresh seeds) would tighten that margin. Demographic-floor loss
(seed 702; pilot 602–603) remains a separate estimand from allelic Red Queen
structure. Threshold sensitivity for \(R_{\min}\) and \(\varepsilon\) was not
part of this sealed primary analysis and would need its own pre-registered
secondary table. None of those amendments may rewrite the present sealed
PASS/FAIL.

## Engine / claim hygiene

HP / infection vocabulary stays in plugin / env / closed_loop modules.
`engine.py` stays domain-free. ClaimGate refuses packaging this campaign as
`red_queen_proved` or as Slowinski invasion PASS.

## Evidence package

Local sealed evidence (outside the primary source tree for size):
`/workspace/codontrace-genesis-storm/evidence_structural_rq_confirm_20260926/`
(`RESULT.md`, `campaign_report.json`, `live_metrics.jsonl`,
`typed_outcome_counts.json`).
