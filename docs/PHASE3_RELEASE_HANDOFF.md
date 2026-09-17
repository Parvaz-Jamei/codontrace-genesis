# Phase 3 — release handoff (not PyPI)

Product stays `0.3.0b4` / `0.3.0b4.dev0`.
This file is **not** a GitHub Release and **not** a version bump.

Published PyPI tip remains `0.3.0b4` (`v0.3.0b4`).
Create-release / create-tag APIs are not available on this agent connection.

## Proposed annotated tag (you run this)

Tag name: `v0.3.0b4.dev0-he02-v1b`

```bash
git fetch origin
git checkout main
git pull --ff-only
git tag -a v0.3.0b4.dev0-he02-v1b -m "0.3.0b4.dev0 HE02 v1b analysis + HE03 status lock (not PyPI)"
git push origin v0.3.0b4.dev0-he02-v1b
gh release create v0.3.0b4.dev0-he02-v1b --title "0.3.0b4.dev0 — HE02 v1b + HE03 lock (not PyPI)" --notes-file docs/PHASE3_RELEASE_HANDOFF.md
```

Install from that tag after you push it:

```bash
pip install "git+https://github.com/Parvaz-Jamei/codontrace-genesis.git@v0.3.0b4.dev0-he02-v1b"
```

## What this tip contains

- HE02 v1b helper, CLI, wrapper: `run_hard_experiment_02_v1b`
- Frozen-row analysis; ClaimGate stays `runtime_observation`
- HE03 research `results_v1` still absent (locked)
- Source wire of `hard_experiment_02.py` still pending (xfail test)

## What it does not contain

- PyPI `0.3.0b5`
- raised ClaimGate
- fabricated HE03 research rows
- Avida replacement / intelligence claims
