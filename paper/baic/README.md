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

The Genesis engine does not know medicine. Biomedical labels are a
`DomainProfile` port (`codontrace.claimgate.domain`). See
[`docs/ARCHITECTURE_PORTS.md`](../../docs/ARCHITECTURE_PORTS.md) and
[`docs/BIOMEDICAL_ENGINEERING.md`](../../docs/BIOMEDICAL_ENGINEERING.md).

## Status versus this git tree

Checked against `main` at the commit that added this directory:

- `docs/hard_experiment_01/results_v7.json` **is** present.
- `09_results/ladder_validation.json` is **not** in the tree. The nine-pack
  auditor numbers in the manuscript are a reported internal sanity check,
  not a committed artifact.
- Branch `fix/small-sample-ci-coverage` **does not exist**.
- Default `exact_sign_flip_permutation_p` is still exhaustive for n≤20 and
  Monte Carlo for n>20, so published HE01 p-values are not silently recut.
- `sign_flip_permutation_detail` reports the method and a censored floor.
  `meet_in_the_middle_sign_flip_p` is exact for n≤40 and is **opt-in**.
- Studentized bootstrap CI is **opt-in** (`method="studentized"`). Default
  `bootstrap_ci_paired` stays BCa so published campaign pins stay.
- Meet-in-the-middle uses a relative float match so all-positive paired
  deltas still count as 2/2^n. It remains opt-in; HE01 `results_v7.json`
  is not recut.
- JOSS Flageat DOI is `10.1109/TEVC.2025.3548438` (IEEE TEVC 30(1):286–295).

Do not strengthen this manuscript with fabricated clinical data.
