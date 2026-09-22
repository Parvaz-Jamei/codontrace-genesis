Use `codontrace.genesis.text_digest.sha256_text_file` for markdown, JSON, `.dat`, and `.csv` pins.

Call sites that use this helper:

- ClaimGate adapters: HE01 / HE02 / HE03, Avida `.dat`, MABE2 CSV
- Campaign prereg digests: `hard_experiment_01.py`, `hard_experiment_02.py`,
  `hard_experiment_03.py`, `ilw/prereg.py`

On Linux this equals raw `read_bytes()` when the file is already LF.
On Windows with `core.autocrlf=true` it keeps the same digest as Linux.

Keep `hashlib.sha256(path.read_bytes())` only for true binary artifacts
(snapshots, zips). Keep `hashlib.sha256(repr(result).encode())` for
in-memory campaign objects that are not files.
