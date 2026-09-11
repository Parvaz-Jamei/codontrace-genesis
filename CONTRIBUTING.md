# Contributing

## Product naming

- Public product name: **CodonTrace Genesis**
- PyPI / import package: `codontrace`
- Do not drop the Genesis qualifier in docs, PRs, issues, or papers
- `codontrace.genesis` is a module path, not a second product name
- Do not put internal naming-order lists in the README

See [`STYLE.md`](STYLE.md).

## Development setup

```bash
python -m pip install -e ".[dev]"
```

## Required checks

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src/codontrace examples
python -m pytest
python -m build
python -m twine check dist/*
```

Keep codontrace compact, testable, research-oriented, PyPI-ready, honest about limitations, and free of scope creep.
