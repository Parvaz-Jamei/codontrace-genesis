# De-toy phase plan (D0–D7) — host_parasite port

**Project:** CodonTrace Genesis  
**Companion:** `DETOY_BRAINSTORM_5ROUND_20260924.md`  
**Local time:** 2026-09-24 ~04:53 IRST (UTC+3:30)  
**Wave name:** De-toy Wave (may earn Wave 7 code phases later)

Hard locks apply to every phase: ONE `host_parasite` DomainProfile; cell =
SemanticGenome substrate; microbe = COU labels; infection on port not
`engine.py`; no `population/`; BAIC pins untouched; no invented DOIs; ClaimGate
refuse list not loosened.

---

## Phase overview

| Phase | Rank | Title | Depends on | Code touch (future) | Docs-only OK? |
|---|---|---|---|---|---|
| **D0** | 1 | CiteGate SF4 DOI + SciAdv comparator split | — | `host_parasite_sim_fidelity_campaigns.py`, SIM_FIDELITY md/json | Prefer with D1 |
| **D1** | 2 | Type-II FR + diagonal \(A\) + graded \(\alpha\) IBM (thin) | D0 | New helper under genesis HP; SF4′ panel | No — needs code |
| **D2** | 3 | Mortality \(d\) × carrying capacity \(K\) region map | D1 | Sweep campaign + digests | No |
| **D3** | 4 | Steal × metabolic-error coupling (dual-null) | D1; D4 stub OK | `host_parasite_env` + phenotype hook | No |
| **D4** | 5 | Abstract metabolic phenotype from SemanticGenome | D1 recommended | Port-local G→P decode (Aevol-inspired) | Design stub OK |
| **D5** | 6 | Cost-of-generalism via phenotype penalty | D4 | Ties to SF1 coexistence | No |
| **D6** | 7 | Type-III / phase-locked rare panel (SciAdv) | D1 | Separate SF9-candidate | No |
| **D7** | 8 | Measurement-honesty + resource→target harshness | D4 for resource channel | DX-style pack | Partial docs |

---

## D0 — CiteGate / bibliography honesty

**Mechanism:** Retarget SF4 primary DOI to Rabajante et al. 2015 *Scientific
Reports* `10.1038/srep10004` (PMC4405699). Remove or demote
`10.1186/s12898-015-0055-7` (does not resolve to Rabajante RQ). Cite SciAdv
`10.1126/sciadv.1501548` as related comparator only.

**Lit hook:** Sci Rep multi-host RQ; SciAdv type-III rare-lock.

**Success metric:** Tests assert DOI string; results MD matches; SF4 remains
FAIL until D1 re-run.

**Refuse:** inventing DOIs; soft-passing FAIL.

**Honest FAIL risk:** N/A (docs).

---

## D1 — First build slice (recommended)

**Mechanism (port-local stepper):**

- \(n \ge 5\) host types and specialist parasites.
- Type-II functional response.
- Diagonally dominant specificity matrix \(A\) (generator invariant + unit test).
- No super-host / super-parasite (acceptance test).
- Default intermediate parasite mortality and adequate host \(K\).
- Graded \(\alpha_{ij}\) from digital overlap / specialist bias (extends boolean
  `infection_eligible` at campaign layer; seat API stays).
- Wire through HP campaign helpers / env — **not** `engine.py`.

**Lit hook:** doi:10.1038/srep10004; overlap analogy Acosta & Zaman
doi:10.3389/fevo.2021.750772.

**Success metric (prereg):** ≥3/5 seeds `cycling_detected` (unique dominants ≥3,
returns ≥2) under declared capable defaults → SUCCESS; 1–2 → PARTIAL; 0 → FAIL.
Always `red_queen_proved=False`.

**Refuse:** `red_queen_proved`, `phage_therapy_cleared`, `clinical_pathogen_model`.

**Honest FAIL risk:** **Medium–high** (RQ region contracts with type count;
defaults may miss). FAIL under capable dynamics is still scientific progress vs
structural impossibility.

**Acceptance tests (sketch):**

1. Generator rejects non-diagonally-dominant \(A\).
2. Super-* configurations refused or flagged non-RQ-capable.
3. ClaimGate spot-check: SUCCESS cannot set `red_queen_proved`.
4. Engine modules still contain zero infection tokens (SF8 regression).
5. Pack digest stable across processes (no `hash()`).

---

## D2 — Mortality × \(K\) region map

**Mechanism:** Sweep \(d\) and \(K\); publish digest of where cycling occurs.

**Lit hook:** Sci Rep parameter-region contraction.

**Success metric:** Nonempty capable region at mid-\(d\) / high-\(K\); empty at
extremes (pre-registered pattern) **or** documented mismatch.

**Refuse:** clinical prediction from region maps.

**Honest FAIL risk:** Medium.

---

## D3 — Steal × phenotype coupling

**Mechanism:** Infected seat increases host metabolic error / reduces replication
credit; content-null kills delta; structure-null kills infection path.

**Lit hook:** Zaman CPU steal; Avida ~0.8 steal fraction analogy.

**Success metric:** Dual-null separation magnitude > prereg threshold.

**Refuse:** `phage_therapy_cleared`.

**Honest FAIL risk:** Low–medium.

---

## D4 — Abstract metabolic phenotype (Aevol-inspired)

**Mechanism:** SemanticGenome → abstract trait contributions → phenotype vs
target → metabolic error. Inspiration from aevol.fr G→P; **not** Aevol identity.

**Lit hook:** Aevol model description (public docs).

**Success metric:** Replay-stable phenotype digests; genome edit changes error;
no wet-metabolism claim strings in ALLOWED set.

**Refuse:** clinical bacteria; Aevol replacement; flux-balance identity.

**Honest FAIL risk:** Medium (design).

---

## D5 — Cost of generalism on phenotype

**Mechanism:** Generalist repertoires pay metabolic-error penalty; specialists
less; coexistence assay links to SF1.

**Lit hook:** doi:10.1098/rspb.2012.0769; doi:10.1098/rspb.2014.2297.

**Success metric:** Cost arm coexistence vs no-cost collapse (digital proxies).

**Refuse:** wet ARD/FSD identity proved.

**Honest FAIL risk:** Low if SF1 remains green.

---

## D6 — Type-III / phase-locked rares (separate panel)

**Mechanism:** Type-III FR regime; detect binary dominant oscillations +
subordinate rare lock; optional noise switching later.

**Lit hook:** doi:10.1126/sciadv.1501548.

**Success metric:** Separate from SF4′; never used to mark SF4 SUCCESS.

**Refuse:** “full multi-type RQ proved via binary oscillations.”

**Honest FAIL risk:** High (distinct regime).

---

## D7 — Measurement honesty + resource→target

**Mechanism:** Channon measurement-only ALLOWED / pass REFUSED; MODES comparator;
Pineau seed tables; resource productivity modulates phenotype target harshness
(after D4).

**Lit hook:** doi:10.1162/artl_a_00430; doi:10.1162/artl_a_00280; Lopez Pascua
line; Pineau checklist.

**Success metric:** DX-style refuse pack green; resource dual-null.

**Refuse:** `tokyo_type1_passed`, `modes_passed*`, clinical prediction.

**Honest FAIL risk:** Low.

---

## Rejected (never schedule as earn-in)

- Infection / metabolism in `engine.py`
- Separate bacteria DomainProfile
- `population/` commit
- Soft-pass SF4 / invent RQ SUCCESS
- Avida or Aevol identity export
- Invented DOIs
- Clinical / phage-therapy clearance language in success criteria

---

## Suggested next PR sequence

1. **This docs PR** — brainstorm + phase plan (no code required).
2. **Code PR “detoy-D0-D1”** — DOI fix + thin type-II diagonal stepper + SF4′ re-run.
3. **Code PR “detoy-D2”** — region map.
4. **Design stub then code** — D4/D3 phenotype coupling.
5. Later — D5, D6, D7 as earned.
