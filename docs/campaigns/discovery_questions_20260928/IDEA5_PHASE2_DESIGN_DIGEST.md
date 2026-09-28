# Idea 5 — Phase-2 design digest: transferable short composable falsifiable causal symbolic laws

**Date:** 2026-09-28 (Asia/Tehran)  
**Base commit:** `71cbebd` (`71cbebd`), `main`  
**Campaign folder:** `docs/campaigns/discovery_questions_20260928/`  
**Status:** phase-2 design freeze only; not a discovery claim; not authorisation to run  
**Claim ceiling:** `phase2_design`  
**Phase-1 anchor:** [`IDEA5_PHASE1_PROBLEM_BOUNDARY.md`](IDEA5_PHASE1_PROBLEM_BOUNDARY.md)  
**Prior-art support:** [`IDEA5_PHASE2_PRIOR_ART_20260928.md`](IDEA5_PHASE2_PRIOR_ART_20260928.md)  
**hypothesis_supported:** `false` (pre-data; no outcome claimed)

This digest records the sealed phase-2 design for testing whether a population can retain short, composable, falsifiable causal laws on a contact/ATP ledger and transfer them to unseen worlds that share causal structure but differ in appearance and history. It distinguishes survival-only selection from memory and boundary teaching, and it includes a pre-registered probe for laws that use private simulator features rather than the shared causal skeleton. It fixes no empirical result. No runner, pilot, or campaign is authorised by this file. Empty required identity fields at run time reopen the freeze.

---

## 1. Standing locks

- The life-loop engine remains domain-free: no infection physics in `engine.py`.
- No Euler-in-loop, no Avida paths into the engine, no mega-utils, and no second population engine.
- Sealed campaign seeds `801–816` remain untouched.
- `red_queen_proved` remains false.
- Unit of replication = **run**; series via `GenerationBoundaryObserver`; contact pairs are not N.
- Offline symbolic regression on a fixed dataset is not equated with evolutionary selection and transfer of falsifiable causal laws across worlds.
- Train-world fit alone never counts as transfer; held-out worlds with shared causal structure are mandatory.
- Combos C and E are mandatory core. Combos A, B, and D are mapped supporting components only, as specified below.
- DreamCoder and related program-synthesis work remain deferred methods literature, not precedent that closes this design gap.
- Runners stay off until the owner explicitly allows execution.
- Claim language is limited to “not aware of a published precedent for …”; search gap is not uniqueness.
- `hypothesis_supported` stays `false` until a later authorised phase raises it under the locked falsifiers.

---

## 2. Design core (from prior-art and phase-1 boundary)

**Mandatory core:** Combo C (survival-selected social learning contrasted with survival-only selection) plus Combo E (the private-feature versus shared-skeleton shortcut probe). The core estimand is held-out interventional transfer of a short law, scored per run, with the teaching contrast and shortcut probe both present.

**Mapped supporting components:** Combo A supplies the symbolic-law and held-out interventional transfer cut; Combo B supplies the compositional law library and generation-boundary retention/teaching mapping; Combo D supplies the multi-world shared-skeleton and cross-appearance transfer structure. None of A, B, or D may replace the mandatory C+E contrast.

**Deferred, not precedent:** DreamCoder is retained as adjacent compositional method literature only. It does not by itself establish evolutionary selection under survival pressure, inter-generation teaching of falsifiable causal laws, held-out causal-skeleton worlds, or the shortcut probe.

**Representation hypotheses (locked for design):**

| ID | Statement |
|---|---|
| **H0** | No arm retains a short composable law that clears the locked held-out interventional threshold and shortcut-probe rule; apparent laws are noise or non-transferable. |
| **H1** | World-specific heuristics only: lineages fit training worlds but fail held-out transfer by the locked margin, so within-world success is not a shared-structure law. |
| **H2** | A retained short composable law clears held-out interventional accuracy ≥ 0.80, passes the shortcut probe, and clears the ≥ 0.15 transfer-success margin against the best non-transfer control. |
| **H3** | Survival alone is insufficient: H2-level transfer appears only when memory and/or boundary teaching is enabled; the survival-only control remains at H0/H1. |

H2 requires both held-out transfer and a shortcut-probe pass. H3 additionally requires the matched survival-only control to fail while memory or teaching succeeds. Train-world fit, private-feature success, or a survival advantage without a valid law assay does not support H2.

---

## 3. Mandatory one-line operations (ledger only; generation boundary)

All four operations use contact/ATP ledger variables and generation boundaries. None opens domain physics in `engine.py`, and none may use a private simulator feature as an unregistered law variable.

1. `retain_short_law` — retain a candidate from the registered short-law class in the individual or lineage ledger, subject to the fixed length, composition, and falsifiability bounds.
2. `teach_at_boundary` — transmit an eligible retained law, and only the registered law metadata, at a `GenerationBoundary`; teaching cannot transmit an unregistered private feature or alter the engine.
3. `survival_only_control` — select on registered reproductive/energetic survival outcomes with no explicit law memory and no teaching events; this is the matched H3 control.
4. `shortcut_probe` — evaluate the retained law on paired held-out worlds that separate private features from the shared causal skeleton, using the pre-registered pass/fail rule in section 4.3.

The operations are recorded at the generation boundary. A missing law assay, empty world split, empty teaching definition, or empty shortcut construction reopens the freeze. No operation silently converts train-world fit into transfer success.

---

## 4. Locked identity fields (non-empty; empty = reopen freeze)

### 4.1 World family and causal skeleton

| Field | Locked value |
|---|---|
| **World-family ID** | `WORLD-FAMILY-CONTACT-ATP-V1` |
| **Shared causal skeleton** | On the contact/ATP ledger, registered contact state and resource offer determine the ATP-yield response under the registered low-cost intervention; the same named interventional relations hold in train and held-out worlds. |
| **Appearance/history axes** | Contact-label frequencies, resource-schedule statistics, surface cue distributions, and trajectory histories may vary while the named ledger relations remain fixed. |
| **Train/held-out split** | Train worlds are available for selection and teaching; held-out worlds are withheld from both during training generations and are used only by the registered transfer and shortcut assays. |
| **Ledger visibility** | World variables, law inputs, interventions, and ATP outcomes are ledger-visible; engine-private state is not an admissible law input. |

The execution preregistration may name the concrete world instances and observables under this ID, but may not empty the held-out split or collapse appearance differences into the shared skeleton.

### 4.2 Short composable law

| Field | Locked value |
|---|---|
| **Law ID** | `LAW-SHORT-COMPOSABLE-V1` |
| **Form** | A falsifiable rule over named contact/ATP ledger variables that predicts or constrains a registered low-cost `do` outcome. |
| **Complexity bound** | At most 12 primitive ledger terms/operators and composition depth at most 3; the exact grammar is fixed before any run. |
| **Composition** | Candidates may be combined only with the registered conjunction/conditional composition algebra; composition cannot introduce private engine variables. |
| **Retention** | The candidate is stored as an explicit ledger object and may persist across generation boundaries only through the registered inheritance, memory, or teaching channel. |
| **Assay** | Interventional accuracy is computed on held-out worlds by horizon T; train-world fit alone is invalid. |

A candidate that is short but unfalsifiable, non-composable, or private-feature dependent is not `LAW-SHORT-COMPOSABLE-V1`.

### 4.3 Simulator-shortcut probe

| Field | Locked value |
|---|---|
| **Probe ID** | `PROBE-PRIVATE-VS-SKELETON-V1` |
| **Construction** | A paired held-out test preserves the shared contact/ATP skeleton while scrambling registered private or surface features, and separately preserves private/surface correlates while breaking or relocating the shared skeleton. |
| **Pass rule** | A retained law must preserve held-out interventional accuracy when the shared skeleton remains and private correlates are scrambled, and must not retain success when only private correlates remain after the skeleton is broken or relocated. |
| **Fail rule** | Success only with private features, or failure when only the shared skeleton remains, is a simulator shortcut and is not transfer success. |
| **Scoring** | Probe pass is recorded per run and included in the transfer-success estimand. |

The exact paired worlds and scramble map are fixed in execution preregistration before any run. Empty pairs or an unregistered private-feature definition reopen the freeze.

### 4.4 Survival, memory, and teaching channels

| Field | Locked value |
|---|---|
| **Survival-only control** | `survival_only_control`: selection on registered reproductive/energetic success; no explicit law memory and no teaching events. |
| **Memory condition** | Individuals may retain `LAW-SHORT-COMPOSABLE-V1` candidates during their lifetime, with retention cost and expiry fixed before execution. |
| **Teaching condition** | `teach_at_boundary` may transmit eligible law candidates at `GenerationBoundary`; teaching does not transmit private features, raw engine state, or unregistered policies. |
| **Matched comparison** | World family, law grammar, horizon, assay, and cost schedule are held fixed across survival-only, memory, and teaching cells. |

### 4.5 Transfer-success event

A run has **transfer success** only if its retained law set reaches held-out interventional accuracy ≥ 0.80 by horizon `T = 40` generation boundaries and passes `PROBE-PRIVATE-VS-SKELETON-V1`. A train-world result without held-out transfer, or a held-out result that fails the probe, is not a successful law.

---

## 5. Locked thresholds (pre-data)

| Quantity | Lock |
|---|---|
| Primary estimand | Share of **runs** achieving transfer success by `T = 40` generation boundaries: held-out interventional accuracy ≥ 0.80 plus shortcut-probe pass |
| θ | **0.80** held-out interventional accuracy; train-world fit alone never counts |
| Transfer margin | Transfer-success share ≥ **0.15** above the best matched non-transfer control |
| Shortcut-probe pass rate | ≥ **0.80** among runs counted as transfer-successful |
| H3 comparison | Memory and/or teaching must clear the locked margin while `survival_only_control` does not under the matched cell |
| Replication unit | `N = run`; independent runs are the replication units; contact pairs are not N |
| Series | Generation-boundary observations via `GenerationBoundaryObserver` |
| `hypothesis_supported` | `false` |

Soft-pass language, including “near 0.80” or “near 0.15,” is forbidden. Post-hoc threshold moves or redefining N reopen the freeze.

---

## 6. Explicit falsifiers

1. No arm clears held-out accuracy ≥ 0.80 with a valid probe pass in any registered cell → favour H0.
2. Training-world fit is high but held-out accuracy drops by ≥ 0.20, or fails the locked margin → favour H1.
3. `survival_only_control` matches memory or teaching within the locked ≥ 0.15 margin → H3 fails; survival may suffice in that cell.
4. A law succeeds only when private features remain, or fails when only the shared skeleton remains → simulator shortcut; not H2.
5. Teaching transmits private engine state, an unregistered policy, or a hidden feature instead of a short law candidate → design FAIL.
6. Combo C is omitted, or the survival-only versus teaching contrast is not matched on the same estimand → mandatory-core FAIL.
7. Combo E is omitted, or `PROBE-PRIVATE-VS-SKELETON-V1` is empty or post hoc → mandatory-core FAIL.
8. Combo A, B, or D is treated as a substitute for C+E; DreamCoder is treated as a precedent that closes the gap → design FAIL.
9. Advantage is obtained through infection physics in `engine.py`, domain RNG hacks, Avida paths, or a second population engine → design FAIL; discard.
10. An empty world-family ID, law ID, probe ID, held-out split, or law assay appears at run time → freeze reopens and results are invalid.

---

## 7. Gap wording and verified prior art (ceiling)

We are not aware of a published precedent for a pre-registered evolutionary multi-world protocol in which populations retain short, composable, falsifiable causal laws, transfer them to held-out worlds sharing a contact/ATP causal skeleton but differing in appearance, contrast survival-only selection with memory or boundary teaching, and use a simulator-shortcut probe to distinguish shared structure from private features, with run-level replication and generation-boundary series. Absence of a search hit is not proof of uniqueness.

Verified nearest published ingredients (DOIs from the prior-art report only): Schmidt & Lipson 2009 `10.1126/science.1165893`; Brunton, Proctor & Kutz 2016 `10.1073/pnas.1517384113`; Rudy et al. 2017 `10.1126/sciadv.1602614`; Udrescu & Tegmark 2020 `10.1126/sciadv.aay2631`; Trinh et al. 2024 `10.1038/s41586-023-06747-5`; Gonzalez, Watson & Bullock 2017 `10.1162/artl_a_00244`; Chen, Xue & Zhang 2022 `10.1109/tcyb.2020.2969689`; Liang et al. 2025 `10.1109/iceaai64185.2025.10956846`; Wang et al. 2024 `10.1145/3638530.3654282`; Ellis et al. 2023 `10.1098/rsta.2022.0050`.

The cited equation-discovery, multitask-transfer, social-learning, geometry, and compositional-program methods motivate mapped components but do not close the integrated C+E design gap. DreamCoder remains deferred method literature, not a locked precedent.

---

## 8. What this phase does not claim

- Not a discovery, law, or “first” claim.
- Not authorisation to start runners, pilots, or campaigns.
- Not a sealed `PHASE2_FREEZE` (this file is a  awaiting freeze).
- Not a revision of sealed seeds `801–816`.
- Not support for H0/H1/H2/H3 (`hypothesis_supported=false`).
- Not evidence that offline symbolic regression, multitask transfer, social learning, geometry proving, or DreamCoder already solves the integrated question.
- Not permission to score train-world fit as held-out causal transfer.
- Not permission to use private simulator features, infection physics, domain RNG hacks, Avida paths, or a second population engine.
- Combos C and E remain mandatory; Combos A, B, and D remain mapped support only.

