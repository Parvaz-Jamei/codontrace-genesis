# Avida ORGANISM_MESSAGING (send-msg / retrieve-msg / broadcast / block)

**CodonTrace Genesis literature digest** (not a substitute for the Avida tree).

- **id:** `avida_cfg_organism_messaging`
- **authors:** Charles Ofria, David M. Bryson, Charles Ofria lab; Goldsby / Knoester messaging line
- **year:** 2004
- **venue:** Avida instruction set / ORGANISM_MESSAGING; Ofria & Wilke 2004 BioSystems; Goldsby coordination instructions
- **identifiers:** https://github.com/devosoft/avida ; Ofria & Wilke 2004 doi:10.1016/j.biosystems.2004.05.025
- **tags:** Avida, ORGANISM_MESSAGING, send-msg, retrieve-msg, broadcast-msg, block_propagation, facing, FIFO inbox, Goldsby, collective intelligence, evidence
- **claim ceiling:** `runtime_observation`

## Digest

Avida ORGANISM_MESSAGING is a CPU-instruction interface, not a researcher-assigned chat log. Typical inst-set names are send-msg (deliver label+data to the faced neighbor), retrieve-msg (pop the organism's own message queue into registers), broadcast / bcast variants (fan-out to the neighborhood), and a block/no-forward control that Goldsby/Ofria papers treat as block_propagation. Inboxes are per-organism and consumed on retrieve. Facing is hardware state (rotate-cw / rotate-ccw). Communication is evidence only if ablation drops group payoff. CodonTrace Genesis Phase E records a shared deme buffer. Phase K evolves send/retrieve/broadcast on that shared latest-message analog. Phase L adds per-organism FIFO pop, faced-neighbor send on a ring, rotate_cw, and block_propagation that suppresses later broadcasts — still a discrete analog, not a C++ port of cHardwareCPU / cOrgMessage. Retrieving this digest is not collective intelligence.

## Key claims

- ORGANISM_MESSAGING is instruction-level: send targets facing, retrieve pops a FIFO, broadcast fans out, block stops forwarding.
- A shared deme "latest message" buffer is a weaker analog than per-organism queues.
- Ablation that does not drop group payoff is not evidence that messaging evolved as coordination.
- An analog ISA is not Avida replacement.

## What CodonTrace Genesis has

Phase E DemeState buffer; Phase K evolved send/retrieve/broadcast analog; Phase L `evaluate_organism_messaging_group` FIFO / facing / block analog on that buffer.

## What CodonTrace Genesis lacks

Avida C++ ORGANISM_MESSAGING hardware; grid neighborhoods; register-level label/data; evolved language.

## Next experiment

How to get collective intelligence evidence: run Phase L `run_organism_messaging_fidelity_experiment` at research scale; keep ClaimGate blocked; do not label the analog an Avida port.

Retrieving this digest is not `collective_intelligence` or intelligence evidence.
