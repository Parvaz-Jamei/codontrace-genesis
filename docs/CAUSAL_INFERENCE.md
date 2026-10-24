# Causal inference layer (`codontrace.causal_inference`)

This package adds graphical identification on top of the engine's evidence
scaffold (`genesis/causal_graph.py`) and its interventional reruns
(`genesis/intervention.py`). The engine never imports it; the layer contract
in `tests/characterization/test_import_direction.py` lists it under `MODULES`.

## Sections

| Module | What it does |
|---|---|
| `graph.py` | ADMG (directed + bidirected edges), `An`, `De`, `G[S]`, `G_{\bar X}`, `G_{\underline X}`, C-components, latent projection |
| `separation.py` | d-separation (linear-time reachability search), m-separation via explicit latents |
| `adjustment.py` | back-door and front-door criteria, exhaustive minimal-set search |
| `expressions.py` | `P(A|B)`, sums, products, fractions; exact evaluation on a discrete joint |
| `identification.py` | ID (sound and complete, returns a hedge on failure) and IDC |
| `scm.py` | random discrete SCMs (parameters from `RNGManager`), exact observational and truncated-factorisation interventional joints |

Each section imports only the ones above it, so a failure can be debugged
one module at a time.

## Build vs. dependency

Checked on 2026-10-21 (PyPI JSON API):

* `y0` 0.2.11, BSD-3-Clause, Python >=3.10. Pulls networkx, sympy-like DSL
  machinery and more; would add several runtime dependencies to a package
  that today has `dependencies = []`.
* `dowhy` 0.14, MIT, `requires_python <3.14,>=3.9`. Genesis supports 3.11 to
  3.14, so DoWhy cannot be a dependency on 3.14.

The engine has no runtime dependencies and must stay installable everywhere it
runs today, so the algorithms are implemented here (about 500 lines, pure
Python). `y0` is used only as an *optional test oracle*: when it is installed,
`tests/causal_inference/test_identification.py` checks that our
identifiability verdicts agree with y0's on random ADMGs and on every
textbook graph; when it is not, those tests are skipped. y0 0.2.11 has one
known defect that the oracle works around (nodes left without a directed edge
by `remove_in_edges` crash `ancestors`), see the test comment.

## How it is tested

* d-separation is compared with brute-force enumeration of every simple path
  on 300 Hypothesis-generated ADMGs.
* ID soundness: on random ADMGs and textbook graphs (front door, back door,
  three confounders with a mediator, the napkin graph), the identified expression is
  evaluated on the exact observational joint of a random SCM and must equal
  the exact interventional distribution to 1e-9.
* ID completeness: non-identifiable textbook graphs (bow arc, confounded
  mediator) raise `NotIdentifiable` with a valid hedge,
  every DAG query is identifiable, and verdicts agree with y0.
* Back-door and front-door adjustment formulas
  are checked numerically whenever the criteria accept a set.
