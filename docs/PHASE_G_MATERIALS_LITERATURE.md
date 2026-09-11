# CodonTrace Genesis Phase G materials / chemistry-effect substrate — literature checklist

CodonTrace Genesis Phase G adds an **opt-in named-materials overlay** so later experiments can
place organisms in an environment whose substances have explicit physical /
chemical *effect coefficients* (energy yield, toxicity, viscosity/diffusion,
permeability, signaling potency, scarcity). It is a software substrate with
schema hooks for a future real-substance table bind. It is **not** an Earth
chemistry simulator, a KEGG/BiGG GEM solver, or a molecular-dynamics engine.

Phase A–E pins stay stable. Defaults remain off.

## Checklist (must remain honest in docs, tests, and ClaimGate)

| Source | What Phase G implements | What Phase G does **not** claim |
|---|---|---|
| Ofria & Wilke 2004 *Artificial Life* — Avida resources/reactions/merit | Named `MaterialSpec` pools with eat/absorb → ATP and a recorded merit coefficient; simple stoichiometric reactions | Not an Avida ISA clone; not logic-9 task–resource coupling; not biological metabolism |
| Avida-ED resource modes; BMC Evol Biol 2021 metabolic signaling; ASMI 2022 nutrient→intracellular profiles | Chemostat-named materials; intracellular inventory; nutrient→ATP mapping | Not a measured intracellular metabolome; not wet-lab signaling |
| Novick & Szilard 1950 chemostat; Phase C `RESOURCE` inflow/outflow | Same unused-outflow-then-inflow update, now per named `MaterialSpec` | Not a laboratory chemostat; not proved microbial physiology |
| Combinatory Chemistry; npj Complexity 2025 spatial ACE; Evolvable Chemotons arXiv 2510.14282 | Optional 2–3 material autocatalytic cycle (`A + B → 2A`) plus spatial-coexistence *measurement* | Not evolved chemotons; not a spatial ACE proof |
| Coevolution of cellularity and metabolism | Membrane permeability (cellularity knob) gates uptake of nutrients and toxins | Not evolved membranes or compartmentalization proof |
| ChEBI / KEGG / BiGG (future bind) | `external_ontology_id`, `units`, `effect_coefficients` on `MaterialSpec`; `MaterialBindingSchema` | GEM solver **deferred**; MD **deferred**; ontology ids are labels only |

## ClaimGate

- Default pack ceiling: `runtime_observation`
- Blocked: `realistic_chemistry_proved`, `wet_lab_equivalent`,
  `kegg_solver_equivalent`, `bigg_gem_equivalent`,
  `molecular_dynamics_equivalent`, `earth_chemistry_simulator`,
  `biological_accuracy_proved`
- A–E forbidden aliases (intelligence, Avida-replacement, Tokyo Type 1 passed)
  remain blocked

See also [`SCIENTIFIC_AUTHORITIES_2026.md`](SCIENTIFIC_AUTHORITIES_2026.md).

## API entry points

```python
from codontrace.genesis import (
    GenesisEngine,
    GenesisRuntimeProfile,
    build_materials_evidence_pack,
    evaluate_materials_claim,
    verify_materials_trajectory_replay,
    materials_snapshots_from_generation_results,
)

spec = GenesisRuntimeProfile.materials_world(seed=7, tick_count=8, population=6)
result = GenesisEngine.from_spec(spec).run_ticks()
pack = build_materials_evidence_pack(result)
print(pack.digest)
print(evaluate_materials_claim(pack).final_claim)

cycle = GenesisRuntimeProfile.materials_world(
    seed=7, tick_count=8, population=4, autocatalytic=True
)
```

`life_loop_world(materials=MaterialsConfig.research_defaults())` is the same
opt-in. Print-only smoke: `examples/genesis_materials_world.py`.
