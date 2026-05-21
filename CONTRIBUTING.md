# Contributing

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
