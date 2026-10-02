"""Engine-coupled GenerationBoundaryObserver for discovery phase-2 ledgers.

Attaches to GenesisEngine.run_ticks so each completed generation samples live
population / world ecology and updates a ContactAtpLedger outside engine.py.

After scheduled ledger ops, a domain-free feedback path adjusts organism
runtime ATP and world resources from the change in ledger contact energy
(present unmasked edge yields). Cuts reduce available ATP/resources; intact
or restored contacts preserve or mildly restore them. Deterministic for a
given seed and op schedule. No domain-specific transmission physics; no second
population engine; coupler stays outside engine.py.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.life_loop.contact_atp_ledger import CONTACT_TAG_RARE, ContactAtpLedger

BoundaryOp = Callable[[ContactAtpLedger, int], Any]

# Domain-free feedback scales (deterministic constants, not tuned for soft-pass).
_FEEDBACK_ATP_PER_ENERGY = 1.5
_FEEDBACK_FOOD_PER_ENERGY = 0.8
_FEEDBACK_STRUCT_ATP = 0.35
_FEEDBACK_DIGEST_ATP = 0.50
_FEEDBACK_TOKEN_ATP = 0.35
_FEEDBACK_EDGE_FOOD = 0.15
_FEEDBACK_RESTORE_FRAC = 0.45


def _population_census(engine: Any) -> list[dict[str, str]]:
    """Ids, genome digests, and recorded parents of the live population.

    A missing parent is an empty string (a founder, or a birth the lineage
    did not record). The ledger tag is not a parent.
    """

    population = engine.runner.population
    parents: dict[str, str] = {}
    for record in getattr(population, "lineage", ()) or ():
        organism_id = str(getattr(record, "organism_id", "") or "")
        if not organism_id:
            continue
        parent = getattr(record, "parent_id", None)
        parents[organism_id] = "" if parent is None else str(parent)
    rows: list[dict[str, str]] = []
    for org in population.organisms:
        genome = getattr(org, "genome", None)
        digest = genome.digest() if genome is not None and hasattr(genome, "digest") else ""
        organism_id = str(getattr(org, "id", "") or "")
        rows.append(
            {
                "id": organism_id,
                "genome": str(digest),
                "parent_id": parents.get(organism_id, ""),
            }
        )
    rows.sort(key=lambda row: row["id"])
    return rows


def sample_ecology(engine: Any) -> dict[str, float]:
    """Sample domain-free ecology meters from a live GenesisEngine."""

    population = engine.runner.population
    organisms = tuple(population.organisms)
    atps = [float(o.atp_state.runtime_available) for o in organisms]
    n_alive = float(len(organisms))
    mean_atp = float(sum(atps) / n_alive) if n_alive > 0.0 else 0.0
    sum_atp = float(sum(atps))
    resources = dict(getattr(engine.runner.world, "resources", {}) or {})
    n_resources = float(len(resources))
    resource_mass = float(sum(float(v) for v in resources.values()))
    loc_fp = 0.0
    for (x, y), amt in resources.items():
        loc_fp += float(x + 1) * float(y + 1) * float(amt)
    return {
        "n_alive": n_alive,
        "mean_atp": mean_atp,
        "sum_atp": sum_atp,
        "n_resources": n_resources,
        "resource_mass": resource_mass,
        "resource_loc_fp": loc_fp,
        "generation": float(getattr(population, "generation", 0)),
    }


def ecology_scale(eco: Mapping[str, float]) -> float:
    """Map ecology meters to a positive rare-yield scale factor."""

    mean_atp = float(eco.get("mean_atp", 0.0))
    n_alive = float(eco.get("n_alive", 0.0))
    resource_mass = float(eco.get("resource_mass", 0.0))
    loc_fp = float(eco.get("resource_loc_fp", 0.0))
    alive_term = 0.35 + 0.65 * math.tanh(n_alive / 4.0)
    atp_term = 0.40 + 0.60 * math.tanh(mean_atp / 8.0)
    food_term = 0.55 + 0.45 * math.tanh(resource_mass / 24.0)
    # Location fingerprint breaks ties when mass is saturated but layout differs.
    loc_term = 0.90 + 0.10 * math.sin(loc_fp / 17.0)
    return float(max(0.05, alive_term * atp_term * food_term * loc_term))


def ledger_contact_energy_snapshot(ledger: ContactAtpLedger) -> dict[str, Any]:
    """Fingerprint present unmasked contact energy and structural markers."""

    parts: list[dict[str, Any]] = []
    contact_energy = 0.0
    n_present = 0
    for eid in sorted(ledger.edges):
        edge = ledger.edges[eid]
        present = bool(edge.present)
        masked = bool(edge.masked)
        yld = float(edge.atp_yield)
        # Weight defaults to 1.0 (ledger has no separate weight field).
        weight = 1.0
        contrib = yld * weight if present and not masked else 0.0
        if present and not masked:
            contact_energy += contrib
            n_present += 1
        parts.append(
            {
                "edge_id": eid,
                "src": str(edge.src),
                "dst": str(edge.dst),
                "present": present,
                "masked": masked,
                "atp_yield": yld,
                "contrib": float(contrib),
            }
        )
    digest_keys = sorted(ledger.failed_prediction_digests)
    token_items = sorted(
        (str(k), str(v)) for k, v in ledger.recovery_tokens.items()
    )
    payload = {
        "parts": parts,
        "contact_energy": float(contact_energy),
        "digest_keys": digest_keys,
        "tokens": token_items,
    }
    return {
        "contact_energy": float(contact_energy),
        "n_present_unmasked": int(n_present),
        "digest_keys": digest_keys,
        "token_items": token_items,
        "fingerprint": canonical_digest(payload, prefix="ledger_ce"),
        "parts": parts,
    }


def population_path_fingerprint(engine: Any) -> str:
    """Hash of sorted organism ids/atp/positions + generation + n_alive + resources."""

    population = engine.runner.population
    organisms = tuple(population.organisms)
    org_rows: list[dict[str, Any]] = []
    for org in sorted(organisms, key=lambda o: str(getattr(o, "id", ""))):
        pos = getattr(org, "position", None)
        org_rows.append(
            {
                "id": str(getattr(org, "id", "")),
                "atp": float(org.atp_state.runtime_available),
                "pos": list(pos) if pos is not None else None,
            }
        )
    resources = dict(getattr(engine.runner.world, "resources", {}) or {})
    res_rows = [
        [list(k), float(v)] for k, v in sorted(resources.items(), key=lambda kv: tuple(kv[0]))
    ]
    payload = {
        "generation": int(getattr(population, "generation", 0)),
        "n_alive": len(organisms),
        "organisms": org_rows,
        "resources": res_rows,
    }
    return canonical_digest(payload, prefix="pop_path")


def engine_pop_path_digest_from_ecology(
    ecology_history: Sequence[Mapping[str, float]],
    *,
    t_intervene: int,
) -> str:
    """Hash post-intervention GB ecology series (OWNER P1 meter)."""

    t_int = int(t_intervene)
    if t_int < 1:
        raise ConfigurationError("t_intervene must be >= 1.")
    # Observer stores one ecology sample per completed generation (index 0 = gen 1).
    # Intervention fires at generation_index == t_int → history index t_int - 1.
    post = list(ecology_history[t_int - 1 :])
    rows = [
        {
            "generation": float(e.get("generation", 0.0)),
            "n_alive": float(e.get("n_alive", 0.0)),
            "mean_atp": float(e.get("mean_atp", 0.0)),
            "sum_atp": float(e.get("sum_atp", 0.0)),
            "resource_mass": float(e.get("resource_mass", 0.0)),
            "resource_loc_fp": float(e.get("resource_loc_fp", 0.0)),
        }
        for e in post
    ]
    return canonical_digest(rows, prefix="engine_pop_path")


def pre_intervene_pop_digest_from_ecology(
    ecology_history: Sequence[Mapping[str, float]],
    *,
    t_intervene: int,
) -> str:
    """Hash pre-intervention GB ecology series (OWNER P1 meter)."""

    t_int = int(t_intervene)
    if t_int < 1:
        raise ConfigurationError("t_intervene must be >= 1.")
    pre = list(ecology_history[: max(0, t_int - 1)])
    rows = [
        {
            "generation": float(e.get("generation", 0.0)),
            "n_alive": float(e.get("n_alive", 0.0)),
            "mean_atp": float(e.get("mean_atp", 0.0)),
            "sum_atp": float(e.get("sum_atp", 0.0)),
            "resource_mass": float(e.get("resource_mass", 0.0)),
            "resource_loc_fp": float(e.get("resource_loc_fp", 0.0)),
        }
        for e in pre
    ]
    return canonical_digest(rows, prefix="pre_intervene_pop")


def _changed_nodes(pre: Mapping[str, Any], post: Mapping[str, Any]) -> set[str]:
    """Endpoints of edges whose presence, ends, mask, or yield changed."""

    pre_parts = {p["edge_id"]: p for p in pre.get("parts", ())}
    post_parts = {p["edge_id"]: p for p in post.get("parts", ())}
    nodes: set[str] = set()
    for eid in set(pre_parts) | set(post_parts):
        left = pre_parts.get(eid)
        right = post_parts.get(eid)
        changed = left is None or right is None
        if left is not None and right is not None:
            changed = (
                left["src"] != right["src"]
                or left["dst"] != right["dst"]
                or left["present"] != right["present"]
                or left["masked"] != right["masked"]
                or float(left["atp_yield"]) != float(right["atp_yield"])
            )
        if not changed:
            continue
        part = left if left is not None else right
        assert part is not None
        nodes.add(str(part["src"]))
        nodes.add(str(part["dst"]))
    return nodes


def _organisms_for_nodes(organisms: Sequence[Any], nodes: set[str]) -> list[Any]:
    """Map ledger node ids onto the live population. Not a contact physics claim."""

    ordered = sorted(organisms, key=lambda org: str(getattr(org, "id", "")))
    if not ordered or not nodes:
        return []
    chosen: list[Any] = []
    seen: set[str] = set()
    for node in sorted(nodes):
        digits = "".join(ch for ch in node if ch.isdigit())
        index = int(digits) if digits else 0
        org = ordered[index % len(ordered)]
        org_id = str(getattr(org, "id", ""))
        if org_id in seen:
            continue
        seen.add(org_id)
        chosen.append(org)
    return chosen



def bind_nodes_to_organisms(
    engine: Any,
    pre_snap: Mapping[str, Any],
    post_snap: Mapping[str, Any],
) -> dict[str, str]:
    """Bind declared ledger contact nodes to live organism ids.

    The binding is the declared node order of the contact ledger against the
    sorted live organisms, and it is *complete or refused*: a partial binding
    returns ``{}`` so the caller cannot silently fall back to a modular index
    map.  This is the endpoint identity the D-2 refusal test needs, and it is a
    structural claim about which organism holds which contact slot, not an
    arithmetic smear.
    """

    nodes: set[str] = set()
    for snap in (pre_snap, post_snap):
        for part in snap.get("parts", ()) or ():
            nodes.add(str(part["src"]))
            nodes.add(str(part["dst"]))
    ordered_nodes = sorted(nodes)
    ordered = sorted(engine.runner.population.organisms, key=lambda org: str(getattr(org, "id", "")))
    if not ordered_nodes or len(ordered) < len(ordered_nodes):
        return {}
    return {node: str(ordered[index].id) for index, node in enumerate(ordered_nodes)}

def _structural_delta(pre: Mapping[str, Any], post: Mapping[str, Any]) -> dict[str, float]:
    """Count domain-free structural deltas between ledger snapshots."""

    pre_parts = {p["edge_id"]: p for p in pre.get("parts", ())}
    post_parts = {p["edge_id"]: p for p in post.get("parts", ())}
    n_edge_changes = 0.0
    for eid in sorted(set(pre_parts) | set(post_parts)):
        a = pre_parts.get(eid)
        b = post_parts.get(eid)
        if a is None or b is None:
            n_edge_changes += 1.0
            continue
        if (
            a["src"] != b["src"]
            or a["dst"] != b["dst"]
            or a["present"] != b["present"]
            or a["masked"] != b["masked"]
            or float(a["atp_yield"]) != float(b["atp_yield"])
        ):
            n_edge_changes += 1.0
    digest_changed = float(
        list(pre.get("digest_keys", ())) != list(post.get("digest_keys", ()))
    )
    token_changed = float(
        list(pre.get("token_items", ())) != list(post.get("token_items", ()))
    )
    energy_delta = float(post.get("contact_energy", 0.0)) - float(
        pre.get("contact_energy", 0.0)
    )
    return {
        "energy_delta": energy_delta,
        "n_edge_changes": n_edge_changes,
        "digest_changed": digest_changed,
        "token_changed": token_changed,
    }


def apply_ledger_feedback_to_engine(
    engine: Any,
    *,
    pre_snap: Mapping[str, Any],
    post_snap: Mapping[str, Any],
    generation_index: int,
    allocation: str = "global_smear",
) -> dict[str, Any]:
    """Apply domain-free ATP/resource feedback from ledger contact deltas.

    ``global_smear`` splits the whole burden across every organism. Endpoint
    identity does not enter that debit, so two equal-cost cuts share one
    aggregate path. ``incident_endpoints`` charges the edge portion only to
    organisms mapped from the changed endpoints. That is a meter check, not
    an identified topology effect. Food removal stays global in both modes.
    """

    allocation_name = str(allocation)
    if allocation_name not in (
        "global_smear",
        "incident_endpoints",
        "incident_endpoints_realised",
    ):
        raise ConfigurationError(
            "feedback allocation must be global_smear or incident_endpoints."
        )

    deltas = _structural_delta(pre_snap, post_snap)
    energy_delta = float(deltas["energy_delta"])
    lost_energy = max(0.0, -energy_delta)
    gained_energy = max(0.0, energy_delta)
    # Fixed coefficients. The edge and token terms count changes; they are
    # not a measured local consequence of contact structure.
    burden_lost_energy = lost_energy * _FEEDBACK_ATP_PER_ENERGY
    burden_edge_changes = float(deltas["n_edge_changes"]) * _FEEDBACK_STRUCT_ATP
    burden_digest = float(deltas["digest_changed"]) * _FEEDBACK_DIGEST_ATP
    burden_token = float(deltas["token_changed"]) * _FEEDBACK_TOKEN_ATP
    burden = (
        burden_lost_energy + burden_edge_changes + burden_digest + burden_token
    )
    restore = gained_energy * _FEEDBACK_ATP_PER_ENERGY * _FEEDBACK_RESTORE_FRAC

    population = engine.runner.population
    organisms = list(population.organisms)
    n_alive_before = len(organisms)
    total_debited = 0.0
    total_credited = 0.0
    g = int(generation_index)

    if allocation_name == "incident_endpoints_realised":
        # Realised-contact allocation: the debit is the ATP of the contact edges
        # that actually changed, charged to the organisms bound to those edges'
        # endpoints.  The global count penalty (n_edge_changes x coeff) is NOT
        # added here, so a difference between two equally-sized cuts can only
        # come from which contacts were cut and who held them.
        binding = bind_nodes_to_organisms(engine, pre_snap, post_snap)
        pre_parts = {str(p["edge_id"]): p for p in pre_snap.get("parts", ())}
        post_parts = {str(p["edge_id"]): p for p in post_snap.get("parts", ())}
        live = {str(org.id): org for org in engine.runner.population.organisms}
        per_organism: dict[str, float] = {}
        unbound: list[str] = []
        changed_edges = [
            eid
            for eid in sorted(set(pre_parts) | set(post_parts))
            if pre_parts.get(eid) != post_parts.get(eid)
        ]
        for eid in changed_edges:
            before = pre_parts.get(eid)
            after = post_parts.get(eid)
            before_present = bool(before is not None and before.get("present") and not before.get("masked"))
            after_present = bool(after is not None and after.get("present") and not after.get("masked"))
            if before_present and not after_present:
                realised = float(before.get("atp_yield", 0.0))
            elif before is not None and after is not None:
                realised = max(
                    0.0,
                    float(before.get("atp_yield", 0.0)) - float(after.get("atp_yield", 0.0)),
                )
            elif before is not None:
                realised = float(before.get("atp_yield", 0.0))
            else:
                realised = 0.0
            part = before if before is not None else after
            assert part is not None
            for node in (str(part["src"]), str(part["dst"])):
                oid = binding.get(node)
                if oid is None or oid not in live:
                    unbound.append(node)
                    continue
                org = live[oid]
                payable = min(realised / 2.0, float(org.atp_state.runtime_available))
                if payable <= 0.0:
                    continue
                org.atp_state.debit_runtime(
                    payable,
                    tick=g,
                    organism_id=oid,
                    codon="ledger_fb",
                    action="contact_ledger_feedback",
                    reason="realised_contact_edge_cut",
                )
                per_organism[oid] = per_organism.get(oid, 0.0) + payable
        identified = bool(changed_edges) and not unbound and bool(binding)
        total = float(sum(per_organism.values()))
        return {
            "energy_delta": energy_delta,
            "burden": total,
            "burden_lost_energy": 0.0,
            "burden_edge_changes": 0.0,
            "burden_digest": 0.0,
            "burden_token": 0.0,
            "restore": 0.0,
            "total_debited": total,
            "total_credited": 0.0,
            "food_removed": 0.0,
            "food_added": 0.0,
            "food_from_lost_energy": 0.0,
            "food_from_edge_count": 0.0,
            "n_alive_before": int(len(live)),
            "n_alive_after": int(len(list(engine.runner.population.organisms))),
            "effect_applied": bool(total > 0.0),
            "n_edge_changes": float(len(changed_edges)),
            "digest_changed": float(deltas["digest_changed"]),
            "token_changed": float(deltas["token_changed"]),
            "allocation": allocation_name,
            "recipient_ids": sorted(per_organism),
            "per_organism_realised_debit": per_organism,
            "unbound_nodes": sorted(set(unbound)),
            "endpoints_enter_debit": True,
            "food_follows_endpoints": False,
            "endpoint_map": "declared_node_order_to_sorted_live_organisms",
            "endpoint_binding_complete": identified,
            # D-2 task-16: the node-to-organism binding is a name-ordered list,
            # not the contact that actually occurred, and no engine contact
            # event is read here.  The topology/precision flags therefore stay
            # False until both endpoints and the realised transfer source come
            # from an engine event.
            "topology_flag_reason": "endpoint binding is name-ordered, not an engine contact event",
            "endpoint_map_is_contact_physics": False,
            "lineage_resource_transfer": False,
            "contact_structure_effect_identified": False,
            "knowledge_effect_identified": False,
            "topology_effect_identified": False,
        }


    def _debit(targets: Sequence[Any], amount: float) -> None:
        nonlocal total_debited
        if not targets or amount <= 0.0:
            return
        per = float(amount) / float(len(targets))
        for org in targets:
            payable = min(per, float(org.atp_state.runtime_available))
            if payable <= 0.0:
                continue
            org.atp_state.debit_runtime(
                payable,
                tick=g,
                organism_id=str(org.id),
                codon="ledger_fb",
                action="contact_ledger_feedback",
                reason="ledger_contact_energy_burden",
            )
            total_debited += payable

    nodes = _changed_nodes(pre_snap, post_snap)
    incident = _organisms_for_nodes(organisms, nodes)
    if allocation_name == "global_smear":
        _debit(organisms, burden)
        recipients = organisms
        endpoints_enter_debit = False
    else:
        edge_burden = burden_lost_energy + burden_edge_changes
        flat_burden = burden_digest + burden_token
        if incident and edge_burden > 0.0:
            _debit(incident, edge_burden)
            endpoints_enter_debit = True
        else:
            _debit(organisms, edge_burden)
            endpoints_enter_debit = False
        _debit(organisms, flat_burden)
        recipients = incident if incident else organisms
    recipient_ids = sorted(str(getattr(org, "id", "")) for org in recipients)

    if organisms and restore > 0.0:
        per = float(restore) / float(len(organisms))
        for org in organisms:
            org.atp_state.credit_runtime(
                per,
                tick=g,
                organism_id=str(org.id),
                codon="ledger_fb",
                action="contact_ledger_feedback",
                reason="ledger_contact_energy_restore",
            )
            total_credited += per

    world = engine.runner.world
    resources = getattr(world, "resources", None)
    food_removed = 0.0
    food_added = 0.0
    food_from_lost_energy = 0.0
    food_from_edge_count = 0.0
    if isinstance(resources, dict):
        food_from_lost_energy = lost_energy * _FEEDBACK_FOOD_PER_ENERGY
        food_from_edge_count = float(deltas["n_edge_changes"]) * _FEEDBACK_EDGE_FOOD
        food_burden = food_from_lost_energy + food_from_edge_count
        if food_burden > 0.0 and resources:
            total_mass = float(sum(float(v) for v in resources.values()))
            if total_mass > 0.0:
                for pos in list(resources.keys()):
                    amt = float(resources[pos])
                    share = food_burden * (amt / total_mass)
                    new_amt = max(0.0, amt - share)
                    food_removed += amt - new_amt
                    if new_amt <= 1e-12:
                        resources.pop(pos, None)
                    else:
                        resources[pos] = new_amt
        food_restore = gained_energy * _FEEDBACK_FOOD_PER_ENERGY * _FEEDBACK_RESTORE_FRAC
        if food_restore > 0.0:
            if resources:
                # Spread restore across existing cells deterministically.
                keys = sorted(resources.keys())
                per = food_restore / float(len(keys))
                for pos in keys:
                    resources[pos] = float(resources[pos]) + per
                    food_added += per
            else:
                # Empty world: place a single restored cell at origin if in bounds.
                place = getattr(world, "place_resource", None)
                if callable(place):
                    place((0, 0), float(food_restore))
                    food_added += float(food_restore)

    n_alive_after = len(list(population.organisms))
    effect_applied = bool(
        total_debited > 0.0
        or total_credited > 0.0
        or food_removed > 0.0
        or food_added > 0.0
    )
    return {
        "energy_delta": energy_delta,
        "burden": float(burden),
        "burden_lost_energy": float(burden_lost_energy),
        "burden_edge_changes": float(burden_edge_changes),
        "burden_digest": float(burden_digest),
        "burden_token": float(burden_token),
        "restore": float(restore),
        "total_debited": float(total_debited),
        "total_credited": float(total_credited),
        "food_removed": float(food_removed),
        "food_added": float(food_added),
        "food_from_lost_energy": float(food_from_lost_energy),
        "food_from_edge_count": float(food_from_edge_count),
        "n_alive_before": int(n_alive_before),
        "n_alive_after": int(n_alive_after),
        "effect_applied": effect_applied,
        "n_edge_changes": float(deltas["n_edge_changes"]),
        "digest_changed": float(deltas["digest_changed"]),
        "token_changed": float(deltas["token_changed"]),
        "allocation": allocation_name,
        "recipient_ids": recipient_ids,
        "endpoints_enter_debit": bool(endpoints_enter_debit),
        "food_follows_endpoints": False,
        "endpoint_map": "node_digits_mod_population",
        "endpoint_map_is_contact_physics": False,
        "lineage_resource_transfer": False,
        # A local debit can move who pays. It does not identify a topology effect.
        "contact_structure_effect_identified": False,
        "knowledge_effect_identified": False,
        "topology_effect_identified": False,
    }


@dataclass(slots=True)
class EngineCoupledLedgerObserver:
    """GenerationBoundaryObserver: ecology→ledger yields, ops, then ledger→engine feedback."""

    engine_holder: MutableMapping[str, Any]
    ledger: ContactAtpLedger
    schedule: Mapping[int, Sequence[BoundaryOp]] = field(default_factory=dict)
    base_rare_yields: dict[str, float] = field(default_factory=dict)
    yield_history: list[float] = field(default_factory=list)
    ecology_history: list[dict[str, float]] = field(default_factory=list)
    census_history: list[list[dict[str, str]]] = field(default_factory=list)
    feedback_history: list[dict[str, Any]] = field(default_factory=list)
    observer_fire_count: int = 0
    auto_advance: bool = True
    harvest_fn: Callable[[ContactAtpLedger], float] | None = None
    feedback_enabled: bool = True
    feedback_allocation: str = "global_smear"

    def __post_init__(self) -> None:
        if not self.base_rare_yields:
            for eid in self.ledger.edges_with_tag(CONTACT_TAG_RARE):
                self.base_rare_yields[eid] = float(self.ledger.edges[eid].atp_yield)

    def __call__(self, *, generation_index: int) -> None:
        if not isinstance(generation_index, int) or isinstance(generation_index, bool):
            raise ConfigurationError("generation_index must be an integer.")
        engine = self.engine_holder.get("engine")
        if engine is None:
            raise ConfigurationError(
                "EngineCoupledLedgerObserver requires engine_holder['engine'] "
                "before run_ticks()."
            )
        g = int(generation_index)
        eco = sample_ecology(engine)
        self.ecology_history.append(dict(eco))
        self.census_history.append(_population_census(engine))
        scale = ecology_scale(eco)
        # Update rare-class edge yields from live ecology (closed-loop variance).
        for eid, base in self.base_rare_yields.items():
            edge = self.ledger.edges.get(eid)
            if edge is None:
                continue
            edge.atp_yield = float(base) * float(scale)
        # Mirror edges carry the scaffold twin's yield so a matched cut can
        # share edge count, degree, contact weight, and ATP lost.
        for src_eid, mirror_eid in self.ledger.match_mirrors.items():
            src = self.ledger.edges.get(src_eid)
            mirror = self.ledger.edges.get(mirror_eid)
            if src is None or mirror is None or not mirror.present:
                continue
            mirror.atp_yield = float(src.atp_yield)
        # Refresh tag aggregate.
        rare_sum = 0.0
        for eid in self.ledger.edges_with_tag(CONTACT_TAG_RARE):
            e = self.ledger.edges[eid]
            if e.present and not e.masked:
                rare_sum += float(e.atp_yield)
        self.ledger.atp_yield_by_tag[CONTACT_TAG_RARE] = float(rare_sum)

        pre_snap = ledger_contact_energy_snapshot(self.ledger)
        ops = self.schedule.get(g, ())
        for op in ops:
            op(self.ledger, g)
        post_snap = ledger_contact_energy_snapshot(self.ledger)

        feedback_rec: dict[str, Any] = {
            "generation_index": g,
            "pre_fingerprint": pre_snap["fingerprint"],
            "post_fingerprint": post_snap["fingerprint"],
            "pre_contact_energy": float(pre_snap["contact_energy"]),
            "post_contact_energy": float(post_snap["contact_energy"]),
            "n_alive_before": int(eco["n_alive"]),
            "effect_applied": False,
        }
        if self.feedback_enabled and (
            pre_snap["fingerprint"] != post_snap["fingerprint"] or bool(ops)
        ):
            applied = apply_ledger_feedback_to_engine(
                engine,
                pre_snap=pre_snap,
                post_snap=post_snap,
                generation_index=g,
                allocation=self.feedback_allocation,
            )
            feedback_rec.update(applied)
            feedback_rec["n_alive_after_feedback"] = int(applied["n_alive_after"])
            feedback_rec["pop_fingerprint"] = population_path_fingerprint(engine)
            feedback_rec["effect_applied"] = bool(applied["effect_applied"])
        else:
            feedback_rec["n_alive_after_feedback"] = int(
                len(tuple(engine.runner.population.organisms))
            )
            feedback_rec["pop_fingerprint"] = population_path_fingerprint(engine)
        self.feedback_history.append(feedback_rec)

        if self.harvest_fn is not None:
            harvested = float(self.harvest_fn(self.ledger))
        else:
            harvested = float(rare_sum)
        self.yield_history.append(harvested)
        self.observer_fire_count += 1

        if self.auto_advance:
            if self.ledger.generation_index < g:
                self.ledger.generation_index = g
            self.ledger.advance_generation()
