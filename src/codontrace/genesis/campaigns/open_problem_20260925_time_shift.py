"""Open problem 2026-09-25 — time-shift FRQ vs ERQ discrimination.

Literature seeds (verified DOIs):
- Decaestecker et al. 2007 Nature doi:10.1038/nature06291
- Brockhurst et al. 2014 Proc B doi:10.1098/rspb.2014.1382
- Buckingham & Ashby 2022 JEB doi:10.1111/jeb.13981

Mechanism innovation lives in codontrace.life_loop.time_shift_assay
(CohortArchive + cross-temporal match + match_linked_cycle /
trait_escalation). HostParasiteWorld is a thin live witness only —
no infection physics in engine.py. A panel that passes on a mechanism
built to cycle tests the detector. It is not a measurement of the
closed-loop population. Claim ceiling: candidate_evidence /
runtime_observation. red_queen_proved and arms_race_proved stay False.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.host_parasite_world import HostParasiteProfile, HostParasiteWorld
from codontrace.life_loop.time_shift_assay import (
    CohortArchive,
    features_from_genome_compact,
    run_mechanism_archive,
    run_time_shift_panel,
)

SCHEMA = "open_problem_20260925_time_shift_v1"
CLAIM_CEILING = "candidate_evidence"
CLAIMGATE_REFUSES = (
    "red_queen_proved",
    "arms_race_proved",
    "causality_proved",
    "intervention_supported",
)

DOIS = {
    "primary": "10.1038/nature06291",
    "modes": "10.1098/rspb.2014.1382",
    "theory_review": "10.1111/jeb.13981",
}

SEEDS_MAIN = (101, 202, 303, 404, 505, 606, 707, 808)
SEEDS_LIVE = (11, 22, 33, 44)

WHY_UNSOLVED = (
    "Short time-shift windows can look directional even under fluctuating "
    "selection (Buckingham & Ashby 2022 doi:10.1111/jeb.13981). Separating "
    "oscillatory Red Queen (contemporaneous match peak / FRQ) from escalatory "
    "arms race (future-advantage / ERQ) is still open on engines that archive "
    "live cohorts during a dynamic life-loop rather than scoring frozen "
    "handmade graphs (Decaestecker 2007; Brockhurst 2014)."
)


@dataclass(frozen=True, slots=True)
class SFRecord:
    """SF-style falsification record with required campaign fields."""

    id: str
    doi: str
    literature_prediction: str
    why_unsolved: str
    success_criterion: str
    null_arms: Mapping[str, Any]
    n_seeds: int
    engineering_green: bool
    hypothesis_supported: bool
    honesty: str
    claim_ceiling: str
    result: str
    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, JsonValue]:
        body: dict[str, JsonValue] = {
            "id": self.id,
            "doi": self.doi,
            "literature_prediction": self.literature_prediction,
            "why_unsolved": self.why_unsolved,
            "success_criterion": self.success_criterion,
            "null_arms": dict(self.null_arms),
            "n_seeds": self.n_seeds,
            "engineering_green": self.engineering_green,
            "hypothesis_supported": self.hypothesis_supported,
            "honesty": self.honesty,
            "claim_ceiling": self.claim_ceiling,
            "result": self.result,
            "red_queen_proved": False,
            "arms_race_proved": False,
            "claimgate_refuses": list(CLAIMGATE_REFUSES),
            "payload": dict(self.payload),
        }
        body["record_digest"] = canonical_digest(
            {k: v for k, v in body.items() if k != "record_digest"},
            prefix="sf_record",
        )
        return body


def _panel_discrimination(seeds: Sequence[int] | None = None) -> SFRecord:
    use_seeds = tuple(seeds) if seeds is not None else SEEDS_MAIN
    cycle_trials: list[dict[str, Any]] = []
    esc_trials: list[dict[str, Any]] = []
    null_trials: dict[str, list[dict[str, Any]]] = {
        "content_null": [],
        "structure_null": [],
        "dual_null": [],
    }
    for seed in use_seeds:
        cycle_trials.append(
            run_mechanism_archive(
                mechanism="match_linked_cycle", steps=48, seed=int(seed), lag=4
            )
        )
        esc_trials.append(
            run_mechanism_archive(
                mechanism="trait_escalation", steps=48, seed=int(seed), lag=4
            )
        )
        for arm in null_trials:
            null_trials[arm].append(
                run_mechanism_archive(
                    mechanism="match_linked_cycle",
                    steps=48,
                    seed=int(seed),
                    lag=4,
                    ablation=arm,  # type: ignore[arg-type]
                )
            )

    n = len(use_seeds)
    need = max(1, (3 * n) // 4)
    cycle_ok = sum(1 for t in cycle_trials if t["pattern"] == "peak_contemp")
    esc_ok = sum(1 for t in esc_trials if t["pattern"] == "mono_rise")
    null_flat = {
        arm: sum(1 for t in trials if t["pattern"] == "flat")
        for arm, trials in null_trials.items()
    }
    engineering_green = all(
        isinstance(t.get("archive_digest"), str) and bool(t["archive_digest"])
        for t in cycle_trials + esc_trials
    )
    hypothesis_supported = (
        cycle_ok >= need
        and esc_ok >= need
        and all(v >= need for v in null_flat.values())
    )
    if not engineering_green:
        result = "FAIL"
    elif hypothesis_supported:
        result = "PASS"
    else:
        result = "FAIL"

    return SFRecord(
        id="SF_TS1_time_shift_frq_erq_discrimination",
        doi=DOIS["primary"],
        literature_prediction=(
            "Fluctuating Red Queen tracking yields a contemporaneous match peak "
            "in time-shift assays (Decaestecker et al. 2007 "
            "doi:10.1038/nature06291). Escalatory arms races yield directional "
            "future-advantage profiles (Brockhurst et al. 2014 "
            "doi:10.1098/rspb.2014.1382)."
        ),
        why_unsolved=WHY_UNSOLVED,
        success_criterion=(
            f">={need}/{n} seeds peak_contemp on match_linked_cycle; "
            f">={need}/{n} seeds mono_rise on trait_escalation; "
            f"content/structure/dual nulls flat on >={need}/{n} seeds; "
            "red_queen_proved=False."
        ),
        null_arms={
            "content_null_flat_seeds": null_flat["content_null"],
            "structure_null_flat_seeds": null_flat["structure_null"],
            "dual_null_flat_seeds": null_flat["dual_null"],
            "n_seeds": n,
        },
        n_seeds=n,
        engineering_green=engineering_green,
        hypothesis_supported=hypothesis_supported,
        honesty=(
            "Digital generative archives on the life_loop time-shift assay. "
            "Pattern labels are structural analogues of FRQ/ERQ time-shift "
            "signatures — not wet Red Queen proof. ClaimGate refuses stay closed."
        ),
        claim_ceiling=CLAIM_CEILING,
        result=result,
        payload={
            "related_dois": DOIS,
            "cycle_peak_contemp_seeds": cycle_ok,
            "escalation_mono_rise_seeds": esc_ok,
            "null_flat_seeds": null_flat,
            "cycle_trials": cycle_trials,
            "escalation_trials": esc_trials,
            "null_trials": null_trials,
            "innovation": (
                "life_loop.time_shift_assay "
                "(CohortArchive + cross-temporal match + "
                "match_linked_cycle / trait_escalation)"
            ),
        },
    )


def _live_world_witness(seeds: Sequence[int] | None = None) -> SFRecord:
    use_seeds = tuple(seeds) if seeds is not None else SEEDS_LIVE
    trials: list[dict[str, Any]] = []
    for seed in use_seeds:
        profile = HostParasiteProfile(
            profile_id=f"ts_live_{seed}",
            seed=int(seed),
            birth_probability_primary=0.25,
            birth_probability_secondary=0.25,
            death_probability_primary=0.08,
            death_probability_secondary=0.08,
            mutation_probability_primary=0.4,
            mutation_probability_secondary=0.4,
            inherit_mode="copy",
            inherit_probability=1.0,
            match_rule_id="feature_overlap",
            max_population_primary=24,
            max_population_secondary=24,
        )
        world = HostParasiteWorld(profile)
        archive_sec = CohortArchive()
        focal_series: dict[int, dict[str, frozenset[str]]] = {}
        ticks = 30
        lag = 5
        pop_a = profile.population_id("primary")
        pop_b = profile.population_id("secondary")
        engineering_ok = True
        panel_dict: dict[str, Any] = {}
        pattern = "other"
        try:
            for step in range(ticks + 1):
                t = int(world.tick_index)
                primary_ids = list(world.registry.get(pop_a).member_ids)
                secondary_ids = list(world.registry.get(pop_b).member_ids)
                focal = {
                    mid: features_from_genome_compact(world.genomes[mid].to_compact())
                    for mid in primary_ids
                    if mid in world.genomes
                }
                partners = {
                    mid: features_from_genome_compact(world.genomes[mid].to_compact())
                    for mid in secondary_ids
                    if mid in world.genomes
                }
                if partners:
                    archive_sec.record(t, partners)
                if focal:
                    focal_series[t] = focal
                if step < ticks:
                    world.tick()
            probe = max(lag, ticks - lag)
            if (
                probe in focal_series
                and archive_sec.at(probe - lag) is not None
                and archive_sec.at(probe) is not None
                and archive_sec.at(probe + lag) is not None
            ):
                panel = run_time_shift_panel(
                    archive_sec,
                    focal_tick=probe,
                    lag=lag,
                    focal_members=focal_series[probe],
                    mode="allele_exact",
                )
                panel_dict = panel.to_dict()
                pattern = str(panel.pattern)
            else:
                engineering_ok = False
        except Exception as exc:  # noqa: BLE001 — honesty path
            engineering_ok = False
            panel_dict = {"error": type(exc).__name__, "detail": str(exc)}
        summary = world.summary()
        if summary.get("red_queen_proved") is not False:
            engineering_ok = False
        trials.append(
            {
                "seed": int(seed),
                "pattern": pattern,
                "panel": panel_dict,
                "archive_digest": archive_sec.digest(),
                "world_digest": summary.get("world_digest"),
                "red_queen_proved": False,
                "coexistence": summary.get("coexistence"),
                "census": summary.get("census"),
                "engineering_ok": engineering_ok,
            }
        )

    eng = all(bool(t["engineering_ok"]) for t in trials)
    peak_n = sum(1 for t in trials if t["pattern"] == "peak_contemp")
    rise_n = sum(1 for t in trials if t["pattern"] == "mono_rise")
    # Live demography alone does not license FRQ/ERQ discrimination.
    hypothesis_supported = False
    result = "PASS" if eng else "FAIL"
    return SFRecord(
        id="SF_TS2_live_world_genome_archive_witness",
        doi=DOIS["theory_review"],
        literature_prediction=(
            "Without match-linked fitness, demographic mutation on "
            "HostParasiteWorld should not license FRQ/ERQ discrimination "
            "(Buckingham & Ashby 2022 doi:10.1111/jeb.13981)."
        ),
        why_unsolved=WHY_UNSOLVED,
        success_criterion=(
            "Engineering: archive+panel runs on all live seeds with "
            "red_queen_proved=False. hypothesis_supported stays False "
            "(no FRQ/ERQ claim from demographics alone)."
        ),
        null_arms={
            "note": "Mechanism nulls live in SF_TS1; live witness is demography-only.",
            "content_null": "n/a",
            "structure_null": "n/a",
            "dual_null": "n/a",
        },
        n_seeds=len(use_seeds),
        engineering_green=eng,
        hypothesis_supported=hypothesis_supported,
        honesty=(
            f"Live genome archive patterns: peak_contemp={peak_n}, "
            f"mono_rise={rise_n} of {len(use_seeds)}. Demography-only engine "
            "does not support FRQ/ERQ discrimination claims. Ceiling held."
        ),
        claim_ceiling="runtime_observation",
        result=result,
        payload={
            "related_dois": DOIS,
            "trials": trials,
            "peak_contemp_seeds": peak_n,
            "mono_rise_seeds": rise_n,
        },
    )


def run_open_problem_campaign(
    *,
    seeds_main: Sequence[int] | None = None,
    seeds_live: Sequence[int] | None = None,
) -> dict[str, Any]:
    ts1 = _panel_discrimination(seeds_main)
    ts2 = _live_world_witness(seeds_live)
    records = [ts1.to_dict(), ts2.to_dict()]
    pack: dict[str, Any] = {
        "schema": SCHEMA,
        "title": "Open problem 2026-09-25: time-shift FRQ vs ERQ discrimination",
        "dois": DOIS,
        "claim_ceiling": CLAIM_CEILING,
        "claimgate_refuses": list(CLAIMGATE_REFUSES),
        "red_queen_proved": False,
        "arms_race_proved": False,
        "innovation_mechanism": (
            "life_loop.time_shift_assay: CohortArchive during loop + "
            "cross-temporal match panel + match_linked_cycle / trait_escalation"
        ),
        "records": records,
        "engineering_green": all(bool(r["engineering_green"]) for r in records),
        "any_hypothesis_supported": any(bool(r["hypothesis_supported"]) for r in records),
    }
    pack["campaign_digest"] = canonical_digest(
        {k: pack[k] for k in pack if k != "campaign_digest"},
        prefix="op_ts_campaign",
    )
    return pack


def write_campaign_results(
    path: Path | str,
    *,
    seeds_main: Sequence[int] | None = None,
    seeds_live: Sequence[int] | None = None,
) -> dict[str, Any]:
    pack = run_open_problem_campaign(seeds_main=seeds_main, seeds_live=seeds_live)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return pack


__all__ = [
    "SCHEMA",
    "CLAIM_CEILING",
    "CLAIMGATE_REFUSES",
    "DOIS",
    "SEEDS_MAIN",
    "SEEDS_LIVE",
    "SFRecord",
    "run_open_problem_campaign",
    "write_campaign_results",
]
