# LLM Review and Rule API

LLM integration is API-mediated and review/rule-proposal oriented. The LLM must interact through CodonTrace-defined request/response schemas and validators. It must not control organism decisions inside the simulation hot loop, and it must not mutate core state outside approved library APIs.

Correct path:

```text
CodonTrace run result -> Evidence / Review / Rule API -> external reviewer -> structured result -> validator -> human approval -> next run config/rule
```

Wrong path:

```text
LLM decides organism action inside tick; LLM mutates world directly; LLM output is eval/exec/imported.
```
