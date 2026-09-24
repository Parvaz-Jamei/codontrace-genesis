# Open challenges — host_parasite port

Scientific and engineering challenges for a CodonTrace Genesis host–parasite
DomainProfile. Citations are from the grounded list in `CITATIONS.md`. Where a
primary source is still needed beyond that list, the item is marked
**OPEN — needs primary source**.

## Scientific challenges

### S1. Contingency vs repeatable complexity under parasitism

Avida host–parasite coevolution can drive complex traits and evolvability, with
contingency-loci analogies (Zaman et al. 2014, doi:10.1371/journal.pbio.1002023).
Challenge: which Genesis observables (task repertoire, capsule utility, QD
archives) map cleanly enough to claim “complexity emergence” without overclaim?

### S2. Obligate CPU theft vs biological resource drawdown

Acosta & Zaman (2022, doi:10.3389/fevo.2021.750772) specify obligate
parasites stealing ~80% CPU, task-overlap infection, one parasite per host,
horizontal injection. Challenge: a thin ClaimGate port must not pretend those
parameters are already encoded; choosing defaults later is a model COU decision
(FDA 2023 CM&S / ASME V&V 40 risk commensurate evidence).

### S3. Parasitism–mutualism continuum

Symbiosis in digital evolution spans parasitism to mutualism; Symbulation
emphasizes transmission mode (Gupta, Vostinar et al. 2021
doi:10.3389/fevo.2021.739047; Zenodo 10.5281/zenodo.6380543). Challenge: naming
hooks without baking a “mutualism = success” fitness narrative.

### S4. Spatial structure and interaction locality

Vostinar research / Symbulation spatial structure changes interaction
opportunities. Challenge: Genesis currently has multiple spatial/population
layers in flux; a port must not smuggle a second population engine via
untracked `population/` junk.

### S5. Coevolution constrains abiotic adaptation

Scanlan et al. / Buckling-line MBE 2015 (doi via
academic.oup.com/mbe/article/32/6/1425): coevolution can constrain
abiotic-beneficial mutations. Challenge: designing a digital assay that can
*falsify* “parasites always help evolvability” (Zaman 2014 complexity results
are not a universal law).

### S6. CRISPR–phage eco-evo dynamics as external targets

Chabas/Westra PLOS Biol 2023 (doi:10.1371/journal.pbio.3002122); CRISPR type
models (doi:10.1371/journal.pcbi.1010329); punctuated CRISPR dynamics
(doi:10.1098/rsif.2024.0195). Challenge: these are rich empirical/model targets;
MVP must not fake spacer genetics.

### S7. Virulence, resistance quality, social infections

Gandon (doi:10.1098/rspb.2000.1100) qualitative vs quantitative resistance;
Alizon et al. social infections (doi:10.1098/rstb.2013.0365). Challenge:
blocked claim `virulence_optimized_for_humans` must stay blocked even if digital
“virulence” proxies exist.

### S8. Multilevel selection / major transitions

Okasha multilevel (Front EcoEvo 2022 doi:10.3389/fevo.2022.793824); Michod &
Nedelcu 2003 fitness reorganization (doi:10.1093/icb/43.1.64). Challenge:
host–parasite coupling can look like a transition; Price-equation summaries are
not causal (Okasha & Otsuka 2020 doi:10.1098/rstb.2019.0365).

### S9. Causal twin falsification

Cornish et al. (JMLR 27(152) 2026 / arXiv:2301.07210): observational accuracy ≠
counterfactual correctness; falsify digital twins under interventions.
Challenge: most digital HP platforms report match-to-history; few pre-register
intervention falsification suites.

## Engineering challenges

### E1. Profile vs engine boundary

Keep infection physics out of `engine.py`; optional later `HostParasiteEnv`
hooks only. Biomedical port is the template.

### E2. Fail-closed clinical language

Therapy / vaccine / epidemic / BSL strings must raise `ConfigurationError`
without requiring callers to remember a checklist.

### E3. Pin integrity

Any suite that uses HE01 as an *executed bundle analog* must not rewrite
`results_v7.json`, `risk_bar.json`, or `biomedical_study.json`.

### E4. Content-null controls

HE02 capsules_shuffled / content-null logic (Floreano 2007; Knoester 2008)
should remain available for coevolution campaigns so “interaction structure”
is not confounded with “payload content.”

### E5. Adapter thinness

Avoid growing `host_parasite.py` into a second biomedical study auditor in MVP;
worksheet/risk-bar ports can wait until a real digital HP campaign exists.

### E6. OPEN — needs primary source

Quantitative mapping from Genesis energy/CPU abstractions to Avida “~80% CPU
theft” under CodonTrace’s own energy model: **OPEN — needs primary source**
(engineering measurement study, not invent a DOI).
