# BAIC 2026 manuscript (camera-ready)

Persian conference paper for BAIC 2026 (Ferdowsi University of Mashhad, ۵–۷ آبان ۱۴۰۵).
Author: **Parvaz Jamei / پرواز جمیعی**.

- Source: [`paper.md`](paper.md)
- Word (قالب_مقاله, two-column RTL, B Nazanin): [`BAIC2026_Jamei_5p.docx`](BAIC2026_Jamei_5p.docx)
- Same text, upload name: [`BAIC2026_Jamei.docx`](BAIC2026_Jamei.docx)

[`SECTIONS_5_8.md`](SECTIONS_5_8.md) is a stub pointing at `paper.md` (do not edit two copies).

Biomedical labels are a `DomainProfile` port (`codontrace.claimgate.domain`). See
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
- HE01 v7 arm-role translation uses `adapters.roles.canonical_role`
  (HE01 map in `he01_arm_roles`). Artifact bytes unchanged.
- `sha256_text_file` pins adapter text artifacts and campaign prereg files
  to Git LF identity. Binary snapshots still use `read_bytes()`.
- JOSS Flageat DOI is `10.1109/TEVC.2025.3548438` (IEEE TEVC 30(1):286–295).
