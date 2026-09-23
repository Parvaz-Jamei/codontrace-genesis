# JOSS submit pack

Do **not** submit before **22 November 2026**.
The public repository was created `2026-05-22`. JOSS asks for more than six months of public development.

Paper files (ready now):

- [`paper/paper.md`](paper.md)
- [`paper/paper.bib`](paper.bib)

The BAIC 2026 Persian manuscript is **not** in this repository. It is held
outside the public tree while the congress reviews it, and `paper/baic/` is
listed in `.gitignore`. The evidence it cites stays in the repository:
`docs/claimgate/biomedical_study.json`, `docs/claimgate/defect_grid.json`,
`docs/claimgate/risk_bar.json`, and `docs/hard_experiment_01/results_v7.json`.

Submit URL when the date has passed and CI on `main` is green:

https://joss.theoj.org/papers/new

## Form values

| Field | Value |
|---|---|
| Software repository | `https://github.com/Parvaz-Jamei/codontrace-genesis` |
| Paper file | `paper/paper.md` |
| Suggested citation | CodonTrace Genesis |
| Version at submit | the then-current public PyPI / GitHub tag, not a forgotten beta |
| Software license | AGPL-3.0-or-later |
| Author | Parvaz Jamei |
| ORCID | `0009-0002-9980-270X` |
| Affiliation | Independent researcher |
| Archive DOI | `10.5281/zenodo.20337435` (refresh Zenodo if a newer tag exists) |

## Honest claims only

- Software paper, not a research-results paper.
- Avida / MABE2 adapters are skeletons.
- Biomedical ClaimGate is a `DomainProfile` port (COU / risk labels). Not SaMD,
  not FDA/CE, not ASME V&V 40 certification.
- Default sign-flip p is exhaustive only for n≤20; Monte Carlo otherwise.
  Meet-in-the-middle is opt-in and must not recut HE01 pins.
- Default paired CI is BCa. Studentized percentile-t is opt-in.
- Not an Avida replacement, not AGI, not collective intelligence.
- HE02 ceiling remains `runtime_observation` unless later evidence earns more.

## Before you click submit

1. CI green on the exact `main` tip you will name.
2. `paper.md` still matches the running software.
3. ORCID Works still lists the Zenodo DOI.
4. Do not use AI in editor/reviewer email.
