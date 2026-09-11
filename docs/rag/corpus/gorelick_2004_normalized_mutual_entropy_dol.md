# Normalized mutual entropy in biology: quantifying diversity and division of labor

**CodonTrace Genesis literature digest** (not a substitute for the paper).

- **id:** `gorelick_2004_normalized_mutual_entropy_dol`
- **authors:** Ron Gorelick, Susan M. Bertram, Peter R. Killeen, Jennifer H. Fewell
- **year:** 2004
- **venue:** Integrative and Comparative Biology 44:345-352
- **identifiers:** doi:10.1093/icb/44.5.345
- **tags:** Gorelick, normalized mutual information, division of labor, DoL statistic, 2004, Goldsby, collective intelligence, evidence
- **claim ceiling:** `runtime_observation`

## Digest

Gorelick, Bertram, Killeen, and Fewell (Integrative and Comparative Biology 2004, doi:10.1093/icb/44.5.345) treat normalized mutual information / mutual entropy between individuals and tasks as a general DoL statistic. Goldsby et al. PNAS 2012 used this family of measures. A single snapshot where each organism appears once inflates mutual information; a lifetime of task choices is required so generalists (mixed tasks) score lower than consistent specialists. CodonTrace Genesis Phase I computes an analog on evolved two-task preferences. That analog is not bit-identical to the paper and is not a Goldsby 50-replicate result. Assigned round-robin role tags are not this statistic.

## Key claims

- DoL should be measured as information between identities and tasks, not as a role-tag count.
- Repeated observations per individual are required; one-shot unique IDs make NMI trivially 1 whenever tasks differ.
- A DoL number is not collective intelligence.

## What CodonTrace Genesis has

Phase I gorelick_normalized_mutual_information on lifetime task samples from an evolved preference gene.

## What CodonTrace Genesis lacks

Bit-identical Gorelick NMI on Avida task-export traces; 50-replicate campaigns as default evidence.

## Next experiment

Keep NMI as a measurement on evolved (not assigned) task choices; pair with ablation of specialization. Claim ceiling runtime_observation.

Retrieving this digest is not `collective_intelligence` or intelligence evidence.
