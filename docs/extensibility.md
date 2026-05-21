# Extensibility

CodonTrace now provides configurable GENESIS research primitives through explicit Registry, Config, Spec, and Protocol objects.

The built-in GENESIS v0 defaults remain available, but researchers can define:

- custom elements and element properties through `ElementRegistry`;
- custom substrate rules through `SubstrateRuleConfig`;
- custom substrate physics settings through `SubstratePhysicsConfig`;
- custom genome alphabet and codon width through `GenomeSpec`;
- custom codon tables through `CodonTableSpec`;
- custom schedulers through `SchedulerProtocol`;
- custom topologies through `TopologyProtocol`;
- custom fitness signals through `FitnessSignalRegistry`;
- custom action statuses through `ActionStatusRegistry`.

This does not make CodonTrace an app, plugin framework, or configuration-file framework. Core APIs accept Python objects and remain dependency-free.

## GENESIS object-based extension example

```python
from codontrace import ElementRegistry, GenomeSpec, SemanticGenome

registry = ElementRegistry.genesis_v0().define(
    symbol="Pl",
    name="Plasma",
    origin="emergent",
    layer="energy",
    properties={"energy_density": 3.5, "volatility": 0.9},
)

genome = SemanticGenome.from_codons(("ACG", "TTA"), spec=GenomeSpec.dna3())
```

## Scope boundaries

The extensibility foundation intentionally does not add:

- automatic config file loading in core;
- UI/dashboard behavior;
- CLI config runners;
- external simulation framework dependencies;
- unrestricted dynamic code execution;
- plugin discovery through entry points for GENESIS registries/configs;
- claims that custom rules validate open-ended discovery.

## Existing custom action support

`ActionRegistry` and `EnergyEffect` remain available for custom actions. Existing action plugin discovery is preserved for backward compatibility, but the GENESIS extensibility foundation above is object-based and does not require or introduce plugin discovery.

```python
from codontrace import Codon, CodonTable
from codontrace.actions import ActionContext, ActionResult, EnergyEffect, default_action_registry


def charge(ctx: ActionContext) -> ActionResult:
    return ActionResult.executed(
        reason="charged",
        position_after=ctx.position,
        world_delta={"charged": True},
        energy=EnergyEffect(credit=1.0, reason="charge_action"),
    )


table = CodonTable.default_minimal().replace(Codon("001", "CHARGE", 0.0))
registry = default_action_registry().extend("CHARGE", charge)
```

Handlers do not receive `ATPAccount`. The agent core applies credits/debits and records ledger entry ids in `TraceEvent.ledger_entry_ids`.

## World objects

`WorldObject` is metadata for domain-specific entities such as food, hazards, beacons, nests, or lights. It does not implement hidden physics or rewards.


## D0 / Discovery Witness / QD Hooks

CodonTrace now provides dependency-free library objects for D0 baseline calibration, distance-to-D0 measurement, conservative DiscoveryCandidate records, DiscoveryWitness evidence scaffolds, Quality-Diversity archive hardening, and ablation/statistical protocol records. These APIs are Python-object based, serializable, digestible, and designed for audit. They do not force positive claims or hide controls. Current Integration smoke/examples can write deterministic evidence bundles and validation summaries, while strong discovery/OEE claims still require configured baselines, controls, multi-seed evidence, and ClaimGate approval. Witness status is evidence infrastructure only and requires baseline, replay/trace, ablation coverage, and configurable multi-seed metadata before reaching evidence-supported scaffold status.


## v0.3.0a1 Release Candidate Hardening + Scientific Evidence Pack

CodonTrace v0.3.0a1 focuses on API hardening, validation objects, compatibility snapshots, example-smoke contracts, research-validation bundle records, and claim-audit scaffolds. These are dependency-free Python object APIs only. They do not add an app, UI, dashboard, CLI, report writer, notebook generator, experiment runner, file writer, p-value engine, or external dependency. The validation pack helps researchers audit reproducibility and claim safety, but it does not prove general-intelligence, artificial life, open-ended discovery, causal-certainty claim, knowledge transfer, or benchmark-rank claim.
