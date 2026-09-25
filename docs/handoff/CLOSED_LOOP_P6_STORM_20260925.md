# Closed-loop phase 6 storm, 2026-09-25

Design note only. `red_queen_proved` stays false. No new simulator. No edit to `engine.py`.

## Unsolved measurement

Repeating Morran is not open. Coevolving *Serratia* already raised outcrossing and removed most obligate selfing in *C. elegans*, while a fixed parasite and no parasite did not (Morran et al. 2011, *Science* 333:216–218, doi:10.1126/science.1206360). A selfing allele invaded controls and fixed-parasite populations and stayed rare under copassage (Slowinski et al. 2016, *Evolution* 70:2632–2639, doi:10.1111/evo.13048). Species interactions usually select against sex and favor it only in a narrow slice (Otto & Nuismer 2004, *Science* 304:1018–1020, doi:10.1126/science.1094072). Parasites can also maintain sex with no Red Queen cycling, by a stable diversity advantage that depends on density and virulence (Ashby 2020, *J. Evol. Biol.* 33:1795–1805, doi:10.1111/jeb.13718).

What this engine has not scored, and those papers do not share, is one ATP ledger that already charges a mating fee. The open measurement is: on that ledger, for which infection debit, matching rule, and Holling shape does outcrossing persist and selfing disappear only while specificity coevolves and type frequencies cycle? `cycling_detected` on the Euler island is not that measurement.

## Imports (not another digital-evolution clone)

| Field | What is imported | What is not imported |
|---|---|---|
| Infection genetics | Matching-allele versus gene-for-gene is one continuum. Detection can be a match; eradication can be gene-for-gene. The virulence-cost knob flips which pattern dominates (Agrawal & Lively 2002, *Evol. Ecol. Res.* 4:79–90; 2003, *Proc. R. Soc. B* 270:323–334, doi:10.1098/rspb.2002.2193). | A second matrix file. Gene-for-gene is the end `assert_no_super_host_or_parasite` currently refuses, not a new stepper. |
| Ecology | Holling type II saturates attack as density rises; type III is sigmoidal (Holling 1959, *Can. Entomol.* 91:385–398, doi:10.4039/Ent91385-7). The type-II shape is already `α H / (1+H)` in `host_parasite_type2_rq.py` (Rabajante et al. 2015, doi:10.1038/srep10004). Type III can lock rare types so they barely cycle (Rabajante et al. 2016, *Sci. Adv.* 2:e1501548, doi:10.1126/sciadv.1501548). | The Euler loop as the birth clock. Import the debit shape only. |
| Causal inference | Freeze parasite updates and zero the debit are two `do` cuts, not one “frozen or absent” switch (Pearl 1995, *Biometrika* 82:669–688, doi:10.1093/biomet/82.4.669). | Setting `intervention_supported` or `red_queen_proved` from an observational gap. |

Polarity must be explicit. A match can mean infection or resistance. The sign decides which rare type is protected.

## Verdict on the expert list

1. Wire the specificity matrix into the closed loop. Keep, narrowed. Call the existing matrix or a new pure score from the life plugin. The score becomes one `debit_runtime` reason on `GenesisOrganism.atp_state`. Do not step `_euler_step` inside `step_population`. `graded_alpha_from_overlap` cannot score two bit-strings: a binary tape collapses to the character set `{0,1}`.
2. The 2×2 sexual × selfing by coevolving × frozen/absent is the control skeleton, not the question. Morran and Slowinski already ran it. Later cells, not this slice: debit size, match-versus-gene-for-gene, type II versus type III, and whether frequencies cycle (Ashby).
3. Track extinction across generations. Keep, later. Also record the outcross-allele trajectory. A binary extinct/persists flag mis-scores Ashby’s stable coexistence. One tick is not a generation. Type-2’s 8000 Euler steps are not population generations.
4. `red_queen_proved = True` iff sexuals persist, selfers die, and the gap vanishes when the parasite is frozen or removed. Reject as sufficient. That pattern also passes a large constant debit and Ashby’s non-cycling maintenance. “Or” lets one intervention stand in for two.

## Acceptance rule (not yet met)

`red_queen_proved` stays false until one plugin and one ATP ledger, mating fee still charged, show all of:

- outcrossing persists and obligate selfing is lost while specificity coevolves
- the gap disappears under both `do(freeze type updates)` and `do(zero the debit)`
- type frequencies cycle in the coevolving arm and not in the frozen arm
- the gap is absent at low debit and present only above a reported debit threshold

Falsifier: selfing is lost whenever the debit is large, whether or not types update or cycle; or outcrossing is lost in every arm once the mating fee is paid.

## Smallest next slice

Opt-in only. Default closed loop stays off, so the phase-A digest pin does not move. A pure function beside `outcross_fee_debit` returns `(amount, label, reason)` or `None`. The motor writes it with the existing `debit_runtime`. Constant alpha is refused. `engine.py` gains no host, parasite, outcross, or red-queen word. No 2×2 runner and no extinction flag in that slice. The first test asserts `red_queen_proved is False`.
