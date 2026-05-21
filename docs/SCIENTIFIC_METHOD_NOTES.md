# Scientific method notes for CodonTrace validation

CodonTrace uses these notes to keep research-alpha claims bounded and testable.

## Quality-Diversity / MAP-Elites

MAP-Elites is an illumination/search algorithm, not just a passive report. The researcher defines behavior descriptors; the archive keeps high-quality elites per descriptor niche; and archive contents should feed parent selection or emitters in later generations. In CodonTrace this maps to: descriptor schema -> archive bin -> elite/novelty score -> parent/offspring generation -> next evaluation.

## Open-Ended Evolution

Open-ended evolution claims need more than a novel trace. Novelty should persist across time, seeds, and lineage; diversity collapse and stagnation should be monitored; and shadow/control runs are needed to distinguish noise from repeatable change. CodonTrace therefore treats discovery and OEE outputs as candidates unless multi-seed, persistence, ablation, novelty/diversity and replay gates pass.

## Causal inference and causal discovery

Temporal precedence and event correlation are not causality. Stronger causal claims require controlled interventions, counterfactual probes, ground-truth scenarios, conditional association tests, or controlled ablations. CodonTrace's default `CausalGraph` remains a causal evidence/prediction scaffold unless `causal_validation` reports stronger evidence.

## Agent-based modeling / ODD

ODD reports should make agent-based models reproducible and reviewable by recording Overview, Design concepts and Details: purpose, entities, state variables, scales, scheduling, initialization, submodels, assumptions and limitations.

## Reproducibility and artifact review

Scientific artifacts should be documented, consistent, complete, exercisable and include verification/validation evidence. CodonTrace links claims to seeds, config hashes, manifest, replay metadata, baseline/ablation results and review status.

## Reporting and uncertainty

For research-facing claims, CodonTrace should report uncertainty, sample size limits, baselines, ablations, leakage/overclaim risks and deterministic digests. Optional heavy dependencies can improve statistics, but core must provide deterministic fallbacks.
