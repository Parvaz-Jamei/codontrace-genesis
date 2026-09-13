# Amd 03 code deviations (sibling note — do not rewrite Amd 03 bytes)

**Product:** CodonTrace Genesis  
**Scope:** Document two `_apply_survival_calibration` differences from the
Amd 01 / v3 overlay wording that landed with SCHEMA v5 / Wave 1d′.  
**Amd 03 frozen file:** `docs/HARD_EXPERIMENT_01_PREREG_AMENDMENT_03.md` — **bytes
unchanged**. This sibling note is the Willroth & Atherton deviation surface
(P3 / Wave 1d′ review).  
**ClaimGate:** unchanged — ceiling stays `runtime_observation`.

---

## Willroth & Atherton rows

| # | Item | Prereg / v3 intent | Code as shipped (v5+) | Quantified delta | Timing | Confirmatory? |
|---|---|---|---|---|---|---|
| D1 | `population_size` for `respawn_draws_per_tick` | v3 used `int(spec.population_max or len(spec.genome_bits))` | `population_size = len(spec.genome_bits)` | Research: `population_max=32`, `len(genome_bits)=16` → draws **16** not 32. Smoke: `population_max=16`, genomes=8 → draws **8** not 16. Matches Amd 03 table row “`max(1, population_size)`” when *population_size* is read as the seeded cohort length, not `population_max`. | Before any v5 pilot / analysis | Yes — overlay calibration |
| D2 | `max_resources` | v3 used `max_resources=len(food_cells)` | `max_resources=lattice_cells` (`width*height`) | Under Amd 03 every-cell food, `len(food_cells) == lattice_cells`, so **Δ = 0** on the v5 layout. Under historical Amd 02 sparse food the lattice ceiling would have exceeded patch count; Amd 03 reverts food to every-cell, so this is a no-op for confirmatory v5/v6 runs. | Before any v5 pilot / analysis | Disclosure — no outcome change under every-cell |

---

## Why a sibling file

Amd 03 §2 already has a Willroth-style table for the *intended* Amd 02→03
reverts (roles-only variance, every-cell food, population respawn draws). The
two rows above are **implementation** details that were not spelled out in that
table: which Python expression supplies `population_size`, and whether
`max_resources` tracks food patches or the lattice. Freezing Amd 03 bytes and
recording the quantification here keeps the audit trail honest without
rewriting hashed prereg text.

## Pilot pointer

Committed pilots: `docs/hard_experiment_01/pilot_v5.json` (Wave 1d′ /
SCHEMA v5) and `docs/hard_experiment_01/pilot_v6.json` (Wave 1e / SCHEMA v6).
