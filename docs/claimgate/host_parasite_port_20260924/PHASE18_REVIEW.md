# Phase 18 review — soft-complete journal ClaimGate attach-registry packet

Human research review of Wave 5 earn-in hygiene. Documents Phases 1–17 attach
keys and the blocked-claim matrix for journal reviewers. Not taxonomy theater;
no new biology claims; claim ladder does not rise.

## What Phase 18 delivers

- `REQUIRED_ATTACH_KEYS` / `BLOCKED_CLAIM_MATRIX` in
  `host_parasite_attach_registry.py`.
- `build_journal_attach_registry_packet` with canonical `registry_digest`.
- `attach_journal_attach_registry` (prereg-bound; soft_complete; proved flags False).
- Tests in `tests/test_host_parasite_phase18.py` (registry completeness, blocked
  matrix, attach ladder stability, BAIC pin SHA256).
- README / REQUIREMENTS soft-complete pointer for Wave 5 Phase 18.

## Critique round 1

### Flaws found

1. **Phases 1–17 attach keys lived only in adapter source**, so reviewers had
   no first-class inventory that could drift silently.
2. **Blocked-claim refuse list mixed profile blocks with campaign flags**, making
   journal checklists incomplete.

### Fixes

- Froze `REQUIRED_ATTACH_KEYS` covering every shipped attach extra-key through
  Phase 17.
- Froze `BLOCKED_CLAIM_MATRIX` covering profile blocks plus refuse-list flags
  (`gene_identity_proved`, `complexity_emergence_proved`, OEE/MODES).

### Retest

Phase 18 unit tests green; pins untouched; `red_queen_proved` still blocked.

## Critique round 2

### Flaws found

1. **Attach without prereg** would diverge from campaign attach norms.
2. **Soft-complete packet could be misread as raising the ladder** if proved
   flags were omitted.

### Fixes

- Attach requires preregistration digest and re-checks `red_queen_proved` block.
- Packet and attach record force `raises_claim_ladder=False` and dynamics
  proved flags False.

### Retest

Phase 18 green; BAIC pins and `engine.py` untouched; no claim ladder rise.
