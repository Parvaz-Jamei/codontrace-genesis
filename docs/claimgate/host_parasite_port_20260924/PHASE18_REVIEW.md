# Phase 18 review — soft-complete journal ClaimGate attach-registry packet

Human research review of Wave 5 earn-in hygiene. Documents Phases 1–17 attach
keys and the blocked-claim matrix for journal reviewers. Not taxonomy theater;
no new biology claims; claim ladder does not rise.

**Experts:** A — digital evolution / ALife · B — microbial / phage honesty ·
C — ClaimGate / V&V / causal methodology.

## What Phase 18 delivers

- `REQUIRED_ATTACH_KEYS` / `BLOCKED_CLAIM_MATRIX` in
  `host_parasite_attach_registry.py`.
- `WAVE5_ATTACH_KEYS` follow-on inventory (Phases 18–23) so hygiene does not
  freeze at Wave 4.
- `build_journal_attach_registry_packet` with canonical `registry_digest`.
- `attach_journal_attach_registry` (prereg-bound; soft_complete; proved flags False).
- Tests in `tests/test_host_parasite_phase18.py` (registry completeness, blocked
  matrix, attach ladder stability, BAIC pin SHA256).
- README / REQUIREMENTS soft-complete pointer for Wave 5 Phase 18.

## موج ۱ / Critique round 1 (experts A / B / C)

### A — feasibility / testable surface

1. **Phases 1–17 attach keys lived only in adapter source**, so reviewers had
   no first-class inventory that could drift silently from shipped digests.

### B — usefulness / honesty

2. **Blocked-claim refuse list mixed profile blocks with campaign flags**, making
   journal checklists incomplete for S1 / gene-identity / OEE refuse language.

### C — ClaimGate / V&V

3. Soft-complete must **not** be readable as innovation theater or ladder rise;
   packet needs explicit `raises_claim_ladder=False` and dynamics proved flags
   False.

### Fixes (round 1)

- Froze `REQUIRED_ATTACH_KEYS` covering every shipped attach extra-key through
  Phase 17.
- Froze `BLOCKED_CLAIM_MATRIX` covering profile blocks plus refuse-list flags
  (`gene_identity_proved`, `complexity_emergence_proved`, OEE/MODES).
- Packet forces soft_complete + proved flags False.

### Retest (round 1)

Phase 18 unit tests green; pins untouched; `red_queen_proved` still blocked.

## موج ۲ / Critique round 2 (experts A / B / C)

### A

1. Inventory that stops at Phase 17 becomes stale the moment Wave 5 attaches
   ship — need a follow-on key list without rewriting Phase 18’s 1–17 contract.

### B

2. No wet biology language must appear in the hygiene packet note.

### C

3. **Attach without prereg** would diverge from campaign attach norms.
4. Soft-complete packet must re-check a representative blocked claim at attach.

### Fixes (round 2)

- Added `WAVE5_ATTACH_KEYS` for Phases 18–23 attach surfaces; Phase 18 packet
  still covers 1–17 as the soft-complete baseline.
- Attach requires preregistration digest and re-checks `red_queen_proved` block.
- Packet and attach record force `raises_claim_ladder=False`.

### Retest (round 2) — sign-off

Phase 18 green; BAIC pins and `engine.py` untouched; no claim ladder rise.
A/B/C sign-off: hygiene complete; proceed to Phase 19.
