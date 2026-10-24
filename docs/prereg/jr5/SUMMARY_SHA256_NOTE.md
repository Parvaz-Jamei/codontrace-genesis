# RQ-MECHANISM-V2 phase 6: `summary_sha256` versus the file hash

The two numbers are different hashes. Neither is wrong.

- `summary_sha256` is written by `src/codontrace/genesis/rq_mechanism_v2_phase6.py:1096-1098`. It is the SHA-256 of `json.dumps({k: v for k, v in summary.items() if k != "summary_sha256"}, sort_keys=True).encode("utf-8")`: every top-level key except itself, Python's default separators `", "` and `": "`, no indent, `ensure_ascii=True`, and no trailing newline.
- The file is then written at `:1099` as `json.dumps(summary, indent=2, sort_keys=True) + "\n"`. That version includes the `summary_sha256` key, uses indent 2 and ends with a newline. Its byte hash is `dec7e432f0a402ad8e8da99877270990ea421a65bb984ae94d9923d99cc17537`.

To reproduce the field from the committed file:

```python
import hashlib, json
d = json.load(open("runs/rq-mechanism-v2/phase6-coevolution/summary.json"))
body = {k: v for k, v in d.items() if k != "summary_sha256"}
hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
# 948413a36d9046448f78de9cfb323207cf42852905d39329d6ba0e46d60b1344
```

This was run at 66f57a5 and matches the stored field. Phase 5 uses the same rule (`rq_mechanism_v2_phase5.py:2111`, `:2360`). JR5 cites both values and names which is which.
