# Host–parasite / microbe–virus ClaimGate port (2026-09-24)

**Additive DomainProfile port.** This folder documents a **separate** opt-in
ClaimGate profile for digital host–parasite and microbe–virus coevolution
evidence — analogous to the biomedical port — **without** baking infection
physics or medicine into `engine.py`.

## What this is / is not

| Is | Is not |
|---|---|
| A ClaimGate `DomainProfile` named `host_parasite` + thin adapter | A second Genesis engine or Avida/Symbulation reimplementation |
| Fail-closed blocked claims (vaccine, phage therapy, clinical pathogen, …) | Clinical, vaccine, antiviral, or epidemic-forecast certification |
| Docs + MVP claim labeling grounded in Avida/Symbulation/phage literature | Wet-lab BSL certification or virulence optimization for humans |
| Paper-safe additive pack (pins untouched) | A change to BAIC manuscript or HE01 empirical numbers |
| Opt-in: profile registered; unlisted clinical claims stay blocked | Implied FDA clearance or ASME V&V 40 pass |

## Architecture (port, not engine)

```
engine.py / genesis ticks     → domain-agnostic (unchanged)
ClaimGate DomainProfile       → host_parasite blocked_claims + limitations
adapters/host_parasite.py     → thin wrap of bundle_from_declared_scores
docs/claimgate/host_parasite… → requirements, challenges, brainstorm, API sketch
Phase 1                      → declared intervention menu stub + hardened blocks
Phase 2                      → optional HostParasiteEnv outside engine core
Phase 3                      → intervention falsification + honesty gates
Phase 4                      → multi-seed campaign digests + ClaimGate factory
Phase 5–6                    → spatial/vertical diagnostics; factorial/prereg
```

Mirror of the biomedical pattern in `src/codontrace/claimgate/domain.py` and
`adapters/biomedical.py`: the profile labels claims; it does not change tick
semantics, grant a claim, or certify a device or therapy.

## Paper safety for BAIC / HE01

**Do not modify** (and this PR does not touch):

- `docs/hard_experiment_01/results_v7.json`
- `docs/claimgate/risk_bar.json`
- `docs/claimgate/biomedical_study.json`

Those pins remain BAIC / paper anchors. This pack is additive documentation
plus a thin registered profile. It does **not** change HE01 empirical numbers
or the BAIC manuscript.

## Sibling packs

- Biomedical applied evidence: `docs/claimgate/applied_medical_evidence_20260924/`
- ALife novel evidence: `docs/claimgate/novel_valuable_evidence_20260924/`

## How to use (opt-in)

```bash
PYTHONPATH=src python -c "
from codontrace.claimgate.adapters.host_parasite import (
    bundle_from_host_parasite_cou,
    assert_claim_allowed,
)
# clinical aliases raise ConfigurationError
"
```

See `API_SKETCH.md`, `REQUIREMENTS.md`, `EXPERT_BRAINSTORM.md` (consensus MVP),
`PHASE1_REVIEW.md`, `PHASE2_REVIEW.md`, `PHASE3_REVIEW.md`, `CITATIONS.md`, and `README_FA.md`.

## Honest limits

- Infection / transmission physics are **not** implemented.
- A ClaimGate grade is a **claim ceiling**, not wet-lab or clinical validity.
- FDA 2023 CM&S / ASME V&V 40 language may appear only as **declared COU risk
  labels**, same stance as the biomedical port — not clearance.
- Untracked junk under `src/codontrace/genesis/population/` is out of scope
  and must not be committed with this work.
