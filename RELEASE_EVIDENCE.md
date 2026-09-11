# Release Evidence

Package: `codontrace`
Version: `0.3.0b3`
Status: beta research-software release candidate
Release bundle: `codontrace-0.3.0b3-release-bundle.zip`

## Scope

This release packages the CodonTrace Genesis library as a deterministic, replay-aware research toolkit for digital-evolution and causal-mechanism experiments. It includes source code, tests, examples, docs, citation metadata, security/contribution policies, and CI/publish workflow templates.

`0.3.0b3` ships Phase F scientific-gap measurement, Phase G named-materials substrate, and post-F/G ClaimGate honesty hygiene on top of the `0.3.0b2` Phase A–E library. Phase A–C and Phase E are opt-in substrates (life-loop ecology; sexual recombination; dynamic/fluctuating environment; capsule/memory/role/deme). Phase D is an opt-in measurement API. Phase G does not mutate legacy `World2D.resources`. Defaults stay off unless a caller selects those presets. No intelligence, collective-intelligence, or chemistry-proved claims.

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

CodonTrace Genesis is a Library-as-Tool. It exposes auditable primitives, protocol records, deterministic digests, and ClaimGate-compatible evidence. It does not hard-code success and does not make positive high-level claims without experiment-specific controls, heldout evaluation, replay digests, and ClaimGate acceptance.

Phase E remains `runtime_observation` only. ClaimGate keeps `collective_intelligence`, `evolved_plasticity`, `avida_replacement`, `intelligence`, `AGI`, `wet_lab_equivalent`, and `realistic_chemistry_proved` blocked.

## Official example-generated pilot outputs

These filenames are produced by the official `examples/genesis_*_pilot.py` CLIs.
They are not committed fake evidence. Live default fixtures keep honest ceilings:

| Example | Output names | Default fixture ceiling |
|---|---|---|
| `examples/genesis_evolution_pilot.py` | `genesis_evolution_pilot.json` | evolution-pilot records; not Avida replacement |
| `examples/genesis_qd_selection_pilot.py` | `qd_selection_pilot.json` | `qd_changed_selection` when pressure is applied |
| `examples/genesis_toolchain_pilot.py` | `toolchain_pilot_summary.json` | toolchain chain records |
| `examples/genesis_capsule_utility_pilot.py` | `capsule_utility_summary.json` | `claim_allowed_for_capsule_usefulness=False` (`no_positive_behavioral_utility`) |
| `examples/genesis_memory_delayed_reward_pilot.py` | `memory_delayed_reward.json` | `pilot_fixture_not_strong_memory_claim`; `claim_allowed_for_strong_memory=False` |
| `examples/genesis_social_partner_pilot.py` | `social_partner_summary.json` | social interaction may be recorded; social intelligence remains denied |

Do not treat presence of these filenames as a strong-memory, capsule-usefulness, intelligence, or chemistry claim.

## Public package contents

Included:

- `src/` package source,
- `tests/`, `examples/`, and `tools/`,
- `docs/`, `README.md`, `CHANGELOG.md`, `PATCH_SUMMARY.md`, `LICENSE`, `CITATION.cff`, `CONTRIBUTING.md`, and `SECURITY.md`,
- GitHub Actions workflows for CI and PyPI Trusted Publishing.

Excluded:

- local reports,
- patch scratch files,
- cache directories,
- build outputs,
- generated local `*_pilot_out/` directories and uncommitted JSON payloads.
