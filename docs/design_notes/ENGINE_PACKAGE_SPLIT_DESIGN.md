# DESIGN ONLY — Future `engine.py` package split

**Status:** Design note (Phase 10). **Do not execute** a mass move without explicit owner go-ahead.  
**Date:** 2026-09-24 (Asia/Tehran)  
**Binding:** Architecture lock modular platform §7; modular ten-phase plan Phase 10.  
**Current monolith:** `src/codontrace/engine.py` (~3298 lines).

## Purpose

Document proposed package boundaries, migration order, and pin risks so a future migration PR can proceed safely. This note is **not** authorization to split code under the Phase 1–10 platform track.

## Proposed conceptual packages

Illustrative names only — final Python paths require owner approval:

| Package | Responsibility | Likely sources today |
|---|---|---|
| `codontrace.kernel.tick` | Ordered multi-individual step / Simulation loop glue | `engine.py`, `simulation.py` |
| `codontrace.kernel.population` | Multi-pop registry surfaces already mirrored in life_loop | `engine.py` population paths; `life_loop/populations.py` remains domain-free runtime |
| `codontrace.kernel.attachment` | Seat / occupancy wiring at engine boundary | Prefer keep physics in `life_loop.attachment`; engine only schedules |
| `codontrace.kernel.energy` | ATP / coupling ledger bridges | `engine.py` energy paths; `life_loop.energy_coupling` |
| `codontrace.kernel.hooks` | Birth/death/contact/resource hook dispatch | `engine.py` + `life_loop.hook_meters` observation |
| `codontrace.kernel.ablation` | Ablation apply at engine boundary | Prefer `life_loop.ablation_template` as source of truth |
| `codontrace.kernel.schedule` | Schedule lock / freeze / replay dispatch | Prefer `life_loop.schedule_lock` |

**Rule:** Domain vocabulary (infection, virulence, host, parasite, ClaimGate, vaccine, CRISPR) stays out of `kernel.*` type names. Discipline modules configure primitives; they do not become a second tick engine.

## Migration order (suggested)

1. Freeze BAIC / HE01 pin digests and ClaimGate refuse snapshots; add a pin CI job if missing.
2. Extract **pure helpers** with zero behavior change (digest, finite checks) — already partly in `canonical.py` / contracts.
3. Move **read-only observation** bridges first (meters → export), never tick ownership.
4. Split schedule / ablation dispatch behind facades that keep public import paths stable (`codontrace.engine` re-exports) for one release.
5. Move population / attachment / energy last; require golden digests for HE01 / BAIC / life_loop unit suites green at each step.
6. Delete shims only after a stability window and owner sign-off.

## Risk to BAIC / HE01 / ClaimGate

| Risk | Mitigation |
|---|---|
| Import path churn breaks pin file hashing | Pins hash file **bytes**, not import graphs — still re-run `assert_baic_pins_untouched` every migration step |
| Accidental edit of locked JSON while “tidying” | Migration PRs forbid touching `docs/hard_experiment_01/results_v7.json`, ClaimGate risk/biomedical JSON |
| Behavior drift in Simulation.step | Golden digest tests + HE01 replay before/after each package cut |
| Domain nouns leak into kernel | Static banned-token audit on `codontrace/kernel/**` |
| Second tick engine via “helpful” HP world split | Architecture lock §4 — HostParasiteWorld stays thin config |

## Ownership checklist (before any split PR)

- [ ] Owner explicit go-ahead recorded
- [ ] Pin trio byte-identical vs pre-migration tip
- [ ] ClaimGate refuses unchanged (incl. `avida_replacement`, `red_queen_proved`, clinical/BSL)
- [ ] life_loop unit suites green without `host_parasite_*` imports
- [ ] Public API compatibility plan (re-export shim duration)
- [ ] No git push policy change unless owner requests

## Explicit non-goals of this note

- Mass-refactoring `engine.py` in Phase 10 (or any phase without go-ahead)
- Relocating life_loop into `kernel.*` without a separate storm
- Using peer engines as the package layout yardstick

**Headline:** *Design the split; do not execute it until the owner orders a migration PR that keeps pins and refuses intact.*
