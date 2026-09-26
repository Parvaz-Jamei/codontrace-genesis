"""HP-ARM01 RQ-earn scaffold — Fork A (asexual clone RQD) measurement wiring.

This module is a **scaffold only**. It wires dense snaps, lagged NFDS clocks,
Pearl coevolve / frozen / absent contrasts, and optional ``debit_backed_cycle``
reuse. It does **not** claim Red Queen Dynamics proved.

Standing locks
--------------
* ``red_queen_proved`` and ``biological_red_queen_proved`` stay False.
* ClaimGate allowlist is not loosened (P4 deferred).
* Estimand default = **Fork A** (asexual clone RQD). Fork B / Slowinski
  invasion and unpaid two-fold cost of sex remain **deferred** — prose must
  not claim sex maintained by RQ while two-fold is unpaid (Hamilton et al.
  1990; Ashby 2020).
* Lag / RQ-earn scoring is evaluated on **debit-active arms only**
  (coevolve / fixed). Avirulent / absent arms never grant RQ-earn credit.
* Seeds typed ``regime_hostile_ne`` are excluded from any lagged_nfds pass
  fraction (demographic floor fail is not an RQ miss).
* ``lagged_nfds_score`` is a paired host↔parasite class series with explicit
  τ — never an alias of ``_oscillation_on_arm``.
* Hold clause stays conjunctive (no OR soft-path); census is not Ne.
* HP physics stays out of ``engine.py``.
* Cuscore / Shewhart / CUSUM / SPC predicates stay **observation-only** and
  never own the accept path for RQ (Pearl SPC module; XFieldInnov).
* Dense ``snap_stride`` series feeds Floquet / phase / lagged NFDS clocks
  only — never the conjunctive hold gate and never an OR soft-path.
* Parasite class memory ring lives on the structural HP arm / env plugin
  only (not ``engine.py``).

Literature anchors: Dybdahl & Lively 1998; Ashby 2020; Buckingham & Ashby
2022; Sasaki 2000; Zaman et al. 2014 (memory analog); Phil. Trans. B
dense sampling / phase under fluctuating eco-evo.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest
from codontrace.genesis.closed_loop_hp_arm01 import (
    ARM_AVIRULENT,
    ARM_COPASSAGED,
    ARM_FIXED,
    CLAIM_CEILING_OBSERVATION,
    ECOLOGY_ARMS,
    SUBSTRATE_LIFE_LOOP,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq import (
    DEBIT_ACTIVE_ARMS,
    OUTCOME_REGIME_HOSTILE_NE,
    STRUCT_PARASITE_CLASS_MEMORY_L,
    collect_dense_snaps,
    dense_snap_generations,
    joint_match_class,
)
from codontrace.genesis.closed_loop_hp_arm01_structural_rq_confirm import (
    CONFIRM_SNAP_STRIDE,
)
from codontrace.genesis.closed_loop_p6 import debit_backed_cycle
from codontrace.genesis.closed_loop_pearl_spc import (
    PASSAGE_ABSENT,
    PASSAGE_COEVOLVE,
    PASSAGE_FROZEN,
)
from codontrace.genesis.measurements.rq_frequency_clocks import (
    DEFAULT_NFDS_THRESHOLD,
    dominant_class_series,
    lagged_nfds_score,
    phase_lag_host_parasite,
)

PREREG_VERSION = "hp_arm01_rq_earn_scaffold_20260926"
HP_ARM01_RQ_EARN_REVISION = "hp-arm01-rq-earn-scaffold-20260926"
SLICE_NAME = "HP-ARM01-RQ-EARN-SCAFFOLD"
ESTIMAND = "fork_a_asexual_clone_rqd_scaffold"
ESTIMAND_FORK = "A"  # Fork B / Slowinski DEFER
FORK_B_SLOWINSKI_STATUS = "deferred"
TWO_FOLD_COST_SEX_STATUS = "unpaid_deferred"

# Pearl passage modes reused for contrast stubs (freeze ≠ absent).
PEARL_PASSAGE_MODES: tuple[str, ...] = (
    PASSAGE_COEVOLVE,
    PASSAGE_FROZEN,
    PASSAGE_ABSENT,
)

# Debit-active ecology arms only grant RQ-earn / lag credit.
RQ_EARN_DEBIT_ARMS: tuple[str, ...] = tuple(DEBIT_ACTIVE_ARMS)

DEFAULT_LAG_TAU = 4
DEFAULT_MIN_POINTS = 20
DEFAULT_SNAP_STRIDE = CONFIRM_SNAP_STRIDE  # 25


def rq_earn_design_dict() -> dict[str, object]:
    return {
        "prereg_version": PREREG_VERSION,
        "revision": HP_ARM01_RQ_EARN_REVISION,
        "slice": SLICE_NAME,
        "estimand": ESTIMAND,
        "estimand_fork": ESTIMAND_FORK,
        "fork_b_slowinski_status": FORK_B_SLOWINSKI_STATUS,
        "two_fold_cost_sex_status": TWO_FOLD_COST_SEX_STATUS,
        "sex_by_rq_claim_allowed": False,
        "substrate": SUBSTRATE_LIFE_LOOP,
        "arms": list(ECOLOGY_ARMS),
        "debit_active_arms": list(RQ_EARN_DEBIT_ARMS),
        "lag_scoring_arms": list(RQ_EARN_DEBIT_ARMS),
        "avi_absent_never_grant_rq_earn_credit": True,
        "pearl_passage_modes": list(PEARL_PASSAGE_MODES),
        "snap_stride": DEFAULT_SNAP_STRIDE,
        "parasite_class_memory_L": STRUCT_PARASITE_CLASS_MEMORY_L,
        "lag_tau": DEFAULT_LAG_TAU,
        "lagged_nfds_threshold": DEFAULT_NFDS_THRESHOLD,
        "lagged_nfds_min_points": DEFAULT_MIN_POINTS,
        "regime_hostile_ne_excluded_from_lagged_nfds_pass_fraction": True,
        "lagged_nfds_is_not_oscillation_flip_wrapper": True,
        "red_queen_proved_allowed": False,
        "biological_red_queen_proved_allowed": False,
        "claim_ceiling_scaffold": CLAIM_CEILING_OBSERVATION,
        "hold_clause": "conjunctive_joint_Rmin_and_max_f_and_ge2_subloci_diverse",
        "or_soft_path_removed": True,
        "body_census_is_ne_proxy": False,
        "spc_owns_accept_path": False,
        "cuscore_spc_observation_only_never_rq_accept": True,
        "dense_snap_feeds_floquet_phase_only_not_hold": True,
        "parasite_memory_ring_hp_env_only": True,
        "confirmatory_prereg_required_before_rq_claim": True,
    }


def rq_earn_design_digest() -> str:
    return canonical_digest(rq_earn_design_dict(), prefix="hp_arm01_rq_earn_design")


def _freq_maps_from_dense_snaps(
    dense_snaps: Mapping[int, Mapping[str, object]],
) -> tuple[dict[int, dict[str, float]], dict[int, dict[str, float]]]:
    """Extract host joint_freq and parasite_class_hist series from dense snaps."""

    host: dict[int, dict[str, float]] = {}
    para: dict[int, dict[str, float]] = {}
    for gen, snap in dense_snaps.items():
        g = int(gen)
        jf = snap.get("joint_freq") or {}
        if isinstance(jf, Mapping):
            host[g] = {str(k): float(v) for k, v in jf.items()}
        ph = snap.get("parasite_class_hist") or {}
        if isinstance(ph, Mapping):
            para[g] = {str(k): float(v) for k, v in ph.items()}
    return host, para


def score_lagged_nfds_on_debit_arms(
    dense_snaps_by_arm: Mapping[str, Mapping[int, Mapping[str, object]]],
    *,
    lag: int = DEFAULT_LAG_TAU,
    min_points: int = DEFAULT_MIN_POINTS,
    threshold: float = DEFAULT_NFDS_THRESHOLD,
    typed_outcome: str | None = None,
) -> dict[str, object]:
    """Score lagged NFDS on debit-active arms only.

    ``regime_hostile_ne`` seeds are excluded from pass-fraction accounting:
    this helper returns ``excluded_regime_hostile_ne=True`` and forces
    ``pass_prelim=False`` without treating the exclusion as an RQ miss.
    Avirulent / absent arms are ignored for credit.
    """

    if typed_outcome == OUTCOME_REGIME_HOSTILE_NE:
        return {
            "pass_prelim": False,
            "excluded_regime_hostile_ne": True,
            "arm_scores": {},
            "debit_arms_scored": [],
            "corr": None,
            "n": 0,
            "lag": int(lag),
            "min_points": int(min_points),
            "red_queen_proved": False,
            "biological_red_queen_proved": False,
        }

    arm_scores: dict[str, dict[str, object]] = {}
    any_pass = False
    for arm_name in RQ_EARN_DEBIT_ARMS:
        snaps = dense_snaps_by_arm.get(arm_name) or {}
        host, para = _freq_maps_from_dense_snaps(snaps)
        score = lagged_nfds_score(
            host, para, lag=lag, min_points=min_points, threshold=threshold
        )
        # Strip any accidental proved key; hardcode false on the envelope.
        score = dict(score)
        score["red_queen_proved"] = False
        score["biological_red_queen_proved"] = False
        arm_scores[arm_name] = score
        if score.get("pass_prelim") is True:
            any_pass = True

    # Aggregate: require debit-active concordance (all scored debit arms pass).
    debit_scored = [a for a in RQ_EARN_DEBIT_ARMS if a in arm_scores]
    all_pass = bool(debit_scored) and all(
        arm_scores[a].get("pass_prelim") is True for a in debit_scored
    )
    return {
        "pass_prelim": all_pass,
        "excluded_regime_hostile_ne": False,
        "arm_scores": arm_scores,
        "debit_arms_scored": list(debit_scored),
        "avi_absent_ignored": True,
        "any_debit_arm_pass": any_pass,
        "lag": int(lag),
        "min_points": int(min_points),
        "threshold": float(threshold),
        "red_queen_proved": False,
        "biological_red_queen_proved": False,
    }


def pearl_contrast_stubs(
    *,
    coevolve_lag_pass: bool,
    frozen_lag_pass: bool,
    absent_lag_pass: bool,
    coevolve_debit_backed_cycle: bool | None = None,
    frozen_debit_backed_cycle: bool | None = None,
) -> dict[str, object]:
    """Pearl coevolve / frozen / absent contrast summary (scaffold stub).

    Expected confirmatory pattern (future prereg): coevolve shows lag/cycle;
    frozen breaks debit-backed cycle / lag; absent does not recreate
    antagonist-driven lag. This stub never sets ``red_queen_proved``.
    """

    return {
        "passage_modes": list(PEARL_PASSAGE_MODES),
        "coevolve_lag_pass": bool(coevolve_lag_pass),
        "frozen_lag_pass": bool(frozen_lag_pass),
        "absent_lag_pass": bool(absent_lag_pass),
        "coevolve_debit_backed_cycle": coevolve_debit_backed_cycle,
        "frozen_debit_backed_cycle": frozen_debit_backed_cycle,
        "freeze_breaks_expected": True,
        "absent_not_antagonist_lag": True,
        "red_queen_proved": False,
        "biological_red_queen_proved": False,
        "scaffold_only": True,
    }


@dataclass(frozen=True, slots=True)
class RQEarnReportStub:
    """Smoke report object for the RQ-earn scaffold.

    Flags are hardcoded False. A future confirmatory prereg + sealed campaign
    is required before ClaimGate may allow ``red_queen_proved``.
    """

    estimand_fork: str = ESTIMAND_FORK
    red_queen_proved: bool = False
    biological_red_queen_proved: bool = False
    claim_ceiling: str = CLAIM_CEILING_OBSERVATION
    design_digest: str = ""
    lagged_nfds: dict[str, object] = field(default_factory=dict)
    pearl_contrast: dict[str, object] = field(default_factory=dict)
    debit_backed_cycle_note: str = "reuse closed_loop_p6.debit_backed_cycle when histories align"
    notes: str = ""
    digest: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "slice": SLICE_NAME,
            "estimand": ESTIMAND,
            "estimand_fork": self.estimand_fork,
            "fork_b_slowinski_status": FORK_B_SLOWINSKI_STATUS,
            "two_fold_cost_sex_status": TWO_FOLD_COST_SEX_STATUS,
            "sex_by_rq_claim_allowed": False,
            "red_queen_proved": False,
            "biological_red_queen_proved": False,
            "claim_ceiling": self.claim_ceiling,
            "design_digest": self.design_digest,
            "lagged_nfds": self.lagged_nfds,
            "pearl_contrast": self.pearl_contrast,
            "debit_backed_cycle_note": self.debit_backed_cycle_note,
            "lag_scoring_debit_active_only": True,
            "regime_hostile_ne_excluded_from_pass_fraction": True,
            "notes": self.notes,
            "digest": self.digest,
            "scaffold_only": True,
        }


def build_rq_earn_report_stub(
    *,
    dense_snaps_by_arm: Mapping[str, Mapping[int, Mapping[str, object]]] | None = None,
    typed_outcome: str | None = None,
    lag: int = DEFAULT_LAG_TAU,
    min_points: int = DEFAULT_MIN_POINTS,
    coevolve_history: Sequence[tuple[str, ...]] | None = None,
    coevolve_debits: Sequence[int] | None = None,
    frozen_history: Sequence[tuple[str, ...]] | None = None,
    frozen_debits: Sequence[int] | None = None,
) -> RQEarnReportStub:
    """Build a scaffold report; flags always False."""

    design = rq_earn_design_digest()
    snaps = dense_snaps_by_arm or {}
    lagged = score_lagged_nfds_on_debit_arms(
        snaps, lag=lag, min_points=min_points, typed_outcome=typed_outcome
    )

    coevo_cycle: bool | None = None
    frozen_cycle: bool | None = None
    if coevolve_history is not None and coevolve_debits is not None:
        if len(coevolve_history) == len(coevolve_debits):
            coevo_cycle = bool(debit_backed_cycle(tuple(coevolve_history), tuple(coevolve_debits)))
    if frozen_history is not None and frozen_debits is not None:
        if len(frozen_history) == len(frozen_debits):
            frozen_cycle = bool(debit_backed_cycle(tuple(frozen_history), tuple(frozen_debits)))

    # Pearl stubs: without live arm runs, lag flags stay False on empty snaps.
    arm_scores = lagged.get("arm_scores") or {}
    coevo_pass = bool(
        (arm_scores.get(ARM_COPASSAGED) or {}).get("pass_prelim")
    )
    # Fixed arm is debit-active frozen-stock contrast in ecology taxonomy.
    frozen_pass = bool((arm_scores.get(ARM_FIXED) or {}).get("pass_prelim"))
    # Absent / avirulent never grant credit — report explicit False.
    absent_pass = False
    if ARM_AVIRULENT in snaps:
        absent_pass = False

    pearl = pearl_contrast_stubs(
        coevolve_lag_pass=coevo_pass,
        frozen_lag_pass=frozen_pass,
        absent_lag_pass=absent_pass,
        coevolve_debit_backed_cycle=coevo_cycle,
        frozen_debit_backed_cycle=frozen_cycle,
    )

    notes = (
        "fork_a_scaffold;fork_b_slowinski=deferred;two_fold=unpaid;"
        "red_queen_proved=false;lag_debit_active_only=true;"
        "regime_hostile_ne_excluded=true;confirmatory_prereg_required=true"
    )
    body = {
        "design": design,
        "lagged": {k: lagged[k] for k in ("pass_prelim", "lag", "n") if k in lagged},
        "pearl": {
            "coevolve_lag_pass": pearl["coevolve_lag_pass"],
            "frozen_lag_pass": pearl["frozen_lag_pass"],
            "absent_lag_pass": pearl["absent_lag_pass"],
        },
        "red_queen_proved": False,
        "revision": HP_ARM01_RQ_EARN_REVISION,
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()

    return RQEarnReportStub(
        estimand_fork=ESTIMAND_FORK,
        red_queen_proved=False,
        biological_red_queen_proved=False,
        claim_ceiling=CLAIM_CEILING_OBSERVATION,
        design_digest=design,
        lagged_nfds=lagged,
        pearl_contrast=pearl,
        notes=notes,
        digest=digest,
    )


def classify_rq_earn_smoke(
    *,
    dense_snaps_by_arm: Mapping[str, Mapping[int, Mapping[str, object]]] | None = None,
    typed_outcome: str | None = None,
) -> dict[str, object]:
    """Smoke classifier: always returns proved flags False."""

    report = build_rq_earn_report_stub(
        dense_snaps_by_arm=dense_snaps_by_arm,
        typed_outcome=typed_outcome,
    )
    payload = report.to_dict()
    payload["smoke"] = True
    payload["red_queen_proved"] = False
    payload["biological_red_queen_proved"] = False
    if report.red_queen_proved or report.biological_red_queen_proved:
        raise ConfigurationError("RQ-earn scaffold must not set proved flags")
    return payload


__all__ = [
    "DEFAULT_LAG_TAU",
    "DEFAULT_MIN_POINTS",
    "DEFAULT_SNAP_STRIDE",
    "ESTIMAND",
    "ESTIMAND_FORK",
    "FORK_B_SLOWINSKI_STATUS",
    "HP_ARM01_RQ_EARN_REVISION",
    "PEARL_PASSAGE_MODES",
    "PREREG_VERSION",
    "RQEarnReportStub",
    "RQ_EARN_DEBIT_ARMS",
    "SLICE_NAME",
    "TWO_FOLD_COST_SEX_STATUS",
    "build_rq_earn_report_stub",
    "classify_rq_earn_smoke",
    "pearl_contrast_stubs",
    "rq_earn_design_dict",
    "rq_earn_design_digest",
    "score_lagged_nfds_on_debit_arms",
    # Re-exports useful to callers wiring dense series
    "collect_dense_snaps",
    "dense_snap_generations",
    "debit_backed_cycle",
    "dominant_class_series",
    "joint_match_class",
    "lagged_nfds_score",
    "phase_lag_host_parasite",
]
