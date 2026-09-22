"""Biomedical port: a DomainProfile, not a second engine."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from codontrace.claimgate.domain import (
    BIOMEDICAL,
    FDA_2023_EVIDENCE_CATEGORIES,
    bundle_from_declared_scores,
)
from codontrace.claimgate.schema import ClaimgateBundle
from codontrace.errors import ConfigurationError

BLOCKED_BIOMEDICAL_CLAIMS = BIOMEDICAL.blocked_claims

_IMPORTANCE = frozenset({"low", "medium", "high"})
_KNOWLEDGE = frozenset({"none", "partial", "adequate"})
_SUBMODEL_ROLES = frozenset(
    {"device", "patient", "coupled", "cohort", "clinician", "outcome_map", "full"}
)
# FDA 2023 cats that are comparator or calculation evidence, not support-only.
_VALIDATING_CATEGORIES = frozenset({1, 3, 4, 5, 8})
_WORKSHEET_NOTE = "Credibility worksheet does not raise the claim ladder."


@dataclass(frozen=True, slots=True)
class CredibilityWorksheet:
    """Executable PIRT plus a weakest-submodel cap.

    PIRT ranking is the nuclear-safety table (importance × knowledge).
    The cap is building-block VVUQ: a coupled model stays at its weakest
    recorded submodel. Neither number is a ClaimGate public grade.
    """

    open_gaps: tuple[str, ...]
    limiting_submodel: str
    limiting_level: int | None
    coupled_ceiling: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "open_gaps": list(self.open_gaps),
            "limiting_submodel": self.limiting_submodel,
            "limiting_level": self.limiting_level,
            "coupled_ceiling": self.coupled_ceiling,
            "raises_claim_ladder": False,
            "sources": ["oecd_nea_pirt", "building_block_vvuq"],
        }


def bundle_from_biomedical_cou(
    *,
    question_of_interest: str,
    context_of_use: str,
    model_influence: int,
    decision_consequence: int,
    treatment_scores: Sequence[float],
    control_scores: Sequence[float],
    metric: str = "declared_score",
    software_name: str = "external-biomedical-table",
    software_version: str = "unspecified",
    claimed: str = "runtime_observation",
    device_software_kind: str = "analog_table",
    iec_62304_class: str = "undeclared",
    imdrf_n12_category: str = "undeclared",
    fda_2023_evidence: Sequence[int] = (),
    physics_based: bool = False,
) -> ClaimgateBundle:
    return bundle_from_declared_scores(
        profile=BIOMEDICAL,
        question_of_interest=question_of_interest,
        context_of_use=context_of_use,
        model_influence=model_influence,
        decision_consequence=decision_consequence,
        treatment_scores=treatment_scores,
        control_scores=control_scores,
        metric=metric,
        software_name=software_name,
        software_version=software_version,
        claimed=claimed,
        device_software_kind=device_software_kind,
        iec_62304_class=iec_62304_class,
        imdrf_n12_category=imdrf_n12_category,
        fda_2023_evidence=fda_2023_evidence,
        physics_based=physics_based,
    )


def bundle_from_device_model_cou(
    *,
    question_of_interest: str,
    context_of_use: str,
    model_influence: int,
    decision_consequence: int,
    treatment_scores: Sequence[float],
    control_scores: Sequence[float],
    device_software_kind: str,
    iec_62304_class: str = "undeclared",
    imdrf_n12_category: str = "undeclared",
    fda_2023_evidence: Sequence[int] = (),
    physics_based: bool = False,
    metric: str = "declared_score",
    software_name: str = "external-device-model-table",
    software_version: str = "unspecified",
    claimed: str = "runtime_observation",
) -> ClaimgateBundle:
    """Equipment-adjacent analog: SiMD/SaMD *labels*, not a device file.

    ``device_software_kind`` must be declared. Declaring ``simd_declared``
    records IMDRF medical-device-software language; it does not classify
    a product or invoke IEC 62304.
    """

    kind = device_software_kind.strip().lower()
    if kind not in {"simd_declared", "samd_declared", "analog_table"}:
        raise ConfigurationError(
            "bundle_from_device_model_cou requires analog_table, simd_declared, or samd_declared;"
            f" got {device_software_kind!r}."
        )
    return bundle_from_biomedical_cou(
        question_of_interest=question_of_interest,
        context_of_use=context_of_use,
        model_influence=model_influence,
        decision_consequence=decision_consequence,
        treatment_scores=treatment_scores,
        control_scores=control_scores,
        metric=metric,
        software_name=software_name,
        software_version=software_version,
        claimed=claimed,
        device_software_kind=kind,
        iec_62304_class=iec_62304_class,
        imdrf_n12_category=imdrf_n12_category,
        fda_2023_evidence=fda_2023_evidence,
        physics_based=physics_based,
    )


def _label(raw: object, allowed: frozenset[str], field: str) -> str:
    if not isinstance(raw, str):
        raise ConfigurationError(f"{field} must be one of {sorted(allowed)}.")
    value = raw.strip().lower()
    if value not in allowed:
        raise ConfigurationError(f"{field} must be one of {sorted(allowed)}; got {raw!r}.")
    return value


def _row_name(raw: Mapping[str, object], kind: str, index: int) -> str:
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ConfigurationError(f"{kind}[{index}].name is required.")
    return name.strip()


def _level(raw: object, index: int) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw not in range(6):
        raise ConfigurationError(f"submodels[{index}].level must be an integer 0–5.")
    return raw


def credibility_worksheet(
    phenomena: Sequence[Mapping[str, object]] = (),
    submodels: Sequence[Mapping[str, object]] = (),
) -> CredibilityWorksheet:
    """Rank phenomena and cap a coupled model at its weakest submodel.

    A high-importance phenomenon is an open gap until knowledge is
    ``adequate``. Medium importance is a gap only when knowledge is
    ``none``. Low importance is screened out, as in a PIRT.

    A submodel declared non-identifiable cannot contribute above 1.
    Evidence limited to calibration, plausibility, or emergent behaviour
    (FDA categories 2, 6, 7) cannot contribute above 2. The ceiling is
    the minimum of those usable levels. It does not call the auditor
    and cannot promote a claim.
    """

    if not phenomena and not submodels:
        raise ConfigurationError("credibility_worksheet needs a phenomenon or a submodel.")
    gaps: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(phenomena):
        if not isinstance(raw, Mapping):
            raise ConfigurationError(f"phenomena[{index}] must be a mapping.")
        name = _row_name(raw, "phenomena", index)
        if name in seen:
            raise ConfigurationError(f"duplicate worksheet name {name!r}.")
        seen.add(name)
        importance = _label(raw.get("importance"), _IMPORTANCE, f"phenomena[{index}].importance")
        knowledge = _label(raw.get("knowledge"), _KNOWLEDGE, f"phenomena[{index}].knowledge")
        if importance == "high" and knowledge != "adequate":
            gaps.append(f"pirt:{name}")
        elif importance == "medium" and knowledge == "none":
            gaps.append(f"pirt:{name}")

    usable: list[tuple[str, int]] = []
    for index, raw in enumerate(submodels):
        if not isinstance(raw, Mapping):
            raise ConfigurationError(f"submodels[{index}] must be a mapping.")
        name = _row_name(raw, "submodels", index)
        if name in seen:
            raise ConfigurationError(f"duplicate worksheet name {name!r}.")
        seen.add(name)
        _label(raw.get("role"), _SUBMODEL_ROLES, f"submodels[{index}].role")
        level = _level(raw.get("level"), index)
        identifiable = raw.get("identifiable", True)
        if not isinstance(identifiable, bool):
            raise ConfigurationError(f"submodels[{index}].identifiable must be true or false.")
        categories = raw.get("evidence_categories", ())
        if isinstance(categories, (str, bytes)) or not isinstance(categories, Sequence):
            raise ConfigurationError(f"submodels[{index}].evidence_categories must be a list.")
        cats: list[int] = []
        for item in categories:
            if isinstance(item, bool) or not isinstance(item, int):
                raise ConfigurationError("fda evidence categories must be integers 1–8.")
            if item not in FDA_2023_EVIDENCE_CATEGORIES:
                raise ConfigurationError("fda evidence categories must be integers 1–8.")
            cats.append(item)
        usable_level = level
        if not identifiable:
            usable_level = min(usable_level, 1)
            gaps.append(f"nonidentifiable:{name}")
        if cats and not _VALIDATING_CATEGORIES.intersection(cats):
            usable_level = min(usable_level, 2)
            gaps.append(f"supporting_evidence_only:{name}")
        usable.append((name, usable_level))

    if not usable:
        return CredibilityWorksheet(tuple(gaps), "", None, None)
    limiting_name, limiting_level = min(usable, key=lambda item: (item[1], item[0]))
    ceiling = limiting_level if len(usable) >= 2 else None
    return CredibilityWorksheet(tuple(gaps), limiting_name, limiting_level, ceiling)


def attach_credibility_worksheet(
    bundle: ClaimgateBundle,
    phenomena: Sequence[Mapping[str, object]] = (),
    submodels: Sequence[Mapping[str, object]] = (),
) -> ClaimgateBundle:
    """Store the worksheet on the bundle. The public ladder is unchanged."""

    sheet = credibility_worksheet(phenomena, submodels)
    extra = dict(bundle.extra or {})
    extra["credibility_worksheet"] = sheet.to_dict()
    limitations = bundle.limitations
    if _WORKSHEET_NOTE not in limitations:
        limitations = limitations + (_WORKSHEET_NOTE,)
    return replace(bundle, extra=extra, limitations=limitations)


@dataclass(frozen=True, slots=True)
class BiomedicalStudy:
    """A worksheet bound to executed bundles, plus the rows still only declared."""

    claim_level: int | None
    worksheet: CredibilityWorksheet
    executed: tuple[str, ...]
    declared_only: tuple[str, ...]
    submodel_sources: tuple[tuple[str, int, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_level": self.claim_level,
            "worksheet": self.worksheet.to_dict(),
            "executed": list(self.executed),
            "declared_only": list(self.declared_only),
            "submodel_sources": [
                {"name": name, "level": level, "source": source}
                for name, level, source in self.submodel_sources
            ],
            "raises_claim_ladder": False,
        }


def _knowledge_from_run(level: int, replay: bool) -> str:
    if level >= 4 and replay:
        return "adequate"
    if level >= 3:
        return "partial"
    return "none"


def _as_rows(raw: object, field: str) -> tuple[Mapping[str, object], ...]:
    if raw is None:
        return ()
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        raise ConfigurationError(f"{field} must be a list.")
    rows: list[Mapping[str, object]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ConfigurationError(f"{field}[{index}] must be a mapping.")
        rows.append(item)
    return tuple(rows)


def audit_biomedical_study(
    study: Mapping[str, object],
    *,
    experiment: ClaimgateBundle | None = None,
    bundles: Mapping[str, ClaimgateBundle] | None = None,
) -> BiomedicalStudy:
    """Bind the worksheet to runs. A declared rank cannot close a gap.

    A phenomenon closes only when its ``arm`` is on ``experiment``, the
    audit is at least 4, and replay is verified. Otherwise a typed
    ``adequate`` is downgraded and the row is ``declared_only``.

    A submodel with ``use_experiment`` or ``bundle`` takes its level from
    ``audit_bundle``. A typed level with no bundle is capped at 2.
    """

    from codontrace.claimgate.auditor import audit_bundle

    claimed = study.get("claimed")
    if isinstance(claimed, str) and claimed.strip().lower() in BIOMEDICAL.blocked_claims:
        raise ConfigurationError(f"{claimed!r} is blocked on the biomedical study.")
    library = dict(bundles or {})
    run_level: int | None = None
    replay = False
    arm_names: set[str] = set()
    if experiment is not None:
        run_level = audit_bundle(experiment).achieved_level
        replay = experiment.replay.verified
        arm_names = {arm.name for arm in experiment.arms}

    phenomena_out: list[dict[str, object]] = []
    executed: list[str] = []
    declared_only: list[str] = []
    for raw in _as_rows(study.get("phenomena"), "phenomena"):
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ConfigurationError("phenomena need a name.")
        arm = raw.get("arm")
        row = dict(raw)
        if isinstance(arm, str) and arm.strip():
            if experiment is None:
                raise ConfigurationError(f"phenomenon {name!r} names an arm but no experiment was given.")
            if arm not in arm_names:
                raise ConfigurationError(f"arm {arm!r} is not in the experiment.")
            assert run_level is not None
            row["knowledge"] = _knowledge_from_run(run_level, replay)
            executed.append(name.strip())
        else:
            declared_only.append(name.strip())
            if row.get("knowledge") == "adequate":
                row["knowledge"] = "partial"
            elif "knowledge" not in row:
                row["knowledge"] = "none"
        phenomena_out.append(row)

    submodels_out: list[dict[str, object]] = []
    sources: list[tuple[str, int, str]] = []
    for raw in _as_rows(study.get("submodels"), "submodels"):
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ConfigurationError("submodels need a name.")
        row = dict(raw)
        bound: ClaimgateBundle | None = None
        if row.get("use_experiment") is True:
            if experiment is None:
                raise ConfigurationError(f"submodel {name!r} requested the experiment, and none was given.")
            bound = experiment
        bundle_key = row.get("bundle")
        if isinstance(bundle_key, str):
            if bundle_key not in library:
                raise ConfigurationError(f"submodel bundle {bundle_key!r} was not provided.")
            bound = library[bundle_key]
        if bound is not None:
            measured = audit_bundle(bound).achieved_level
            typed = row.get("level")
            if isinstance(typed, bool) or not isinstance(typed, int):
                typed = measured
            row["level"] = min(typed, measured)
            sources.append((name.strip(), row["level"], "executed"))
            executed.append(name.strip())
        else:
            typed = row.get("level", 0)
            if isinstance(typed, bool) or not isinstance(typed, int) or typed not in range(6):
                raise ConfigurationError(f"submodel {name!r} needs a level 0–5 or a bundle.")
            row["level"] = min(typed, 2)
            sources.append((name.strip(), row["level"], "declared"))
            declared_only.append(name.strip())
        submodels_out.append(row)

    sheet = credibility_worksheet(phenomena_out, submodels_out)
    extra_gaps = list(sheet.open_gaps)
    for name in declared_only:
        extra_gaps.append(f"declared_only:{name}")
    sheet = CredibilityWorksheet(
        tuple(extra_gaps),
        sheet.limiting_submodel,
        sheet.limiting_level,
        sheet.coupled_ceiling,
    )
    return BiomedicalStudy(run_level, sheet, tuple(executed), tuple(declared_only), tuple(sources))


def audit_biomedical_study_file(path: str) -> BiomedicalStudy:
    """Read a study JSON. ``experiment`` is an HE01 campaign path, not a certificate."""

    import json
    from pathlib import Path

    from codontrace.claimgate.adapters.codontrace import bundle_from_hard_experiment_01

    study_path = Path(path)
    if not study_path.is_file():
        raise ConfigurationError(f"study file not found: {path}")
    loaded = json.loads(study_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ConfigurationError("study JSON must be an object.")
    experiment_raw = loaded.get("experiment")
    experiment = None
    if isinstance(experiment_raw, str) and experiment_raw.strip():
        candidate = Path(experiment_raw)
        if not candidate.is_file():
            for parent in study_path.parents:
                hit = parent / experiment_raw
                if hit.is_file():
                    candidate = hit
                    break
        if not candidate.is_file():
            raise ConfigurationError(f"study experiment not found: {experiment_raw}")
        experiment = bundle_from_hard_experiment_01(candidate)
    return audit_biomedical_study(loaded, experiment=experiment)