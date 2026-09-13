# ILW-6 — Exploratory phylogeny + MODES-style probes

**Status:** Exploratory only.  
**ClaimGate ceiling:** `runtime_observation` (unchanged).  
**Scientific name:** `integrated eco-evolutionary runtime`  
**Schema:** `ilw6_exploratory_v1`

## What this milestone is

ILW-6 adds **measurement hooks**, not science claims:

1. **Organism phylogeny** from ILW lineage records (parent/child, generation, genome digests).
2. **Capsule genealogy** from experience→capsule chains (`capsule_parent_id`, provenance).
3. **Joinable view** between the two trees on shared keys (`lineage_id`, `organism_id` / `source_id`) — trees stay separate.
4. **MODES-style** change / novelty / complexity / ecological-potential series with a simple persistence window (Dolson et al. 2019 inspired; **not** a C++ MODES port).
5. **Learnability probe** — descriptive capsule→policy→subsequent-action coupling surface only.

## Explicit exploratory ceiling

| Allowed | Forbidden |
|---------|-----------|
| Digests + export of phylogeny / genealogy / probes | ClaimGate ladder promotion |
| Empty `claim_promotions: []` | CCE / Mesoudi & Thornton claim |
| `exploratory_only: true` | intelligence / AGI / collective intelligence |
| Honest limitations list | `modes_passed` / OEE pass / Tokyo Type 1 pass |
| Join rows for instrumentation | Treating novelty numbers as creativity / intelligence |

Mesoudi & Thornton’s four CCE criteria remain catalogued and **unpassed**. Learnability ratios are correlation surfaces, not causal CCE proof.

## Code map

| Path | Role |
|------|------|
| `src/codontrace/genesis/ilw/exploratory.py` | Phylogeny, genealogy, join, MODES-style + learnability probes, export |
| `tests/test_ilw6_exploratory.py` | Digests/export + empty promotions |
| `docs/ILW6_EXPLORATORY.md` | This ceiling note |

## How to run (smoke)

```python
from codontrace.genesis.ilw.exploratory import run_ilw6_exploratory_smoke

report = run_ilw6_exploratory_smoke()
payload = report.export()
assert payload["claim_promotions"] == []
assert payload["exploratory_only"] is True
assert payload["cce_claimed"] is False
```

## References

- MODES Toolbox: https://doi.org/10.1162/artl_a_00280
- Phylotrack: https://doi.org/10.48550/arXiv.2405.09389
- Cumulative cultural evolution (not claimed): https://doi.org/10.1098/rspb.2018.0712
