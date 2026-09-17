# Agent wave completion status (2026-09-17)

Product: CodonTrace Genesis `0.3.0b4`. Not a PyPI bump.

## This continuation

Official live entry point after the swallowed-`dz` bug:

```python
from codontrace.genesis.he02_contrasts import run_hard_experiment_02_v1b
```

Frozen-row analysis:

```bash
python -m codontrace.genesis.he02_contrasts
```

`run_hard_experiment_02` on `main` still contains the two-argument call.
`run_hard_experiment_02_v1b` rescores that campaign before return.
ClaimGate is not raised.

## Still not shipped

- GitHub Release tag / PyPI cut
- HE03 research `results_v1`
- lint/mypy backlog
