# CLAIM A — ACCEPT

**Claim.** The three BAIC pin digests are line-ending-normalised, and on this Windows
checkout the raw-byte hash differs.

**Verdict: ACCEPT.** LF-normalised hashes match all three pins; raw-byte hashes match none.

## Reproduction

Own code path: `docs/experiments/2026-09-29/verification/claim_a_hash.py` reads each file with `Path.read_bytes()`
(no text decoding, no universal-newline translation), hashes the raw bytes, then hashes
`raw.replace(b"\r\n", b"\n")`. Counts come from `bytes.count` on the raw buffer.
The pins were taken from the claim statement, not from any file in the repository.

| file | size (bytes) | CRLF pairs | lone LF | lone CR | raw sha256 | LF-normalised sha256 | raw == pin | LF == pin |
|---|---|---|---|---|---|---|---|---|
| `docs/hard_experiment_01/results_v7.json` | 401 445 | 10 201 | 0 | 0 | `4a5987c2ed0f09d1088b3c1bca6d81fe2310f3867fa84f22a33fbeee7b5d7efd` | `35bb593604438797755e5e7b28af4d1371992a6181a403d08005f7f45421cbd6` | **no** | **yes** |
| `docs/claimgate/risk_bar.json` | 1 430 | 61 | 0 | 0 | `b7091921bf00c350fa286caf117fa46af81e9760b1b6d4d135eefd042dabd404` | `4dbe4aa3a6ef8e771f180d2a6589c64b0dd5ffebe0aa73703a7256c17d771cd7` | **no** | **yes** |
| `docs/claimgate/biomedical_study.json` | 1 095 | 40 | 0 | 0 | `2e5193639aad58ceda68ef9bc33943f8eae2c45f042209a060af890c93785079` | `9685f2fbafb21477d977dfa0c0bf73e02bea81d084e7605978ea25c47bf5ddce` | **no** | **yes** |

All three files are *uniformly* CRLF: 10 201/61/40 CRLF pairs and **zero** lone LF and
**zero** lone CR bytes. The byte-count difference is exactly the number of LF bytes
(401 445 − 10 201 = 391 244; 1 430 − 61 = 1 369; 1 095 − 40 = 1 055).

## Two independent confirmations

1. **The repository's own digest helper agrees.** `docs/experiments/2026-09-29/verification/claim_a_crosscheck.py`
   imports `codontrace-genesis/src/codontrace/genesis/text_digest.py::sha256_text_file`
   and calls it on each file. It returns exactly the pins. That function's implementation is
   `read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")`, and its docstring states the
   intent: *"Text-file SHA-256 that follows Git LF identity, not the working-tree bytes."*
   The pins are consumed by `host_parasite_world.py::assert_baic_pins_untouched` via that
   helper, and `codontrace-genesis/.gitattributes` declares `* text=auto`.
   Because there are no lone CRs, the CRLF→LF-only and CRLF/CR→LF normalisations give
   identical digests here (verified per file).

2. **The pins are the SHA-256 of the git blobs.** `docs/experiments/2026-09-29/verification/claim_a_blob_identity.py`
   resolves each path through the repository's own object database (HEAD commit → trees →
   blob), reads the blob bytes, and verifies both that the blob re-hashes to its own git
   SHA-1 and that the LF-normalised working-tree bytes are *byte-identical* to the blob:

   | file | git blob SHA-1 | blob size | sha256(blob) == pin | LF-normalised worktree == blob |
   |---|---|---|---|---|
   | `results_v7.json` | `2108bafcbcc619c4d2385ddcab3fcc717fe9881b` | 391 244 | yes | yes |
   | `risk_bar.json` | `78cf70a66dcb16098130aa778f17fd7bece318ad` | 1 369 | yes | yes |
   | `biomedical_study.json` | `36d3ff3adf730d69777d628b1663be9813c0958e` | 1 055 | yes | yes |

## Caveat

HEAD moved while this verification ran (the repository receives concurrent commits); the
blob proof was taken at HEAD `17a12f65040932ae0491572c766e7b50f7041be5`. The three pinned
files themselves were last modified 2026-09-24 and did not change between runs.

## Artifacts

- `docs/experiments/2026-09-29/verification/claim_a_hash.py`, `claim_a_out.txt`, `claim_a_raw.json`
- `docs/experiments/2026-09-29/verification/claim_a_crosscheck.py`, `claim_a_crosscheck_out.txt`, `claim_a_crosscheck.json`
- `docs/experiments/2026-09-29/verification/claim_a_blob_identity.py`, `claim_a_blob_out.txt`, `claim_a_blob_identity.json`
