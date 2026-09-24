# Phase D0+D1 review — CiteGate DOI + type-II / diagonal-A stepper

**Project:** CodonTrace Genesis  
**Branch:** `feat/detoy-d0-d1-type2-diagonal`  
**Local time:** 2026-09-24 ~05:01 IRST (UTC+3:30)  
**Scope:** De-toy first build slice (D0 bibliography honesty + D1 port-local
type-II FR / diagonally dominant specificity). ONE `host_parasite`
DomainProfile; infection stays off `engine.py`; `red_queen_proved` stays False.

**Experts**

- **A** — ALife / host–parasite ecology (Avida parasites, Rabajante RQ, Zaman)
- **B** — microbial genome / abstract metabolism honesty (Aevol-inspired depth later)
- **C** — ClaimGate honesty / reproducibility
- **D** — Cross-field innovator (ecology ODE, matching-allele immunology, control /
  discrete Holling-II, network specificity, epidemiology SIR variants, EGT)

---

## Literature + competitor code (executor search, pre-build)

| Source | Finding used |
|---|---|
| Rabajante et al. 2015 *Sci Rep* doi:10.1038/srep10004 (PMC4405699) | Primary SF4 cite; type-II FR; diagonal A; mid-d / large-K region; no super-* |
| Rabajante et al. *Sci Adv* doi:10.1126/sciadv.1501548 | Related comparator only (type-III rare-lock) — **not** SF4 SUCCESS |
| Ghost DOI `10.1186/s12898-015-0055-7` | Does **not** resolve to Rabajante RQ — rejected |
| Zaman / Acosta Avida parasites (PLOS Biol 2014; Front Ecol Evol 2021; github.com/miguelfortuna/avida_host-parasite) | Steal ~0.8 and task-overlap infection already on port; do **not** clone Avida IBM into engine |
| Aevol G→P (aevol.fr) | Inspiration reserved for D4; not identity |
| Matching-allele / partial MA (Agrawal & Lively; Luijckx et al.) | Interpret diagonal A as partial matching-allele — transferable immunology framing |
| Discrete Holling-II / Euler prey–predator literature | Discrete Euler stepper is an acceptable digital analogue of the Sci Rep ODE |

---

## Pre-build plan (locked)

1. **D0:** Retarget SF4 `doi` → `10.1038/srep10004`; keep PMC4405699; record SciAdv as related; reject ghost BMC Ecol DOI in panel metadata.
2. **D1:** New `host_parasite_type2_rq.py` on the port: generator for diagonally dominant A; typed refusal of super-*; type-II Euler stepper; graded α from task overlap; SF4 panel rewired to `run_type2_campaign`; legacy weak NFD kept as contrast (must still fail).
3. Prereg: ≥3/5 seeds `cycling_detected` → SUCCESS; always `red_queen_proved=False`.

---

## موج ۱ / Critique wave 1 (before coding) — experts A/B/C/D

### A (ecology)

1. Weak NFD float proxy cannot produce winnerless multi-type replacement; type-II + diagonal A + inter-host competition are mandatory.
2. Defaults must sit in the Sci Rep mid-d / adequate-K region; extremes should be able to FAIL honestly.

### B (genome / metabolism)

3. Do not claim wet metabolism or phage therapy from float densities; cell substrate deepening waits for D4.
4. Graded α from digital overlap is fine as a *campaign-layer* extension of `infection_eligible`, not an engine change.

### C (ClaimGate)

5. SUCCESS must not flip `red_queen_proved`; SciAdv must not soft-pass SF4; ghost DOI must be explicitly rejected in metadata.
6. Pack digests must use canonical SHA-256 (no Python `hash()`); BAIC pins untouched.

### D (cross-field)

7. **Adopt:** partial matching-allele reading of diagonal A (immunology); Holling type-II FR (ecology ODE); discrete Euler stepping (control / discrete dynamics literature).
8. **Reject:** IPM economic-threshold switching (pest-management clinical-adjacent framing); pure GFG with universal virulence / super-parasite (breaks no-super-* lock); Allee / refuge chaos packs (out of D1 scope; ClaimGate noise).

### Fixes after موج ۱

- Encoder plan includes `assert_no_super_host_or_parasite` and ConfigurationError on non-dominant A.
- SF4 panel fields: `related_comparator_doi`, `ghost_doi_rejected`, `structurally_testable`, legacy NFD contrast.
- Capable defaults: n=5, d=0.12, K=2.0, r=0.5, type-II, α_off=0.01 (Sci Rep–analogue).

---

## موج ۲ / Critique wave 2 (pre-build sign-off)

### A

1. Confirm legacy weak NFD still reports 0 cycling seeds (documents structural upgrade).

### B

2. Confirm no Aevol identity strings in ALLOWED claim set; no bacteria DomainProfile.

### C

3. Refuse-list spot-check remains; intentional_hard_failure flag retired (panel is now structurally testable — FAIL only if seeds miss).

### D

4. Confirm rejected cross-field ideas are written down (IPM switch, Allee chaos, super-GFG).

### Sign-off (pre-build)

A/B/C/D approve D0+D1 plan for coding on `feat/detoy-d0-d1-type2-diagonal`.

---

## Build summary (filled after coding)

- Module: `src/codontrace/genesis/host_parasite_type2_rq.py`
- SF4 panel rewired in `host_parasite_sim_fidelity_campaigns.py`
- Tests: `tests/test_host_parasite_type2_rq.py` + updated `test_host_parasite_sim_fidelity.py`
- Docs: this review + `_FA.md`; SIM_FIDELITY MD/JSON refresh

---

## موج ۱ / Post-build critique (results)

### A

1. With capable defaults, all five SF4 seeds show epoch-level dominance replacement (cycling_detected); high-d and tiny-K controls remain non-cycling — region sensitivity present for D2.

### B

2. Densities are digital; no wet-metabolism claim strings introduced; graded overlap helper is port-local.

### C

3. `red_queen_proved` False on SUCCESS; DOI is Sci Rep; ghost DOI recorded; BAIC pins unchanged; engine hygiene SF8 still green.

### D

4. Adopted matching-allele / type-II / Euler; rejected IPM switch and Allee packs as planned.

### Fixes after post-build موج ۱

- Keep legacy NFD contrast assertion in tests.
- Document SciAdv as related only in results MD.

---

## موج ۲ / Post-build sign-off

A/B/C/D sign-off: D0+D1 complete; SF4 structurally testable; ClaimGate ceilings intact; proceed to Phase D2 (mortality × K region map) only after this PR is green locally.

**Refused forever:** infection in `engine.py`; `population/` tree; separate bacteria DomainProfile; clinical/phage claims; inventing DOIs; soft-passing SF4 via SciAdv binary oscillations; Tokyo/MODES passed; CRISPR gene identity proved.
