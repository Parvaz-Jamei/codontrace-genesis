# API Stability Policy

CodonTrace is a library-first scientific engine.

## Stable public API
`codontrace.*` exposes stable or compatibility-oriented APIs.

## Research / alpha API
`codontrace.genesis.*` exposes research-alpha scientific APIs. These are importable and tested, but may evolve across alpha versions with migration notes.

## Experimental API
Objects marked experimental are intended for scientific protocol development and may change while preserving artifact migration helpers where feasible.

## Deprecated / legacy alias
Legacy aliases such as `CausalGraph` remain for compatibility during the alpha cycle. Canonical scientific terminology should prefer newer names such as `EventGraph` where documented.

## Forbidden runtime boundaries
CodonTrace does not provide a UI, server, database service, background worker, dashboard, cloud orchestration system, or LLM hot-loop controller. Future UIs must consume the library API rather than becoming the engine.
