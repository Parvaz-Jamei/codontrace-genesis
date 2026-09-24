# Phase build protocol — CodonTrace Genesis

**Status:** Binding for platform and module workstreams  
**Date:** 2026-09-24  
**Related:** `docs/architecture/` modular platform lock (handoff copy may also live outside the tree)

## Purpose

Every numbered build phase for the modular platform (and for discipline profiles such as host–parasite) must be made scientifically current and cross-disciplinary **before** code lands, then stress-tested by a second critique pass, then implemented. Phases are not skipped. Completed phases land on `main` by direct push (when remote write is available).

## Roles

| Role | Focus |
|------|--------|
| A — Artificial life / digital evolution | Kernel life-loop, populations, hooks |
| B — Microbial ecology / coevolution science | Domain science that stays in module config and metrics |
| C — Claim honesty / refuse discipline | ClaimGate ceilings; no soft-pass |
| M — Senior program / architecture management | Anti–second-engine, reuse across future disciplines, delivery gates |
| I — Cross-field innovation | Search for **capabilities not yet standard** in comparable platforms that would make processing or problem-solving in this phase novel; propose concrete affordances to adopt |

## Per-phase cycle (mandatory order)

### Stage 1 — Design storm (two rounds)

1. Round 1: A/B/C/M/I each bring literature or repo evidence; I must search for unused affordances (pipelines, controls, measurement tricks, coupling patterns) that are rare or absent in Avida/Symbulation/MABE-class stacks and relevant to **this** phase.
2. Round 2: Critique each other; consensus on what enters the phase brief (adopt / defer / reject). Novelty is scored by **process affordance**, not by buzzwords.

### Stage 2 — Integrator revision

The integrator (maintainer executing the phase) re-searches with current sources, rewrites the phase brief: goals, engine hooks, forbidden parallel work, accept tests, ClaimGate notes, and the innovation items selected for this phase.

### Stage 3 — Adversarial storm (two rounds)

1. Round 1: Group attacks the revised brief for scientific holes, second-engine risk, ClaimGate leakage, digest/pin risk, and missing tests.
2. Round 2: Attempt to break the accept criteria on paper (and with spike tests when cheap); consensus on required fixes.

### Stage 4 — Apply and implement

Integrator applies agreed fixes, implements on a branch, runs phase accept tests, writes ordinary research notes (no tool-chain attribution), and lands the phase on `main` by direct push. Next phase does not start Stage 4 until Stage 3 consensus is recorded.

## Platform positioning

CodonTrace Genesis is an **independent** ALife / validation engine with its own life-loop.
It is **not** an Avida plugin or derivative baseline. Peer platforms (including Avida) may be
compared or optionally supported for compatibility; design storms must not treat them as the
foundation. Novelty is scored on process affordances on the CodonTrace stack.

## Standing constraints

- Engine remains a modular general ALife / validation platform; discipline modules configure primitives and do not reimplement tick / population / energy / replay.
- Domain vocabulary stays out of kernel types (`engine.py` and successors).
- BAIC / HE01 pins and ClaimGate refuses are never loosened to “make green.”
- Honest FAIL is allowed; soft-pass is not.
- Commit and doc prose must not name automation vendors or role labels that mark machine authorship; ordinary scientific English/Persian is enough.

## Record-keeping

Each phase folder or handoff note should store: Stage 1 consensus, Stage 2 brief, Stage 3 critique log, Stage 4 accept-test results and commit hash on `main`.
