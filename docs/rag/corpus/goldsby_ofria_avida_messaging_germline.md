# Avida messaging, GermlineReplication, and digital germlines (Goldsby/Ofria line)

**CodonTrace Genesis literature digest** (not a substitute for the paper).

- **id:** `goldsby_ofria_avida_messaging_germline`
- **authors:** Heather J. Goldsby, Charles Ofria, David B. Knoester, Benjamin Kerr, Anna Dornhaus
- **year:** 2014
- **venue:** Avida ORGANISM_MESSAGING / DEME_GROUP / GECCO 2008 germlines; PLOS Biology dirty-work soma (2014)
- **identifiers:** doi:10.1371/journal.pbio.1001858
- **tags:** Goldsby, Ofria, Avida, messaging, send_message, retrieve_message, broadcast_message, block_propagation, GermlineReplication, DEME_GROUP, GECCO 2008, digital germlines, soma, cooperative networks, collective intelligence, evidence
- **claim ceiling:** `runtime_observation`

## Digest

The Goldsby/Ofria Avida line treats communication and germline/soma architecture as evolvable instructions, not as researcher-assigned tags. Avida ORGANISM_MESSAGING exposes send_message, retrieve_message, broadcast_message, and block_propagation. Those instructions must pay: communication ablation that does not drop group payoff is not evidence that messaging evolved as coordination. GermlineReplication / avida.cfg DEME_GROUP (DEMES_GROUP_REPLICATE, GERMLINE) copies a deme when mean fitness clears a threshold, exporting a germline/propagule — multilevel selection as an experiment, not a rank table. GECCO 2008 digital germlines describe cooperative networks in which soma vs germline eligibility is discovered. Goldsby, Knoester, Kerr, and Ofria (PLOS Biology 2014, dirty-work hypothesis) show somatic cells evolving to handle costly tasks while germlines sequester reproduction. CodonTrace Genesis Phase E implements a messaging *buffer* and role *gates*; Phase F records deme payoff, ranking, and DoL metrics with communication_ablation_status=not_run and multilevel_selection_experiment=scaffold_only. Phase H runs the ablation harness (messaging on vs off) as measurement. That still is not evolved language, not Avida C++, and not a major transition. This line is the primary literature map for how to get collective intelligence evidence: communication ablation, germline export-of-fitness, and cooperative networks that are discovered rather than tagged.

## Key claims

- Coordination instructions are evidence only if ablation drops group payoff.
- Deme replicate-on-mean-fitness is multilevel selection only as a controlled experiment.
- Germline/soma eligibility must be discovered, not assigned, to match GECCO 2008 / dirty-work results.
- A contribution ledger is attribution, not causal proof of cooperation.

## What CodonTrace Genesis has

Messaging buffer; role gates; Phase H communication-ablation harness; Phase I heldout/MLS analogs; Phase K evolved send/retrieve/broadcast instruction genomes on the Phase E buffer; Phase L per-organism FIFO / faced-neighbor send / `block_propagation` / `DEME_GROUP` analog via `maybe_replicate_demes`.

## What CodonTrace Genesis lacks

Avida C++ ORGANISM_MESSAGING / DEME_GROUP; grid neighborhoods; evolved language; evolved germline/soma networks.

## Next experiment

How to get collective intelligence evidence: Phase L `run_organism_messaging_fidelity_experiment` at research scale; never set ClaimGate flags from smoke.

Retrieving this digest is not `collective_intelligence` or intelligence evidence.
