# Discovery program — stage-0 result

**Date:** 2026-09-29  
**Parent tip:** `5824446`  
**Program:** RQ-1, RQ-2, RQ-3, RQ-4, D-1, D-2, D-3, D-4  
**Claim ceiling:** `phase2_design`  
**Status:** stage-0 instrument only — not a population pilot and not a discovery

## Count

The program names eight tests. None of the eight had been written as a population test. This record does not run them. Adjacent hand meters already in the tree (realised-pressure separation, the swap-signal arithmetic, and the structural time-shift labels) were re-run and stayed green. Those meters are not the pilots.

## Sealed positive outcome

The positive outcome is that the meter reproduces locked arithmetic and rejects the pre-specified null fixtures. It is not evidence about a live population.

1. Contact rule: mean of three two-bit sub-locus scores, debit `1.2 × affinity`. Example 1 gives `π_A = 0.900`, `π_B = 0.100`, difference `0.800`, histogram difference `0`. The old table's `0.700` treated `111100` against `000011` as affinity `1/6`. Under the rule that affinity is `0`. The rule was not changed. `0.20` and `−0.148` were not changed.
2. Flat affinity `0.5`: both classes at `π = 0.600`. A histogram shift of `+0.250` does not move `π`.
3. Truncation: intended class difference `0`, realised difference `0.100`. The paid debit does not exceed the reserve.
4. RQ-1 fixtures, not a run: a contemporary matrix and a lagged matrix receive those labels. A flat matrix, a directional increase, and one rotation of the time labels do not. The live model did not produce the matrices.
5. RQ-3 hand channel: `S = −0.600`, so the preregistered direction and the `0.20` floor hold as arithmetic. The same pairing held fixed gives `S = 0`. The live census is not this channel.
6. The hand-section digest is unchanged on a second call.
7. Short live cells stay blocked: idea 2, seed 301, 4 generations, population 4; idea 4 control, seed 301, horizon 5, population 4. The antagonist is not a genotype population. The checkpoint is not a full fork. Topology is not identified.

## Explicit non-outcomes

- No pilot and no confirmatory run of RQ-1, RQ-3, or D-2. Population-run count in the pack is 0.
- Stage 0 never returns `SUPPORTED_IN_MODEL`. Flags that merely say the machinery exists would make RQ-1 and D-2 `INCONCLUSIVE`, not supported. D-3 and D-4 stay `BLOCKED_MEASUREMENT` because this stage has no inputs for them.
- `hypothesis_supported=false`. `red_queen_proved=false`.
- `−0.148` still sits inside the magnitude barrier. It was not recomputed and not raised.
- A time-shift assay is not new. Decaestecker et al. (2007) already used it. A hand matrix with a contemporary peak is not fluctuating selection in this model.
- Reading `instrument_positive_case` as a discovery is FAIL.

## Decision

`BLOCKED_MEASUREMENT` for RQ-1, RQ-3, and D-2 on the live model. The hand meter passed. Phase 3 stays closed.

## References

- Decaestecker, Gaba, Raeymaekers, Stoks, Van Kerckhoven, Ebert, and De Meester. Host–parasite ‘Red Queen’ dynamics archived in pond sediment. *Nature* 450, 870–873 (2007). doi:10.1038/nature06291
- Buckingham and Ashby. Coevolutionary theory of hosts and parasites. *Journal of Evolutionary Biology* 35, 205–224 (2022). doi:10.1111/jeb.13981
- Buckingham and Ashby. Separation of evolutionary timescales in coevolving species. *Journal of Theoretical Biology* 579, 111688 (2024). doi:10.1016/j.jtbi.2023.111688
- Blount, Lenski, and Losos. Contingency and determinism in evolution: Replaying life's tape. *Science* 362, eaam5979 (2018). doi:10.1126/science.aam5979

The program note also points at later re-evolution and network papers. Those bounds are why this stage does not claim novelty. Absence of a matching run here is not a claim that the pattern was demonstrated.
