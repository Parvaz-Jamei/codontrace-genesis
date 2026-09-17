# Agent wave completion status (2026-09-17)

Product: CodonTrace Genesis `0.3.0b4`. Not a PyPI bump.

## Requested vs shipped

| Request | Shipped? | Note |
|---|---|---|
| Advisor review of the repo | yes | technical, no sympathy |
| Scientific-value judgment | yes | methods > results |
| Avida comparison | yes | not a replacement |
| Score table after updates | yes | in conversation |
| Merge / polish HE02 analysis | yes | PR #38 merged |
| GitHub Release tag | no | create-release API not available |
| PyPI release | no | analysis patch is not a version cut |
| HE02 analysis bugfix | **partial** | helper + locks shipped; runner source on `main` still has the two-arg call |
| HE03 research `results_v1` | no | prereg/docs only; no fabricated campaign |
| Full lint/mypy cleanup | no | pre-existing backlog |
| Strategy-doc QD/ESP32 research | no | wire exists; not a scientific campaign |
| «10/10 whole platform» | no | false target |

## What is executable now

```bash
python -m codontrace.genesis.he02_contrasts
```

Locks:

- `tests/test_he02_analysis_v1b_lock.py`
- `tests/test_he02_decision_rule_v1b.py`
- `tests/test_he02_decision_rule_logic.py`

ClaimGate ceiling for committed HE02 rows: `runtime_observation`.
Reason: `information_control_not_separated`.

## Remaining source defect

`src/codontrace/genesis/hard_experiment_02.py` still contains
`paired_effect_size(lefts, rights)`.
Do not read `dz` out of `docs/hard_experiment_02/results_v1.json`.
Use `he02_contrasts.analyze_committed_research`.
