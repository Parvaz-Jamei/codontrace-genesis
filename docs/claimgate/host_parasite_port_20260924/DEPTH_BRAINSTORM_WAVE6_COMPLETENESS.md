# Design workshop — Wave 6 completeness audit (five-round expert brainstorm)

**Context:** Wave 6 (Phases 24–26) is squash-merged on `main` at
`fa01873f8e565c66e8901282b3f8128d93fe925e` (PR #48). Waves 1–5 (Phases 1–23)
precede it. This workshop audits whether the Wave-6 host–parasite ClaimGate
slice is **soft-complete** for journal-facing correctness — no leftover
blocking defects — without reopening hard locks or expanding into refused
scopes.

**Project name:** CodonTrace Genesis.

**Innovation bar for this audit:** find concrete defects, refuse vague “improve
later,” ship only small in-scope hardenings, and seed Wave 7 only if earned.

**Roles (same cast)**

- **A — Digital evolution / ALife** (Avida, MODES, Channon OEE honesty, Goldsby
  MLS awareness; freeze≠replay≠reciprocal; entropy×contingency join)
- **B — Microbial / phage–bacteria / cell genome honesty** (wet→digital maps;
  COU labels; Acosta & Zaman opportunity/necessity; Adami physical complexity)
- **C — ClaimGate / V&V / causal methodology** (dual-null, prereg, Cornish,
  ceilings, blocked claims; ladder non-rise on multi-attach)

**Hard locks (not reopened):** one `host_parasite` DomainProfile; cell =
SemanticGenome substrate; microbe/virus = COU labels only; no infection logic in
`engine.py`; BAIC pins byte-identical; never commit
`src/codontrace/genesis/population/`; committed docs = ordinary human research
prose; blocked claims stay blocked; no invented DOIs.

**Score axes (every proposal):** feasibility, quality, usefulness, testable
innovation (1–5 each).

---

## Round 1 — Inventory & defect hunt

### Delivered surface (Phases 24–26)

| Phase | Module / attach | Dual-null / refuse | Tests |
|---|---|---|---|
| 24 | `host_parasite_wave6_smoke` / `attach_wave6_journal_smoke` | Ordered attach Phases 18–23; ladder_before==ladder_after; blocked spot-check (Red Queen, phage therapy, CRISPR, clinical); honesty flags False | phase24 |
| 25 | `host_parasite_he_hp_refresh` / `attach_he_hp_locked_digest_refresh` | Replay four HE_HP locks; BAIC pin SHA assert; `wave5_does_not_invalidate_he_hp=True` | phase25 |
| 26 | `host_parasite_entropy_contingency_bridge` / `attach_entropy_contingency_bridge` | Joint universal-rise falsified; `complexity_emergence_proved=False`; Red Queen block re-check | phase26 |

Docs inventoried: `DEPTH_BRAINSTORM_WAVE6.md`, `PHASE{24,25,26}_REVIEW.md`
(each with موج ۱ / موج ۲ — verified present), `WAVE6_ATTACH_KEYS` +
`assert_wave6_attach_surface_wired()`, adapters in
`claimgate/adapters/host_parasite.py`, evidence `he_hp_locked_digests.md`
Wave-6 refresh section, README Wave-6 rows.

### Expert A — digital evolution / ALife

1. Phase 24 is inventory hygiene, not new ALife dynamics — correct scope.
2. Phase 26 joins Phase 11 entropy dual-null with Phase 21 contingency. The
   outer seed is a **stratification key**; contingency companions use
   `S+1000` / `S+2000` because Phase 21 requires ≥3 seeds. Acceptable if
   documented; undocumented companion construction is an honesty gap.
3. MODES / Channon / Goldsby correctly absent as proved claims.
4. Synthetic bridge is not Zaman live coevolution; `complexity_emergence_proved`
   stays False — correct.

### Expert B — microbial / genome honesty

1. **Blocking honesty defect (inherited, exposed by literature pressure):**
   DOI `10.3389/fevo.2021.750772` was labeled “Fortuna MA, Zaman L, Ofria C,
   Wagner A (2021). Ecological Opportunity and the Rise of Complexity…” in
   `CITATIONS.md` and `evidence/fortuna_2021_ecological_opportunity.md`. The DOI
   resolves to **Acosta MM & Zaman L (2022)** *Ecological Opportunity and
   Necessity…*. Title/authors were wrong (never invent / mis-attribute papers).
2. **Blocking honesty defect:** `evidence/fortuna_2017_network_origin.md`
   titled the rstb.2016.0431 paper as “Coevolutionary dynamics shape the
   structure of bacteria–phage infection networks” — actual title is
   *Non-adaptive origins of evolutionary innovations increase network
   complexity…* (Fortuna, Zaman, Wagner, Bascompte).
3. **Gap:** Phase 26 shipped without a dedicated evidence note (Zaman/Adami
   comparators). Soft-complete for this slice wants a comparator note
   (Wave-5 Scanlan precedent).
4. Phase 24/25/26 payloads keep therapy / CRISPR / Red Queen / complexity
   flags False; COU labels only.

### Expert C — ClaimGate / V&V

1. All Wave-6 attaches are prereg-bound; ladders do not rise in unit tests;
   `WAVE6_ATTACH_KEYS` ↔ callables wiring assert exists and is tested (Phase 24).
2. **Blocking docs hygiene:** README still said Wave 6 “lands on
   `feat/host-parasite-wave6`” / “this PR” after squash-merge to `main` @
   `fa01873` — stale branch claim.
3. Phase 25 lacked a double-attach refuse test (Phase 24 has one; attach code
   already refuses).
4. COMPARATOR_MATRIX lacked a Wave-6 bridge row.
5. DomainProfile blocked set remains fail-closed. Phase-18 soft_complete still
   means Phases 1–17 baseline (Wave-6 keys additive).

### Round-1 consensus defect list

| ID | Severity | Defect |
|---|---|---|
| D1 | **Blocking (docs hygiene)** | README stale feat-branch / “this PR” claim after #48 merge |
| D2 | **Blocking (soft-complete hygiene)** | Missing Phase 26 Zaman/Adami evidence note + companion-seed honesty |
| D3 | **Blocking (honesty)** | Acosta & Zaman 2022 DOI mis-attributed as “Fortuna 2021” |
| D4 | **Blocking (honesty)** | Fortuna 2017 evidence note wrong title/authors for rstb.2016.0431 |
| D5 | Non-blocking docs | COMPARATOR_MATRIX Wave-6 bridge row; CHALLENGES/REQUIREMENTS living refs |
| D6 | Nice-to-have | Phase 25 double-attach test; adapter `__all__` re-exports (absent across waves) |
| D7 | Out of scope | Live Avida-scale infection; MLS engine; OEE proved; DomainProfile split |

**Forced disagreement:** A wanted richer live-env join before soft-complete;
B+C veto as refused infection-in-engine / Avida-identity theater. Lock:
soft-complete means **ClaimGate-auditable Wave-6 protocol slice**, not Avida
replacement.

---

## Round 2 — Literature pressure

Searches this session (WebSearch; DOI resolution). No invented DOIs.

| Source | Verified ID | Pressure on Wave 6 |
|---|---|---|
| Zaman et al. 2014 | doi:10.1371/journal.pbio.1002023 | Contingency / freeze–replay humility — Phase 26 must keep `complexity_emergence_proved=False` |
| Adami, Ofria, Collier 2000 | doi:10.1073/pnas.97.9.4463 | Physical complexity = environment-relative information — Phase 11/26 entropy is a dual-null assay, not Adami identity |
| Acosta & Zaman 2022 | doi:10.3389/fevo.2021.750772 | Correct paper behind the DOI previously mis-labeled Fortuna 2021 — **must fix bibliography** |
| Fortuna et al. 2017 | doi:10.1098/rstb.2016.0431 | Correct title *Non-adaptive origins…* — evidence note must match |
| Cornish et al. | JMLR 27(152) 2026; arXiv:2301.07210 | Observational match ≠ intervention — Wave 6 does not reopen Phase 22 |
| Gupta & Vostinar Symbulation | doi:10.3389/fevo.2021.739047 | Continuum comparator only |
| Dolson MODES | doi:10.1162/artl_a_00280 | Comparator only — `modes_passed_proved` refused |
| Channon Tokyo Type-1 | doi:10.1162/artl_a_00430 | Comparator only — `oee_type1_proved` refused |
| Goldsby et al. 2014 | doi:10.1371/journal.pone.0102713 | Deme MLS comparator — no MLS engine |
| JaxLife (Lu et al.) | arXiv:2409.00853 | **No** HP ClaimGate surface — port refused |

**Quality / usefulness / testable-innovation push**

- **A:** Wave 6’s testable innovation is integration smoke + lock refresh +
  entropy×contingency join — not richer infection physics. Push usefulness by
  documenting companion-seed construction so reviewers cannot misread Phase 26
  as single-seed identity.
- **B:** Wet/digital literature’s distinctive claims are mapped; leftover
  defects are honesty packaging (D1–D4), not missing biology phases.
- **C:** Push README post-merge honesty and evidence notes. Soft-complete
  usefulness is an attach surface a reviewer can inventory.

**Kill list (still killed under literature pressure):** separate DomainProfiles;
infection in `engine.py`; BAIC pin edits; wet HGT/CRISPR/therapy/BSL/clinical;
`red_queen_proved` / `major_transition_proved` / OEE-MODES passed; Goldsby MLS
engine; Avida identity export; JaxLife HP port; co-infection multi-seat;
invented DOIs.

---

## Round 3 — Fix-or-refuse

| ID | Decision | Plan |
|---|---|---|
| D1 | **FIX** | README: Phases 24–26 on `main` @ `fa01873`; drop feat-branch / “this PR” |
| D2 | **FIX** | Add `evidence/phase26_entropy_contingency_bridge.md`; document companion seeds in Phase 26 module docstring |
| D3 | **FIX** | Correct CITATIONS + evidence note to Acosta & Zaman 2022; update CHALLENGES/REQUIREMENTS living refs |
| D4 | **FIX** | Correct Fortuna 2017 evidence title/authors for rstb.2016.0431 |
| D5 | **FIX** | COMPARATOR_MATRIX Wave-6 bridge row + opportunity/necessity row |
| D6 | **FIX** (test) / **REFUSE** (`__all__`) | Add Phase 25 double-attach test; refuse adapter `__all__` re-export churn (absent for Wave 5 too — not Wave-6 unique) |
| D7 | **REFUSE** | All hard-lock / Wave-6 refuse-list items |

No vague “improve later.” Fixes are file-level and in-scope for a completeness
hardening on the audit branch (not a new numbered phase requiring separate موج ۱
/ موج ۲ reviews beyond this workshop’s documentation). Historical brainstorm
docs that still say “Fortuna 2021” are left as session records; canonical
`CITATIONS.md` + `evidence/` are authoritative.

---

## Round 4 — Completeness gate

**Question:** Would a journal reviewer / ClaimGate auditor accept Wave 6 as
**soft-complete** for this host–parasite port slice?

### Verdict after Round-3 fixes: **YES, soft-complete with conditions**

**Conditions (must hold on the audit tip):**

1. D1–D5 landed (README, Phase 26 evidence + companion-seed note, Acosta/Zaman
   + Fortuna 2017 honesty, COMPARATOR row).
2. Phase 25 double-attach test green (D6 partial).
3. `pytest` host_parasite + claimgate host_parasite green (~189+).
4. BAIC pins byte-identical:
   - `results_v7.json` SHA256 `35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6`
   - `risk_bar.json` SHA256 `4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7`
   - `biomedical_study.json` SHA256 `9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce`
5. `engine.py` absent / empty diff vs `origin/main`.
6. No `population/` junk; Phase-18 `soft_complete` still means Phases 1–17;
   Wave-6 surface verified via `assert_wave6_attach_surface_wired()`.

### Must-fix (blocking) vs nice-to-have vs out-of-scope

| Bucket | Items |
|---|---|
| **Must-fix (this audit)** | D1–D5 (+ Phase 25 double-attach test) |
| **Nice-to-have** | Adapter `__all__` re-exports; richer live-env coupling |
| **Out of scope (explicit refuse)** | Infection in `engine.py`; separate DomainProfiles; BAIC pin edits; Goldsby MLS engine; Avida identity export; JaxLife HP port; co-infection multi-seat; wet HGT / CRISPR / phage therapy / BSL / clinical; proved Red Queen / OEE-MODES passed / major transition |

**Soft-complete definition used here:** every Wave-6 phase has (a) dual-null or
honesty refuse, (b) prereg-bound attach, (c) blocked-claim re-check where
relevant, (d) review prose with two critique waves (موج ۱+۲ verified), (e)
comparator DOI honesty, (f) pins/engine locks intact. It does **not** mean wet
replication, Avida replacement, or proved dynamics.

---

## Round 5 — Sign-off + next-wave seeds (only if earned)

### Expert scores (post-fix Wave-6 slice)

| Expert | Feas. | Qual. | Use. | Test. innov. | Notes |
|---|---|---|---|---|---|
| A | 5 | 4 | 5 | 4 | Bridge is thin join; quality capped vs live Avida; ClaimGate usefulness high |
| B | 5 | 5 | 5 | 4 | DOI/title honesty restored; companion-seed documented; COU maps intact |
| C | 5 | 5 | 5 | 5 | Wiring assert + smoke + lock refresh + prereg/blocked matrix = journal V&V |

**Product (min expert product of axes):** A=400, B=500, C=625 → panel accepts
soft-complete.

### Blocking fixes priority (executed on this branch)

1. **P0** D1 README post-merge honesty
2. **P0** D3/D4 citation/evidence title corrections
3. **P0** D2 Phase 26 evidence + companion-seed docstring
4. **P1** D5 COMPARATOR row; Phase 25 double-attach test

### Wave 7 seeds (earned only — survived all five rounds)

Wave 6 itself was the earned soft-complete hygiene + thin bridge from Wave 5.
After this audit, **no new numbered Wave-7 biology phase is earned**. Optional
hygiene-only seeds that survived without touching refuse locks:

| Seed ID | Candidate | Why earned / deferred | Dual-null / refuse sketch |
|---|---|---|---|
| W7-a | **Deferred** — living-doc sweep of historical brainstorm files still saying “Fortuna 2021” | Would rewrite session history; canonical CITATIONS/evidence already corrected | Docs-only; no new claims |
| W7-b | **Not earned** — deeper live multi-update coevolution join | A wanted it; B+C veto as engine creep / Avida-identity theater | Refuse infection-in-engine |

**Killed for Wave 7 (not earned):** MLS engine; OEE/MODES measurement claiming
passed; infection in engine; DomainProfile split; Avida export identity;
JaxLife HP; co-infection seats; wet CRISPR/HGT/therapy; pin edits; new
numbered biology phase without a concrete ClaimGate gap.

### Sign-off

- **A/B/C:** Wave 6 host–parasite ClaimGate port slice is **soft-complete** on
  `main` @ `fa01873` **after** P0/P1 hardenings on this audit branch.
- Remaining work is optional living-doc history sweep (W7-a deferred) or
  unrelated Genesis tracks — **no earned Wave-7 biology phase**.
- Hard locks remain closed.

## Persian one-liner

موج ۶ پس از ادغام #48 در main نرم‌کامل است؛ نقص‌های مسدودکنندهٔ README کهنه،
نسبت‌دهی اشتباه DOI Acosta & Zaman، عنوان اشتباه Fortuna 2017، و نبود یادداشت
شواهد فاز ۲۶ در همین حسابرسی اصلاح شدند — بدون باز کردن قفل‌های ردشده و بدون
بذر بیولوژی موج ۷.

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
