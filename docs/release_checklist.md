# Release checklist

Run these commands from a clean checkout:

```bash
python -m pip install -e ".[dev]"
python -m compileall -q src tests examples tools
python -m pytest tests --disable-plugin-autoload
python -m build
python -m twine check dist/*
```

Manual checks:

- `README.md` describes the package as beta research software.
- `CITATION.cff` version matches `pyproject.toml` and `codontrace.__version__`.
- `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, and `CHANGELOG.md` are present.
- PyPI publication uses Trusted Publishing from GitHub Actions when possible.
