"""Engine-coupled GenerationBoundaryObserver for discovery phase-2 ledgers.

Attaches to GenesisEngine.run_ticks so each completed generation samples live
population / world ecology and updates a ContactAtpLedger outside engine.py.

After scheduled ledger ops, a domain-free feedback path adjusts organism
runtime ATP and world resources from the change in ledger contact energy
(present unmasked edge yields). Cuts reduce available ATP/resources; intact
or restored contacts preserve or mildly restore them. Deterministic for a
given seed and op schedule. No infection physics; no second population
engine; coupler stays outside engine.py.
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
_FEEDBACK_RESTORE_FRAC = 0.45


def _population_census(engine: Any) -> list[dict[str, str]]:
    """Ids and genome digests of the live population. Not a ledger tag."""

    rows: list[dict[str, str]] = []
    for org in engine.runner.population.organisms:
        genome = getattr(org, "genome", None)
        digest = genome.digest() if genome is not None and hasattr(genome, "digest") else ""
        rows.append({"id": str(getattr(org, "id", "")), "genome": str(digest)})
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
) -> dict[str, Any]:
    """Apply domain-free ATP/resource feedback from ledger contact deltas."""

    deltas = _structural_delta(pre_snap, post_snap)
    energy_delta = float(deltas["energy_delta"])
    lost_energy = max(0.0, -energy_delta)
    gained_energy = max(0.0, energy_delta)
    # Positive burden when contacts are cut/masked/rewired/ablated/relocated.
    burden = (
        lost_energy * _FEEDBACK_ATP_PER_ENERGY
        + float(deltas["n_edge_changes"]) * _FEEDBACK_STRUCT_ATP
        + float(deltas["digest_changed"]) * _FEEDBACK_DIGEST_ATP
        + float(deltas["token_changed"]) * _FEEDBACK_TOKEN_ATP
    )
    restore = gained_energy * _FEEDBACK_ATP_PER_ENERGY * _FEEDBACK_RESTORE_FRAC

    population = engine.runner.population
    organisms = list(population.organisms)
    n_alive_before = len(organisms)
    total_debited = 0.0
    total_credited = 0.0
    g = int(generation_index)

    if organisms and burden > 0.0:
        per = float(burden) / float(len(organisms))
        for org in organisms:
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
    if isinstance(resources, dict):
        food_burden = lost_energy * _FEEDBACK_FOOD_PER_ENERGY + float(
            deltas["n_edge_changes"]
        ) * 0.15
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
        "restore": float(restore),
        "total_debited": float(total_debited),
        "total_credited": float(total_credited),
        "food_removed": float(food_removed),
        "food_added": float(food_added),
        "n_alive_before": int(n_alive_before),
        "n_alive_after": int(n_alive_after),
        "effect_applied": effect_applied,
        "n_edge_changes": float(deltas["n_edge_changes"]),
        "digest_changed": float(deltas["digest_changed"]),
        "token_changed": float(deltas["token_changed"]),
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
