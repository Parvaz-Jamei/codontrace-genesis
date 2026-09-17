# Snapshot — HE02 analysis v1b (not PyPI)

Product: CodonTrace Genesis `0.3.0b4`.
Merged: PR #38 @ `0fc9e14` (2026-09-17).
Helper: `src/codontrace/genesis/he02_contrasts.py`.
Locks: `tests/test_he02_analysis_v1b_lock.py`, `tests/test_he02_decision_rule_v1b.py`.
Reproduce: `python -m codontrace.genesis.he02_contrasts`

## What shipped

- Frozen research ATP rows stay in `docs/hard_experiment_02/results_v1.json`.
- Corrected contrasts: `docs/hard_experiment_02/analysis_v1b_contrasts.json`.
- Write-up: `docs/hard_experiment_02/ANALYSIS_CORRECTION_v1b.md`.
- Executable analysis: `contrasts_from_seed_dicts`, `decision_from_contrasts`,
  `analyze_committed_research`.

## Honest result

Holm survives vs `content_null` / `channel_off` (dz ≈ 1.13, ΔATP = +0.53 on baseline 44).
Holm fails vs `capsules_shuffled` (dz ≈ 0.20, p_holm ≈ 0.37).
Decision rule: fail (`information_control_not_separated`).
ClaimGate ceiling: `runtime_observation`. Not `intervention_supported`.

## Still true

`run_hard_experiment_02` on `main` still contains the old two-argument call.
Patched runner is local (`hard_experiment_02_wired.py` in the agent tree) until
that 34k file is committed. Analysis of committed rows does **not** depend on it.

## Not in this snapshot

- No PyPI `0.3.0b5`.
- HE03 research `results_v1` still deferred.
- ESP32 remains an engineering stub.
- Lint/mypy backlog unchanged.
