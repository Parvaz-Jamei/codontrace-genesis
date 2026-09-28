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
- [`IDEA1_PHASE2_DESIGN_DIGEST.md`](IDEA1_PHASE2_DESIGN_DIGEST.md) — Costly causal experimentation vs reactive learning (claim ceiling `phase2_design`; runners off).
- [`IDEA1_PHASE2_PRIOR_ART_20260928.md`](IDEA1_PHASE2_PRIOR_ART_20260928.md) — Idea 1 live prior-art support (not a discovery claim).
- [`IDEA3_PHASE2_DESIGN_DIGEST.md`](IDEA3_PHASE2_DESIGN_DIGEST.md) — Collective causal knowledge (claim ceiling `phase2_design`; runners off).
- [`IDEA3_PHASE2_PRIOR_ART_20260928.md`](IDEA3_PHASE2_PRIOR_ART_20260928.md) — Idea 3 live prior-art support (not a discovery claim).
- [`IDEA5_PHASE2_DESIGN_DIGEST.md`](IDEA5_PHASE2_DESIGN_DIGEST.md) — Transferable short composable falsifiable causal symbolic laws (claim ceiling `phase2_design`; runners off).
- [`IDEA5_PHASE2_PRIOR_ART_20260928.md`](IDEA5_PHASE2_PRIOR_ART_20260928.md) — Idea 5 live prior-art support (not a discovery claim).
- [`IDEA6_PHASE2_DESIGN_DIGEST.md`](IDEA6_PHASE2_DESIGN_DIGEST.md) — Adaptive epistemic restraint (claim ceiling `phase2_design`; runners off).
- [`IDEA6_PHASE2_PRIOR_ART_20260928.md`](IDEA6_PHASE2_PRIOR_ART_20260928.md) — Idea 6 live prior-art support (not a discovery claim).

All phase-1 files share claim ceiling `phase1_problem_boundary`. Phase-2 digests share claim ceiling `phase2_design`. Runners and campaigns remain off until explicitly authorised.

## Phase-2 harness (implementation under sealed digests; smoke only)

Claim ceiling remains `phase2_design` (no elevation above the sealed digests). Harness code is implementation under those digests — not a discovery claim and not a “first” claim.

Harness modules:

- `src/codontrace/life_loop/contact_atp_ledger.py` — mutable contact/ATP ledger and generation-boundary ops (Idea4 + Idea2).
- `src/codontrace/life_loop/discovery_boundary_hooks.py` — `GenerationBoundaryObserver` wiring for scheduled ledger interventions.
- `src/codontrace/genesis/campaigns/discovery_q_20260928_idea4.py` — Idea4 constants + `run_idea4_smoke`.
- `src/codontrace/genesis/campaigns/discovery_q_20260928_idea2.py` — Idea2 constants + `run_idea2_smoke`.

Tests: `tests/campaigns/discovery_questions_20260928/` (distinction locks + harness smoke).

Test-gate honesty note: [`PHASE2_HARNESS_TEST_GATE.md`](PHASE2_HARNESS_TEST_GATE.md) — engineering pass on `ab8e5d6`; smoke is not Idea-4 window evidence and not Idea-2 G2/M2 evidence; claim ceiling remains `phase2_design`.

**Runners stay off** until the owner explicitly allows full campaigns. Harness smoke and unit tests only; do not treat smoke packs as authorisation for JSONL campaigns. Full campaigns preferably need ≥6 cores when allowed. Sealed seeds `801–816` remain untouched. `red_queen_proved` stays false.

## JSONL smoke path (honest wiring dump; not a campaign)

A thin multi-seed writer exists for the sealed Idea 4 + Idea 2 phase-2 harness:

- Module: `src/codontrace/genesis/campaigns/discovery_q_20260928_jsonl_smoke.py`
- CLI: `scripts/run_discovery_q_20260928_jsonl_smoke.py`
- Output: `outputs/campaigns/discovery_questions_20260928/jsonl_smoke/`

Claim ceiling remains `phase2_design`. Every record sets `hypothesis_supported=False` and `red_queen_proved=False`. This path is still **not** a full campaign and still **not** measurement evidence: it is not a recovery-window result (Idea 4) and not G2/M0–M3 evidence (Idea 2). Default live smoke uses 48 non-sealed seeds (`101–148`; outside `801–816`) with up to 8 parallel workers. Track C phase-2 digests are not invented here.


## Scored JSONL campaign (meters under phase2_design; not a discovery claim)

Authorised scored multi-cell N=run path (structurally distinct from `jsonl_smoke`):

- Module: `src/codontrace/genesis/campaigns/discovery_q_20260928_jsonl_campaign.py`
- Idea4/Idea2 scored cell APIs in `discovery_q_20260928_idea4.py` / `discovery_q_20260928_idea2.py`
- CLI: `scripts/run_discovery_q_20260928_jsonl_campaign.py`
- Output: `outputs/campaigns/discovery_questions_20260928/jsonl_campaign/`

Idea4: mid-history `t_tilde` on T=40 (intervene 10/20/30); factorial cells control / scramble_contacts / cut_named_scaffold / cut_matched_random / ablate_knowledge_digest; FI recover bool; checkpoint `CKPT-RELOCATE-RECOVERY-TOKEN-V1`.

Idea2: cells baseline / pi_deception / do_ablation / sham_predphase; arms gene / pattern / causal; `survival_to_T` + `margin_vs_best_rival`; sham `SHAM-CUE-PREDPHASE-V1` ≠ NC-*.

Claim ceiling remains `phase2_design`. Every record sets `hypothesis_supported=False` and `red_queen_proved=False`. **Volume ≠ discovery.** Default seeds `201–264` (64); sealed `801–816` refused. Track C stays standby.


## Phase-2 result records (sealed; engineering only)

- [`IDEA4_PHASE2_RESULT.md`](IDEA4_PHASE2_RESULT.md) — Idea 4: harness + distinction pass; **not** a recovery-window measurement.
- [`IDEA2_PHASE2_RESULT.md`](IDEA2_PHASE2_RESULT.md) — Idea 2: harness + sham/do distinction pass; **not** G2/M0–M3 scored evidence.

Claim ceiling remains `phase2_design`. `hypothesis_supported=False`; `red_queen_proved=False`. JSONL campaigns remain off until explicitly authorised.

Post-data gate: [`PHASE2_JSONL_POSTDATA_GATE.md`](PHASE2_JSONL_POSTDATA_GATE.md) — `ecf7148` PASS as harness evidence only; FAIL discovery/window/G2 claims; WARN thin wall-time / low Idea4 seed variance / Idea2 smoke-ledger RNG.

## Engine closed-loop JSONL (pilot + N≥64 full; not a discovery claim)

Authorised engine path distinct from harness `jsonl_campaign/`:

- Coupler: `src/codontrace/life_loop/engine_ledger_coupler.py`
- Modules: `discovery_q_20260928_idea4_engine.py`, `discovery_q_20260928_idea2_engine.py`, `discovery_q_20260928_jsonl_engine.py`
- CLI: `scripts/run_discovery_q_20260928_jsonl_engine.py`
- Output: `outputs/campaigns/discovery_questions_20260928/jsonl_engine/`

`GenerationBoundaryObserver` fires on `GenesisEngine` life-loop; Idea4 FI recover has no `recovery_progress` multiplier; Idea2 pressure comes from engine ecology (not smoke-ledger RNG). Claim ceiling remains `phase2_design`.

- **Pilot** (default / tip `cb4f88d`): 12 seeds, reduced factorial — honesty note [`PHASE2_ENGINE_PILOT_GATE.md`](PHASE2_ENGINE_PILOT_GATE.md).
- **Full N≥64:** `.venv/bin/python scripts/run_discovery_q_20260928_jsonl_engine.py --full --max-workers 8` uses seeds `301–364`, full OPS_CELLS (5) × T grid (≥3) and all 4 Idea2 cells. Same honesty ceiling; volume ≠ discovery. See scale note in the pilot gate doc and `outputs/.../jsonl_engine/README.md`.
