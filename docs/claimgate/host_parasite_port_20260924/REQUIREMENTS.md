# Requirements — host_parasite DomainProfile port

Status legend: **MUST** / **SHOULD** / **WON'T**. Every scientific MUST cites a
grounded source from `CITATIONS.md`.

## MUST

1. **MUST** keep the Genesis engine domain-agnostic; host–parasite work is a
   ClaimGate `DomainProfile` + thin adapter + docs, not infection logic inside
   `engine.py` (repo pattern: `domain.py` / biomedical adapter).
2. **MUST** register an opt-in profile (`host_parasite`) in `PROFILES` with
   fail-closed blocked claims, including at least:
   `vaccine_efficacy_proved`, `antiviral_therapy_validated`,
   `clinical_pathogen_model`, `epidemic_forecast_certified`,
   `phage_therapy_cleared`, `virulence_optimized_for_humans`,
   `biosafety_level_certified`.
3. **MUST NOT** modify BAIC pins:
   `docs/hard_experiment_01/results_v7.json`,
   `docs/claimgate/risk_bar.json`,
   `docs/claimgate/biomedical_study.json`.
4. **MUST** treat digital parasite CPU-theft / obligate infection as an
   *analogy* for claim labeling, grounded in Avida parasites that steal ~80%
   CPU cycles under a task-overlap infection rule (Fortuna, Zaman et al. 2021,
   doi:10.3389/fevo.2021.750772; Zaman et al. 2014,
   doi:10.1371/journal.pbio.1002023).
5. **MUST** acknowledge the parasitism–mutualism continuum and vertical vs
   horizontal transmission structure when naming future env hooks (Gupta,
   Vostinar et al. 2021, doi:10.3389/fevo.2021.739047; Symbulation —
   Zenodo 10.5281/zenodo.6380543).
6. **MUST** keep content-null / shuffle logic available as a methodological
   control for any later coevolution campaign (HE02 pattern; Floreano 2007
   doi:10.1016/j.cub.2007.01.058; Knoester 2008
   doi:10.1145/1389095.1389130) — not implemented as infection physics here.
7. **MUST** cite Price≠causality caution when interpreting coevolution
   correlations (Okasha & Otsuka 2020, doi:10.1098/rstb.2019.0365).
8. **MUST** allow COU/risk language reuse from FDA 2023 CM&S and ASME V&V
   40-2018 only as **declared labels** (same biomedical port stance) — never
   as clearance claims.

## SHOULD

1. **SHOULD** support later MVP metrics aligned with Avida parasite literature:
   task-overlap infection eligibility, single-parasite-per-host, horizontal
   injection (Fortuna et al. 2021, doi:10.3389/fevo.2021.750772).
2. **SHOULD** plan optional spatial-structure and vertical-transmission knobs
   for a v2 env (Symbulation / Vostinar spatial interaction; Zenodo
   10.5281/zenodo.6380543) without implying mutualism is “solved.”
3. **SHOULD** expose Expert-C innovations as *optional protocols* (causal twin
   falsification under interventions — Cornish et al., JMLR 27(152) 2026 /
   arXiv:2301.07210; multilevel fitness reorganization — Michod & Nedelcu 2003
   doi:10.1093/icb/43.1.64; Okasha multilevel Front EcoEvo 2022
   doi:10.3389/fevo.2022.793824).
4. **SHOULD** keep CRISPR–phage eco-evo models (Chabas/Westra PLOS Biol 2023
   doi:10.1371/journal.pbio.3002122; CRISPR types PLOS Comp Biol
   doi:10.1371/journal.pcbi.1010329; punctuated dynamics RS Interface 2024
   doi:10.1098/rsif.2024.0195) as **external comparator literature**, not as
   coded genetics in MVP.
5. **SHOULD** treat Scanlan/Buckling-line genome-wide coevolution constraint
   results (MBE 2015, doi via academic.oup.com/mbe/article/32/6/1425) as a
   target phenomenon for later digital experiments, not a claimed replication.

## WON'T (this PR / MVP scope)

1. **WON'T** implement full infection physics, phage adsorption kinetics, or
   CRISPR spacer dynamics in the engine.
2. **WON'T** claim vaccine efficacy, antiviral validation, phage therapy
   clearance, epidemic forecast certification, human virulence optimization,
   or BSL certification.
3. **WON'T** commit untracked `src/codontrace/genesis/population/` junk.
4. **WON'T** change BAIC manuscript text or HE01 empirical numbers.
5. **WON'T** merge host_parasite blocked claims into the biomedical profile
   (separate domains; separate fail-closed sets).
6. **WON'T** treat observational accuracy of a digital twin as counterfactual
   correctness (Cornish et al. arXiv:2301.07210 / JMLR 27(152) 2026).
7. **WON'T** add separate `DomainProfile`s for bacteria, archaea, or wet-lab
   cells; digital host–parasite roles are sufficient for this port.


## Wave 4 delivery (Phases 14–17)

- Phase 14: mode-completeness hardening (mixed blend digests; noise-transfer on declared menu; keep-mode registry).
- Phase 15: genome × VT × spatial × continuum factorial digests.
- Phase 16: virulence/resistance quality proxies; `virulence_optimized_for_humans` blocked.
- Phase 17: Price≠causality refusal assay; `major_transition_proved` blocked.
- See `MODE_AUDIT_WAVE4.md` and `DEPTH_BRAINSTORM_WAVE4.md`.

## Wave 5 delivery (Phases 18–22, optional 23)

- Phase 18: soft-complete journal ClaimGate attach-registry packet (hygiene).
- Phase 19: ARD→FSD transition + cost-of-generalism digests; `red_queen_proved` blocked.
- Phase 20: resource × coevolution-dynamics factorial (Lopez Pascua honesty).
- Phase 21: multi-seed contingency / repeatability under parasitism (S1).
- Phase 22: sequential Cornish multi-intervention deepening.
- Phase 23 (optional): Scanlan mutator / abiotic-constraint dual-null.
- See `DEPTH_BRAINSTORM_WAVE5.md`.
