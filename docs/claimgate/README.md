# ClaimGate committed outputs

These files are **local, developer-run** checks. They do not make the
project prestigious, certified, or independently reviewed.

| File | What it is | What it is not |
|---|---|---|
| `ladder_validation.json` | Live auditor grades of nine synthetic packs | Population false-accept rate |
| `test_snapshot.json` | Local pytest count of ClaimGate adapter/port tests | GitHub Actions matrix / multi-OS proof |

Rebuild validation:

```bash
PYTHONPATH=src python tools/export_ladder_validation.py
PYTHONPATH=src python -m pytest tests/test_claimgate_ladder_packs.py tests/test_claimgate_biomedical.py tests/test_claimgate_adapters.py tests/test_claimgate_roles.py tests/test_claimgate_he03_adapter.py tests/test_text_digest.py
```

Still missing for any stronger claim: external raters, factorial HE01,
public Avida `.dat`, and a real biomedical model under a stated COU.
