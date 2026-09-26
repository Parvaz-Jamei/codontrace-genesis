# Owner policy — engine and module updates (2026-09-26)

This note **supersedes** earlier standing language that treated `engine.py`,
closed-loop modules, plugins, or measurements as “do not touch” or
“byte-frozen” except for historical run records (those remain accurate for
the commits they describe).

## What changed

- **Modules and the engine may be updated freely** when a design or defect
  requires it (life-loop fidelity, measurements, env/plugin, closed-loop
  runners, ClaimGate plumbing after earned gates, docs).
- The BAIC ClaimGate/model-credibility submission was **desk-rejected** and
  dropped as a venue lock. **BAIC biomedical pin “byte-identical” freezes
  no longer bind** CodonTrace Genesis work. Do not treat BAIC pins as a
  reason to refuse engine or module edits.
- Older handoffs that say “`engine.py` was not edited” or “BAIC pins
  untouched” are **historical facts for that run**, not forward locks.

## What remains (only architectural bar)

- **`GenesisEngine` / `engine.py` stay general (domain-free ALife).** Do not
  import host–parasite / infection / virulence / match-allele / Red Queen
  domain physics into the kernel. Domain science stays in env, plugin,
  DomainProfile, closed-loop arms, and measurement modules.
- Improving domain-free life-loop fidelity **in** `engine.py` is allowed and
  expected when justified (hooks, census emission, ATP/birth/passage
  generality for other disciplines).
- No second population registry that bypasses `GenesisEngine`.
- ClaimGate honesty bars (no soft-pass; `red_queen_proved` only after earned
  gates + Critic sign-off) are unchanged by this policy.
- Public GitHub prose stays ordinary research English (no tool/workflow
  meta).

## Guidance for the next agent

1. Prefer fixing the real defect in the right layer; do **not** refuse an
   engine edit solely because older waves preferred “env only.”
2. If an edit would put HP vocabulary or infection physics into `engine.py`,
   refuse that shape and put it in env/plugin instead — that is the
   **general-engine** rule, not a no-touch rule.
3. Cite this file when older docs conflict.
