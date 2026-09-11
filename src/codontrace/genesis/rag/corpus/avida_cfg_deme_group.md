# avida.cfg DEME_GROUP / GermlineReplication (wiki Deme-introduction)

**CodonTrace Genesis literature digest** (not a substitute for avida.cfg).

- **id:** `avida_cfg_deme_group`
- **authors:** Charles Ofria, David M. Bryson, Avida developers; Goldsby / GECCO 2008 germline line
- **year:** 2008
- **venue:** avida.cfg DEME_GROUP; devosoft/avida wiki Deme-introduction; GermlineReplication / GECCO 2008
- **identifiers:** https://github.com/devosoft/avida/wiki/Deme-introduction ; avida.cfg DEMES_GROUP_REPLICATE / GERMLINE
- **tags:** Avida, DEME_GROUP, DEMES_GROUP_REPLICATE, GERMLINE, GermlineReplication, deme, wiki, multilevel selection, collective intelligence, evidence
- **claim ceiling:** `runtime_observation`

## Digest

The devosoft/avida wiki Deme-introduction and avida.cfg DEME_GROUP family describe demes as spatially bounded subpopulations that can compete as groups. Typical knobs include DEMES_ENABLED / NUM_DEMES, DEMES_GROUP_REPLICATE (copy a deme when a group criterion is met), DEMES_USE_GERMLINE / GERMLINE (export a germline or propagule rather than the whole soma), DEMES_REPLICATE_CPU_CYCLES / DEMES_MAX_AGE, and DEMES_DIVIDE_METHOD (how the target deme is overwritten). That is multilevel selection as an experiment: which group occupies space next, not a rank table of mean fitness. GECCO 2008 digital germlines and later Goldsby dirty-work work treat soma vs germline eligibility as something evolution can discover. CodonTrace Genesis Phase E DemeConfig.replicate_on_mean_fitness plus maybe_replicate_demes records an extra target deme and an optional germline copy. Phase L wires that hook from the ORGANISM_MESSAGING analog and records extra_target_deme_preserved. It is still an analog, not Avida C++ deme hardware, and not MLS2 at literature scale. Retrieving this digest is not collective intelligence.

## Key claims

- DEME_GROUP replication is group-level replacement, not observational ranking.
- GERMLINE / GermlineReplication exports a propagule; assigned RoleKind tags are not that result.
- Extra target-deme preservation after refresh is bookkeeping unless selection changes lineage outcome.
- An analog hook is not avida.cfg.

## What CodonTrace Genesis has

Phase E DemeConfig / DemeReplicationEvent; Phase F/H group-vs-individual campaigns; Phase L optional maybe_replicate_demes from the messaging analog with extra_target_deme_preserved.

## What CodonTrace Genesis lacks

Avida C++ DEME_GROUP hardware; spatial deme occupancy; evolved germline networks; literature-scale MLS2.

## Next experiment

How to get collective intelligence evidence: keep Phase L DEME_GROUP events as measurement; do not set multilevel_selection_experiment beyond analog bookkeeping; ClaimGate stays blocked for collective_intelligence.

Retrieving this digest is not `collective_intelligence` or intelligence evidence.
