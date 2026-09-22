# BAIC 2026 manuscript (honest source)

Persian conference paper for BAIC 2026 (Ferdowsi University of Mashhad).
Author: **Parvaz Jamei / پرواز جمیعی**.

This file is the git-tracked source. It is **not** a medical-device paper.

| Allowed | Not allowed |
|---|---|
| Claim audit of a user-declared evidence bundle | SaMD / IVD / diagnostic tool |
| ASME V&V 40 *complement* (QOI / COU / declared risk labels) | `asme_vv40_passed`, FDA/CE clearance |
| Reporting defects found by ordinary engineering review | “the ladder discovered its own bugs automatically” |
| Toy or retrospective score tables | Clinical validity |
| Opt-in exact sign-flip (n≤40) and method reporting | Silent recut of HE01 p-values |
| Declared SiMD/SaMD / IEC 62304 / FDA 2023 cats as labels | Device certification or in-silico trial validity |

The Genesis engine does not know medicine. Biomedical labels are a
`DomainProfile` port (`codontrace.claimgate.domain`). See
[`docs/ARCHITECTURE_PORTS.md`](../../docs/ARCHITECTURE_PORTS.md) and
[`docs/BIOMEDICAL_ENGINEERING.md`](../../docs/BIOMEDICAL_ENGINEERING.md).

## Status versus this git tree

- `docs/hard_experiment_01/results_v7.json` **is** present.
- Nine-pack auditor table is now generated from the live auditor:
  [`docs/claimgate/ladder_validation.json`](../../docs/claimgate/ladder_validation.json).
  Rebuild: `PYTHONPATH=src python tools/export_ladder_validation.py`.
  The old path `09_results/ladder_validation.json` was never in the tree.
  This is still **not** an external rater study and **not** a population
  false-accept rate.
- Branch `fix/small-sample-ci-coverage` **does not exist**.
- Default `exact_sign_flip_permutation_p` is still exhaustive for n≤20 and
  Monte Carlo for n>20, so published HE01 p-values are not silently recut.
- Studentized bootstrap CI is **opt-in**. Default `bootstrap_ci_paired` stays BCa.
- Meet-in-the-middle sign-flip is **opt-in**.

Do not strengthen this manuscript with fabricated clinical data.
