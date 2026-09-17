# Known issues (open, documented)

## HE02 research artifact

`docs/hard_experiment_02/results_v1.json` now stores the v1b contrast numbers
(`dz` / `p_raw` / `p_holm`). Campaign digest after the inline is
`4909c1ed7243137eee2758b6024dca184987cce28672aadb1cb2e2f0b0d96bf4`.

The as-run payload (null `dz`, swallowed TypeError) remains identified as
`45741d911facd4eae0e7f000c2fcd3873280d4b344d3266c4fab9fbe28295419` in
`analysis_v1b_contrasts.json` (`as_run_digest`). Seed ATP rows were not
regenerated. Claim ceiling stays `runtime_observation`.

## Lint / type

Most ruff findings are `E501`. `mypy --strict src` is a separate backlog.
`lint-type` stays `continue-on-error: true`.

## `__init__.__version__` lag

`package_version()` follows `pyproject.toml`. `codontrace.__version__` may
lag one cut until `src/codontrace/__init__.py` imports `_version`.
