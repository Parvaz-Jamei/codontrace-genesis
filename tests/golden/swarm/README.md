# Swarm wire golden fixtures

Shared `genesis_swarm_v1` / `genesis_swarm_v2` frames for
`codontrace.swarm.protocol.decode`. One JSON frame per file, exact bytes.

- `valid/` must decode. The `v2_*` frames from `v2_hello_five_types` to
  `v2_category_unicode` are byte-for-byte the CodonTraceSwarm C++ encoder output
  (`evidence/messages.jsonl` at 76a39e0), so the decoder is tested against what the
  encoder emits today.
- `invalid/` must raise `ValueError`.

Reading `value` types (v2, `contracts.channels.VALUE_TYPES`): scalar = finite
number; vector/waveform = flat list of 1..256 finite numbers; boolean = `true`/`false`;
category = nonempty text of at most 128 characters; `null` only when `valid` is false.
v1 readings carry a finite number only. Value nesting is at most one array level;
`NaN`, `Infinity` and overflowing literals are rejected.

The Swarm repo (Parvaz-Jamei/CodonTraceSwarm) pins these same files by sha256.
`MANIFEST.sha256` lists every fixture in `sha256sum` format; verify with
`sha256sum -c MANIFEST.sha256`. Changing a fixture changes its hash, so update the
manifest here and the pin in the Swarm repo in the same change.
