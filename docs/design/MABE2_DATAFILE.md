# MABE2 DataFile ingest (skeleton)

Coordinator literature search: 2026-09-12.

## Format

- MABE2 `DataFile` registers columns with `ADD_COLUMN(name, expr)` and
  writes with `WRITE`.
- When the filename ends in `.csv`, the file is CSV (header row, then
  values).

ClaimGate’s skeleton reads that CSV. It does not execute MABE2,
reconstruct `ADD_COLUMN` expressions, or claim full MABE2 support.

## ClaimGate role

`codontrace.claimgate.adapters.mabe2` wraps one DataFile CSV as a
bundle. Seeds and arm role are user-supplied. Complementary to Avida
`.dat` ingest; neither adapter is a platform replacement.

See [`CLAIMGATE_STANDALONE.md`](../CLAIMGATE_STANDALONE.md).
