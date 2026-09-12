# Avida `.dat` ingest (skeleton)

Coordinator literature search: 2026-09-12. Sources: avidaR and the
Avida PrintData wiki.

## Format

- Files are **whitespace-separated**.
- Column names live in comment lines of the form `# N: column name`.
- Other `#` lines are ignored.
- Each run directory is treated as **one seed**.
- Arm mapping (`treatment`, `mechanism_ablation`, `channel_off`,
  `negative_control`, `dose`) is **user-supplied**. ClaimGate cannot
  infer Avida treatments from folder names alone.

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
