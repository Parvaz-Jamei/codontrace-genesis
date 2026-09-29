# RQ-1 pack notes

## Working-tree drift during this session

The manager is the single writer for `codontrace-genesis`. While this pack was
being built the tree changed under it:

| File | sha256 at probe time | sha256 at patch-rebase time |
|---|---|---|
| `src/codontrace/genesis/host_parasite_world.py` | `88f5acf41832d8e5fb4f837d7695187d3ed3d0bec956e5bf08ae86de189027bb` | `17e3ffbd397a7e9dbea04568c07d039b9d9a872c2935aa96ee28f257309320a8` |

The change was unrelated to RQ-1 (an unused `import hashlib` was removed and the
line count moved 1448 → 1448 with a shifted import block). `PROPOSED_CHANGE.patch`
was rebased onto the **current** file after that change and re-verified:
`logs/patch_verify.txt` → `PATCH_OK` (all six hunks apply exactly, both new files
compile, and the pressure law reproduces the reference affinity and the hand
values `kappa = 1.2`, intended `1.0`, zero-affinity `0.0`, capped realised `0.5`).

The git executable is not on this session's `PATH`, so the manifest's dirty flag
is `null` with that reason. `git` could not tell us about the drift; the file
hashes did.

## What this agent did not do

* Nothing inside `codontrace-genesis` was written. Repository files were read,
  and for patch verification the hunks were applied **in memory** only
  (`verify_patch_rq1.py` reads the file and writes the patched text to a temp
  directory).
* No seed or parameter was tuned to manufacture an effect. There was no RQ-1
  effect to manufacture: the assay's input does not exist.
* The program's locked thresholds `0.20` and `−0.148` were not recomputed and
  not changed.

## How to read the pack

| File | Role |
|---|---|
| `prior_art.md` | search date, nearest work, testable difference |
| `design.md` | locked design (locked before any confirmatory seed) |
| `raw/probe_*.json` | raw precondition and instrument evidence |
| `raw/events.jsonl`, `raw/population.jsonl` | per-generation raw records with defined nulls |
| `raw/stage0_fixtures*.jsonl` | instrument fixture matrices and contrasts |
| `analysis.json` | derived from raw only |
| `effect_table.json` | effect and interval table |
| `run_manifest.json` | commit/hashes/seeds/RNG/budget/stop code/artifacts |
| `replay_rq1.py` | one replay command from the manifest |
| `decision.md` | the single decision code |
| `EXCLUSIONS.md` | every exclusion and its reason |
| `PROPOSED_CHANGE.patch` | smallest change that would unblock |
| `logs/` | raw command output (pytest, probe, analysis, patch verify) |

## Replay

```
cd docs/experiments/2026-09-29/rq1_time_shift
C:\Users\parvaz\AppData\Local\Programs\Python\Python314\python.exe replay_rq1.py --from-manifest run_manifest.json
```

Reproduces: artifact checksums, the fixture pack, and `analysis.json`'s digest.
