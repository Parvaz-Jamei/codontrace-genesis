# Library-as-Tool digest and capsule policy notes

This note is intentionally narrow: it documents engine/library semantics without
turning GENESIS into a runner, benchmark app, or success-forcer.

## Engine digest audit

`result.engine_digest_audit` is an internal deterministic-field audit. It reports
whether digest-critical fields known to the library are process-independent and
free from runtime object identity, unsorted container iteration, or wall-clock
state. It does **not** spawn a second Python process during normal engine runs.

Cross-process stability is a test-suite/release-check responsibility. The
regression test `test_engine_native_digests_are_cross_process_stable` executes a
separate Python process and explicitly passes the source checkout `src` path via
`PYTHONPATH`, so the test works both after editable installation and directly
from a portable source checkout.

## Provisional capsule source fitness

Capsule `source_fitness_status` has an evidence-strength ordering:

```text
measured > last_known > provisional > unavailable
```

`unavailable` is never treated as numeric zero for threshold checks.
`provisional` is accepted by default for backward compatibility and exploratory
runs, but strict policies can set:

```python
CapsuleTransferConfig(accept_provisional_source_fitness=False)
```

When strict mode rejects a provisional source fitness record, adoption is blocked
with `source_fitness_provisional_not_accepted`. This keeps capsule communication
utility-measurable without hard-coding capsules as good or bad.
