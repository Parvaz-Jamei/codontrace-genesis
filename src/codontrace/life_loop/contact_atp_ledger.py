"""Contact/ATP ledger for discovery phase-2 harness ops.

Mutable ledger of named contact edges, ATP yield counters by tag,
failed-prediction digests, recovery-eligibility tokens, scaffold edge
sets, and predicted/realised pressure-phase fields. All interventions
run at a generation boundary and never mutate genotype. No second
population engine; no engine.py physics.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float

SCHEMA_VERSION = "life_loop_contact_atp_ledger_v1"

CONTACT_TAG_RARE = "rare"
DIGEST_PRED_FAIL_PREFIX = "digest:pred_fail:"
TOKEN_RECOVERY_PREFIX = "token:recovery:"
SCAFFOLD_EDGES_PREFIX = "scaffold_edges:"
CHECKPOINT_RELOCATE_RECOVERY = "CKPT-RELOCATE-RECOVERY-TOKEN-V1"
SHAM_CUE_PREDPHASE = "SHAM-CUE-PREDPHASE-V1"
REJECTED_CHECKPOINT_ALIASES = frozenset(
    {
        "CKPT-REMOVE-PREDFAIL-DIGEST-MID-V1",
        "CKPT-CUT-SCAF-MEMBERSHIP-FREEZE-V1",
    }
)
NAMED_CONTACT_EDGE_IDS = frozenset(
    {
        "NC-H0-A0",
        "NC-H0-A1",
        "NC-H1-A0",
        "NC-H1-A1",
        "NC-H2-A0",
        "NC-H2-A1",
    }
)


def _as_str(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{name} must be a string.")
    text = value.strip()
    if not text and not allow_empty:
        raise ConfigurationError(f"{name} must be a non-empty string.")
    return text


def _as_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{name} must be an integer.")
    if minimum is not None and value < minimum:
        raise ConfigurationError(f"{name} must be >= {minimum}.")
    return value


def _as_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{name} must be a bool.")
    return value


@dataclass(slots=True)
class ContactEdge:
    """Named ledger contact edge (identity is edge_id, never a genotype class)."""

    edge_id: str
    src: str
    dst: str
    class_tag: str | None = None
    present: bool = True
    masked: bool = False
    atp_yield: float = 0.0

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "edge_id": self.edge_id,
            "src": self.src,
            "dst": self.dst,
            "class": self.class_tag,
            "present": self.present,
            "masked": self.masked,
            "atp_yield": float(self.atp_yield),
        }


@dataclass
class ContactAtpLedger:
    """Mutable contact/ATP ledger for generation-boundary interventions."""

    edges: dict[str, ContactEdge] = field(default_factory=dict)
    atp_yield_by_tag: dict[str, float] = field(default_factory=dict)
    failed_prediction_digests: dict[str, str] = field(default_factory=dict)
    recovery_tokens: dict[str, str] = field(default_factory=dict)
    scaffold_edge_sets: dict[str, set[str]] = field(default_factory=dict)
    predicted_pressure_phase: float = 0.0
    realised_pressure_phase: float = 0.0
    generation_index: int = 0
    rng_seed: int = 0
    _one_generation_masks: set[str] = field(default_factory=set, repr=False)
    _one_generation_budget: dict[str, float] | None = field(default=None, repr=False)
    _cut_buffer: set[str] = field(default_factory=set, repr=False)
    _rng: random.Random = field(default_factory=random.Random, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(int(self.rng_seed))
        require_finite_float("predicted_pressure_phase", self.predicted_pressure_phase)
        require_finite_float("realised_pressure_phase", self.realised_pressure_phase)

    # --- construction helpers ---

    def add_edge(
        self,
        edge_id: str,
        *,
        src: str,
        dst: str,
        class_tag: str | None = None,
        atp_yield: float = 0.0,
    ) -> ContactEdge:
        eid = _as_str(edge_id, "edge_id")
        if eid in self.edges:
            raise ConfigurationError(f"edge_id already present: {eid!r}.")
        tag = None if class_tag is None else _as_str(class_tag, "class_tag")
        edge = ContactEdge(
            edge_id=eid,
            src=_as_str(src, "src"),
            dst=_as_str(dst, "dst"),
            class_tag=tag,
            atp_yield=float(require_finite_float("atp_yield", atp_yield)),
        )
        self.edges[eid] = edge
        if tag is not None:
            self.atp_yield_by_tag[tag] = self.atp_yield_by_tag.get(tag, 0.0) + edge.atp_yield
        return edge

    def register_scaffold(self, scaffold_id: str, edge_ids: Iterable[str]) -> None:
        sid = _as_str(scaffold_id, "scaffold_id")
        key = sid if sid.startswith(SCAFFOLD_EDGES_PREFIX) else f"{SCAFFOLD_EDGES_PREFIX}{sid}"
        ids = {_as_str(e, "edge_id") for e in edge_ids}
        missing = sorted(ids - set(self.edges))
        if missing:
            raise ConfigurationError(f"scaffold edge ids not on ledger: {missing}.")
        self.scaffold_edge_sets[key] = set(ids)

    def place_recovery_token(self, token_key: str, *, payload: str = "eligible") -> None:
        key = _as_str(token_key, "token_key")
        if not key.startswith(TOKEN_RECOVERY_PREFIX):
            raise ConfigurationError(
                f"recovery token key must start with {TOKEN_RECOVERY_PREFIX!r}."
            )
        self.recovery_tokens[key] = _as_str(payload, "payload")

    def place_failed_prediction_digest(self, digest_key: str, *, digest: str) -> None:
        key = _as_str(digest_key, "digest_key")
        if not key.startswith(DIGEST_PRED_FAIL_PREFIX):
            raise ConfigurationError(
                f"failed-prediction digest key must start with {DIGEST_PRED_FAIL_PREFIX!r}."
            )
        self.failed_prediction_digests[key] = _as_str(digest, "digest")

    def tag_is_ledger_only(self, tag: str) -> bool:
        """Contact-ledger tag helper — never a genotype mapping API."""

        _as_str(tag, "tag")
        return True

    def edges_with_tag(self, tag: str) -> list[str]:
        """Return edge ids carrying a contact-ledger class tag (tag only)."""

        want = _as_str(tag, "tag")
        return sorted(
            eid for eid, edge in self.edges.items() if edge.class_tag == want
        )

    def degree(self, node: str) -> int:
        n = _as_str(node, "node")
        return sum(
            1
            for edge in self.edges.values()
            if edge.present and (edge.src == n or edge.dst == n)
        )

    def edge_degree(self, edge_id: str) -> int:
        edge = self._require_edge(edge_id)
        return self.degree(edge.src) + self.degree(edge.dst)

    def _require_edge(self, edge_id: str) -> ContactEdge:
        eid = _as_str(edge_id, "edge_id")
        if eid not in self.edges:
            raise ConfigurationError(f"unknown edge_id: {eid!r}.")
        return self.edges[eid]

    def advance_generation(self) -> None:
        """Clear one-generation interventions and bump generation_index."""

        for eid in list(self._one_generation_masks):
            if eid in self.edges:
                self.edges[eid].masked = False
        self._one_generation_masks.clear()
        self._one_generation_budget = None
        self.generation_index = int(self.generation_index) + 1

    # --- Idea4 ops ---

    def scramble_contacts(self, *, degree_preserving: bool = True) -> dict[str, Any]:
        """Degree-preserving (or free) rewiring of present contact endpoints."""

        preserve = _as_bool(degree_preserving, "degree_preserving")
        present = [e for e in self.edges.values() if e.present]
        if len(present) < 2:
            return {"op": "scramble_contacts", "rewired": 0, "degree_preserving": preserve}
        nodes = sorted({n for e in present for n in (e.src, e.dst)})
        if preserve:
            stubs: list[str] = []
            for e in present:
                stubs.append(e.src)
                stubs.append(e.dst)
            self._rng.shuffle(stubs)
            # Configuration model pairing; fall back if self-loops dominate.
            pairs: list[tuple[str, str]] = []
            i = 0
            while i + 1 < len(stubs):
                a, b = stubs[i], stubs[i + 1]
                if a != b:
                    pairs.append((a, b))
                i += 2
            if len(pairs) < len(present):
                # Keep original endpoints shuffled among edges when pairing fails.
                ends = [(e.src, e.dst) for e in present]
                self._rng.shuffle(ends)
                for edge, (a, b) in zip(present, ends, strict=True):
                    edge.src, edge.dst = a, b
            else:
                self._rng.shuffle(pairs)
                for edge, (a, b) in zip(present, pairs[: len(present)], strict=True):
                    edge.src, edge.dst = a, b
        else:
            for edge in present:
                edge.src = self._rng.choice(nodes)
                edge.dst = self._rng.choice(nodes)
        return {
            "op": "scramble_contacts",
            "rewired": len(present),
            "degree_preserving": preserve,
        }

    def cut_named_scaffold(self, scaffold_id: str) -> dict[str, Any]:
        """Cut pre-registered scaffold edges by named edge ID (not max-degree)."""

        sid = _as_str(scaffold_id, "scaffold_id")
        if sid in REJECTED_CHECKPOINT_ALIASES or sid == CHECKPOINT_RELOCATE_RECOVERY:
            raise ConfigurationError(
                "cut_named_scaffold must not be used as a checkpoint alias; "
                "scaffold cut is distinct from recovery-token relocation."
            )
        key = sid if sid.startswith(SCAFFOLD_EDGES_PREFIX) else f"{SCAFFOLD_EDGES_PREFIX}{sid}"
        if key not in self.scaffold_edge_sets:
            raise ConfigurationError(f"unknown scaffold_id: {sid!r}.")
        cut: list[str] = []
        for eid in sorted(self.scaffold_edge_sets[key]):
            edge = self._require_edge(eid)
            if edge.present:
                edge.present = False
                cut.append(eid)
                self._cut_buffer.add(eid)
        return {"op": "cut_named_scaffold", "scaffold_id": sid, "cut_edge_ids": cut}

    def cut_matched_random(self, degree: int) -> dict[str, Any]:
        """Cut one present non-scaffold edge whose endpoint-degree sum matches."""

        deg = _as_int(degree, "degree", minimum=0)
        scaffold_members: set[str] = set()
        for members in self.scaffold_edge_sets.values():
            scaffold_members |= members
        candidates = [
            eid
            for eid, edge in self.edges.items()
            if edge.present and eid not in scaffold_members and self.edge_degree(eid) == deg
        ]
        if not candidates:
            # Fall back to any present non-scaffold edge closest in degree.
            pool = [
                eid
                for eid, edge in self.edges.items()
                if edge.present and eid not in scaffold_members
            ]
            if not pool:
                raise ConfigurationError("no present non-scaffold edges for matched random cut.")
            candidates = sorted(pool, key=lambda e: abs(self.edge_degree(e) - deg))
            candidates = [candidates[0]]
        chosen = self._rng.choice(candidates)
        self.edges[chosen].present = False
        self._cut_buffer.add(chosen)
        return {
            "op": "cut_matched_random",
            "degree": deg,
            "cut_edge_ids": [chosen],
        }

    def ablate_knowledge_digest(self, digest_key: str) -> dict[str, Any]:
        """Remove a failed-prediction digest only — never recovery tokens or scaffolds."""

        key = _as_str(digest_key, "digest_key")
        if key in REJECTED_CHECKPOINT_ALIASES or key == CHECKPOINT_RELOCATE_RECOVERY:
            raise ConfigurationError(
                "ablate_knowledge_digest cannot act as checkpoint; "
                "rejected collapsed aliases are not live ops."
            )
        if not key.startswith(DIGEST_PRED_FAIL_PREFIX):
            raise ConfigurationError(
                "ablate_knowledge_digest only removes digest:pred_fail:* keys; "
                "refusing distinction collapse into recovery tokens or scaffolds."
            )
        if key.startswith(TOKEN_RECOVERY_PREFIX):
            raise ConfigurationError(
                "ablate_knowledge_digest must not remove recovery tokens."
            )
        removed = self.failed_prediction_digests.pop(key, None)
        return {
            "op": "ablate_knowledge_digest",
            "digest_key": key,
            "removed": removed is not None,
        }

    def relocate_recovery_token(
        self,
        token_key: str,
        *,
        remove: bool = False,
        new_payload: str | None = None,
    ) -> dict[str, Any]:
        """Implement CKPT-RELOCATE-RECOVERY-TOKEN-V1 on token:recovery:* only."""

        key = _as_str(token_key, "token_key")
        if key in REJECTED_CHECKPOINT_ALIASES:
            raise ConfigurationError(
                f"rejected checkpoint alias {key!r} is not a live recovery-token op."
            )
        if not key.startswith(TOKEN_RECOVERY_PREFIX):
            raise ConfigurationError(
                "relocate_recovery_token only acts on token:recovery:* keys; "
                "refusing collapse into digest ablation or scaffold cuts."
            )
        if key.startswith(DIGEST_PRED_FAIL_PREFIX):
            raise ConfigurationError(
                "relocate_recovery_token must not ablate failed-prediction digests."
            )
        if key not in self.recovery_tokens:
            raise ConfigurationError(f"recovery token not present: {key!r}.")
        before = self.recovery_tokens[key]
        if remove:
            del self.recovery_tokens[key]
            after = None
        else:
            payload = "relocated" if new_payload is None else _as_str(new_payload, "new_payload")
            self.recovery_tokens[key] = payload
            after = payload
        return {
            "op": "relocate_recovery_token",
            "checkpoint_id": CHECKPOINT_RELOCATE_RECOVERY,
            "token_key": key,
            "removed": remove,
            "before": before,
            "after": after,
        }

    # --- Idea2 ops ---

    def mask_named_contacts(
        self,
        edge_ids: Sequence[str],
        *,
        one_generation: bool = True,
    ) -> dict[str, Any]:
        """Mask named contact edges by ledger edge ID (never genotype class)."""

        ids = [_as_str(e, "edge_id") for e in edge_ids]
        if not ids:
            raise ConfigurationError("mask_named_contacts requires at least one edge_id.")
        for eid in ids:
            lowered = eid.casefold()
            if "genotype" in lowered or lowered.startswith("class:") or lowered == "class":
                raise ConfigurationError(
                    "mask_named_contacts rejects genotype-class targeting; "
                    "named_contact is a ledger edge ID only."
                )
            if eid not in self.edges:
                raise ConfigurationError(f"unknown edge_id for mask: {eid!r}.")
        masked: list[str] = []
        for eid in ids:
            self.edges[eid].masked = True
            masked.append(eid)
            if one_generation:
                self._one_generation_masks.add(eid)
        return {
            "op": "mask_named_contacts",
            "edge_ids": masked,
            "one_generation": bool(one_generation),
        }

    def reallocate_contact_budget(
        self,
        *,
        class_blind: bool = True,
        zero_sum: bool = True,
        one_generation: bool = True,
        budget: float = 1.0,
    ) -> dict[str, Any]:
        """Reallocate per-boundary contact ATP budget (class-blind, zero-sum)."""

        if not _as_bool(class_blind, "class_blind"):
            raise ConfigurationError("reallocate_contact_budget requires class_blind=True.")
        if not _as_bool(zero_sum, "zero_sum"):
            raise ConfigurationError("reallocate_contact_budget requires zero_sum=True.")
        total = float(require_finite_float("budget", budget))
        if total <= 0.0:
            raise ConfigurationError("budget must be > 0.")
        present = [e for e in self.edges.values() if e.present and not e.masked]
        if not present:
            raise ConfigurationError("no present unmasked edges for budget reallocation.")
        shares = [self._rng.random() for _ in present]
        s = sum(shares) or 1.0
        alloc = {e.edge_id: total * (w / s) for e, w in zip(present, shares, strict=True)}
        if one_generation:
            self._one_generation_budget = dict(alloc)
        return {
            "op": "reallocate_contact_budget",
            "class_blind": True,
            "zero_sum": True,
            "one_generation": bool(one_generation),
            "allocation": alloc,
        }

    def cut_or_restore_named_contact_edge(
        self,
        edge_id: str,
        *,
        restore: bool = False,
    ) -> dict[str, Any]:
        """Cut or restore a named contact edge by ledger edge ID."""

        eid = _as_str(edge_id, "edge_id")
        edge = self._require_edge(eid)
        if restore:
            edge.present = True
            self._cut_buffer.discard(eid)
        else:
            edge.present = False
            self._cut_buffer.add(eid)
        return {
            "op": "cut_or_restore_named_contact_edge",
            "edge_id": eid,
            "restore": bool(restore),
            "present": edge.present,
        }

    def matched_random_edge(self, *, degree: int | None = None) -> str:
        """Pick a present edge for matched-random control (optional degree match)."""

        present = [eid for eid, e in self.edges.items() if e.present]
        if not present:
            raise ConfigurationError("no present edges for matched_random_edge.")
        if degree is None:
            return self._rng.choice(present)
        deg = _as_int(degree, "degree", minimum=0)
        matched = [eid for eid in present if self.edge_degree(eid) == deg]
        if matched:
            return self._rng.choice(matched)
        return min(present, key=lambda e: abs(self.edge_degree(e) - deg))

    def sham_cue_predphase(self, *, offset: float = math.pi) -> dict[str, Any]:
        """SHAM-CUE-PREDPHASE-V1: intervene only on predicted_pressure_phase.

        Must not touch NC-* named-contact edge presence or mask state.
        """

        off = float(require_finite_float("offset", offset))
        before = float(self.predicted_pressure_phase)
        # Force predicted phase to realised + offset (default antiphase π).
        self.predicted_pressure_phase = float(self.realised_pressure_phase) + off
        # Snapshot NC edge state to document non-interference.
        nc_state = {
            eid: {
                "present": self.edges[eid].present if eid in self.edges else False,
                "masked": self.edges[eid].masked if eid in self.edges else False,
            }
            for eid in sorted(NAMED_CONTACT_EDGE_IDS)
        }
        return {
            "op": "sham_cue_predphase",
            "sham_id": SHAM_CUE_PREDPHASE,
            "before": before,
            "after": float(self.predicted_pressure_phase),
            "offset": off,
            "nc_edge_state_unchanged_snapshot": nc_state,
        }

    def snapshot(self) -> dict[str, JsonValue]:
        return {
            "schema": SCHEMA_VERSION,
            "generation_index": int(self.generation_index),
            "predicted_pressure_phase": float(self.predicted_pressure_phase),
            "realised_pressure_phase": float(self.realised_pressure_phase),
            "edges": {eid: edge.to_dict() for eid, edge in sorted(self.edges.items())},
            "atp_yield_by_tag": dict(sorted(self.atp_yield_by_tag.items())),
            "failed_prediction_digests": dict(sorted(self.failed_prediction_digests.items())),
            "recovery_tokens": dict(sorted(self.recovery_tokens.items())),
            "scaffold_edge_sets": {
                k: sorted(v) for k, v in sorted(self.scaffold_edge_sets.items())
            },
        }

    def digest(self) -> str:
        return canonical_digest(self.snapshot(), prefix="contact_atp_ledger")


def build_engine_scaffold_ledger(*, seed: int = 0) -> ContactAtpLedger:
    """Idea4 engine scaffold ledger (edge skeleton for observer coupling).

    Scaffold-only: provides rare-class contact edges, named scaffold set, and
    recovery *token placement* for checkpoint relocate. Does **not** implement
    or enable any harness ``recovery_progress`` multiplier path — engine Idea4
    FI recover is scored from ecology-coupled rare-class ATP yields alone.
    """

    ledger = ContactAtpLedger(rng_seed=int(seed), generation_index=0)
    # Generic contact edges with some rare-class tags (ledger tags only).
    specs = [
        ("E0", "n0", "n1", CONTACT_TAG_RARE, 1.0),
        ("E1", "n1", "n2", CONTACT_TAG_RARE, 1.2),
        ("E2", "n2", "n3", None, 0.5),
        ("E3", "n3", "n0", None, 0.4),
        ("E4", "n0", "n2", CONTACT_TAG_RARE, 0.8),
        ("E5", "n1", "n3", None, 0.6),
    ]
    for eid, src, dst, tag, yld in specs:
        ledger.add_edge(eid, src=src, dst=dst, class_tag=tag, atp_yield=yld)
    # Pre-register named scaffold by edge ID (NOT max-degree rule).
    ledger.register_scaffold("SCAF-CONTACT-SRC-PATH-V1", ["E0", "E1"])
    ledger.place_recovery_token(
        "token:recovery:FI-RARECLASS-CONTACT-YIELD-V1", payload="eligible"
    )
    # Key id "smoke_v1" is locked for ablate_knowledge_digest / PRED_FAIL_DIGEST_KEY
    # compatibility across harness+engine; it is NOT a recovery_progress path.
    ledger.place_failed_prediction_digest(
        "digest:pred_fail:smoke_v1",
        digest=canonical_digest({"kind": "pred_fail", "id": "smoke_v1"}, prefix="digest"),
    )
    return ledger


def build_idea2_engine_scaffold_ledger(*, seed: int = 0) -> ContactAtpLedger:
    """Idea2 engine scaffold ledger with locked NC-* named-contact edge set.

    Scaffold-only skeleton for engine closed-loop arms. Realised antagonist
    pressure comes from GenesisEngine ecology via GenerationBoundaryObserver —
    not from an independent smoke-ledger RNG stream. No recovery_progress path.
    """

    ledger = ContactAtpLedger(
        rng_seed=int(seed),
        generation_index=0,
        predicted_pressure_phase=0.0,
        realised_pressure_phase=0.0,
    )
    slots = [
        ("NC-H0-A0", "H0", "A0"),
        ("NC-H0-A1", "H0", "A1"),
        ("NC-H1-A0", "H1", "A0"),
        ("NC-H1-A1", "H1", "A1"),
        ("NC-H2-A0", "H2", "A0"),
        ("NC-H2-A1", "H2", "A1"),
    ]
    for eid, src, dst in slots:
        ledger.add_edge(eid, src=src, dst=dst, class_tag=None, atp_yield=0.5)
    return ledger


def build_smoke_ledger(*, seed: int = 0) -> ContactAtpLedger:
    """Harness-only alias of :func:`build_engine_scaffold_ledger`.

    Kept for harness smoke / scored jsonl_campaign paths. Engine closed-loop
    modules must call :func:`build_engine_scaffold_ledger` by name (no bare
    smoke symbol on the engine path).
    """

    return build_engine_scaffold_ledger(seed=int(seed))


def build_idea2_smoke_ledger(*, seed: int = 0) -> ContactAtpLedger:
    """Harness-only alias of :func:`build_idea2_engine_scaffold_ledger`.

    Kept for harness smoke / scored jsonl_campaign. Engine Idea2 must call
    :func:`build_idea2_engine_scaffold_ledger` by name.
    """

    return build_idea2_engine_scaffold_ledger(seed=int(seed))
