# Engine closed-loop JSONL (Ideas 4 and 2)

**Not** the harness path under `../jsonl_campaign/` (`ecf7148` harness-only).

- Module: `src/codontrace/genesis/campaigns/discovery_q_20260928_jsonl_engine.py`
- CLI: `scripts/run_discovery_q_20260928_jsonl_engine.py`
- Engine cells: `discovery_q_20260928_idea4_engine.py`, `discovery_q_20260928_idea2_engine.py`
- Coupler: `src/codontrace/life_loop/engine_ledger_coupler.py` (`GenerationBoundaryObserver` on `GenesisEngine`)

Ledger skeleton: `build_engine_scaffold_ledger` / `build_idea2_engine_scaffold_ledger` (scaffold-only; smoke aliases are harness-only). Claim ceiling remains `phase2_design`. Every record sets `hypothesis_supported=False` and `red_queen_proved=False`. Soft-pass near 0.15 = FAIL. Volume ≠ discovery.


## Full N≥64 path

```bash
.venv/bin/python scripts/run_discovery_q_20260928_jsonl_engine.py --full --max-workers 8
```

- Default full seeds: `301–364` (64; sealed `801–816` refused). Override with `--seeds` if needed.
- Full factorial: Idea4 `OPS_CELLS` (5) × `T_INTERVENE_GRID` (≥3 on T=40); Idea2 all 4 engine cells × 3 arms.
- Expect ≈1728 records when Idea2 emits 3 arms per cell (`64×(5×3 + 4×3)`).
- Pilot (`--full` omitted) stays at 12 seeds / reduced cells; pilot tip `cb4f88d`.
- Claim ceiling remains `phase2_design`; still **not** a discovery claim.
