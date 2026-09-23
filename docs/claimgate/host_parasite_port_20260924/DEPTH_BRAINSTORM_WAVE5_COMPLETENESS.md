# Design workshop — Wave 5 completeness audit (five-round expert brainstorm)

**Context:** Waves 1–5 (Phases 1–23) are squash-merged on `main` at
`f093ed826876b916a140c39e9bba1ef7baeff257` (PR #46 Wave 5 on #45 docs, #44
Wave 4, #43 Wave 3). This workshop audits whether the host–parasite ClaimGate
port slice is **soft-complete** for journal-facing correctness — no leftover
blocking defects — without reopening hard locks or expanding into refused
scopes.

**Project name:** CodonTrace Genesis.

**Innovation bar for this audit:** find concrete defects, refuse vague “improve
later,” ship only small in-scope hardenings, and seed Wave 6 only if earned.

**Roles (same cast)**

- **A — Digital evolution / ALife** (Avida, MODES, Channon OEE honesty, Goldsby
  MLS awareness; freeze≠replay≠reciprocal; mode digests)
- **B — Microbial / phage–bacteria / cell genome honesty** (wet→digital maps;
  COU labels; Scanlan/Buckling; Hall ARD/FSD; Lopez Pascua resource×FSD)
- **C — ClaimGate / V&V / causal methodology** (dual-null, prereg, Cornish,
  ceilings, blocked claims; Price≠causality)

**Hard locks (not reopened):** one `host_parasite` DomainProfile; cell =
SemanticGenome substrate; microbe/virus = COU labels only; no infection logic in
`engine.py`; BAIC pins byte-identical; never commit
`src/codontrace/genesis/population/`; committed docs = ordinary human research
prose; blocked claims stay blocked; no invented DOIs.

**Score axes (every proposal):** feasibility, quality, usefulness, testable
innovation (1–5 each).

---

## Round 1 — Inventory & defect hunt

### Delivered surface (Phases 18–23)

| Phase | Module / attach | Dual-null / refuse | Tests |
|---|---|---|---|
| 18 | `host_parasite_attach_registry` / `attach_journal_attach_registry` | soft_complete for Phases 1–17; ladder False; Red Queen block re-check | phase18 |
| 19 | `host_parasite_ard_fsd_transition` / `attach_ard_fsd_transition` | structure-null + abiotic; `red_queen_proved=False`; wet identity False | phase19 |
| 20 | `host_parasite_resource_dynamics` / `attach_resource_dynamics_factorial` | biotic-absent cells; outside-engine productivity; wet virulence False | phase20 |
| 21 | `host_parasite_contingency` / `attach_multi_seed_contingency` | parasite-absent dual-null; `complexity_emergence_proved=False` | phase21 |
| 22 | `host_parasite_cornish_sequential` / `attach_sequential_cornish_campaign` | obs-first schedule; `intervention_supported=False`; clinical False | phase22 |
| 23 | `host_parasite_mutator` / `attach_scanlan_mutator_campaign` | content-null + abiotic elevated; gene/CRISPR identity False | phase23 |

Docs inventoried: `DEPTH_BRAINSTORM_WAVE5.md` (+ FA), `PHASE{18–23}_REVIEW.md`
(each with موج ۱ / موج ۲), `COMPARATOR_MATRIX.md`, `REQUIREMENTS.md`, README
Wave-5 rows, claim ladder / blocked-claim matrix in Phase 18 packet, attach
adapters in `claimgate/adapters/host_parasite.py`, evidence notes under
`evidence/`.

### Expert A — digital evolution / ALife

1. **Synthetic range trajectories** in Phases 19–20 are schedule-bound digital
   assays, not live Avida-scale coevolution. Acceptable for ClaimGate digests
   if honesty flags stay False — but reviewers must not misread them as Zaman
   complexity laws.
2. Phase 21 contingency correctly refuses “parasites always raise complexity
   across seeds”; freeze/replay (Phase 7/10) remains schedule control, not
   repeatability law. **No leftover ALife overclaim found** in Wave-5 code.
3. MODES / Channon / Goldsby correctly absent as proved claims.

### Expert B — microbial / genome honesty

1. **Blocking honesty defect:** `evidence/hall_lopez_pascua_ard_fsd.md` titled
   Lopez Pascua 2014 as “Resource availability and the evolution of virulence”
   while CITATIONS.md and the real paper title are “Higher resources decrease
   fluctuating selection during host–parasite coevolution”
   (doi:10.1111/ele.12337). Hall title was truncated. **Must fix.**
2. **Gap:** Phase 23 Scanlan dual-null shipped without a dedicated evidence note
   (Zaman/Fortuna/Hall notes exist; Scanlan DOI only in CITATIONS). Journal
   soft-complete for this slice wants a comparator note.
3. Phase 19 cost-of-generalism proxy and Phase 20 Lopez Pascua honesty map
   behave as designed (early ARD-like → late FSD-like; high resource + present
   → ARD-like, not increased FSD). COU labels only; no wet CRISPR/BSL language
   in payloads.

### Expert C — ClaimGate / V&V

1. All Wave-5 attaches are prereg-bound; representative blocked claims
   re-checked; ladders do not rise in unit tests.
2. **Gap:** `WAVE5_ATTACH_KEYS` listed Phase 18–23 keys but nothing fail-closed
   if an attach callable drifted off the adapter. Soft-complete hygiene for
   Wave 5 needs a wiring assert (without rewriting Phase-18’s Phases 1–17
   baseline contract).
3. `COMPARATOR_MATRIX` ARD/FSD row lacked inline Hall/Lopez DOIs (present later
   in Wave-5 rows); blank-line formatting noise.
4. DomainProfile blocked set remains fail-closed for therapy / Red Queen /
   major transition / CRISPR / Avida replacement. Campaign-only flags
   (`gene_identity_proved`, `oee_type1_proved`, `modes_passed_proved`) stay in
   the Phase-18 matrix — correct split.

### Round-1 consensus defect list

| ID | Severity | Defect |
|---|---|---|
| D1 | **Blocking (honesty)** | Lopez Pascua / Hall evidence-note title errors |
| D2 | **Blocking (soft-complete hygiene)** | Missing Scanlan 2015 evidence note for Phase 23 |
| D3 | **Blocking (V&V wiring)** | No fail-closed Wave-5 attach-key → callable assert |
| D4 | Non-blocking docs | COMPARATOR_MATRIX Hall/Lopez DOI inline + blank line |
| D5 | Nice-to-have | Phase 19/20 are synthetic assays (honesty already flagged) |
| D6 | Out of scope | Live Avida-scale infection physics; MLS engine; OEE proved |

**Forced disagreement:** A wanted deeper live-env coupling before calling soft-
complete; B+C veto as scope expansion into refused infection-in-engine /
Avida-identity theater. Lock: soft-complete means **ClaimGate-auditable
protocol slice**, not Avida replacement.

---

## Round 2 — Literature pressure

Searches this session (WebSearch; Crossref/DOI resolution). No invented DOIs.

| Source | Verified ID | Pressure on Wave 5 |
|---|---|---|
| Hall et al. 2011 | doi:10.1111/j.1461-0248.2011.01624.x | ARD gives way to FSD via costs of generalism — Phase 19 transition protocol is the right ClaimGate shape; evidence note must carry the full title |
| Lopez Pascua et al. 2014 | doi:10.1111/ele.12337 | Higher resources decrease FSD (shift toward ARD) — Phase 20 hypothesis `higher_resources_always_increase_fsd_like_labels` correctly fails; mis-titled evidence note was unacceptable |
| Koskella & Brockhurst 2014 | doi:10.1111/1574-6976.12072 | Costs of generalism synthesis — Phase 19 proxy is a digital label, not wet proof (correct refuse) |
| Scanlan et al. 2015 | doi:10.1093/molbev/msv032 | Coevolution constrains abiotic-beneficial acquisition; mutators appear — Phase 23 dual-null matches the honesty map; needs evidence note |
| Zaman et al. 2014 | doi:10.1371/journal.pbio.1002023 | Complexity under coevolution is contingent — Phase 21 S1 contingency is the humility packet; do not reopen as law |
| Fortuna et al. 2021 | doi:10.3389/fevo.2021.750772 | One-parasite-per-host / CPU theft — already Wave 1–2; co-infection multi-seat stays refused |
| Cornish et al. | JMLR 27(152) 2026; arXiv:2301.07210 | Observational match ≠ intervention support — Phase 22 sequential schedule is the V&V differentiator vs history-matching papers |
| Dolson MODES | doi:10.1162/artl_a_00280 | Comparator only — claiming `modes_passed_proved` would be theater |
| Channon Tokyo Type-1 | doi:10.1162/artl_a_00430 | Comparator only — `oee_type1_proved` stays refused |
| Goldsby et al. 2014 | doi:10.1371/journal.pone.0102713 | Deme MLS comparator — no MLS engine in Wave 5/6 without separate earn-in |
| JaxLife (Lu et al.) | arXiv:2409.00853 | Open-ended agentic sim; **no** HP ClaimGate surface — port refused |
| Avida HP configs | Dryad / Fortuna lineage | Comparison ≠ identity export |

**Quality / usefulness / testable-innovation push**

- **A:** Wave 5’s testable innovation is protocol digests (transition, resource
  factorial, contingency, sequential Cornish, mutator dual-null) — not richer
  infection physics. Push usefulness by making evidence notes title-accurate so
  reviewers can verify DOIs in one hop.
- **B:** Wet literature’s distinctive claims are already mapped; leftover
  defects are honesty packaging (D1–D2), not missing biology phases.
- **C:** Push fail-closed wiring (D3). Usefulness of soft-complete is an
  attach surface a reviewer can inventory without reading 2k-line adapter
  source.

**Kill list (still killed under literature pressure):** separate DomainProfiles;
infection in `engine.py`; BAIC pin edits; wet HGT/CRISPR/therapy/BSL/clinical;
`red_queen_proved` / `major_transition_proved` / OEE-MODES passed; Goldsby MLS
engine; Avida identity export; JaxLife HP port; co-infection multi-seat;
invented DOIs.

---

## Round 3 — Fix-or-refuse

| ID | Decision | Plan |
|---|---|---|
| D1 | **FIX** | Correct Hall + Lopez Pascua titles/pages in `evidence/hall_lopez_pascua_ard_fsd.md`; point to Phases 19–20 digital use |
| D2 | **FIX** | Add `evidence/scanlan_2015_mutator_abiotic.md` + README row (Phase 23 comparator) |
| D3 | **FIX** | Add `WAVE5_ATTACH_CALLABLES` + `assert_wave5_attach_surface_wired()` in `host_parasite_attach_registry.py`; test in `tests/test_host_parasite_phase18.py` |
| D4 | **FIX** | Inline Hall/Lopez DOIs on COMPARATOR_MATRIX ARD/FSD row; drop blank-line noise |
| D5 | **REFUSE** | Live multi-update Avida-scale coevolution inside Phase 19/20 — would reopen infection-physics / engine creep; honesty flags already refuse wet identity |
| D6 | **REFUSE** | All hard-lock / Wave-5 refuse-list items (DomainProfiles, MLS engine, OEE proved, therapy, etc.) |

No vague “improve later.” Fixes are file-level and in-scope for a completeness
hardening on the audit branch (not a new numbered phase requiring separate موج ۱
/ موج ۲ reviews beyond this workshop’s documentation).

---

## Round 4 — Completeness gate

**Question:** Would a journal reviewer / ClaimGate auditor accept Wave 5 as
**soft-complete** for this host–parasite port slice?

### Verdict after Round-3 fixes: **YES, soft-complete with conditions**

**Conditions (must hold on the audit tip):**

1. D1–D4 landed (evidence titles, Scanlan note, Wave-5 wiring assert, matrix DOI).
2. `pytest` host_parasite + claimgate host_parasite green.
3. BAIC pins byte-identical:
   - `results_v7.json` SHA256 `35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6`
   - `risk_bar.json` SHA256 `4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7`
   - `biomedical_study.json` SHA256 `9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce`
4. `engine.py` empty diff vs `origin/main`.
5. No `population/` junk committed; Phase-18 `soft_complete` still means
   Phases 1–17 inventory baseline (Wave-5 surface verified separately via
   wiring assert — does not silently rewrite the Phase-18 contract).

### Must-fix (blocking) vs nice-to-have vs out-of-scope

| Bucket | Items |
|---|---|
| **Must-fix (this audit)** | D1–D4 |
| **Nice-to-have** | Richer live-env coupling for range series; adapters `__init__` re-exports of Wave-5 attaches; extra Phase-20 refuse-edge tests |
| **Out of scope (explicit refuse)** | Infection in `engine.py`; separate DomainProfiles; BAIC pin edits; Goldsby MLS engine; Avida identity export; JaxLife HP port; co-infection multi-seat; wet HGT / CRISPR / phage therapy / BSL / clinical; proved Red Queen / OEE-MODES passed / major transition |

**Soft-complete definition used here:** every Wave-5 phase has (a) dual-null or
Cornish refusal, (b) prereg-bound attach, (c) blocked-claim re-check where
relevant, (d) review prose with two critique waves, (e) comparator DOI honesty,
(f) pins/engine locks intact. It does **not** mean wet replication, Avida
replacement, or proved dynamics.

---

## Round 5 — Sign-off + next-wave seeds (only if earned)

### Expert scores (post-fix Wave-5 slice)

| Expert | Feas. | Qual. | Use. | Test. innov. | Notes |
|---|---|---|---|---|---|
| A | 5 | 4 | 5 | 4 | Synthetic assays limit quality vs live Avida; ClaimGate usefulness high |
| B | 5 | 5 | 5 | 4 | Evidence honesty restored; COU maps match Hall/Lopez/Scanlan |
| C | 5 | 5 | 5 | 5 | Wiring assert + prereg/blocked matrix = journal-facing V&V |

**Product (min expert product of axes):** A=400, B=500, C=625 → panel accepts
soft-complete.

### Blocking fixes priority (executed on this branch)

1. **P0** D1 evidence titles
2. **P0** D2 Scanlan evidence note
3. **P0** D3 Wave-5 attach wiring assert + test
4. **P1** D4 COMPARATOR_MATRIX DOI/format

### Wave 6 seeds (earned only — survived all five rounds)

Only seeds that add ClaimGate-auditable protocols **not** already covered by
Phases 1–23, without touching refuse locks:

| Seed ID | Candidate | Why earned | Dual-null / refuse sketch |
|---|---|---|---|
| W6-a | **Journal packet integration smoke** — one prereg-bound bundle attaching Phases 18–23 digests in order; ladder audit; blocked matrix spot-check | C: soft-complete is per-phase today; a single reviewer smoke pack is hygiene, not taxonomy | Refuse ladder rise; refuse therapy claims |
| W6-b | **HE_HP locked-digest refresh note** — document which HE_HP digests remain valid after Wave 5 without editing BAIC pins | C+A: reproducibility hygiene for stacked main | Pins byte-identical forever |
| W6-c | **Optional: repertoire×genome contingency bridge** — seed-stratified digest that *pairs* Phase 11 entropy dual-null with Phase 21 contingency without new biology claims | A+B: closes a thin join between genome and S1 humility | `complexity_emergence_proved=False`; no Red Queen |

**Killed for Wave 6 (not earned):** MLS engine; OEE/MODES measurement claiming
passed; infection in engine; DomainProfile split; Avida export identity;
JaxLife HP; co-infection seats; wet CRISPR/HGT/therapy; pin edits.

### Sign-off

- **A/B/C:** Wave 5 host–parasite ClaimGate port slice is **soft-complete** on
  `main` @ `f093ed8` **after** P0/P1 hardenings on this audit branch.
- Remaining work is Wave-6 seeds above (optional) or unrelated Genesis tracks.
- Hard locks remain closed.

## Persian one-liner

موج ۵ پس از ادغام در main نرم‌کامل است؛ نقص‌های مسدودکنندهٔ عنوان شواهد
Lopez Pascua/Hall، نبود یادداشت Scanlan، و نبود assert سیم‌کشی attach موج ۵
در همین حسابرسی اصلاح شدند — بدون باز کردن قفل‌های ردشده.

---

## Explicit refuse list (unchanged)

- Taxonomy DomainProfiles (bacteria/cell/archaea)
- Infection physics in `engine.py`
- BAIC / HE01 pin edits; `population/` junk
- Phage therapy, BSL, clinical, vaccine, epidemic, CRISPR identity/therapy
- `red_queen_proved`, `major_transition_proved`, `gene_identity_proved`,
  `virulence_optimized_for_humans`, OEE/MODES “passed” claims
- Goldsby MLS engine code; Avida identity export; JaxLife HP port
- Co-infection multi-seat engine creep
- Invented DOIs; authorship machine-meta in committed docs
