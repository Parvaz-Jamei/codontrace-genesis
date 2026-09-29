# CLAIM B — ACCEPT

**Claim.** In `codontrace-genesis`, commit `67c4a10` exists and is an ancestor of HEAD.

**Verdict: ACCEPT.** `67c4a10` resolves to a commit object and is reachable from every HEAD
observed during verification.

## Environment deviation (disclosed)

**There is no `git` executable on this machine.** It is not on `PATH`, not at
`C:\Program Files\Git\cmd\git.exe`, not under `%LOCALAPPDATA%\Programs\Git`, and
`C:\Users\parvaz\AppData\Local\GitHubDesktop` contains no bundled `git.exe`
(`winget`/`scoop`/`chocolatey` locations also checked; a recursive `C:\` scan was abandoned
after a 300 s timeout). The three requested commands therefore could not be shelled out to.

Instead, `docs/experiments/2026-09-29/verification/claim_b_git.py` reproduces them **from the repository's own
object database**, reading raw artifacts:

- loose objects: `zlib.decompress(.git/objects/xx/yyyy…)`, parse `"<type> <size>\0"` header;
- packfiles: idx v2 (fanout + names + **CRC32 table** + 4-byte offsets + large-offset table),
  pack entry header varints, **zlib-inflated payloads**, and `ofs_delta` / `ref_delta`
  reconstruction via git's delta instruction format;
- every reconstructed object is re-hashed (`sha1("<type> <size>\0" + body)`) and must equal
  the id it was requested by.

The two bugs found and fixed while building the reader (the omitted CRC32 table, and the
missing zlib inflate) are exactly the kind of thing the re-hash check catches.

### Reader validation (`claim_b_validate_reader.py`)

Every object in every pack and every loose object was resolved and re-hashed:

| pack | objects | re-hash OK | pack SHA-1 trailer |
|---|---|---|---|
| `pack-1b8129c0e354f1d62dc0c92e195fdaee076d6c45` | 4 438 | 4 438 | matches |
| `pack-319e3c956cf826bb89265a54ec2564839e4b493a` | 1 057 | 1 057 | matches |
| `pack-ddeb483c63f9f8cf0e2725702e533f6eac4cccc6` | 612 | 612 | matches |
| loose objects | 161 | 161 | — |

**6 268 objects, zero mismatches.** The reader is sound, so its answers are trustworthy.

## Emulated commands

```
$ git cat-file -t 67c4a10
commit        # full sha 67c4a10a93344cbbbd9ac9d536ddc201fac9b5e8
              # exit code 0

$ git merge-base --is-ancestor 67c4a10 HEAD
              # exit code 0 (is an ancestor)
```

Ancestry was checked by an exhaustive parent walk from HEAD (the semantics of
`merge-base --is-ancestor`): exit `0` if the target is reached, `1` if the walk exhausts
without reaching it.

```
$ git log --oneline -3          (HEAD = 17a12f65040932ae0491572c766e7b50f7041be5)
17a12f6 feat(engine): restorable state fork and contact-identified ledger debits
49750b1 docs(discovery): file the RQ-1 route addendum
cff84cd fix(ci): hash text pins through the LF-normalising helper
```

Resolved commit metadata for `67c4a10`:

```
tree    ad6e199e42afa84d94444b8bf9c2e2bde4848854
parents 8238459f34e48ea44f646d0a6b441d11b8ecc706
subject "fix(tests): rebaseline stale artifact pins and align version strings"  (leading U+FEFF BOM in the raw message)
```

## HEAD moved during verification

Another process is committing to `codontrace-genesis` concurrently. The first observation of
HEAD was `d40068782b31799ae006b55bad58f95c86cb06d3` (`style(discovery): rename unused loop
variable for ruff B007`); at recheck time HEAD was
`17a12f65040932ae0491572c766e7b50f7041be5`. **Ancestry of `67c4a10` was confirmed against
both HEAD values (exit 0 in both cases)**, so the verdict does not depend on which snapshot
is used. The reflog independently shows `8238459f` committed directly on top of `67c4a10`.

## Artifacts

- `docs/experiments/2026-09-29/verification/claim_b_git.py` (reader + emulated commands), `claim_b_out.txt`, `claim_b_raw.json`
- `docs/experiments/2026-09-29/verification/claim_b_validate_reader.py`, `claim_b_validate_out.txt`, `claim_b_reader_validation.json`
- `docs/experiments/2026-09-29/verification/claim_b_recheck.py`, `claim_b_recheck_out.txt`, `claim_b_recheck.json`
