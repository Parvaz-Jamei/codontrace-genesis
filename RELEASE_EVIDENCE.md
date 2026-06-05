# Release Evidence

Package: `codontrace`
Version: `0.3.0b1`
Status: beta research-software release candidate
Release bundle: `codontrace-0.3.0b1-release-bundle.zip`

## Scope

This release packages the CodonTrace Genesis library as a deterministic, replay-aware research toolkit for digital-evolution and causal-mechanism experiments. It includes source code, tests, examples, docs, citation metadata, security/contribution policies, and CI/publish workflow templates.

## Evidence gates expected before publishing

Run from the repository root:

```bash
python -m compileall -q src tests examples tools
python -m pytest tests --disable-plugin-autoload
python -m build
python -m twine check dist/*
```

For limited environments, run tests in documented chunks and record the command output in a release note or CI artifact.

## Claim boundaries

CodonTrace is a Library-as-Tool. It exposes auditable primitives, protocol records, deterministic digests, and ClaimGate-compatible evidence. It does not hard-code success and does not make positive high-level claims without experiment-specific controls, heldout evaluation, replay digests, and ClaimGate acceptance.

## Public package contents

Included:

- `src/` package source,
- `tests/`, `examples/`, and `tools/`,
- `docs/`, `README.md`, `CHANGELOG.md`, `LICENSE`, `CITATION.cff`, `CONTRIBUTING.md`, and `SECURITY.md`,
- GitHub Actions workflows for CI and PyPI Trusted Publishing.

Excluded:

- local reports,
- patch scratch files,
- cache directories,
- build outputs,
