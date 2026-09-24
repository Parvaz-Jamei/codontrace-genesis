# De-toy brainstorm — five rounds × three experts (2026-09-24)

**Project:** CodonTrace Genesis  
**Folder:** `docs/claimgate/host_parasite_port_20260924/`  
**Branch (docs):** `docs/detoy-brainstorm-hp-20260924`  
**Local time:** authored 2026-09-24 ~04:52 IRST (UTC+3:30)  
**Scope:** invent **non-toy**, ClaimGate-honest innovations that deepen the
`host_parasite` DomainProfile port after honest SF-campaign limitations —
especially SF4 FAIL — without baking infection into `engine.py`, without a
separate bacteria DomainProfile, without inventing DOIs, and without claiming
Red Queen proved / phage therapy / clinical prediction.

**Architecture locks (unchanged):**

| Lock | Meaning |
|---|---|
| ONE profile | `host_parasite` only |
| Cell | SemanticGenome / Genesis substrate (not a DomainProfile) |
| Microbe | COU semantic labels / roles only — not wet bacteria with metabolism |
| Infection physics | stay on the HP port (`host_parasite_env.py` and campaign helpers) |
| Engine | domain-agnostic; no infection / virulence / inject tokens |
| Population | never commit `src/codontrace/genesis/population/` |
| BAIC pins | A–C byte-identical |
| Docs prose | ordinary human research prose (no AI / agents / LLM / bot meta) |
| Differentiation | ClaimGate / auditor posture — not “become Avida” |

**Expert cast**

- **A — ALife ecology / digital coevolution** (Avida parasites, Zaman freeze–replay,
  Rabajante multi-type RQ structural conditions, Quigley cost-of-generalism)
- **B — Microbial genome / abstract metabolism honesty** (Aevol-inspired G→P depth
  on the *port*, Scanlan mutator humility, COU labels ≠ clinical bacteria)
- **C — ClaimGate honesty / V&V** (Okasha Price≠causality, Pineau reproducibility,
  Channon Tokyo Type 1 measurement-only, Dolson MODES comparator, Cornish
  observational≠interventional)

---

## 0. Inventory — why the HP port feels toy *now*

Concrete reading of tip code and SF artifacts (`host_parasite_env.py`,
`host_parasite_sim_fidelity_campaigns.py`, `host_parasite_resource_dynamics.py`,
`SIM_FIDELITY_CAMPAIGNS_20260924.md`, cell↔microbe hard campaigns).

### Diagnosis table

| Symptom | What the code actually does | Why that is toy relative to lit | Honest ceiling |
|---|---|---|---|
| **SF4 FAIL** | `_sf4_nfd_proxy`: 6 float counts, 40 gens, mild bonus `0.05*(1−f)` + hash noise; cycle = ≥3 unique dominants with ≥2 returns | No type-II functional response; no diagonally dominant specificity matrix \(A=[\alpha_{ij}]\); no specialist parasite coupling; no intermediate parasite mortality; no host carrying capacity \(K\); no inter-host competition term | `red_queen_proved=False` forever; FAIL is correct for *this* proxy |
| **Infection = boolean overlap** | `infection_eligible` = nonempty task-set intersection; one seat; steal_fraction default 0.8 | Fortuna/Acosta–Zaman analogy is present, but there is no graded specificity, no satiating FR, no IGFG/GFG continuum beyond labels | Digital eligibility only |
| **Cell = genome substrate only** | `SemanticGenome` = validated codon tuple + digest; cell campaigns treat host as genome digests | No transcription / translation / abstract metabolic phenotype target on the HP port (Aevol-style G→P is inspiration only) | Not wet cell biology |
| **Microbe ≈ COU labels** | DomainProfile + COU semantic tags; parasite payload is int tuple | Labels are correct architecture — but readers can mistake them for bacteria-with-metabolism | COU only; no clinical pathogen model |
| **Resource “dynamics”** | Phase 20 builds *synthetic* infectivity/resistance trajectories modulated by `resource_productivity` | Lopez Pascua honesty *map*, not resource metabolism or chemostat physics | Diagnostic labels, not wet ecology |
| **Small scale / seed-limited** | SF4: 5 seeds; SF1 hosts ~50 count-proxies; CM packs small | Lab-realistic demography / large IBM / multi-decade phage chemostats are out of scope by design | ClaimGate correctly blocks clinical prediction |
| **SF campaigns that *do* work** | SF1 coexistence-under-cost; SF2 biotic entropy contrast; SF3 ARD→FSD cost-rise; SF5 dual-genome digests; SF6–8 Cornish / replay / engine hygiene | Those successes are real *within digital ceilings* — they do not erase SF4’s structural gap | Do not inflate successes into RQ proof |

### SF4 literature cite — honesty correction (verify, do not invent)

| Field | Current SF4 panel | Verified (this session) |
|---|---|---|
| Title intent | Multi-host Red Queen perpetual dominance replacement | Correct phenomenon |
| DOI in code/docs | `10.1186/s12898-015-0055-7` | **Does not resolve to Rabajante RQ**; neighbor BMC Ecol `…0054-8` is an anthrax deer paper (unrelated) |
| PMC cited | `PMC4405699` | PubMed maps PMC4405699 → **Sci Rep** doi:`10.1038/srep10004` (Rabajante et al. 2015) |
| Correct primary cite for SF4 | — | **Rabajante et al. 2015 *Scientific Reports*** doi:[10.1038/srep10004](https://doi.org/10.1038/srep10004) |
| Related type-III / phase-locked rares | User-supplied | doi:[10.1126/sciadv.1501548](https://doi.org/10.1126/sciadv.1501548) (Rabajante et al. *Science Advances*) — binary oscillations + rare subordinates; **not** the SF4 success criterion |

**Action for a later code PR (not this docs PR):** retarget SF4 `doi` / literature string to `10.1038/srep10004`, keep PMC4405699, add SciAdv as *related comparator*, never soft-pass FAIL.

### Structural conditions Rabajante Sci Rep states (what SF4 lacks)

From the verified Sci Rep paper (type-II FR; diagonally dominant parasitism matrix; no super-host/super-parasite; intermediate parasite mortality; sufficiently large host carrying capacity; inter-host competition):

1. **Type-II functional response** \(\alpha_{ij} H_i / (1 + H_i)\) — satiating infection, not linear rare-bonus.
2. **Diagonally dominant specificity** — \(H_i\) is the main host of \(P_{j=i}\); off-diagonal alternatives weak; **no** super-host / super-parasite.
3. **≥~5 interacting types** (paper explores 3…20); diversity with specialists.
4. **Intermediate parasite mortality** — too high or too low contracts the RQ region.
5. **Large enough host \(K\)** — small carrying capacity collapses cycles.
6. **Inter-host competition** — intensifies as type count rises; interacts with infectivity.

SF4’s weak NFD proxy implements **none** of (1)–(5) as coupled host–parasite dynamics. FAIL is therefore a *structural impossibility* under the current assay, not bad luck of seeds.

---

## Round 1 — Shared diagnosis & proposal flood

**A (ALife ecology):** SF4 is not a near-miss. A rare-type fitness bump on uncoupled count vectors cannot produce winnerless multi-type replacement. The minimal *structural* upgrade is a port-local multi-type IBM/ODE-style stepper with type-II FR + diagonal \(A\), wired through `HostParasiteEnv` / campaign helpers — never `engine.py`. Success metric must stay qualitative cycling detection with `red_queen_proved=False` even if cycles appear.

**B (microbial G→P):** Agrees SF4 is structurally empty, but warns that “just add an ODE” without richer genotype→phenotype on the *cell substrate* keeps the module feeling like labeled floats. Propose an **Aevol-inspired abstract metabolic phenotype target** computed from SemanticGenome digests *on the HP port only* (transcription/translation *analogue*, not identity with Aevol). Microbe remains COU labels; metabolism is a *digital phenotype channel* for hosts (and optionally parasite “load” traits), not bacteria.

**C (ClaimGate):** Approves deepening only if every new mechanism ships with: prereg success criterion, dual-null / content-null path, refuse list spot-check, Pineau-style seed/hyperparameter disclosure, and explicit “FAIL still allowed.” Vetoes: inventing DOIs, claiming SciAdv phase-lock as SF4 SUCCESS, baking metabolism into engine core, splitting DomainProfiles, clinical / phage-therapy language in success criteria.

**Round-1 consensus weaknesses**

1. SF4 assay is structurally incapable of RQ-like cycles (toy NFD).
2. Infection specificity is binary overlap, not graded / diagonal.
3. Cell substrate lacks an abstract metabolic phenotype channel (Aevol-inspired).
4. Scale is seed-limited by design; ClaimGate must keep clinical prediction closed.
5. SF4 DOI string is wrong (BMC Ecol ghost); Sci Rep is the correct primary.

**Round-1 kill list (early)**

| Idea | Kill? | Why |
|---|---|---|
| Infection in `engine.py` | **Kill** | Hard lock |
| Separate bacteria DomainProfile | **Kill** | No unique blocked-claim set; architecture theater |
| Claim clinical bacteria / phage therapy | **Kill** | Blocked forever |
| Soft-pass SF4 with PARTIAL cosmetics | **Kill** | Honesty defect |
| Invent BMC Ecol DOI as “also correct” | **Kill** | Does not resolve to Rabajante |
| Become Avida / export Avida identity | **Kill** | Differentiation is ClaimGate, not clone |
| Commit `population/` | **Kill** | Hard lock |

---

## Round 2 — Force disagreement; pressure-test eight candidates

**A proposes**

1. **D1 — Multi-type type-II FR + diagonal specificity IBM on the port** (Rabajante Sci Rep conditions as *digital* knobs).
2. **D2 — Graded infectivity from task/IGF overlap** (replace boolean eligible with continuous \(\alpha_{ij}\) derived from overlap + specialist bias).
3. **D3 — Intermediate mortality + host \(K\) sweeps** as first-class campaign factors with pre-registered RQ-region map (still `red_queen_proved=False`).

**B proposes**

4. **D4 — Abstract metabolic phenotype target from SemanticGenome** (Aevol-inspired triangles / metabolic-error analogue on HP port).
5. **D5 — Parasite “CPU/metabolic load” coupled to host phenotype error** (Avida steal inspiration + Aevol fitness coupling — *port-only*).
6. **D6 — Cost-of-generalism as metabolic cost**, not only infectivity penalty (ties Quigley / Koskella–Brockhurst honesty to phenotype).

**C proposes**

7. **D7 — SF4-rebuild ClaimGate packet**: correct DOI, prereg cycling metric, intentional FAIL path retained, SciAdv type-III as *separate* SF panel (not a soft SF4).
8. **D8 — Measurement-honesty pack**: Channon measurement-only ALLOWED / pass REFUSED; MODES comparator; Pineau seed table; Okasha Price≠causality already shipped — extend to any new RQ-region claims.

**Forced disagreement**

- A wants D1 first (structural RQ capability).
- B wants D4 before celebrating RQ (otherwise cycles on toy floats).
- C wants D7 documentation/CiteGate hygiene *before* shipping dynamics that could be misread as proof.

**Round-2 lock:** order is **D7 (honesty/DOI) → D1+D2 (structural FR+specificity) → D3 (mortality/\(K\) map) → D4+D5 (phenotype coupling) → D6 (generalism as metabolic cost) → D8 (measurement pack)**. D4 may stub in parallel as a thin digest channel without blocking D1.

**Survivors after Round 2:** D1–D8 all survive if scoped to the port and refuse list. Theater killed above stays dead.

---

## Round 3 — Make dynamics *structurally capable* of RQ-like cycles

Focus: what must exist so SF4 is no longer a structural impossibility — while ClaimGate ceilings stay.

### Minimal dynamical skeleton (port-local)

Let host densities \(H_i\) and parasite densities \(P_j\) evolve under:

- Host growth with inter-host competition and carrying capacity \(K\).
- Type-II infection term with specificity matrix \(A\) **diagonally dominant by construction** (or sampled under a diagonal-dominance constraint).
- Parasite growth from infected host mass; **intermediate** mortality \(d\).
- **No** all-resistant host; **no** all-infecting parasite (super-* forbidden; ClaimGate documents the constraint).
- Optional stochastic noise later (SciAdv switching) — **separate panel**, not SF4 SUCCESS criterion.

Infection entry points:

- Map digital types ↔ `HostParasiteEnv` seats / task repertoires via graded \(\alpha_{ij}\) (D2).
- Keep `try_horizontal_inject` / `infection_eligible` as the *discrete* seat API; add a **campaign-level continuous stepper** that does not live in `engine.py`.

### Pre-registered success metric (SF4′ / De-toy SF4)

| Field | Spec |
|---|---|
| Metric | `cycling_detected`: ≥3 unique host dominants with ≥2 returns over \(T\) gens; optionally out-of-phase host–parasite peaks |
| Seeds | ≥5 declared seeds; report per-seed and fraction |
| SUCCESS | ≥3/5 seeds cycling under **declared** (type-II, diagonal \(A\), mid \(d\), adequate \(K\)) |
| PARTIAL | 1–2/5 seeds cycling |
| FAIL | 0/5 — still honest; do not loosen |
| Ceiling | `runtime_observation` or `candidate_evidence` only |
| Always False | `red_queen_proved`, `phage_therapy_cleared`, `clinical_pathogen_model` |

### SciAdv type-III panel (separate)

Type-III FR → binary dominant oscillations + phase-locked rare subordinates (doi:10.1126/sciadv.1501548). Ship as **SF9-candidate**, never as a way to mark SF4 SUCCESS when multi-type perpetual replacement is absent.

**A:** Approves skeleton; insists diagonal dominance is enforced in generators, not hoped for.
**B:** Approves only if host growth can later read metabolic phenotype (D4), even if stubbed.
**C:** Approves metrics; adds refuse-list regression test that SUCCESS cannot flip `red_queen_proved`.

**Round-3 survivors:** D1, D2, D3, D7, SciAdv-as-separate (call it **D9**).

---

## Round 4 — Richer cell ecology without claiming bacteria

**B leads.** Goal: deepen *cell* as SemanticGenome substrate so “host” is not a float label, while microbe stays COU.

### Innovation sketches

| ID | Mechanism (port-only) | Lit hook | Wow-but-honest pitch | Refuse |
|---|---|---|---|---|
| D4 | Decode SemanticGenome → abstract trait function (triangle / bin contributions) → phenotype vs target → metabolic error | Aevol model description (aevol.fr); not Aevol identity | “Hosts have a real digital metabolism channel — still not *E. coli*” | `clinical_pathogen_model`, Aevol replacement |
| D5 | Infected seat increases host metabolic error / reduces effective replication credit (steal × phenotype coupling) | Zaman/Avida CPU steal ~0.8; Acosta & Zaman 2022 doi:10.3389/fevo.2021.750772 | “Infection hurts through phenotype, not only a boolean flag” | `phage_therapy_cleared` |
| D6 | Generalists pay metabolic-error penalty (cost of generalism on phenotype), specialists pay less | Quigley et al. doi:10.1098/rspb.2012.0769; Gómez et al. doi:10.1098/rspb.2014.2297 | “Cost of generalism becomes visible in the cell substrate” | wet ARD identity |
| D10 | Resource productivity modulates phenotype target harshness (digital chemostat proxy) | Lopez Pascua line (already Phase 20 honesty map) | “Resources change what the cell must match — still abstract” | wet ecology proved |
| D11 | Parasite payload as short SemanticGenome under microbe **label** (already partly in genome_zaman) — deepen coupling to \(\alpha_{ij}\) | Zaman 2014 doi:10.1371/journal.pbio.1002023 | “Dual genomes drive specificity grades” | `gene_identity_proved`, `crispr_identity_proved` |

**A:** Wants D5 before D10; ecology cycles need fitness coupling.
**C:** Requires dual-null: content-null payload must break D5 effect; structure-null must break \(\alpha_{ij}\).

**Round-4 survivors:** D4, D5, D6, D10, D11 (all port-scoped).

---

## Round 5 — Ranked buildable phases (De-toy Wave / Wave 7 seed)

### Ranked innovations (build order)

| Rank | ID | Phase tag | Mechanism | Lit hook | Success metric (prereg) | ClaimGate refuse | Est. risk still FAIL honestly |
|---|---|---|---|---|---|---|---|
| 1 | D7 | **D0** | CiteGate: SF4 DOI → Sci Rep `10.1038/srep10004`; SciAdv comparator note; no soft-pass | Sci Rep / SciAdv | Docs + test assert DOI string; FAIL retained if no cycles | inventing DOIs | Negligible (docs) |
| 2 | D1+D2 | **D1** | Type-II FR + diagonally dominant \(A\) + graded overlap→\(\alpha\) on port IBM | Rabajante Sci Rep; Acosta–Zaman overlap | SF4′ SUCCESS criterion (≥3/5 cycling) **or honest FAIL** | `red_queen_proved` | **Medium–high** — parameter region contracts with type count |
| 3 | D3 | **D2** | Mortality \(d\) × \(K\) sweep map; publish RQ-capable region digests | Rabajante Sci Rep | Region nonempty under declared mid-\(d\) / high-\(K\); empty under extremes | clinical prediction | Medium — wrong grid → empty region (honest) |
| 4 | D5 | **D3** | Steal × metabolic-error coupling on infected seats | Zaman; Avida steal | Dual-null: content-null kills coupling delta | phage therapy | Low–medium |
| 5 | D4 | **D4** | Abstract metabolic phenotype from SemanticGenome | Aevol (inspiration) | Phenotype digest stable under replay; mutates under genome edit | Aevol identity; wet metabolism | Medium (design risk) |
| 6 | D6 | **D5** | Cost-of-generalism via phenotype penalty | Quigley; Gómez | Coexistence under cost (ties SF1) with phenotype channel | wet identity | Low if SF1 already green |
| 7 | D9 | **D6** | Separate type-III / phase-locked-rare panel | SciAdv 10.1126/sciadv.1501548 | Binary dominant + rare subordinates detected **or FAIL** | using D6 to pass SF4 | High — distinct regime |
| 8 | D8+D10 | **D7** | Measurement-honesty + resource→target harshness | Channon; Dolson; Pineau; Lopez Pascua | Measurement ALLOWED / pass REFUSED; resource dual-null | MODES/Tokyo passed | Low |

### Recommended **first build slice** (smallest non-toy step)

**Ship D0 (DOI honesty) + D1 thin slice together in the next *code* PR:**

1. Fix SF4 bibliography to Sci Rep `10.1038/srep10004` (keep PMC4405699).
2. Replace `_sf4_nfd_proxy` with a **port-local** multi-type stepper:
   - \(n \ge 5\) host and specialist parasite types;
   - type-II FR;
   - diagonally dominant \(A\) generator (no super-*);
   - mid mortality + adequate \(K\) as defaults;
   - same prereg cycling metric;
   - `intentional_hard_failure` retained if cycles absent;
   - `red_queen_proved=False` always.
3. No engine changes; no `population/`; no DomainProfile split; no metabolic full D4 yet (optional stub hook only).

This is the smallest change that can flip SF4 from **structural impossibility** → **testable** (SUCCESS *or* honest FAIL under capable dynamics).

### What must stay FAIL-closed

- `red_queen_proved`, `phage_therapy_cleared`, `clinical_pathogen_model`, `biosafety_level_certified`, `virulence_optimized_for_humans`
- `crispr_identity_proved`, `gene_identity_proved`, `complexity_emergence_proved`
- `intervention_supported`, `major_transition_proved`
- `tokyo_type1_passed`, `modes_passed*`, `oee_*`, `intelligence*`
- Avida / Aevol **identity** / replacement claims
- Lab-realistic clinical prediction from seed-limited digital runs

### Explicit false upgrades (rejected)

| False upgrade | Why rejected |
|---|---|
| Baking metabolism into `engine.py` | Breaks domain-agnostic engine; infection/metabolism belong on HP port |
| Claiming clinical bacteria | Microbe = COU labels; ClaimGate blocks |
| Avida identity export | Differentiation is auditor posture |
| Inventing RQ SUCCESS without cycles | Honesty defect |
| Multi DomainProfile split (bacteria vs cell) | Architecture theater; no unique refuse set |
| Soft-passing SF4 via SciAdv binary oscillations | Different phenomenon; separate panel |
| Committing `population/` | Hard lock |
| Inventing DOIs / keeping BMC Ecol ghost as primary | CiteGate fail |

---

## Top innovations — “wow but honest” pitches

1. **Capable Red Queen *assay*, not Red Queen *proof*** — type-II + diagonal \(A\) makes cycles *possible*; ClaimGate still refuses `red_queen_proved`.
2. **Graded specificity from digital overlap** — infection stops being a toy boolean without becoming wet immunology.
3. **Mortality×\(K\) region map** — publish where cycles can exist; empty corners are scientific results, not bugs.
4. **Cell metabolic channel (Aevol-inspired)** — SemanticGenome drives an abstract phenotype target; still not bacteria.
5. **Infection hurts through phenotype** — steal × metabolic error; dual-null falsifiable.
6. **Cost of generalism on the cell substrate** — links Quigley coexistence to phenotype, not only count games.
7. **Type-III rare-lock panel (separate)** — explains persistent rares without faking multi-type SF4 SUCCESS.
8. **Measurement theater refusal** — spectacular cycling metrics never promote OEE/MODES/Tokyo/clinical claims (DX lineage).

### Real depth vs cosmetic complexity

| Real depth | Cosmetic (avoid) |
|---|---|
| Coupled host–parasite densities with type-II FR + diagonal \(A\) | More seeds on the old weak-NFD proxy |
| Graded \(\alpha_{ij}\) from repertoire structure | Renaming boolean overlap |
| Phenotype error channel from SemanticGenome | Extra COU synonym labels |
| Dual-null that can kill the new effect | Dashboard charts without falsifiers |
| DOI correction to Sci Rep | Keeping BMC Ecol ghost “also” |
| Separate SciAdv panel | Calling binary oscillations “SF4 fixed” |

---

## موج ۱ / Critique wave 1 (experts A / B / C)

### A — ALife ecology

1. Do not ship D4 full metabolic decode before D1; readers will confuse prettier genomes with RQ capability.
2. Diagonal dominance must be a **generator invariant** with a unit test (random \(A\) draws rejected if not diagonally dominant).
3. Cycle metric should optionally require host–parasite peak lag (out-of-phase), else pure host noise can false-positive.

### B — Microbial genome / metabolism

4. D4 must state loudly: abstract mathematical phenotype (Aevol *inspiration*), not proteomics / flux balance / clinical MIC.
5. Microbe COU labels must not gain a second DomainProfile when phenotype lands — phenotype is cell-substrate depth on ONE profile.
6. SciAdv type-III is valuable but dangerous marketing; keep naming “binary oscillation / rare-lock,” never “full RQ fixed.”

### C — ClaimGate honesty

7. SF4 DOI bug is a **blocking CiteGate defect** for any de-toy code PR — fix in D0.
8. SUCCESS on SF4′ must add a regression: bundle still has `red_queen_proved=False` and ClaimGate refuses the string.
9. Pineau-style disclosure: list seeds, \(n\) types, \(d\), \(K\), \(A\) construction, generations, and compute budget in the results JSON.

### Fixes locked after موج ۱

- Build order confirmed: D0 → D1(+D2) → D2/D3 mortality-\(K\) → D3 steal×phenotype → D4 metabolism decode…
- Out-of-phase lag = optional secondary metric, not required for first slice.
- SciAdv = D6 panel name in phase plan, not SF4 alias.
- CiteGate DOI fix mandatory in first code PR.

---

## موج ۲ / Critique wave 2 (experts A / B / C)

### A

1. Thin D1 stepper may still FAIL honestly if defaults miss the contracting RQ region — that FAIL is acceptable and must be documented as parameter sensitivity, not “Genesis cannot do RQ forever.”
2. Avoid hidden super-generalists via task-overlap: if overlap coding recreates super-parasites, enforce specialist bias / cost.

### B

3. Persian summary must answer bachelor-level: می‌شود از اسباب‌بازی درآورد؟ بله، با فیزیک ساختاری RQ روی پورت — نه با ادعای باکتری واقعی.
4. Resource×target (D10) stays behind D4; Phase 20 synthetic trajectories are not enough to call metabolism done.

### C

5. Docs PR must not loosen DomainProfile blocked set; only describe future attach keys.
6. Reject any wording that SF campaigns “almost proved” Red Queen — SF tally stays 7 SUCCESS / 1 FAIL until SF4′ re-run.
7. Cross-check Quigley published DOI `10.1098/rspb.2012.0769` (arXiv:1210.2320 secondary) — already correct in SIM_FIDELITY docs.

### Fixes locked after موج ۲

- Phase plan states **honest FAIL still possible** after D1 with nonempty probability.
- Specialist-bias / anti-super-* constraints listed in D1 acceptance tests.
- Persian FA doc mirrors bachelor sentence + ranked phases.
- No ClaimGate ladder edits in this docs PR.

### Sign-off (موج ۲)

A / B / C agree: de-toy is **real** if and only if structural FR+specificity lands on the port; cosmetic seed inflation is rejected; clinical/RQ-proved claims stay closed; first slice = D0+D1.

---

## Literature grounded this session (verified; no invented DOIs)

| Topic | Citation |
|---|---|
| Multi-host RQ, type-II, diagonal \(A\) | Rabajante et al. 2015 *Sci Rep* doi:10.1038/srep10004 (PMC4405699) |
| Type-III binary RQ + phase-locked rares | Rabajante et al. *Sci Adv* doi:10.1126/sciadv.1501548 |
| Coevolution → complexity (Avida) | Zaman et al. 2014 *PLOS Biology* doi:10.1371/journal.pbio.1002023 |
| Ecological opportunity / CPU-theft comparator | Acosta & Zaman 2022 *Front Ecol Evol* doi:10.3389/fevo.2021.750772 |
| Cost of generalism / mode of interaction | Quigley et al. 2012 *Proc R Soc B* doi:10.1098/rspb.2012.0769 (arXiv:1210.2320) |
| Mixing → ARD | Gómez, Ashby & Buckling 2015 *Proc R Soc B* doi:10.1098/rspb.2014.2297 |
| Aevol G→P (inspiration) | aevol.fr model description (transcription/translation + abstract metabolic target) |
| Price ≠ causality | Okasha & Otsuka doi:10.1098/rstb.2019.0365 |
| MODES (comparator) | Dolson et al. 2019 doi:10.1162/artl_a_00280 |
| Tokyo Type 1 procedure (measurement) | Channon 2024 doi:10.1162/artl_a_00430 |
| Reproducibility checklist spirit | Pineau ML Reproducibility Checklist |
| Observational ≠ interventional | Cornish et al. arXiv:2301.07210 |

**Do not cite as Rabajante RQ:** `10.1186/s12898-015-0055-7` (does not resolve to that paper).

---

## Deliverables pointer

| File | Role |
|---|---|
| This file | Full English five-round brainstorm + دو موج critique |
| `DETOY_BRAINSTORM_5ROUND_20260924_FA.md` | Persian summary for bachelor-level readers |
| `DETOY_PHASE_PLAN.md` | Ordered phases D0–D7 with acceptance tests |

**Next code PR (out of scope here):** implement D0+D1 thin slice; re-run SF4′; keep FAIL-closed claims.
