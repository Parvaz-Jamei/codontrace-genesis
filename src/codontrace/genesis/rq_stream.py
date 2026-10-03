"""Domain-separated random streams for one history.

Derivation is root, then history id, then subsystem, then generation.
The mix is a canonical JSON document hashed with SHA-256. It is not a
numeric sum, product, or other collision-prone combination of the seed
and the generation. 9201 at generation 2 and 9202 at generation 1
therefore do not share a stream.

Arms of one history use the recorded policy below. They may derive the
same integers, but each arm holds its own RNGManager. A draw on one
object does not advance another.
"""

from __future__ import annotations

import hashlib
import json

from codontrace.rng import RNGManager

STREAM_VERSION = "rq-stream/1"

# Recorded sharing policy. This is not a parameter of the biological model.
ARM_STREAM_POLICY: dict[str, str] = {
    "policy_id": "shared-derivation-separate-objects",
    "statement": (
        "Arms of one history derive host-step and passage streams from the "
        "same (root, history_id, subsystem, generation) tuple, so the draws "
        "offered at a generation do not depend on the arm label. Each arm "
        "constructs its own RNGManager. Arms do not share a mutable RNG "
        "object. Independent histories differ in history_id. Order of "
        "histories is not an input."
    ),
}


def derive_stream_seed(root: str, history_id: str, subsystem: str, generation: int) -> int:
    """Return the integer seed for one subsystem at one generation.

    ``generation`` is the 1-based generation index. The result depends on
    the four strings/integers as separate fields. Adding the history id to
    the generation is not used.
    """

    if not root or not subsystem:
        msg = "stream root and subsystem must be non-empty"
        raise ValueError(msg)
    if not str(history_id):
        msg = "history id must be non-empty"
        raise ValueError(msg)
    generation_i = int(generation)
    if generation_i < 1:
        msg = "stream generation must be >= 1"
        raise ValueError(msg)
    payload = {
        "generation": generation_i,
        "history_id": str(history_id),
        "root": str(root),
        "subsystem": str(subsystem),
        "version": STREAM_VERSION,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def open_stream(root: str, history_id: str, subsystem: str, generation: int) -> RNGManager:
    """Open a new RNGManager for this identity. Callers must not share it."""

    seed = derive_stream_seed(root, history_id, subsystem, generation)
    namespace = f"{STREAM_VERSION}/{root}/{history_id}/{subsystem}/g{int(generation)}"
    return RNGManager(seed=seed, namespace=namespace)
