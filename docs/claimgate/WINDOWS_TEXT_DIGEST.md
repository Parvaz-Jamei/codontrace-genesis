# Text-file digest policy

Use `codontrace.genesis.text_digest.sha256_text_file` for markdown, JSON, `.dat`, and `.csv` pins.

On Linux this equals raw `read_bytes()` when the file is already LF.
On Windows with `core.autocrlf=true` it keeps the same digest as Linux.

Remaining call sites that still hash raw bytes live in large campaign modules
(`hard_experiment_01.py` and siblings). Replace
`hashlib.sha256(path.read_bytes()).hexdigest()` with `sha256_text_file(path)`
there as well; the helper is the single source of truth.
