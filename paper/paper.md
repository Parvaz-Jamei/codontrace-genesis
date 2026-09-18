---
title: 'CodonTrace Genesis: A Deterministic Evidence-Auditing Framework for Digital Evolution Experiments'
tags:
  - Python
  - artificial life
  - digital evolution
  - evolutionary computation
  - reproducibility
  - quality-diversity
authors:
  - given-names: Parvaz
    surname: Jamei
    corresponding: true
    affiliation: 1
affiliations:
  - name: Independent researcher
    index: 1
date: 18 September 2026
bibliography: paper.bib
---

# Summary

Digital-evolution platforms let researchers study evolutionary and ecological
processes by running populations of self-replicating digital organisms inside
a virtual world. CodonTrace Genesis is a Python library in this tradition.
It combines a lightweight organism, genome, and world engine; a
capsule-mediated information-transfer mechanism for studying social and
signaling behaviour; and an independent evidence-auditing layer, ClaimGate,
that grades experiment output on a six-level scale (0-5) before a scientific
claim is allowed to be stated. ClaimGate is simulator-agnostic. Besides a
native adapter, it ships early Avida and MABE2 adapters that translate run
directories into a common evidence bundle. The Avida adapter reads named
`.dat` columns (preferring `ave_fitness` over the `update` clock) and
aggregates folders that share a user-supplied ClaimGate role. It remains a
skeleton: it is not an `avida.cfg` interpreter and does not claim Avida
replacement. The package also includes a dependency-free statistical protocol
(paired effect sizes, bootstrap confidence intervals, exact sign-flip
permutation tests, Holm correction) and a deterministic digest and replay
system so that every recorded claim can be traced to the configuration, seed
set, and code version that produced it.

# Statement of need

Digital-evolution and artificial-life research has a well-documented
reproducibility problem: informal or missing negative controls, undocumented
seed sensitivity, and claims that outrun the statistical evidence behind them
are common failure modes. Recent work has shown that even established
quality-diversity algorithms in the MAP-Elites family
[@mouretclune2015mapelites] exhibit a measurable
performance-reproducibility trade-off [@flageat2026reproducibility].
Established platforms such as Avida [@ofria2004avida], MABE
[@bohm2017mabe], DEAP [@fortin2012deap], QDax [@chalumeau2024qdax], and
pyribs [@tjanaka2023pyribs] provide strong simulation and search
capability, but none of them ships a built-in, simulator-independent
mechanism for grading how much evidence a given result actually has, or for
enforcing pre-registration and negative controls before a claim is recorded.
CodonTrace Genesis is aimed at researchers, students, and open-source
contributors in ALife and evolutionary computation who want an experiment's
evidentiary status to be explicit and machine-checkable, and at reviewers who
need a tool-agnostic way to audit a digital-evolution result without
re-deriving the statistics by hand.

# State of the field

CodonTrace Genesis does not aim to replace Avida, MABE, DEAP, QDax, or
pyribs as a simulation or search engine. Each of those tools is more mature
and, in Avida's case, has decades of published use [@ofria2004avida]. Nor
does it duplicate open-endedness search frameworks such as ASAL
[@kumar2024asal] or OMNI-EPIC [@faldor2024omniepic], which use foundation
models to discover interesting simulations but do not apply a formal
evidence-grading step to what they discover. The gap this package fills is
orthogonal: a claim ladder and audit layer that can sit on native, Avida, or
MABE2 output and refuse to let a claim exceed what its pre-registration,
controls, and replay evidence support.

# Software design

The package is organised around three layers. The simulation core (genome,
organism, world, capsule-mediated signalling, and an optional multi-stage
toolchain task) is written in dependency-free Python and produces a
deterministic, content-addressed digest for every run. The statistical and
audit layer (`claimgate/`) is a separate package with zero imports from the
simulation core, enforced by an automated boundary check. It defines the
six-level claim ladder, a schema for evidence bundles, and adapters that
translate native, Avida, and MABE2 artifacts into that schema. Keeping the
auditor off the engine is a deliberate trade-off: it prevents a passing
simulation from silently promoting a scientific claim, at the cost of
requiring an explicit adapter for each external format. One shipped example
experiment tests a task-switching-cost hypothesis in the tradition of
division-of-labor studies in digital evolution [@goldsby2012division]. The
open-ended discovery layer adds a quality-diversity search loop with three
explicit negative controls (a random proposer, a shuffled-archive proposer,
and a no-op archive) so that a discovered behaviour is retained only after it
beats chance and not merely the existence of a channel. An optional
hardware-agnostic bridge can send a handful of evolved genomes to small
physical robots as a low-volume reality check, following the transferability
approach of Koos et al. [@koos2013transferability]. The project uses
`pytest` for testing, `ruff` and `mypy` for static checks, and a
ports-and-adapters architecture for evidence adapters.

# Research impact statement

CodonTrace Genesis is intended as infrastructure rather than as a vehicle
for a single scientific finding. Near-term scholarly signals are a versioned
PyPI package (`codontrace`), a Zenodo archive
(DOI `10.5281/zenodo.20337435`), continuous integration across Python
3.11-3.14, and a written Claim Ladder Protocol in the style of reporting
standards such as ODD [@grimm2020odd] and the machine-learning
reproducibility checklist of Pineau et al. [@pineau2021reproducibility].
The protocol is meant for independent use by other digital-evolution
researchers regardless of simulator. Worked examples shipped with the
package (a capsule-signalling experiment and a task-switching-cost
experiment) demonstrate the audit workflow end-to-end, including cases
where a pre-registered comparison did not reach significance. They are
illustrations of how to use the software, not research findings of this
paper. The public claim ceiling stays at runtime observation until stronger
evidence is actually earned.

# AI usage disclosure

Generative AI tools were used during development. Grok (xAI; Grok 4 family,
2026) assisted with code generation, refactoring, test scaffolding,
documentation edits, and drafting of this paper. Human author Parvaz Jamei
reviewed, edited, and validated all AI-assisted code and text, and made the
core design decisions: the claim-ladder architecture, the engine/auditor
boundary, the choice of negative controls, and the scope of each experiment.
Conversational AI was not used to interact with JOSS editors or reviewers.

# Acknowledgements

No external funding was received for this work.

# References
