# Known issues (open, documented)

These are not hidden. They stay open on purpose until a dedicated cleanup
or a new research campaign replaces them.

## Lint / type inventory

`ruff check src tests` previously reported ~1300 findings. About 75% were
`E501` (line length at 100 columns). The rest is import order, unused
imports in tests, `StrEnum` churn, and one `F821` name in a type hint in
`engine.py` (`ChildAdmissionResult`).

`[tool.ruff.lint] ignore` now lists that inventory so `ruff check src tests`
exits 0. The `lint-type` CI job remains `continue-on-error: true` because
`mypy --strict src` is a separate backlog. Shrinking the ignore list is a
formatting PR, not a science PR.

## HE02 `results_v1.json` `dz: null`

The committed research file is the as-run artifact
(digest `45741d911facd4eae0e7f000c2fcd3873280d4b344d3266c4fab9fbe28295419`).
Three primary `paired_contrasts[].dz` values are null because
`paired_effect_size` was called on raw arm vectors and the `TypeError` was
swallowed. Seed ATP rows are valid.

Do **not** rewrite that file in place: changing `dz` changes
`HardExperiment02Campaign` digest payload and would relabel a frozen run.

Corrected numbers live in
[`docs/hard_experiment_02/analysis_v1b_contrasts.json`](hard_experiment_02/analysis_v1b_contrasts.json).
The HE02 ClaimGate adapter overlays those numbers when it sees null `dz`.
Claim ceiling stays `runtime_observation` (shuffled Holm does not survive).

## `__init__.__version__` lag

`package_version()` follows `pyproject.toml`. `codontrace.__version__` may
lag one cut until `src/codontrace/__init__.py` imports `_version`.
