# Avida `.dat` ingest (skeleton)

Coordinator literature search: 2026-09-12. Sources: avidaR and the
Avida PrintData wiki. Adapter metric fix: 2026-09-18.

## Format

- Files are **whitespace-separated**.
- Column names live in comment lines of the form `# N: column name`.
- Other `#` lines are ignored.
- Each run directory is treated as **one seed**.
- Arm mapping (`treatment`, `mechanism_ablation`, `channel_off`,
  `negative_control`, `dose`) is **user-supplied**. ClaimGate cannot
  infer Avida treatments from folder names alone.
- The primary outcome is a fitness-like column. Preference order:
  `ave_fitness`, `average_fitness`, `mean_fitness`, `fitness`.
  The leading `update` clock is never used as the outcome.
- Folders that share a ClaimGate role are **one arm**; `n` is the folder count.
  The recorded value per folder is the last row of the chosen column.

Example:

```text
# 1: update
# 2: ave_fitness
# 3: max_fitness
100 0.50 1.20
200 0.55 1.25
```

## ClaimGate role

`codontrace.claimgate.adapters.avida` parses this skeleton into a
`claimgate_bundle_v1`. It does **not** claim full Avida support, an
`avida.cfg` interpreter, NAND-CPU parity, or Avida replacement.

See [`CLAIMGATE_STANDALONE.md`](../CLAIMGATE_STANDALONE.md).
