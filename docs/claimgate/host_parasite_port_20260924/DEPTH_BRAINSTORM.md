# Design workshop — deepening the host–parasite ClaimGate port

Three reviewers (digital evolution; empirical phage–bacteria coevolution;
causal/V&V methodology) met to decide what must be built next so the port is
research-grade rather than a score toy. Citations are limited to the package
bibliography. Disagreement is recorded. Ends with a three-phase build plan.

## Shared diagnosis of the current baseline

What already exists is useful hygiene: a fail-closed `HOST_PARASITE` profile,
an optional env outside `engine.py` (task-overlap, one seat, horizontal inject,
steal fraction), dual-null and several digital falsification hooks, multilevel
and ARD/FSD *labels*, and review notes from six earlier critique rounds.

What is still missing for a serious contribution:

1. No multi-seed campaign with frozen digests (Zaman-style freeze/replay of
   parasite states is cited in the literature but not implemented here).
2. Vertical transmission and spatial structure are named but not first-class
   dynamics (Symbulation / Gupta–Vostinar continuum).
3. No abiotic × biotic factorial that can catch one-sided “parasites raise
   complexity” stories (Scanlan/Buckling constraint; Fortuna abiotic×biotic).
4. ARD/FSD are string labels, not diagnostics computed from infectivity /
   resistance range trajectories (Hall et al. 2011; Lopez Pascua et al. 2014).
5. Intervention falsification is single-shot score deltas, not a preregistered
   campaign pack that ClaimGate can refuse to promote past
   `runtime_observation` / `candidate_evidence` without multi-arm digests
   (Cornish et al., JMLR 27(152) 2026 / arXiv:2301.07210).
6. No interaction-network summary (Fortuna et al. 2017 Phil Trans B on
   host–parasite network complexity under adaptive vs non-adaptive origins).

Innovation target (locked): not “another Avida,” but an auditable
claim–evidence layer for digital host–parasite campaigns — dual nulls,
freeze/replay, abiotic controls, and intervention falsification wired so
overclaim fails closed.

---

## Round 1 — What would a journal reviewer reject?

**Digital evolution:** A mean retained-CPU score with four null kinds will be
read as a unit-test helper, not a result. Without multi-seed digests and a
freeze/replay arm (Zaman et al. 2014 doi:10.1371/journal.pbio.1002023), you
cannot even claim the digital analogue of “parasite history matters.”

**Empirical coevolution:** Labeling `ard_candidate` without computing range
escalation vs fluctuation will be called marketing. Hall et al. 2011
(doi:10.1111/j.1461-0248.2011.01624.x) and Lopez Pascua et al. 2014
(doi:10.1111/ele.12337) give concrete diagnostics: within- vs between-time
infectivity/resistance patterns and resource shifts. Also refuse CRISPR identity
claims forever; use wet papers only as external comparators
(doi:10.1371/journal.pbio.3002122).

**Causal/V&V:** Observational matching must not unlock interventional grades
(Cornish et al. arXiv:2301.07210). A menu that says `executed: false` while
`run_intervention_falsification` exists is fine only if ClaimGate bundle extras
cannot silently set `intervention_supported`. Price-style aggregates stay
non-causal (Okasha & Otsuka 2020 doi:10.1098/rstb.2019.0365).

**Agreed fix:** Build a campaign runner with digests; keep engine untouched;
raise evidence only through explicit ClaimGate paths that stay fail-closed.

---

## Round 2 — Where is the real novelty?

**Digital evolution:** Freeze/replay plus dual-null plus abiotic-only, all
emitting the same digest schema, is rare as a *library* feature even when Avida
configs exist in papers. Make that the product surface.

**Empirical:** Resource and mixing knobs that flip ARD-like vs FSD-like
*diagnostics* (not proved Red Queen) map Lopez Pascua / Brockhurst into the
digital port without stealing wet identity.

**Causal/V&V:** Preregistered intervention pack + refusal to promote claim
ceiling when only observational arms exist — that is CodonTrace’s differentiator
versus platforms that plot coevolution and stop.

**Disagreement preserved:** Digital evolution wants richer genomes/tasks soon;
empirical wants range diagnostics sooner; methodology wants ClaimGate wiring
sooner. Build order below privileges methodology + diagnostics + freeze/replay
before genome richness (genome richness without audit is how toys get published).

---

## Three-phase build plan (faakhir depth)

### Phase 4 — Auditable campaign runner (freeze/replay + multi-seed digests)

- Deterministic multi-seed campaign object outside `engine.py`.
- Arms: intact, content-null, structure-null, dual-null, abiotic-only,
  freeze/replay parasites (frozen parasite task/payload list reused across
  host updates — Zaman freeze/replay analogy).
- Canonical digests per arm and for the whole campaign.
- ClaimGate bundle factory that attaches campaign digests and refuses
  ceilings above `candidate_evidence` without passing falsification rules.
- Strip “toy” wording from public docstrings; replace with honest digital-scope
  language.
- `PHASE4_REVIEW.md`: two critique rounds, defects, fixes, tests.

### Phase 5 — Spatial structure, vertical transmission, ARD/FSD diagnostics

- Grid / neighborhood infectivity (local inject) as spatial structure knob
  (Symbulation / Brockhurst mixing contrast).
- Vertical transmission on host replication events (configurable probability);
  mixed mode must actually blend horizontal+vertical rather than advertise
  `not_implemented`.
- Time-series infectivity/resistance *range* summaries → ARD-like /
  FSD-like / mixed *diagnostic* enums with `red_queen_proved=False` always.
- Resource productivity knob affecting steal cost / eligibility pressure
  (Lopez Pascua 2014 analogy).
- `PHASE5_REVIEW.md`: two critique rounds.

### Phase 6 — Factorial evidence pack + network metrics + preregistration

- Abiotic × biotic factorial campaign template (Fortuna 2021 opportunity;
  Scanlan/Buckling constraint humility).
- Adaptive-origin gate flag (allow vs suppress “exaptation-like” task gains) as
  a declared control inspired by Fortuna et al. 2017
  (doi:10.1098/rstb.2016.0431) — digital only, no wet claim.
- Host–parasite interaction network summaries (edge count, strength
  heterogeneity) with digests.
- Preregistration record schema (QOI, COU, arms, success metrics, forbidden
  claims) required before campaign attach.
- Evidence docs under `docs/claimgate/host_parasite_port_20260924/evidence/`
  with DOIs; no BAIC pin edits; no clinical language.
- `PHASE6_REVIEW.md`: two critique rounds.

### Explicit non-goals (unchanged)

- Infection physics inside `engine.py`.
- CRISPR identity, phage therapy, vaccine, epidemic, BSL, human virulence
  optimization, proved intelligence, proved Red Queen, proved major transition.
- Committing `src/codontrace/genesis/population/` junk.
- Changing BAIC pinned JSON digests.

## Persian one-liner

هدف این عمق‌بخشی: پورت میزبان–انگل به‌عنوان لایهٔ حسابرسی ادعای قابل استناد،
نه یک نمرهٔ اسباب‌بازی و نه یک Avida دیگر.
