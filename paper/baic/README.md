# BAIC 2026 manuscript (honest source)

Persian conference paper for BAIC 2026 (Ferdowsi University of Mashhad).
Author: **Parvaz Jamei / پرواز جمیعی**.

Git-tracked source of truth: [`paper.md`](paper.md). It is **not** a medical-device paper.
[`SECTIONS_5_8.md`](SECTIONS_5_8.md) is a stub pointing at that file (do not edit two copies).

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

- `docs/hard_experiment_01/results_v7.json` **is** present (internal digest prefix `28f812c5`).
- Live nine-pack grades: [`docs/claimgate/ladder_validation.json`](../../docs/claimgate/ladder_validation.json) (digest `ea0366d0`). This is **not** an external rater study and **not** a population error rate.
- `09_results/ladder_validation.json` is **not** in the tree.
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
- HE01 v7 arm-role translation lives in
  `codontrace.claimgate.adapters.he01_arm_roles` and is applied by the
  ClaimGate adapter (artifact bytes unchanged).
- JOSS Flageat DOI is `10.1109/TEVC.2025.3548438` (IEEE TEVC 30(1):286–295).

Do not strengthen this manuscript with fabricated clinical data.
