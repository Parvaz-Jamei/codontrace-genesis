# GENESIS final library hardening notes

This patch keeps the public API backward-compatible while adding public,
deterministic evidence surfaces for serious GENESIS intelligence runs.

Added or hardened library-level surfaces:

- QD selection audit reasons via `QDFallbackReason`, plus parent feedback and archive summary access.
- BehaviorDescriptor v2 fields used as the shared source for QD, role, social, tool-chain, and task-sensitive scoring.
- Capsule source-fitness status handling so `unavailable` is never silently treated as real low zero fitness.
- Per-capsule adoption records with pre/post ATP fields, standard blocked reasons, and final MODERATE profile values aligned with the hardening protocol.
- Engine-level social interaction records derived from capsule teaching/learning attempts.
- Tool-chain state gating for wood/stone/tool/key/door/water/food/home progress, deterministic World2D object-state transition evidence, and tool-chain fitness contribution.
- Role assignment and role contribution records exposed from `GenesisRunResult`.
- Memory and delayed-reward evidence record contracts exposed conservatively.
- Exact engine frames and schema-versioned evidence manifest access from `GenesisRunResult`.

Claim control remains conservative: these records improve auditability and testability;
they do not by themselves prove collective intelligence, planning, or generalization.
