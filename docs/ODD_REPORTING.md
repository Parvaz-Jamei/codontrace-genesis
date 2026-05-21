# ODD Reporting

CodonTrace supports ODD-style reports for agent-based modeling review. ODD helps reviewers understand the model without reading all implementation files.

## Sections

A `GenesisODDReport` should include:

- Purpose
- Entities
- State variables
- Scales
- Process overview and scheduling
- Design concepts
- Initialization
- Input data
- Submodels
- Assumptions
- Limitations
- Claim level

## Mapping to CodonTrace

Entities include organisms, population state, World2D/ElementGrid bridge, capsules/Nexus, EventGraph, memory, and QD archive. State variables include genome, ATP runtime/learning, memory digest, event graph digest, position, fitness breakdown, behavior descriptor, and translation profile digest.

## Claim boundary

ODD reports document a model. They do not validate artificial life, causal intelligence, or full GENESIS claims. ClaimGate remains the authority for allowed claim labels.

## Artifacts

ODD report digests can be linked to manifest and evidence bundles for review.
