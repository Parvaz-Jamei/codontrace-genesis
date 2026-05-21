# GENESIS Action Wiring Matrix

**Status:** Phase 1 strong-core artifact
**Purpose:** public, digestible audit surface for action reachability, runtime registration, world effects, preconditions, costs, and claim relevance.

GENESIS is a library for AI / digital-evolution / discovery experiments. A strong action space must be inspectable without private engine hacks. The action wiring matrix answers these questions for every action:

- Is the action registered in the public `ActionRegistry`?
- Is it reachable from a public `CodonTable`?
- Does it have a real world transition, inventory transition, energy effect, capsule effect, toolchain effect, or reproduction gate?
- Which blocked reasons are official enough for tests and evidence?
- Which claim family can use the action as evidence?

## Public API

```python
from codontrace.genesis import export_action_wiring_matrix

matrix = export_action_wiring_matrix()
for row in matrix.records:
    print(row.action_name, row.codon_reachable, row.world_effecting, row.blocked_reasons)
```

Public objects:

- `ActionWiringRecord`
- `ActionWiringMatrix`
- `export_action_wiring_matrix(...)`

The helper uses public surfaces only: `ActionRegistry.names()`, `ActionRegistry.get()`, and `CodonTable.actions()`. It does not execute a scenario and does not mutate worlds. When attached to `GenesisRunResult`, the matrix is built from the resolved codon table and action registry for that exact engine run, not from a global toolchain default.

Each row carries runtime provenance fields:

- `effect_source`: `contract`, `runtime_smoke`, or `pilot_trace`
- `runtime_validated`: whether this row has runtime delta evidence
- `runtime_validation_digest`: digest of the runtime smoke/pilot validation when available

Contract-only rows are exported as `provisional` evidence until runtime smoke or pilot trace validation upgrades them.

## Claim rules

| Evidence situation | Claim treatment |
|---|---|
| Registered + codon reachable + world-effecting | Eligible as runtime instrumentation evidence after smoke delta test |
| Registered but not codon reachable | Available primitive, not genome-reachable under that codon table |
| Codon reachable but not registered | Configuration gap; action must not be used for runtime claim |
| World-effecting by contract but no smoke delta | Not claim-ready until a runtime smoke test confirms a real transition |
| Reproduction action | Evidence belongs to reproduction gate, not forced birth |
| Capsule action | Evidence belongs to capsule signaling; utility still requires before/after and `utility_delta` |

## Scientific note

Quality-diversity and digital evolution systems need measurable variation, selection, and runtime effects. The matrix does not claim intelligence; it exposes the action substrate that later tests use to prove real effects.
