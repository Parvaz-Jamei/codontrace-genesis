# RQ-3 locked design — does the apparent cycle need heritable antagonist feedback?

**Version:** `rq3-design-v1`, locked 2026-09-29, round 1
**Owner:** dag-prereg (RQ-3 test agent)
**Base revision:** local discovery-program tip; repository writes by this agent: none.
**Claim ceiling:** `phase2_design`. `hypothesis_supported=false`, `red_queen_proved=false`.
**Thresholds locked here:** none may be changed after any run.

## 1. Question and pre-registered direction

> Does the apparent host–antagonist cycle require heritable feedback from the antagonist,
> or does it persist when the antagonist pays real contact and energy cost but cannot pass
> any frequency information to the next generation?

The hypothesis under test (`H1`) is that a delayed, **heritable** antagonist adaptation to the
host class that was previously common is what generates the rare-class growth advantage and
the later pressure on the previously common genotype. The nulls are (a) the same pattern with
the antagonist composition frozen while contact and cost stay real, (b) the same pattern with
the antagonist update cut from the host labels, and (c) demographic drift and resource
dynamics alone.

Pre-registered expectation: under `H1`, the coevolving arm shows a larger rare-ness effect and
a stronger delayed pressure contrast than both cut arms, and both cut arms' intervals include
zero while the coevolving interval does not. A bare `S < −0.20` is not an acceptance; the two
components of the outcome must agree in sign and magnitude.

## 2. Unit of replication and pairing

* The unit is one independent population history: a seed.
* Within a seed, arms start from the same initial state; after the intervention each arm uses
  its own labelled, replayable stream. No arm may gain an advantage in seed choice or tuning.
* Arms are paired on seed, and every seed is assigned to every arm.
* Provisional design (used in round 1): four arms — `coevolve`, `frozen` (fixed antagonist
  composition, real contact and real cost), `shuffled` (update cut from host labels),
  `sham` (intervention applied to an uninformative channel).
* Round-1 finding: at equal starting state the arms diverge demographically within a few
  generations, so the arm contrast is not identifiable until the snapshot-based fork of
  section 3 is implemented. That is recorded, not worked around.

## 3. Primary and secondary outcomes

All outcomes are computed per run from raw JSONL only (`rq3_analyze.py`).

1. **Rare-ness effect on growth (primary component A).** Over the measurement window, the
   mean difference in log growth between the below-median-frequency class and the
   above-median-frequency class, in log count per generation.
2. **Later pressure on the previously common genotype (primary component B).** The delayed
   pressure contrast: realised pressure on the class that was common `τ = 4` generations
   earlier minus realised pressure on the class that was rare then, in ATP per host per
   contact opportunity, plus the cross-lag correlation between host frequency and later
   pressure on the same class.
3. **Paired difference between arms** for both components, with a cluster bootstrap interval
   over seeds (10,000 resamples, seed `20260928`) and a moving-block secondary interval.
4. Secondary: extinction and censoring rates reported separately from the effect size;
   census trajectory; contact opportunities per class; antagonist ancestry rows.

`S < −0.20` alone is not the primary outcome and does not decide the test.

## 4. Stage 0 gates (all must hold before the confirmatory block)

| Gate | What it checks | Status in round 1 |
|---|---|---|
| G0.1 unit and property tests of the meter | affinity and pressure arithmetic | pass: six probe pairs, kernel self-consistent (`out_aff.txt`) |
| G0.2 hand-computed cases | `π_A = 0.900`, `π_B = 0.200`, flat affinity both 0.600, truncation difference 0.100 | pass (`out_hand.txt`) |
| G0.3 antagonist population functional test | heritable adaptation exists and the cut removes it | pass: coevolve 0.75 common-window share vs 0.25 for both cut arms (`out_antpop2.txt`) |
| G0.4 positive control, pre-defined | common host class contacted more, antagonist composition follows | pass (same file) |
| G0.5 negative control that must remove the effect | frozen and shuffled arms | **frozen arm does not remove the delayed link in the live model (round-1 pilot): gate fails → `BLOCKED_MEASUREMENT`** |
| G0.6 byte-identical replay from a snapshot | one replay command reproduces the summary from raw | implemented (`--stage replay`); checksums verified per run |
| G0.7 energy and population invariants | census positive, contacts bounded by seats, ATP paid never exceeds reserve | partially: the meter truncates at reserve; no arm-level ledger identity check yet |

## 5. Budget and schedule (program ceilings)

| Stage | Scope | Ceiling |
|---|---|---|
| timing | one seed, one generation, three arms | measured: 0.97–1.11 s per generation per arm, census 64 |
| calibration | 2 development seeds × 80 generations | met (`out_analyze1.txt`) |
| pilot | 4 further seeds × 150 generations | one seed run to 150 (`out_analyze_pilot.txt`); three more not spent because G0.5 failed |
| confirmatory | 8 locked unseen seeds × 200 generations | **not opened** |

Wall cap 8 minutes per test, 45 minutes per pack, one worker; soft memory stop at 3.5 GiB.
Stop conditions used: invariant violation, duplicate-id failure, incomplete data, over budget.
No run was stopped because a result was unwelcome.

## 6. Decision labels

Exactly one of `SUPPORTED_IN_MODEL`, `FALSIFIED_IN_MODEL`, `INCONCLUSIVE`,
`BLOCKED_MEASUREMENT`. `BLOCKED_MEASUREMENT` is legal only with an unblocking patch attached
and a re-run after it lands. A `PASS` label is never issued for a smoke test or for an injected
positive.
