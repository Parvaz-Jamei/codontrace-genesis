# Engine closed-loop JSONL (Ideas 4 and 2)

**Not** the harness path under `../jsonl_campaign/` (`ecf7148` harness-only).

- Module: `src/codontrace/genesis/campaigns/discovery_q_20260928_jsonl_engine.py`
- CLI: `scripts/run_discovery_q_20260928_jsonl_engine.py`
- Engine cells: `discovery_q_20260928_idea4_engine.py`, `discovery_q_20260928_idea2_engine.py`
- Coupler: `src/codontrace/life_loop/engine_ledger_coupler.py` (`GenerationBoundaryObserver` on `GenesisEngine`)

Claim ceiling remains `phase2_design`. Every record sets `hypothesis_supported=False` and `red_queen_proved=False`. Soft-pass near 0.15 = FAIL. Volume ≠ discovery.
