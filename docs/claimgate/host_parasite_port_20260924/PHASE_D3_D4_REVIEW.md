# Phase D3+D4 review — infection×phenotype coupling + abstract metabolic channel

**Project:** CodonTrace Genesis  
**Local time:** 2026-09-24 ~05:25 IRST (UTC+3:30)  
**Scope (bounded):** D4 abstract phenotype from SemanticGenome on the HP port
(Aevol-*inspired*, not identity) + D3 infection-cost × metabolic-error coupling
with dual-null. NOT engine.py infection; NOT real bacteria metabolism; NOT
Aevol replacement.

**Experts:** A · B · C · D (cross-field)

---

## Literature + competitor code (pre-build)

| Source | Use |
|---|---|
| Aevol G→P (aevol.fr decoding example) | Triangle traits + metabolic error Δ vs target — inspiration only |
| Zaman / Avida steal ~0.8 | Couple infection seat cost into phenotype error via steal_fraction |
| Matching-allele / virulence–cost tradeoff lit | Cost of infection as digital phenotype penalty, not clinical virulence |
| Dual-null HE pattern already on port | content_null kills payload delta; structure_null kills infection path |

---

## Pre-build plan

1. **D4:** `decode_abstract_phenotype(genome)` → bins on [0,1], `metabolic_error`, stable digest.
2. **D3:** Intact arm: occupied seat raises error by f(steal, payload). content_null → Δ≈0 vs baseline seat. structure_null → no infection → Δ≈0.
3. Success: dual-null separation magnitude > prereg threshold; refuse phage/clinical/Aevol-identity claims.

---

## موج ۱ (pre-build)

### A
1. Coupling must use existing HostParasiteEnv seats — no second infection physics.

### B
2. Explicit “not Aevol identity / not wet metabolism” in schema honesty fields.

### C
3. Dual-null mandatory; BAIC pins; refuse list spot-check.

### D
4. **Adopt:** abstract triangle phenotype (Aevol-inspired math); infection cost as phenotype error (virulence–cost tradeoff analogy).
5. **Reject:** flux-balance / real bacterial metabolism claims; SIR clinical R0 from error; exporting Aevol binaries.

## موج ۲ pre-build sign-off: A/B/C/D approve.

---

## Build summary

- `host_parasite_abstract_phenotype.py` (D4)
- `host_parasite_infection_phenotype_coupling.py` (D3)
- Tests: `test_host_parasite_abstract_phenotype.py`, `test_host_parasite_infection_phenotype_coupling.py`

## Post-build موج ۱

### A
1. Coupling uses HostParasiteEnv inject + retained CPU; no second infection core.

### B
2. `aevol_identity=False`, `wet_metabolism_claim=False` on all payloads; genome edit changes error.

### C
3. Dual-null: intact Δ≈0.63; content/structure Δ=0; refuse phage_therapy_cleared; pins green.

### D
4. Adopted triangle phenotype + virulence-cost-as-error; rejected FBA/SIR clinical overlays.

### Fixes
- `add_host` API (not register_host); simplified arm loop.

## Post-build موج ۲ — sign-off

A/B/C/D sign-off D3+D4. Three De-toy build phases complete.
