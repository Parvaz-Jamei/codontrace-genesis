"""Gorelick et al. 2004 normalized mutual information / entropy for DoL.

Confirmatory HARD_EXPERIMENT_03 metric. Non-NMI DoL proxies elsewhere remain
**legacy** and are not confirmatory for HE03.

Literature:
- Gorelick, Bertram, Killeen, Fewell (2004). Am Nat 164:677–682.
- Gorelick & Bertram (2007). Insectes Sociaux (NMI/NME for DoL).
- Goldsby et al. (2012). PNAS (uses Gorelick MI on individual×task matrices).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.genesis.canonical import canonical_digest


def _entropy(counts: Mapping[str, int], n: float) -> float:
    if n <= 0.0:
        return 0.0
    ent = 0.0
    for count in counts.values():
        if count <= 0:
            continue
        p = count / n
        ent -= p * math.log2(p)
    return ent


@dataclass(frozen=True, slots=True)
class GorelickNMIResult:
    """Gorelick NMI/NME components on an individual×task matrix."""

    n_observations: int
    n_individuals: int
    n_tasks: int
    mutual_information: float
    h_individual: float
    h_task: float
    d_task: float
    d_indiv: float
    d_sym: float
    matrix_degenerate: bool
    literature_ref: str = "gorelick_etal_2004_amnat_10.1086/424968"
    claim_ceiling: str = "runtime_observation"
    collective_intelligence: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "n_observations": self.n_observations,
            "n_individuals": self.n_individuals,
            "n_tasks": self.n_tasks,
            "mutual_information": self.mutual_information,
            "h_individual": self.h_individual,
            "h_task": self.h_task,
            "d_task": self.d_task,
            "d_indiv": self.d_indiv,
            "d_sym": self.d_sym,
            "matrix_degenerate": self.matrix_degenerate,
            "literature_ref": self.literature_ref,
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": self.collective_intelligence,
            "legacy_proxy": False,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


def gorelick_nmi(
    individual_tasks: Sequence[tuple[str, str]],
) -> GorelickNMIResult:
    """Compute Gorelick DoL metrics from (individual_id, task_id) samples.

    Returns zeros with ``matrix_degenerate=True`` when the joint matrix cannot
    support a meaningful NMI (empty, single individual, or single task).
    """

    if not individual_tasks:
        return GorelickNMIResult(
            n_observations=0,
            n_individuals=0,
            n_tasks=0,
            mutual_information=0.0,
            h_individual=0.0,
            h_task=0.0,
            d_task=0.0,
            d_indiv=0.0,
            d_sym=0.0,
            matrix_degenerate=True,
        )

    n = float(len(individual_tasks))
    joint: dict[tuple[str, str], int] = {}
    indiv_counts: dict[str, int] = {}
    task_counts: dict[str, int] = {}
    for individual_id, task_id in individual_tasks:
        key = (str(individual_id), str(task_id))
        joint[key] = joint.get(key, 0) + 1
        indiv_counts[key[0]] = indiv_counts.get(key[0], 0) + 1
        task_counts[key[1]] = task_counts.get(key[1], 0) + 1

    n_indiv = len(indiv_counts)
    n_tasks = len(task_counts)
    degenerate = n_indiv <= 1 or n_tasks <= 1
    h_x = _entropy(indiv_counts, n)
    h_y = _entropy(task_counts, n)
    h_xy = 0.0
    for count in joint.values():
        if count <= 0:
            continue
        p = count / n
        h_xy -= p * math.log2(p)
    mutual = h_x + h_y - h_xy
    if mutual < 0.0:
        mutual = 0.0
    if degenerate:
        return GorelickNMIResult(
            n_observations=len(individual_tasks),
            n_individuals=n_indiv,
            n_tasks=n_tasks,
            mutual_information=round(mutual, 10),
            h_individual=round(h_x, 10),
            h_task=round(h_y, 10),
            d_task=0.0,
            d_indiv=0.0,
            d_sym=0.0,
            matrix_degenerate=True,
        )

    d_task = 0.0 if h_y <= 0.0 else min(1.0, mutual / h_y)
    d_indiv = 0.0 if h_x <= 0.0 else min(1.0, mutual / h_x)
    denom = math.sqrt(h_x * h_y)
    d_sym = 0.0 if denom <= 0.0 else min(1.0, mutual / denom)
    return GorelickNMIResult(
        n_observations=len(individual_tasks),
        n_individuals=n_indiv,
        n_tasks=n_tasks,
        mutual_information=round(mutual, 10),
        h_individual=round(h_x, 10),
        h_task=round(h_y, 10),
        d_task=round(d_task, 10),
        d_indiv=round(d_indiv, 10),
        d_sym=round(d_sym, 10),
        matrix_degenerate=False,
    )
