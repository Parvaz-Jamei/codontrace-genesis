# Discovery questions (2026-09-28)

Six open scientific questions on evolution, causal knowledge, and collective intelligence.
See `DISCOVERY_QUESTIONS.md` for the full brief, mandatory prior-art rule, shared phase cycle, and priority table.

Working priority near the current engine: idea 4 (evolutionary reversibility window), then idea 2 (causality under coevolving antagonist pressure).

## Phase-1 problem boundaries (landed)

Near-engine track:

- [`IDEA4_PHASE1_PROBLEM_BOUNDARY.md`](IDEA4_PHASE1_PROBLEM_BOUNDARY.md) — Evolutionary reversibility window (claim ceiling `phase1_problem_boundary`; runners off).
- [`IDEA2_PHASE1_PROBLEM_BOUNDARY.md`](IDEA2_PHASE1_PROBLEM_BOUNDARY.md) — Causality under coevolving antagonist pressure (claim ceiling `phase1_problem_boundary`; runners off).

Ambitious track (ideas 1, 3, 5) and medium (idea 6):

- [`IDEA1_PHASE1_PROBLEM_BOUNDARY.md`](IDEA1_PHASE1_PROBLEM_BOUNDARY.md) — Evolutionary selection of costly causal experimentation.
- [`IDEA3_PHASE1_PROBLEM_BOUNDARY.md`](IDEA3_PHASE1_PROBLEM_BOUNDARY.md) — Collective causal knowledge.
- [`IDEA5_PHASE1_PROBLEM_BOUNDARY.md`](IDEA5_PHASE1_PROBLEM_BOUNDARY.md) — Transferable symbolic laws.
- [`IDEA6_PHASE1_PROBLEM_BOUNDARY.md`](IDEA6_PHASE1_PROBLEM_BOUNDARY.md) — Adaptive epistemic restraint.

## Phase-2 design digests (landed; design only)

- [`IDEA4_PHASE2_DESIGN_DIGEST.md`](IDEA4_PHASE2_DESIGN_DIGEST.md) — Branching-history recovery window (claim ceiling `phase2_design`; runners off).
- [`IDEA2_PHASE2_DESIGN_DIGEST.md`](IDEA2_PHASE2_DESIGN_DIGEST.md) — Gene / pattern / causal competition under coevolving antagonist pressure (claim ceiling `phase2_design`; runners off).

All phase-1 files share claim ceiling `phase1_problem_boundary`. Phase-2 digests share claim ceiling `phase2_design`. Runners and campaigns remain off until explicitly authorised.

## Phase-2 harness (implementation under sealed digests; smoke only)

Claim ceiling for harness code and these notes: `phase2_harness`. This is implementation under the sealed digests — not a discovery claim and not a “first” claim.

Harness modules:

- `src/codontrace/life_loop/contact_atp_ledger.py` — mutable contact/ATP ledger and generation-boundary ops (Idea4 + Idea2).
- `src/codontrace/life_loop/discovery_boundary_hooks.py` — `GenerationBoundaryObserver` wiring for scheduled ledger interventions.
- `src/codontrace/genesis/campaigns/discovery_q_20260928_idea4.py` — Idea4 constants + `run_idea4_smoke`.
- `src/codontrace/genesis/campaigns/discovery_q_20260928_idea2.py` — Idea2 constants + `run_idea2_smoke`.

Tests: `tests/campaigns/discovery_questions_20260928/` (distinction locks + harness smoke).

**Runners stay off** until the owner explicitly allows full campaigns. Harness smoke and unit tests only; do not treat smoke packs as authorisation for JSONL campaigns. Full campaigns preferably need ≥6 cores when allowed. Sealed seeds `801–816` remain untouched. `red_queen_proved` stays false.
