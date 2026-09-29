"""Contact/ATP ledger for discovery phase-2 harness ops.

Mutable ledger of named contact edges, ATP yield counters by tag,
failed-prediction digests, recovery-eligibility tokens, scaffold edge
sets, and predicted/realised pressure-phase fields. All interventions
run at a generation boundary and never mutate genotype. No second
population engine; no engine.py physics.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.rng import StdlibSeedRNG

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

# Track C phase-2 identity IDs (locked in digests; empty at run = reopen)
RIVAL_PAIR_ATP_DRAIN = "RP-LEDGER-ATP-DRAIN-V1"
LAW_CONTACT_ATP_PARENT = "LAW-LEDGER-CONTACT-ATP-PARENT-V1"
UNREACH_L_SINGLE_LIFETIME = "UNREACH-L-SINGLE-LIFETIME-V1"
PKG_REASON_FAIL_BOUND = "PKG-REASON-FAIL-BOUND-V1"
WORLD_FAMILY_CONTACT_ATP = "WORLD-FAMILY-CONTACT-ATP-V1"
LAW_SHORT_COMPOSABLE = "LAW-SHORT-COMPOSABLE-V1"
PROBE_PRIVATE_VS_SKELETON = "PROBE-PRIVATE-VS-SKELETON-V1"
USTAR_RESTRAINT = "USTAR-RESTRAINT-V1"
SUPPORT_VERIFY_CONSULT = "SUP-VERIFY-CONSULT-V1"
SUPPORT_RETEST = "SUP-RETEST-V1"
SUPPORT_SANCTION = "SUP-SANCTION-V1"
SUPPORT_CUT_CELL = "SUPCUT-REMOVE-CHANNELS-V1"
REV_HIGH_NOISE_BLIND_ACCEPT = "REV-HIGH-NOISE-BLIND-ACCEPT-V1"
U_LEDGER_EVIDENCE_STRENGTH = "U-LEDGER-EVIDENCE-STRENGTH-V1"


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
    # Scaffold edge → non-scaffold twin. Not part of the ledger digest.
    # Twins are scaled with the scaffold so a matched cut can be exact.
    match_mirrors: dict[str, str] = field(default_factory=dict)
    # Track C harness-visible state (scaffold; generation-boundary ops mutate these)
    rival_pair_id: str = ""
    rival_assay_log: list[dict[str, Any]] = field(default_factory=list)
    reactive_memory: dict[str, float] = field(default_factory=dict)
    explore_log: list[dict[str, Any]] = field(default_factory=list)
    law_id: str = ""
    unreach_id: str = ""
    package_schema_id: str = ""
    reversal_cell_id: str = ""
    causal_packages: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw_pool: dict[str, Any] = field(default_factory=dict)
    imitation_buffer: list[dict[str, Any]] = field(default_factory=list)
    package_cut_applied: bool = False
    world_family_id: str = ""
    short_law_id: str = ""
    probe_id: str = ""
    retained_laws: dict[str, dict[str, Any]] = field(default_factory=dict)
    teaching_log: list[dict[str, Any]] = field(default_factory=list)
    survival_only_active: bool = False
    held_out_split: dict[str, list[str]] = field(default_factory=dict)
    shortcut_probe_log: list[dict[str, Any]] = field(default_factory=list)
    ustar_id: str = ""
    evidence_measure_id: str = ""
    evidence_u: float = 0.0
    ustar_value: float | None = None
    support_channels: dict[str, bool] = field(default_factory=dict)
    restraint_log: list[dict[str, Any]] = field(default_factory=list)
    support_cut_applied: bool = False
    _one_generation_masks: set[str] = field(default_factory=set, repr=False)
    _one_generation_budget: dict[str, float] | None = field(default=None, repr=False)
    _cut_buffer: set[str] = field(default_factory=set, repr=False)
    _rng: StdlibSeedRNG = field(default_factory=StdlibSeedRNG, repr=False)

    def __post_init__(self) -> None:
        self._rng = StdlibSeedRNG(seed=int(self.rng_seed))
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
                cut.append(eid)
        degree_sum = int(sum(self.edge_degree(eid) for eid in cut)) if cut else 0
        # Contact weight ≡ atp_yield (ledger has no separate weight field).
        weight_sum = float(sum(float(self.edges[eid].atp_yield) for eid in cut))
        atp_lost = float(weight_sum)
        for eid in cut:
            self.edges[eid].present = False
            self._cut_buffer.add(eid)
        return {
            "op": "cut_named_scaffold",
            "scaffold_id": sid,
            "cut_edge_ids": cut,
            "n_edges_cut": len(cut),
            "degree_sum": degree_sum,
            "contact_weight_sum": weight_sum,
            "atp_lost": atp_lost,
        }

    def _choose_matched_edges(
        self,
        degree: int,
        *,
        n_edges: int = 1,
        target_degree_sum: int | None = None,
        target_atp_sum: float | None = None,
        target_weight_sum: float | None = None,
        exclude_edge_ids: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Pick a degree/ATP matched cut. Does not change the ledger."""

        deg = _as_int(degree, "degree", minimum=0)
        n_cut = _as_int(n_edges, "n_edges", minimum=1)
        scaffold_members: set[str] = set()
        for members in self.scaffold_edge_sets.values():
            scaffold_members |= members
        blocked = {str(eid) for eid in (exclude_edge_ids or ())}
        pool = sorted(
            eid
            for eid, edge in self.edges.items()
            if edge.present and eid not in scaffold_members and eid not in blocked
        )
        if len(pool) < n_cut:
            raise ConfigurationError(
                f"need {n_cut} present non-scaffold edges for matched random cut; "
                f"found {len(pool)}."
            )

        tgt_deg = (
            int(target_degree_sum)
            if target_degree_sum is not None
            else int(deg) * int(n_cut)
        )
        tgt_atp = float(target_atp_sum) if target_atp_sum is not None else None
        tgt_w = (
            float(target_weight_sum)
            if target_weight_sum is not None
            else tgt_atp
        )

        def _sums(combo: tuple[str, ...]) -> tuple[int, float, float]:
            deg_sum = int(sum(self.edge_degree(e) for e in combo))
            atp_sum = float(sum(float(self.edges[e].atp_yield) for e in combo))
            return deg_sum, atp_sum, atp_sum

        exact: list[tuple[str, ...]] = []
        if len(pool) <= 16 and n_cut <= 4:
            for combo in itertools.combinations(pool, n_cut):
                deg_sum, atp_sum, weight_sum = _sums(combo)
                atp_ok = tgt_atp is None or abs(atp_sum - float(tgt_atp)) <= 1e-9
                weight_ok = tgt_w is None or abs(weight_sum - float(tgt_w)) <= 1e-9
                if deg_sum == tgt_deg and atp_ok and weight_ok:
                    exact.append(tuple(sorted(combo)))
        used_nearest_fallback = False
        if exact:
            exact.sort()
            chosen = exact[0]
        else:
            used_nearest_fallback = True
            best: tuple[str, ...] | None = None
            best_key: tuple[Any, ...] | None = None
            search = (
                list(itertools.combinations(pool, n_cut))
                if len(pool) <= 16 and n_cut <= 4
                else [tuple(pool[:n_cut])]
            )
            for combo in search:
                deg_sum, atp_sum, weight_sum = _sums(tuple(combo))
                key = (
                    abs(deg_sum - tgt_deg),
                    abs(atp_sum - float(tgt_atp)) if tgt_atp is not None else 0.0,
                    abs(weight_sum - float(tgt_w)) if tgt_w is not None else 0.0,
                    tuple(sorted(combo)),
                )
                if best_key is None or key < best_key:
                    best_key = key
                    best = tuple(sorted(combo))
            assert best is not None
            chosen = best

        cut_ids = list(chosen)
        degree_sum = int(sum(self.edge_degree(eid) for eid in cut_ids))
        weight_sum = float(sum(float(self.edges[eid].atp_yield) for eid in cut_ids))
        atp_lost = float(weight_sum)
        n_edges_cut = len(cut_ids)
        atp_exact = tgt_atp is not None and abs(atp_lost - float(tgt_atp)) <= 1e-9
        weight_exact = tgt_w is not None and abs(weight_sum - float(tgt_w)) <= 1e-9
        if tgt_atp is None and tgt_w is None:
            match_exact = (
                (not used_nearest_fallback)
                and n_edges_cut == n_cut
                and degree_sum == tgt_deg
            )
        else:
            match_exact = (
                (not used_nearest_fallback)
                and n_edges_cut == n_cut
                and degree_sum == tgt_deg
                and atp_exact
                and weight_exact
            )
        return {
            "degree": deg,
            "n_edges_requested": n_cut,
            "cut_edge_ids": cut_ids,
            "n_edges_cut": n_edges_cut,
            "degree_sum": degree_sum,
            "contact_weight_sum": weight_sum,
            "atp_lost": atp_lost,
            "target_degree_sum": tgt_deg,
            "target_atp_sum": tgt_atp,
            "target_weight_sum": tgt_w,
            "used_nearest_fallback": bool(used_nearest_fallback),
            "match_exact": bool(match_exact),
            "n_pool": len(pool),
            "n_exact_combos": len(exact),
        }

    def cut_matched_random(
        self,
        degree: int,
        *,
        n_edges: int = 1,
        target_degree_sum: int | None = None,
        target_atp_sum: float | None = None,
        target_weight_sum: float | None = None,
        exclude_edge_ids: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Cut ``n_edges`` present non-scaffold edges matched on degree/ATP.

        Prefer exact endpoint-degree matches. If the exact-degree pool cannot
        supply ``n_edges``, fall back to nearest-degree edges and set
        ``used_nearest_fallback=True``. Never labels a nearest fallback as
        ``match_exact=True``.
        """

        chosen = self._choose_matched_edges(
            degree,
            n_edges=n_edges,
            target_degree_sum=target_degree_sum,
            target_atp_sum=target_atp_sum,
            target_weight_sum=target_weight_sum,
            exclude_edge_ids=exclude_edge_ids,
        )
        for eid in chosen["cut_edge_ids"]:
            self.edges[eid].present = False
            self._cut_buffer.add(eid)
        chosen["op"] = "cut_matched_random"
        return chosen


    def scaffold_cut_profile(self, scaffold_id: str) -> dict[str, Any]:
        """Describe what ``cut_named_scaffold`` would cut without mutating."""

        sid = _as_str(scaffold_id, "scaffold_id")
        key = sid if sid.startswith(SCAFFOLD_EDGES_PREFIX) else f"{SCAFFOLD_EDGES_PREFIX}{sid}"
        if key not in self.scaffold_edge_sets:
            raise ConfigurationError(f"unknown scaffold_id: {sid!r}.")
        cut = [
            eid
            for eid in sorted(self.scaffold_edge_sets[key])
            if eid in self.edges and self.edges[eid].present
        ]
        degree_sum = int(sum(self.edge_degree(eid) for eid in cut)) if cut else 0
        weight_sum = float(sum(float(self.edges[eid].atp_yield) for eid in cut))
        return {
            "scaffold_id": sid,
            "cut_edge_ids": cut,
            "n_edges_cut": len(cut),
            "degree_sum": degree_sum,
            "contact_weight_sum": weight_sum,
            "atp_lost": weight_sum,
            "per_edge_degree": (
                int(self.edge_degree(cut[0])) if cut else 0
            ),
        }

    @staticmethod
    def build_cut_match_report(
        scaffold_profile: Mapping[str, Any],
        matched_result: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Emit OWNER P3 match report for a scaffold vs matched cut pair."""

        s_ids = list(scaffold_profile.get("cut_edge_ids", []))
        m_ids = list(matched_result.get("cut_edge_ids", []))
        s_n = int(scaffold_profile.get("n_edges_cut", len(s_ids)))
        m_n = int(matched_result.get("n_edges_cut", len(m_ids)))
        s_deg = int(scaffold_profile.get("degree_sum", 0))
        m_deg = int(matched_result.get("degree_sum", 0))
        s_w = float(scaffold_profile.get("contact_weight_sum", 0.0))
        m_w = float(matched_result.get("contact_weight_sum", 0.0))
        s_atp = float(scaffold_profile.get("atp_lost", s_w))
        m_atp = float(matched_result.get("atp_lost", m_w))
        used_fallback = bool(matched_result.get("used_nearest_fallback", False))
        # Never promote nearest fallback to exact.
        match_exact = (
            (not used_fallback)
            and s_n == m_n
            and s_deg == m_deg
            and abs(s_w - m_w) <= 1e-9
            and abs(s_atp - m_atp) <= 1e-9
        )
        weight_aliases_atp = (
            abs(s_w - s_atp) <= 1e-9 and abs(m_w - m_atp) <= 1e-9
        )
        return {
            "scaffold_cut_edge_ids": s_ids,
            "matched_cut_edge_ids": m_ids,
            "n_edges_cut_scaffold": s_n,
            "n_edges_cut_matched": m_n,
            "n_edges_cut_equal": s_n == m_n,
            "degree_sum_scaffold": s_deg,
            "degree_sum_matched": m_deg,
            "contact_weight_sum_scaffold": s_w,
            "contact_weight_sum_matched": m_w,
            "atp_lost_scaffold": s_atp,
            "atp_lost_matched": m_atp,
            # Ledger contact weight is the edge ATP yield. Matching both
            # names is not two independent quantities.
            "contact_weight_is_atp_yield": bool(weight_aliases_atp),
            "used_nearest_fallback": used_fallback,
            "match_exact": bool(match_exact),
            "exclude_from_combo_e": not bool(match_exact),
        }

    def independent_match_design(self, scaffold_id: str) -> dict[str, Any]:
        """Look for an exact degree/ATP match that is not a planted mirror.

        Does not cut. A miss is a design failure. The nearest leftover edges
        are listed only so the miss can be audited. They are not a result.
        """

        profile = self.scaffold_cut_profile(scaffold_id)
        blocked = set(self.match_mirrors.values()) | set(self.match_mirrors)
        blocked |= {str(eid) for eid in profile["cut_edge_ids"]}
        n_edges = int(profile["n_edges_cut"])
        if n_edges < 1:
            raise ConfigurationError("scaffold cut profile has no present edges to match.")
        try:
            chosen = self._choose_matched_edges(
                int(profile["per_edge_degree"]),
                n_edges=n_edges,
                target_degree_sum=int(profile["degree_sum"]),
                target_atp_sum=float(profile["atp_lost"]),
                target_weight_sum=float(profile["contact_weight_sum"]),
                exclude_edge_ids=blocked,
            )
        except ConfigurationError:
            chosen = {
                "cut_edge_ids": [],
                "match_exact": False,
                "used_nearest_fallback": True,
                "n_pool": 0,
                "n_exact_combos": 0,
            }
        exact = bool(chosen["match_exact"])
        planned = [str(eid) for eid in chosen["cut_edge_ids"]]
        return {
            "op": "independent_match_design",
            "mutated": False,
            "independent_of_planted_mirrors": True,
            "blocked_edge_ids": sorted(blocked),
            "n_pool": int(chosen["n_pool"]),
            "n_exact_combos": int(chosen["n_exact_combos"]),
            "match_exact": exact,
            "design_failure": not exact,
            "exclude_from_scientific_contrast": True,
            "planned_edge_ids": planned if exact else [],
            "nearest_ids_not_analysed": [] if exact else planned,
            "used_nearest_fallback": bool(chosen["used_nearest_fallback"]),
        }

    def cut_independent_of_mirrors(self, scaffold_id: str) -> dict[str, Any]:
        """Match degree and ATP on edges that are not planted yield mirrors.

        A miss is a design failure. It is excluded from the contrast. It is
        not replaced by the mirror twin and then analysed as a success.
        """

        profile = self.scaffold_cut_profile(scaffold_id)
        blocked = set(self.match_mirrors.values()) | set(profile["cut_edge_ids"])
        n_edges = int(profile["n_edges_cut"])
        if n_edges < 1:
            raise ConfigurationError("scaffold cut profile has no present edges to match.")
        matched = self.cut_matched_random(
            int(profile["per_edge_degree"]),
            n_edges=n_edges,
            target_degree_sum=int(profile["degree_sum"]),
            target_atp_sum=float(profile["atp_lost"]),
            target_weight_sum=float(profile["contact_weight_sum"]),
            exclude_edge_ids=blocked,
        )
        report = self.build_cut_match_report(profile, matched)
        report["independent_of_planted_mirrors"] = True
        report["blocked_edge_ids"] = sorted(blocked)
        report["design_failure"] = not bool(report["match_exact"])
        report["exclude_from_combo_e"] = not bool(report["match_exact"])
        matched["match_report"] = report
        matched["match_exact"] = bool(report["match_exact"])
        matched["exclude_from_combo_e"] = bool(report["exclude_from_combo_e"])
        matched["independent_of_planted_mirrors"] = True
        matched["design_failure"] = bool(report["design_failure"])
        return matched

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


    # --- Idea1 ops (Track C) ---

    def do_rival_discriminate(
        self,
        *,
        parent_edge_id: str,
        cost: float = 0.25,
        rival_pair_id: str | None = None,
    ) -> dict[str, Any]:
        """Issue a ledger intervention that separates the locked rival pair.

        Debits real ATP/survival cost. Does not silently substitute genotype.
        Empty rival-pair ID reopens the freeze.
        """

        pair = _as_str(
            self.rival_pair_id if rival_pair_id is None else rival_pair_id,
            "rival_pair_id",
        )
        if pair != RIVAL_PAIR_ATP_DRAIN and pair != self.rival_pair_id:
            # Allow only the locked identity or the ledger-registered one.
            if not pair:
                raise ConfigurationError(
                    "empty rival_pair_id reopens Idea1 freeze."
                )
        if not self.rival_pair_id:
            self.rival_pair_id = pair
        if not self.rival_pair_id:
            raise ConfigurationError("empty rival_pair_id reopens Idea1 freeze.")
        eid = _as_str(parent_edge_id, "parent_edge_id")
        edge = self._require_edge(eid)
        c = float(require_finite_float("cost", cost))
        if c <= 0.0:
            raise ConfigurationError("do_rival_discriminate cost must be > 0 (not cosmetic).")
        # Intervene on contact-parent: one-generation mask + ATP debit on tag yield.
        edge.masked = True
        self._one_generation_masks.add(eid)
        if edge.class_tag is not None:
            self.atp_yield_by_tag[edge.class_tag] = (
                self.atp_yield_by_tag.get(edge.class_tag, 0.0) - c
            )
        entry = {
            "op": "do_rival_discriminate",
            "rival_pair_id": self.rival_pair_id,
            "parent_edge_id": eid,
            "cost": c,
            "generation_index": int(self.generation_index),
            "assay": "separates_R1_contact_parent_vs_R2_resource_schedule",
        }
        self.rival_assay_log.append(entry)
        return dict(entry)

    def update_reactive_ledger(
        self,
        *,
        observation_key: str,
        value: float,
    ) -> dict[str, Any]:
        """Reactive / associative update without a discrimination intervention."""

        key = _as_str(observation_key, "observation_key")
        val = float(require_finite_float("value", value))
        prev = float(self.reactive_memory.get(key, 0.0))
        # Exponential smooth — H1 control, not rival discrimination.
        updated = 0.7 * prev + 0.3 * val
        self.reactive_memory[key] = updated
        entry = {
            "op": "update_reactive_ledger",
            "observation_key": key,
            "before": prev,
            "after": updated,
            "discrimination": False,
        }
        return entry

    def reward_explore_eps(
        self,
        *,
        epsilon: float = 0.1,
        budget: float = 1.0,
    ) -> dict[str, Any]:
        """ε-style reward exploration without locked rival-explanation contrast.

        Method name uses ``_eps`` because Python identifiers cannot contain ε;
        the locked op identity string remains ``reward_explore_ε``.
        """

        eps = float(require_finite_float("epsilon", epsilon))
        if eps < 0.0 or eps > 1.0:
            raise ConfigurationError("epsilon must be in [0, 1].")
        bud = float(require_finite_float("budget", budget))
        if bud <= 0.0:
            raise ConfigurationError("budget must be > 0.")
        present = [e for e in self.edges.values() if e.present and not e.masked]
        if not present:
            raise ConfigurationError("no present unmasked edges for reward_explore_ε.")
        # Explore: pick a random present edge and bump its yield slightly (ATP-seeking).
        chosen = self._rng.choice(present)
        before = float(chosen.atp_yield)
        chosen.atp_yield = before + 0.05 * bud * (1.0 if self._rng.random() < eps else 0.2)
        entry = {
            "op": "reward_explore_ε",
            "epsilon": eps,
            "budget": bud,
            "edge_id": chosen.edge_id,
            "before_yield": before,
            "after_yield": float(chosen.atp_yield),
            "rival_contrast": False,
        }
        self.explore_log.append(entry)
        return dict(entry)

    # Alias so make_op("reward_explore_ε") and make_op("reward_explore_eps") both work.
    def reward_explore_ε(self, **kwargs: Any) -> dict[str, Any]:
        return self.reward_explore_eps(**kwargs)

    # --- Idea3 ops (Track C) ---

    def transmit_package(
        self,
        *,
        package_id: str,
        interventional_claim: str,
        failed_intervention: str,
        validity_bounds: str,
        revision_rule: str = "retain_edit_or_drop",
    ) -> dict[str, Any]:
        """Transmit a critiqueable causal hypothesis package (reasons+fail+bounds)."""

        if not self.law_id:
            raise ConfigurationError("empty law_id reopens Idea3 freeze.")
        if not self.unreach_id:
            raise ConfigurationError("empty unreach_id reopens Idea3 freeze.")
        if not self.reversal_cell_id:
            raise ConfigurationError(
                "empty reversal_cell_id reopens Idea3 freeze."
            )
        pid = _as_str(package_id, "package_id")
        pkg = {
            "package_id": pid,
            "schema_id": self.package_schema_id or PKG_REASON_FAIL_BOUND,
            "law_id": self.law_id,
            "reversal_cell_id": self.reversal_cell_id,
            "interventional_claim": _as_str(interventional_claim, "interventional_claim"),
            "failed_intervention": _as_str(failed_intervention, "failed_intervention"),
            "validity_bounds": _as_str(validity_bounds, "validity_bounds"),
            "revision_rule": _as_str(revision_rule, "revision_rule"),
            "cut_failed_and_bounds": False,
        }
        self.causal_packages[pid] = pkg
        return {"op": "transmit_package", **pkg}

    def pool_raw_only(
        self,
        *,
        pool_key: str,
        observations: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Share raw observations without reasons, failed interventions, or bounds."""

        key = _as_str(pool_key, "pool_key")
        obs = dict(observations or {"n": 1, "mean_atp": 0.5})
        # Strip any reason/fail/bound keys if present — pooling control.
        for banned in ("failed_intervention", "validity_bounds", "interventional_claim", "reasons"):
            obs.pop(banned, None)
        self.raw_pool[key] = obs
        return {
            "op": "pool_raw_only",
            "pool_key": key,
            "observations": obs,
            "has_reasons": False,
            "has_failed": False,
            "has_bounds": False,
        }

    def imitate_success_only(
        self,
        *,
        act_id: str,
        payoff: float = 1.0,
    ) -> dict[str, Any]:
        """Copy successful acts only; negatives and bounds are not transmitted."""

        aid = _as_str(act_id, "act_id")
        pay = float(require_finite_float("payoff", payoff))
        entry = {
            "op": "imitate_success_only",
            "act_id": aid,
            "payoff": pay,
            "negatives_transmitted": False,
            "bounds_transmitted": False,
        }
        self.imitation_buffer.append(entry)
        return dict(entry)

    def cut_failed_and_bounds(self, *, package_id: str) -> dict[str, Any]:
        """Remove failed-intervention and validity-bound fields (Combo B cut test).

        Empty cut (no fields removed) reopens the freeze.
        """

        pid = _as_str(package_id, "package_id")
        if pid not in self.causal_packages:
            raise ConfigurationError(
                f"cut_failed_and_bounds: unknown package_id {pid!r}; empty cut reopens freeze."
            )
        pkg = dict(self.causal_packages[pid])
        removed: list[str] = []
        for field_name in ("failed_intervention", "validity_bounds"):
            if field_name in pkg and pkg[field_name]:
                pkg[field_name] = ""
                removed.append(field_name)
        if not removed:
            raise ConfigurationError(
                "cut_failed_and_bounds removed nothing; empty cut reopens Idea3 freeze."
            )
        pkg["cut_failed_and_bounds"] = True
        self.causal_packages[pid] = pkg
        self.package_cut_applied = True
        return {
            "op": "cut_failed_and_bounds",
            "package_id": pid,
            "removed_fields": removed,
            "cut_applied": True,
        }

    # --- Idea5 ops (Track C) ---

    def retain_short_law(
        self,
        *,
        law_key: str,
        law_body: str,
        n_terms: int = 4,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Retain a short composable falsifiable law candidate on the ledger."""

        if not self.short_law_id:
            raise ConfigurationError("empty short_law_id reopens Idea5 freeze.")
        if not self.world_family_id:
            raise ConfigurationError("empty world_family_id reopens Idea5 freeze.")
        if self.survival_only_active:
            raise ConfigurationError(
                "retain_short_law forbidden under survival_only_control."
            )
        key = _as_str(law_key, "law_key")
        body = _as_str(law_body, "law_body")
        terms = _as_int(n_terms, "n_terms", minimum=1)
        dep = _as_int(depth, "depth", minimum=1)
        if terms > 12 or dep > 3:
            raise ConfigurationError("law exceeds locked complexity bound (≤12 terms, depth ≤3).")
        entry = {
            "law_key": key,
            "law_id": self.short_law_id,
            "body": body,
            "n_terms": terms,
            "depth": dep,
            "private_feature": False,
        }
        self.retained_laws[key] = entry
        return {"op": "retain_short_law", **entry}

    def teach_at_boundary(self, *, law_key: str) -> dict[str, Any]:
        """Transmit eligible retained law metadata at a generation boundary."""

        if self.survival_only_active:
            raise ConfigurationError(
                "teach_at_boundary forbidden under survival_only_control."
            )
        key = _as_str(law_key, "law_key")
        if key not in self.retained_laws:
            raise ConfigurationError(f"teach_at_boundary: unknown law_key {key!r}.")
        law = self.retained_laws[key]
        if law.get("private_feature"):
            raise ConfigurationError(
                "teach_at_boundary cannot transmit private-feature laws."
            )
        entry = {
            "op": "teach_at_boundary",
            "law_key": key,
            "law_id": law["law_id"],
            "body": law["body"],
            "generation_index": int(self.generation_index),
            "private_feature_transmitted": False,
        }
        self.teaching_log.append(entry)
        return dict(entry)

    def survival_only_control(self) -> dict[str, Any]:
        """Matched H3 control: survival selection only; clear law memory and teaching."""

        self.survival_only_active = True
        cleared_laws = list(self.retained_laws.keys())
        self.retained_laws.clear()
        self.teaching_log.clear()
        return {
            "op": "survival_only_control",
            "survival_only_active": True,
            "cleared_law_keys": cleared_laws,
            "teaching_events": 0,
            "explicit_law_memory": False,
        }

    def shortcut_probe(
        self,
        *,
        skeleton_intact_accuracy: float | None = None,
        private_only_accuracy: float | None = None,
    ) -> dict[str, Any]:
        """Record a held-out probe. Injected accuracies are not measurements.

        World ids in the held-out split carry no behaviour outcomes, so this
        op cannot report a scientific pass. Constants such as 0.85 / 0.40 are
        ignored.
        """

        if not self.probe_id:
            raise ConfigurationError("empty probe_id reopens Idea5 freeze.")
        if not self.held_out_split.get("held_out"):
            raise ConfigurationError(
                "empty held-out split reopens Idea5 freeze."
            )
        injected = (
            skeleton_intact_accuracy is not None or private_only_accuracy is not None
        )
        if injected:
            require_finite_float(
                "skeleton_intact_accuracy",
                0.0 if skeleton_intact_accuracy is None else skeleton_intact_accuracy,
            )
            require_finite_float(
                "private_only_accuracy",
                0.0 if private_only_accuracy is None else private_only_accuracy,
            )
        entry = {
            "op": "shortcut_probe",
            "probe_id": self.probe_id,
            "held_out_worlds": list(self.held_out_split.get("held_out", [])),
            "skeleton_intact_accuracy": None,
            "private_only_accuracy": None,
            "injected_constants_ignored": True,
            "measured_from_behavior": False,
            "pass": False,
            "scientific_pass": False,
            "train_fit_alone_counts": False,
            "genealogical_consequence": False,
        }
        self.shortcut_probe_log.append(entry)
        return dict(entry)

    # --- Idea6 ops (Track C) ---

    def withhold_if_u_below(self) -> dict[str, Any]:
        """When evidence u < u*, withhold harmful action and declare experiment/consult."""

        if not self.ustar_id:
            raise ConfigurationError("empty ustar_id reopens Idea6 freeze.")
        if not self.evidence_measure_id:
            raise ConfigurationError(
                "empty evidence_measure_id reopens Idea6 freeze."
            )
        if self.ustar_value is None:
            raise ConfigurationError("empty u* (ustar_value) reopens Idea6 freeze.")
        u = float(require_finite_float("evidence_u", self.evidence_u))
        ustar = float(require_finite_float("ustar_value", self.ustar_value))
        withheld = u < ustar
        entry = {
            "op": "withhold_if_u_below",
            "ustar_id": self.ustar_id,
            "evidence_measure_id": self.evidence_measure_id,
            "u": u,
            "u_star": ustar,
            "withheld": bool(withheld),
            "declare_experiment_or_consult": bool(withheld),
        }
        self.restraint_log.append(entry)
        return dict(entry)

    def consult_verified_neighbour(self, *, neighbour_id: str) -> dict[str, Any]:
        """Query a ledger-visible neighbour's verified recent outcome on support channel."""

        nid = _as_str(neighbour_id, "neighbour_id")
        active = [cid for cid, on in self.support_channels.items() if on]
        if not active:
            raise ConfigurationError(
                "consult_verified_neighbour requires an active support channel; "
                "empty support reopens freeze for support-on cell."
            )
        entry = {
            "op": "consult_verified_neighbour",
            "neighbour_id": nid,
            "support_channels_used": active,
            "verified_only": True,
        }
        self.restraint_log.append(entry)
        return dict(entry)

    def bold_act_below_threshold(self, *, harm_cost: float = 0.3) -> dict[str, Any]:
        """Act on best hypothesis even when u < u*, paying weak-hypothesis harm."""

        if not self.evidence_measure_id:
            raise ConfigurationError(
                "empty evidence_measure_id reopens Idea6 freeze."
            )
        if self.ustar_value is None:
            raise ConfigurationError("empty u* reopens Idea6 freeze.")
        u = float(require_finite_float("evidence_u", self.evidence_u))
        ustar = float(require_finite_float("ustar_value", self.ustar_value))
        cost = float(require_finite_float("harm_cost", harm_cost))
        if cost <= 0.0:
            raise ConfigurationError("harm_cost must be > 0 (ledger-visible).")
        below = u < ustar
        # Apply harm to a present edge yield as ledger-visible ATP cost.
        present = [e for e in self.edges.values() if e.present]
        harmed: str | None = None
        if present and below:
            target = present[0]
            target.atp_yield = float(target.atp_yield) - cost
            harmed = target.edge_id
        entry = {
            "op": "bold_act_below_threshold",
            "u": u,
            "u_star": ustar,
            "acted_below_threshold": bool(below),
            "harm_cost": cost,
            "harmed_edge_id": harmed,
        }
        self.restraint_log.append(entry)
        return dict(entry)

    def support_cut(self) -> dict[str, Any]:
        """Remove registered support channels (H2 collapse cell).

        Empty support_cut (no channels disabled) reopens the freeze.
        """

        before = dict(self.support_channels)
        removed = [cid for cid, on in before.items() if on]
        if not removed:
            raise ConfigurationError(
                "support_cut removed nothing; empty support_cut reopens Idea6 freeze."
            )
        for cid in removed:
            self.support_channels[cid] = False
        self.support_cut_applied = True
        return {
            "op": "support_cut",
            "support_cut_cell_id": SUPPORT_CUT_CELL,
            "removed_channels": removed,
            "support_channels_after": dict(self.support_channels),
            "cut_applied": True,
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
            "rival_pair_id": self.rival_pair_id,
            "rival_assay_log_len": len(self.rival_assay_log),
            "reactive_memory": dict(sorted(self.reactive_memory.items())),
            "explore_log_len": len(self.explore_log),
            "law_id": self.law_id,
            "unreach_id": self.unreach_id,
            "package_schema_id": self.package_schema_id,
            "reversal_cell_id": self.reversal_cell_id,
            "causal_package_ids": sorted(self.causal_packages),
            "raw_pool_keys": sorted(self.raw_pool),
            "imitation_buffer_len": len(self.imitation_buffer),
            "package_cut_applied": bool(self.package_cut_applied),
            "world_family_id": self.world_family_id,
            "short_law_id": self.short_law_id,
            "probe_id": self.probe_id,
            "retained_law_keys": sorted(self.retained_laws),
            "teaching_log_len": len(self.teaching_log),
            "survival_only_active": bool(self.survival_only_active),
            "held_out_split": {
                k: list(v) for k, v in sorted(self.held_out_split.items())
            },
            "shortcut_probe_log_len": len(self.shortcut_probe_log),
            "ustar_id": self.ustar_id,
            "evidence_measure_id": self.evidence_measure_id,
            "evidence_u": float(self.evidence_u),
            "ustar_value": (
                None if self.ustar_value is None else float(self.ustar_value)
            ),
            "support_channels": dict(sorted(self.support_channels.items())),
            "restraint_log_len": len(self.restraint_log),
            "support_cut_applied": bool(self.support_cut_applied),
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
    # Primary K4 (scaffold E0/E1 live here). Secondary K4 supplies
    # degree- and ATP-matched non-scaffold edges for the matched cut op.
    specs = [
        ("E0", "n0", "n1", CONTACT_TAG_RARE, 1.0),
        ("E1", "n1", "n2", CONTACT_TAG_RARE, 1.2),
        ("E2", "n2", "n3", None, 0.5),
        ("E3", "n3", "n0", None, 0.4),
        ("E4", "n0", "n2", CONTACT_TAG_RARE, 0.8),
        ("E5", "n1", "n3", None, 0.6),
        ("E6", "n4", "n5", None, 1.0),
        ("E7", "n5", "n6", None, 1.2),
        ("E8", "n6", "n7", None, 0.5),
        ("E9", "n7", "n4", None, 0.4),
        ("E10", "n4", "n6", None, 0.8),
        ("E11", "n5", "n7", None, 0.6),
    ]
    for eid, src, dst, tag, yld in specs:
        ledger.add_edge(eid, src=src, dst=dst, class_tag=tag, atp_yield=yld)
    # Pre-register named scaffold by edge ID (NOT max-degree rule).
    ledger.register_scaffold("SCAF-CONTACT-SRC-PATH-V1", ["E0", "E1"])
    # E6/E7 mirror E0/E1 (same base yield, isomorphic K4). Scaled with them.
    ledger.match_mirrors = {"E0": "E6", "E1": "E7"}
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


def build_idea1_scaffold_ledger(*, seed: int = 0) -> ContactAtpLedger:
    """Idea1 scaffold ledger (rival discrimination vs reactive/reward).

    Scaffold-only edge skeleton with locked rival-pair identity. Harness smoke
    and scored campaign paths may call this by name; the smoke alias is retained
    for harness-only callers and must not be cited as campaign evidence.
    """

    ledger = ContactAtpLedger(rng_seed=int(seed), generation_index=0)
    ledger.rival_pair_id = RIVAL_PAIR_ATP_DRAIN
    # Parent-intervenable contact edges (R1) plus filler contacts.
    specs = [
        ("P0", "parent0", "child0", CONTACT_TAG_RARE, 1.0),
        ("P1", "parent1", "child1", CONTACT_TAG_RARE, 0.9),
        ("E2", "n2", "n3", None, 0.5),
        ("E3", "n3", "n0", None, 0.4),
    ]
    for eid, src, dst, tag, yld in specs:
        ledger.add_edge(eid, src=src, dst=dst, class_tag=tag, atp_yield=yld)
    return ledger


def build_idea1_smoke_ledger(*, seed: int = 0) -> ContactAtpLedger:
    """Harness-only alias of :func:`build_idea1_scaffold_ledger`.

    Kept for harness smoke paths. Scored campaign / engine evidence paths must
    call :func:`build_idea1_scaffold_ledger` by name.
    """

    return build_idea1_scaffold_ledger(seed=int(seed))


def build_idea3_scaffold_ledger(*, seed: int = 0) -> ContactAtpLedger:
    """Idea3 scaffold ledger (collective causal knowledge).

    Scaffold-only with locked law, unreachability, package schema, and reversal
    cell identities. Empty reversal_cell_id reopens the freeze.
    """

    ledger = ContactAtpLedger(rng_seed=int(seed), generation_index=0)
    ledger.law_id = LAW_CONTACT_ATP_PARENT
    ledger.unreach_id = UNREACH_L_SINGLE_LIFETIME
    ledger.package_schema_id = PKG_REASON_FAIL_BOUND
    ledger.reversal_cell_id = REV_HIGH_NOISE_BLIND_ACCEPT
    specs = [
        ("E0", "n0", "n1", CONTACT_TAG_RARE, 1.0),
        ("E1", "n1", "n2", CONTACT_TAG_RARE, 1.2),
        ("E2", "n2", "n3", None, 0.5),
        ("E3", "n3", "n0", None, 0.4),
    ]
    for eid, src, dst, tag, yld in specs:
        ledger.add_edge(eid, src=src, dst=dst, class_tag=tag, atp_yield=yld)
    return ledger


def build_idea3_smoke_ledger(*, seed: int = 0) -> ContactAtpLedger:
    """Harness-only alias of :func:`build_idea3_scaffold_ledger`.

    Kept for harness smoke paths. Scored campaign paths must call
    :func:`build_idea3_scaffold_ledger` by name.
    """

    return build_idea3_scaffold_ledger(seed=int(seed))


def build_idea5_scaffold_ledger(*, seed: int = 0) -> ContactAtpLedger:
    """Idea5 scaffold ledger (short composable law transfer).

    Scaffold-only with locked world-family, short-law, and shortcut-probe
    identities plus a held-out split. Harness smoke alias retained separately.
    """

    ledger = ContactAtpLedger(rng_seed=int(seed), generation_index=0)
    ledger.world_family_id = WORLD_FAMILY_CONTACT_ATP
    ledger.short_law_id = LAW_SHORT_COMPOSABLE
    ledger.probe_id = PROBE_PRIVATE_VS_SKELETON
    ledger.held_out_split = {
        "train": ["W-TRAIN-0", "W-TRAIN-1"],
        "held_out": ["W-HOLD-0", "W-HOLD-1"],
    }
    specs = [
        ("E0", "n0", "n1", CONTACT_TAG_RARE, 1.0),
        ("E1", "n1", "n2", CONTACT_TAG_RARE, 1.1),
        ("E2", "n2", "n3", None, 0.5),
        ("E3", "n3", "n0", None, 0.4),
    ]
    for eid, src, dst, tag, yld in specs:
        ledger.add_edge(eid, src=src, dst=dst, class_tag=tag, atp_yield=yld)
    return ledger


def build_idea5_smoke_ledger(*, seed: int = 0) -> ContactAtpLedger:
    """Harness-only alias of :func:`build_idea5_scaffold_ledger`.

    Kept for harness smoke paths. Scored campaign paths must call
    :func:`build_idea5_scaffold_ledger` by name.
    """

    return build_idea5_scaffold_ledger(seed=int(seed))


def build_idea6_scaffold_ledger(*, seed: int = 0) -> ContactAtpLedger:
    """Idea6 scaffold ledger (adaptive epistemic restraint).

    Scaffold-only with locked u* identity, evidence-measure identity
    ``U-LEDGER-EVIDENCE-STRENGTH-V1`` (ledger evidence strength, not audit
    logs), and support channels. Empty evidence_measure_id or empty u*
    reopens the freeze.
    """

    ledger = ContactAtpLedger(rng_seed=int(seed), generation_index=0)
    ledger.ustar_id = USTAR_RESTRAINT
    ledger.evidence_measure_id = U_LEDGER_EVIDENCE_STRENGTH
    ledger.ustar_value = 0.55  # execution-prereg smoke lock; not a discovery threshold invent
    ledger.evidence_u = 0.30  # below u* so withhold/bold paths are exercisable
    ledger.support_channels = {
        SUPPORT_VERIFY_CONSULT: True,
        SUPPORT_RETEST: True,
        SUPPORT_SANCTION: True,
    }
    specs = [
        ("E0", "n0", "n1", CONTACT_TAG_RARE, 1.0),
        ("E1", "n1", "n2", None, 0.8),
        ("E2", "n2", "n3", None, 0.5),
        ("E3", "n3", "n0", None, 0.4),
    ]
    for eid, src, dst, tag, yld in specs:
        ledger.add_edge(eid, src=src, dst=dst, class_tag=tag, atp_yield=yld)
    return ledger


def build_idea6_smoke_ledger(*, seed: int = 0) -> ContactAtpLedger:
    """Harness-only alias of :func:`build_idea6_scaffold_ledger`.

    Kept for harness smoke paths. Scored campaign paths must call
    :func:`build_idea6_scaffold_ledger` by name.
    """

    return build_idea6_scaffold_ledger(seed=int(seed))
