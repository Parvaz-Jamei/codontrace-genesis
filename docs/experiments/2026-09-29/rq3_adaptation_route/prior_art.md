# RQ-3 prior art and novelty boundary

**Search date:** 2026-09-29 (document searches for RQ-3's mechanism).
**Question searched:** does an apparent host–antagonist cycle require *heritable* antagonist
feedback, i.e. can the delayed adaptation route be cut while contact and energy cost stay real?

**Repository-side sources are treated as evidence, not as an exhaustive review.** The
repository's own stage-0 record and reference lists were used, and the program's five named
sources were re-read. Independent web search was attempted; the search channel returned a
result set with no retrievable full text for the specific control design at issue, so nothing
below is claimed as a "first" and no absence of a hit is treated as uniqueness.

## Nearest work, and the testable difference for RQ-3

| Nearest work | What it establishes | Testable difference RQ-3 would add |
|---|---|---|
| Decaestecker, Gaba, Raeymaekers, Stoks, Van Kerckhoven, Ebert & De Meester (2007), *Nature* 450, 870–873, doi:10.1038/nature06291 | A time-shift assay reconstructs past host–parasite coevolution from a natural archive; the antagonist of a given date is best adapted to hosts of that date | The time-shift assay is *not* novelty. RQ-3's difference is the cut: the same contrast computed with the antagonist's heritable route removed and its contact cost intact, so the assay measures whether the delayed link needs heredity at all |
| Gibson, Harrison, Maldet, Beaudoin & Reuter (2020), *Biology Letters* 16, 20200210, doi:10.1098/rsbl.2020.0210 ([link](https://royalsocietypublishing.org/rsbl/article-split/16/7/20200210/62795/An-experimental-test-of-parasite-adaptation-to)) | An experimental test that a parasite adapts to common more than to rare host genotypes; rare advantage alone is not new | RQ-3 does not test rare advantage. It tests whether the *route* that would produce it is heritable, by running an antagonist whose composition is fixed but whose cost is real, and an antagonist whose update is cut from the host labels |
| Buckingham & Ashby (2022), *Journal of Evolutionary Biology* 35, 205–224, doi:10.1111/jeb.13981; Buckingham & Ashby (2024), *Journal of Theoretical Biology* 579, 111688, doi:10.1016/j.jtbi.2023.111688 | Coevolutionary theory of hosts and parasites, and the separation of evolutionary timescales between the two species | Those papers separate timescales analytically. RQ-3's difference is an operational cut on a running digital population: the antagonist keeps paying the energy cost of contact while its heritable feedback is removed, which no analytic timescale separation defines |
| Morran, Schmidt, Gelarden, Parrish & Lively (2011), *Science* 333, 216–218, doi:10.1126/science.1206360; Ashby (2020), *Journal of Evolutionary Biology*, doi:10.1111/jeb.13718 | Coevolution can select for biparental sex; polymorphism and cycling are not by themselves Red Queen dynamics | The second point is the reason for the control arm. RQ-3 inherits it and adds the requirement that the control *destroy* the delayed link, and reports `BLOCKED_MEASUREMENT` when it does not |
| Schenk, Schulenburg & Traulsen (2020), *BMC Evolutionary Biology*, doi:10.1186/s12862-019-1562-5 | Genetic drift limits how long Red Queen dynamics survive; population size and ecological rules matter | RQ-3's round-1 pilot shows the drift and demography confound directly: the arms diverge in census, and the delayed contrast is largest in the arm with a frozen antagonist. This is a measurement lesson from the model, and it is why the snapshot-based within-history design is required before any confirmatory seed |
| Acosta & Zaman (2022), *Frontiers in Ecology and Evolution* 9, 750772, doi:10.3389/fevo.2021.750772 | A digital host–parasite factorial over biotic and abiotic factors is published | Digital host–parasite systems are established; RQ-3 claims no new medium. Its difference is the heritable-route cut at matched contact and cost, plus the ancestry log on both sides |
| Avida / ecological-network work (`Environmental change makes robust ecological networks fragile`, *Nature Communications* 2016, doi:10.1038/ncomms12462) | Digital coevolutionary ecology has precedent | Same boundary as above: no novelty in "digital host–antagonist simulation"; possible novelty only in the cut |

## Conclusion for RQ-3's claim

The mechanism RQ-3 probes is not new: parasite adaptation to common hosts, rare advantage,
time-shift reconstruction, the non-identity of cycling with Red Queen dynamics, and digital
host–parasite simulation all have published precedent. What is not covered by those sources,
as far as this search found, is the operational cut: run the antagonist with real contact and
real energy cost, remove its heritable feedback in two independent ways (frozen composition,
and an update cut from the host labels), and measure whether the delayed frequency-to-pressure
link and the rare-class growth advantage survive.

That is a claim about *this model's mechanism boundary*, not about biology, and it is only
testable after the cut exists in code. The round-1 verdict is therefore
`BLOCKED_MEASUREMENT` with the unblocking patch attached, not a novelty claim.
