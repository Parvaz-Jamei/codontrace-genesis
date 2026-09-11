"""Phase J replay-verified CI candidate packs for CodonTrace Genesis.

Measurement-first follow-on after Phase I: independent campaign digest
re-execution so ``replay_verification`` can be earned honestly, plus an
Okasha/Price covariance scaffold on the two-task analog.

None of this auto-sets ClaimGate flags. Smoke never earns flags.
``collective_intelligence`` / ``intelligence`` / AGI stay blocked.
``collective_intelligence_candidate`` may be *allowed* only when every
ClaimGate flag is actually earned, including a matching independent replay.
That is still a candidate label, never proved CI.

Claim ceiling for new measurement objects: ``runtime_observation``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import (
    canonical_digest,
    is_real_evidence_digest,
    require_finite_float,
)
from codontrace.genesis.claim_gate import ClaimDecision, ClaimRequest, ScientificClaimGate
from codontrace.genesis.phase_h import (
    _CLAIM_CEILING,
    _FORBIDDEN,
    RESEARCH_SEED_COUNT,
    SMOKE_SEED_COUNT,
    _assert_ci_blocked,
    _mean,
    collective_intelligence_candidate_checklist,
)
from codontrace.genesis.phase_i import (
    DEFAULT_GROUP_SIZE,
    RESEARCH_GENERATION_COUNT,
    SMOKE_GENERATION_COUNT,
    EvolvedDivisionOfLaborCampaign,
    ExportOfFitnessObservation,
    HeldoutUnfamiliarPartnerCampaign,
    MlsEvolutionaryOutcomeCampaign,
    TaskGroupEvaluation,
    _resolve_group_count,
    _resolve_seeds,
    build_export_of_fitness_observation,
    earn_collective_intelligence_candidate_flags,
    evaluate_phase_i_claim,
    evolve_two_task_population,
    run_evolved_division_of_labor_experiment,
    run_heldout_unfamiliar_partner_experiment,
    run_mls_evolutionary_outcome_experiment,
)

HELD_OUT_KIND = "heldout_unfamiliar_partner"
EVOLVED_DOL_KIND = "evolved_division_of_labor"
MLS_KIND = "mls_evolutionary_outcome"
PRICE_KIND = "price_equation_covariance"
PHASE_I_REPLAY_KINDS: tuple[str, ...] = (HELD_OUT_KIND, EVOLVED_DOL_KIND, MLS_KIND)
KNOWN_REPLAY_KINDS: frozenset[str] = frozenset((*PHASE_I_REPLAY_KINDS, PRICE_KIND))
PRICE_PARTITION_TOLERANCE = 1e-8
MEASURED_RUNTIME = "measured_runtime_observation"

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "price_1970_selection_and_covariance",
        "Price 1970 Nature doi:10.1038/227520a0: selection as covariance. "
        "Phase J records a last-generation snapshot partition, not a full "
        "multi-generation Price paper and not a transmission term.",
    ),
    (
        "okasha_2006_mls1_price_partition",
        "Okasha 2006: MLS1 Price bookkeeping (between + within covariance) is "
        "not MLS2 evolutionary outcome. Phase I still owns the outcome label; "
        "this scaffold is the covariance terms.",
    ),
    (
        "replay_verification_independent_digest",
        "ClaimGate replay_verification requires an independent re-execution "
        "whose campaign digests match. Matching is not faked; smoke never earns.",
    ),
)


def _campaign_digest(campaign: object) -> str:
    digest = getattr(campaign, "digest", "")
    if callable(digest):
        digest = digest()
    text = str(digest or "")
    if not is_real_evidence_digest(text):
        raise ConfigurationError("campaign digest is not a real evidence digest.")
    return text


def population_covariance(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Population covariance (Price 1970 moment: divide by n, not n-1)."""

    if len(xs) != len(ys):
        raise ConfigurationError("covariance vectors must be the same length.")
    if len(xs) < 2:
        return 0.0
    left = [require_finite_float("cov_x", float(item)) for item in xs]
    right = [require_finite_float("cov_y", float(item)) for item in ys]
    mean_x = sum(left) / len(left)
    mean_y = sum(right) / len(right)
    total = sum((x - mean_x) * (y - mean_y) for x, y in zip(left, right, strict=True))
    return round(total / len(left), 10)


@dataclass(frozen=True, slots=True)
class PriceEquationPartition:
    """Okasha-style MLS1 Price snapshot. Not a major transition."""

    n_groups: int
    n_organisms: int
    mean_trait: float
    mean_personal_fitness: float
    mean_group_fitness: float
    between_group_covariance_mls1: float
    between_group_covariance_mls2_analog: float
    within_group_covariance: float
    total_organism_covariance: float
    mls1_partition_residual: float
    transmission_term_estimated: bool = False
    price_equation_complete: bool = False
    major_transition_in_individuality: bool = False
    schema_version: str = "price_equation_partition_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.n_groups < 1 or self.n_organisms < 1:
            raise ConfigurationError("Price partition requires at least one group and organism.")
        for name in (
            "mean_trait",
            "mean_personal_fitness",
            "mean_group_fitness",
            "between_group_covariance_mls1",
            "between_group_covariance_mls2_analog",
            "within_group_covariance",
            "total_organism_covariance",
            "mls1_partition_residual",
        ):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))
        if self.transmission_term_estimated or self.price_equation_complete:
            raise ConfigurationError("snapshot scaffold must not claim a complete Price equation.")
        if self.major_transition_in_individuality:
            raise ConfigurationError(
                "Price scaffold must not set major_transition_in_individuality."
            )
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("PriceEquationPartition digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "n_groups": self.n_groups,
            "n_organisms": self.n_organisms,
            "mean_trait": self.mean_trait,
            "mean_personal_fitness": self.mean_personal_fitness,
            "mean_group_fitness": self.mean_group_fitness,
            "between_group_covariance_mls1": self.between_group_covariance_mls1,
            "between_group_covariance_mls2_analog": self.between_group_covariance_mls2_analog,
            "within_group_covariance": self.within_group_covariance,
            "total_organism_covariance": self.total_organism_covariance,
            "mls1_partition_residual": self.mls1_partition_residual,
            "transmission_term_estimated": self.transmission_term_estimated,
            "price_equation_complete": self.price_equation_complete,
            "major_transition_in_individuality": self.major_transition_in_individuality,
            "collective_intelligence": False,
            "limitations": [
                "last_generation_snapshot_no_transmission_term",
                "two_task_analog_not_price_1970_paper",
                "mls2_group_fitness_is_not_mean_particle_fitness",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def price_partition_from_groups(rows: Sequence[TaskGroupEvaluation]) -> PriceEquationPartition:
    """MLS1 Price identity on equal-sized groups: total = between + within.

    Trait ``z`` is heritable task preference. Organism fitness ``w`` is personal
    task yield. MLS1 group fitness is mean personal fitness. The MLS2 analog
    uses complementary-task group payoff and is **not** in the identity.
    """

    if not rows:
        raise ConfigurationError("price partition needs at least one group.")
    traits: list[float] = []
    personal: list[float] = []
    group_traits: list[float] = []
    group_w_mls1: list[float] = []
    group_w_mls2: list[float] = []
    within_covs: list[float] = []
    sizes: list[int] = []
    for row in rows:
        z = [float(item) for item in row.preferences]
        w = [float(item) for item in row.personal_fitness]
        if len(z) != len(w) or not z:
            raise ConfigurationError(
                "preferences and personal_fitness must align and be non-empty."
            )
        if sizes and len(z) != sizes[0]:
            raise ConfigurationError("Price scaffold requires equal group sizes.")
        traits.extend(z)
        personal.extend(w)
        sizes.append(len(z))
        group_traits.append(sum(z) / len(z))
        group_w_mls1.append(sum(w) / len(w))
        group_w_mls2.append(float(row.group_fitness))
        within_covs.append(population_covariance(w, z))
    within = _mean(within_covs)
    between_mls1 = population_covariance(group_w_mls1, group_traits)
    between_mls2 = population_covariance(group_w_mls2, group_traits)
    total = population_covariance(personal, traits)
    residual = round(total - (between_mls1 + within), 10)
    partition = PriceEquationPartition(
        n_groups=len(rows),
        n_organisms=len(traits),
        mean_trait=_mean(traits),
        mean_personal_fitness=_mean(personal),
        mean_group_fitness=_mean(group_w_mls2),
        between_group_covariance_mls1=between_mls1,
        between_group_covariance_mls2_analog=between_mls2,
        within_group_covariance=within,
        total_organism_covariance=total,
        mls1_partition_residual=residual,
        transmission_term_estimated=False,
        price_equation_complete=False,
        major_transition_in_individuality=False,
    )
    _assert_ci_blocked(partition.to_dict(), ScientificClaimGate())
    return partition


@dataclass(frozen=True, slots=True)
class PriceEquationSeedRecord:
    """One seed: MLS vs organism-only Price snapshots. Bookkeeping, not CI."""

    seed: int
    mls: PriceEquationPartition
    organism_only: PriceEquationPartition

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "seed": self.seed,
            "mls": self.mls.to_dict(),
            "organism_only": self.organism_only.to_dict(),
            "collective_intelligence": False,
        }


@dataclass(frozen=True, slots=True)
class PriceEquationCovarianceCampaign:
    """Multi-seed Price snapshot campaign. Does not set ClaimGate flags."""

    seeds: tuple[int, ...]
    generations: int
    n_groups: int
    group_size: int
    seed_records: tuple[PriceEquationSeedRecord, ...]
    mean_mls_between_mls1: float
    mean_mls_within: float
    mean_organism_between_mls1: float
    mean_mls1_partition_residual: float
    mls1_identity_holds: bool
    price_equation_status: str = MEASURED_RUNTIME
    claim_gate_flags_auto_set: bool = False
    major_transition_in_individuality: bool = False
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    claim_ceiling: str = _CLAIM_CEILING
    schema_version: str = "price_equation_covariance_campaign_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.seeds) < 2:
            raise ConfigurationError("PriceEquationCovarianceCampaign requires seed_count >= 2.")
        if self.generations < 1:
            raise ConfigurationError("generations must be >= 1.")
        for name in (
            "mean_mls_between_mls1",
            "mean_mls_within",
            "mean_organism_between_mls1",
            "mean_mls1_partition_residual",
        ):
            object.__setattr__(self, name, require_finite_float(name, getattr(self, name)))
        if self.claim_gate_flags_auto_set:
            raise ConfigurationError("Phase J Price campaign must not auto-set ClaimGate flags.")
        if self.major_transition_in_individuality:
            raise ConfigurationError(
                "Price campaign must not set major_transition_in_individuality."
            )
        if self.claim_ceiling in _FORBIDDEN or self.claim_ceiling != _CLAIM_CEILING:
            raise ConfigurationError("Price campaign ceiling must stay runtime_observation.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("PriceEquationCovarianceCampaign digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "seeds": list(self.seeds),
            "generations": self.generations,
            "n_groups": self.n_groups,
            "group_size": self.group_size,
            "seed_records": [item.to_dict() for item in self.seed_records],
            "mean_mls_between_mls1": self.mean_mls_between_mls1,
            "mean_mls_within": self.mean_mls_within,
            "mean_organism_between_mls1": self.mean_organism_between_mls1,
            "mean_mls1_partition_residual": self.mean_mls1_partition_residual,
            "mls1_identity_holds": self.mls1_identity_holds,
            "price_equation_status": self.price_equation_status,
            "claim_gate_flags_auto_set": self.claim_gate_flags_auto_set,
            "major_transition_in_individuality": self.major_transition_in_individuality,
            "literature_checklist": [[key, text] for key, text in self.literature_checklist],
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "intelligence": False,
            "limitations": [
                "snapshot_not_full_price_equation_paper",
                "not_okasha_book_treatment",
                "major_transition_in_individuality_false",
                "claimgate_flags_not_auto_set",
            ],
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def run_price_equation_covariance_scaffold(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    generations: int | None = None,
    n_groups: int | None = None,
    group_size: int = DEFAULT_GROUP_SIZE,
    smoke: bool = False,
) -> PriceEquationCovarianceCampaign:
    """Last-generation Price partition under MLS vs organism-only selection."""

    seed_tuple = _resolve_seeds(
        seeds, seed_count, default_count=SMOKE_SEED_COUNT if smoke else RESEARCH_SEED_COUNT
    )
    gen_count = int(
        SMOKE_GENERATION_COUNT
        if generations is None and smoke
        else RESEARCH_GENERATION_COUNT
        if generations is None
        else generations
    )
    groups = _resolve_group_count(n_groups, smoke=smoke)
    records: list[PriceEquationSeedRecord] = []
    for seed in seed_tuple:
        _mls_prefs, mls_rows = evolve_two_task_population(
            seed=seed,
            generations=gen_count,
            n_groups=groups,
            group_size=group_size,
            mode="mls",
        )
        _org_prefs, org_rows = evolve_two_task_population(
            seed=seed,
            generations=gen_count,
            n_groups=groups,
            group_size=group_size,
            mode="organism_only",
        )
        records.append(
            PriceEquationSeedRecord(
                seed=seed,
                mls=price_partition_from_groups(mls_rows),
                organism_only=price_partition_from_groups(org_rows),
            )
        )
    residuals = [
        abs(item.mls.mls1_partition_residual) + abs(item.organism_only.mls1_partition_residual)
        for item in records
    ]
    campaign = PriceEquationCovarianceCampaign(
        seeds=seed_tuple,
        generations=gen_count,
        n_groups=groups,
        group_size=group_size,
        seed_records=tuple(records),
        mean_mls_between_mls1=_mean([item.mls.between_group_covariance_mls1 for item in records]),
        mean_mls_within=_mean([item.mls.within_group_covariance for item in records]),
        mean_organism_between_mls1=_mean(
            [item.organism_only.between_group_covariance_mls1 for item in records]
        ),
        mean_mls1_partition_residual=_mean([item.mls.mls1_partition_residual for item in records]),
        mls1_identity_holds=all(value <= PRICE_PARTITION_TOLERANCE for value in residuals),
        price_equation_status=MEASURED_RUNTIME,
        claim_gate_flags_auto_set=False,
        major_transition_in_individuality=False,
    )
    _assert_ci_blocked(campaign.to_dict(), ScientificClaimGate())
    return campaign


@dataclass(frozen=True, slots=True)
class CampaignReplaySpec:
    """Config identity for independent re-execution. Not an evidence flag."""

    kind: str
    seeds: tuple[int, ...]
    generations: int
    n_groups: int
    group_size: int
    smoke: bool
    schema_version: str = "campaign_replay_spec_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.kind not in KNOWN_REPLAY_KINDS:
            raise ConfigurationError(f"unknown campaign replay kind: {self.kind}")
        if len(self.seeds) < 2:
            raise ConfigurationError("CampaignReplaySpec requires at least two seeds.")
        if self.generations < 1 or self.n_groups < 1 or self.group_size < 2:
            raise ConfigurationError("CampaignReplaySpec generations/groups/size invalid.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("CampaignReplaySpec digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "seeds": list(self.seeds),
            "generations": self.generations,
            "n_groups": self.n_groups,
            "group_size": self.group_size,
            "smoke": self.smoke,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


@dataclass(frozen=True, slots=True)
class CampaignReplayCapture:
    """Observed campaign digest plus the spec needed to re-run it."""

    spec: CampaignReplaySpec
    observed_digest: str
    source_id: int = 0
    schema_version: str = "campaign_replay_capture_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        require_digest = is_real_evidence_digest(self.observed_digest)
        if not require_digest:
            raise ConfigurationError("CampaignReplayCapture.observed_digest must be a real digest.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("CampaignReplayCapture digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "spec": self.spec.to_dict(),
            "observed_digest": self.observed_digest,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest, "source_id": self.source_id}


def capture_campaign_replay(
    kind: str, campaign: object, spec: CampaignReplaySpec
) -> CampaignReplayCapture:
    """Bind a campaign's digest to the spec that produced it."""

    if spec.kind != kind:
        raise ConfigurationError("capture kind must match CampaignReplaySpec.kind.")
    return CampaignReplayCapture(
        spec=spec,
        observed_digest=_campaign_digest(campaign),
        source_id=id(campaign),
    )


def _run_from_spec(spec: CampaignReplaySpec) -> object:
    seeds = spec.seeds
    generations = spec.generations
    n_groups = spec.n_groups
    group_size = spec.group_size
    smoke = spec.smoke
    if spec.kind == HELD_OUT_KIND:
        return run_heldout_unfamiliar_partner_experiment(
            seeds=seeds,
            generations=generations,
            n_groups=n_groups,
            group_size=group_size,
            smoke=smoke,
        )
    if spec.kind == EVOLVED_DOL_KIND:
        return run_evolved_division_of_labor_experiment(
            seeds=seeds,
            generations=generations,
            n_groups=n_groups,
            group_size=group_size,
            smoke=smoke,
        )
    if spec.kind == MLS_KIND:
        return run_mls_evolutionary_outcome_experiment(
            seeds=seeds,
            generations=generations,
            n_groups=n_groups,
            group_size=group_size,
            smoke=smoke,
        )
    if spec.kind == PRICE_KIND:
        return run_price_equation_covariance_scaffold(
            seeds=seeds,
            generations=generations,
            n_groups=n_groups,
            group_size=group_size,
            smoke=smoke,
        )
    raise ConfigurationError(f"cannot re-execute unknown kind: {spec.kind}")


@dataclass(frozen=True, slots=True)
class DigestReplayVerification:
    """Honest captured-vs-replayed digest check. Never auto-passes."""

    captures: tuple[CampaignReplayCapture, ...]
    replay_digests: tuple[tuple[str, str], ...]
    matched: bool
    re_executed: bool
    issues: tuple[str, ...]
    schema_version: str = "digest_replay_verification_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if not self.captures:
            raise ConfigurationError("DigestReplayVerification requires at least one capture.")
        kinds = [item.spec.kind for item in self.captures]
        if len(kinds) != len(set(kinds)):
            raise ConfigurationError("DigestReplayVerification captures must have unique kinds.")
        computed_match, computed_issues = _compare_replay_digests(
            self.captures, self.replay_digests
        )
        object.__setattr__(self, "matched", computed_match)
        merged_issues = tuple(sorted(set(tuple(self.issues) + computed_issues)))
        object.__setattr__(self, "issues", merged_issues)
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("DigestReplayVerification digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def earns_replay_verification(self) -> bool:
        if not self.re_executed or not self.matched or self.issues:
            return False
        if not self.captures:
            return False
        for capture in self.captures:
            if not is_real_evidence_digest(capture.observed_digest):
                return False
        return all(is_real_evidence_digest(value) for _kind, value in self.replay_digests)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "captures": [{**item._payload(), "digest": item.digest} for item in self.captures],
            "replay_digests": [[kind, value] for kind, value in self.replay_digests],
            "matched": self.matched,
            "re_executed": self.re_executed,
            "issues": list(self.issues),
            "collective_intelligence": False,
            "note": "matched_only_when_independent_re_execution_digests_agree",
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def _compare_replay_digests(
    captures: Sequence[CampaignReplayCapture],
    replay_digests: Sequence[tuple[str, str]],
) -> tuple[bool, tuple[str, ...]]:
    observed = {item.spec.kind: item.observed_digest for item in captures}
    replayed = {kind: value for kind, value in replay_digests}
    issues: list[str] = []
    if set(observed) != set(replayed):
        issues.append("replay_kind_set_mismatch")
    for kind, value in observed.items():
        other = replayed.get(kind, "")
        if not other:
            issues.append(f"missing_replay_digest:{kind}")
        elif other != value:
            issues.append(f"digest_mismatch:{kind}")
    return (not issues), tuple(sorted(set(issues)))


def verify_digest_replay(
    captures: Sequence[CampaignReplayCapture],
    *,
    replay_campaigns: Mapping[str, object] | None = None,
    re_execute: bool = False,
) -> DigestReplayVerification:
    """Compare captured digests to an independent re-run. Never fake a pass."""

    capture_tuple = tuple(captures)
    if not capture_tuple:
        raise ConfigurationError("verify_digest_replay requires captures.")
    issues: list[str] = []
    replayed: list[tuple[str, str]] = []
    independently_executed = False
    if re_execute:
        independently_executed = True
        for capture in capture_tuple:
            replayed_campaign = _run_from_spec(capture.spec)
            replayed.append((capture.spec.kind, _campaign_digest(replayed_campaign)))
            if id(replayed_campaign) == capture.source_id:
                issues.append(f"replay_is_same_object:{capture.spec.kind}")
                independently_executed = False
    elif replay_campaigns is not None:
        independently_executed = True
        for capture in capture_tuple:
            campaign = replay_campaigns.get(capture.spec.kind)
            if campaign is None:
                issues.append(f"missing_replay_campaign:{capture.spec.kind}")
                independently_executed = False
                continue
            if id(campaign) == capture.source_id:
                issues.append(f"replay_is_same_object:{capture.spec.kind}")
                independently_executed = False
            replayed.append((capture.spec.kind, _campaign_digest(campaign)))
        extra = set(replay_campaigns) - {item.spec.kind for item in capture_tuple}
        if extra:
            issues.append("unexpected_replay_campaign_kinds")
    else:
        issues.append("no_replay_source_supplied")
    verification = DigestReplayVerification(
        captures=capture_tuple,
        replay_digests=tuple(replayed),
        matched=False,
        re_executed=independently_executed
        and not any(
            item.startswith("replay_is_same_object") or item.startswith("missing_replay")
            for item in issues
        )
        and bool(replayed),
        issues=tuple(issues),
    )
    _assert_ci_blocked(verification.to_dict(), ScientificClaimGate())
    return verification


def _pack_spec(
    kind: str,
    *,
    seeds: tuple[int, ...],
    generations: int,
    n_groups: int,
    group_size: int,
    smoke: bool,
) -> CampaignReplaySpec:
    return CampaignReplaySpec(
        kind=kind,
        seeds=seeds,
        generations=generations,
        n_groups=n_groups,
        group_size=group_size,
        smoke=smoke,
    )


@dataclass(frozen=True, slots=True)
class ReplayVerifiedCiCandidatePack:
    """Phase I evidence + honest replay object. Does not mutate ClaimGate."""

    heldout: HeldoutUnfamiliarPartnerCampaign
    evolved_dol: EvolvedDivisionOfLaborCampaign
    mls: MlsEvolutionaryOutcomeCampaign
    export_of_fitness: ExportOfFitnessObservation
    price: PriceEquationCovarianceCampaign | None
    replay: DigestReplayVerification
    earned_flags: tuple[tuple[str, bool], ...]
    candidate_allowed: bool
    candidate_missing_flags: tuple[str, ...]
    smoke: bool
    research_scale: bool
    claim_gate_flags_auto_set: bool = False
    claim_ceiling: str = "collective_intelligence_candidate"
    schema_version: str = "replay_verified_ci_candidate_pack_v1"
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_gate_flags_auto_set:
            raise ConfigurationError("ReplayVerifiedCiCandidatePack must not auto-set ClaimGate.")
        if self.export_of_fitness.major_transition_in_individuality:
            raise ConfigurationError("pack must not unlock a major transition.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("ReplayVerifiedCiCandidatePack digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def as_mapping(self) -> dict[str, bool]:
        return {name: value for name, value in self.earned_flags}

    def _payload(self) -> dict[str, JsonValue]:
        price_payload: JsonValue = None if self.price is None else self.price.to_dict()
        return {
            "schema_version": self.schema_version,
            "heldout": self.heldout.to_dict(),
            "evolved_dol": self.evolved_dol.to_dict(),
            "mls": self.mls.to_dict(),
            "export_of_fitness": self.export_of_fitness.to_dict(),
            "price": price_payload,
            "replay": self.replay.to_dict(),
            "earned_flags": [[name, value] for name, value in self.earned_flags],
            "candidate_allowed": self.candidate_allowed,
            "candidate_missing_flags": list(self.candidate_missing_flags),
            "smoke": self.smoke,
            "research_scale": self.research_scale,
            "claim_gate_flags_auto_set": self.claim_gate_flags_auto_set,
            "claim_ceiling": self.claim_ceiling,
            "collective_intelligence": False,
            "intelligence": False,
            "note": "candidate_allowed_only_with_full_earned_flags_including_honest_replay",
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}


def build_replay_verified_ci_candidate_pack(
    seeds: Sequence[int] | None = None,
    *,
    seed_count: int | None = None,
    generations: int | None = None,
    n_groups: int | None = None,
    group_size: int = DEFAULT_GROUP_SIZE,
    smoke: bool = False,
    re_execute_replay: bool = True,
    include_price_equation: bool = True,
) -> ReplayVerifiedCiCandidatePack:
    """Run Phase I research-scale campaigns, re-execute, earn flags honestly.

    Smoke never earns. ``collective_intelligence`` stays forbidden even when
    ``collective_intelligence_candidate`` becomes allowable under ClaimGate.
    """

    seed_tuple = _resolve_seeds(
        seeds, seed_count, default_count=SMOKE_SEED_COUNT if smoke else RESEARCH_SEED_COUNT
    )
    gen_count = int(
        SMOKE_GENERATION_COUNT
        if generations is None and smoke
        else RESEARCH_GENERATION_COUNT
        if generations is None
        else generations
    )
    groups = _resolve_group_count(n_groups, smoke=smoke)
    heldout = run_heldout_unfamiliar_partner_experiment(
        seeds=seed_tuple,
        generations=gen_count,
        n_groups=groups,
        group_size=group_size,
        smoke=smoke,
    )
    evolved_dol = run_evolved_division_of_labor_experiment(
        seeds=seed_tuple,
        generations=gen_count,
        n_groups=groups,
        group_size=group_size,
        smoke=smoke,
    )
    mls = run_mls_evolutionary_outcome_experiment(
        seeds=seed_tuple,
        generations=gen_count,
        n_groups=groups,
        group_size=group_size,
        smoke=smoke,
    )
    export_of_fitness = build_export_of_fitness_observation(mls)
    price: PriceEquationCovarianceCampaign | None = None
    if include_price_equation:
        price = run_price_equation_covariance_scaffold(
            seeds=seed_tuple,
            generations=gen_count,
            n_groups=groups,
            group_size=group_size,
            smoke=smoke,
        )
    captures = [
        capture_campaign_replay(
            HELD_OUT_KIND,
            heldout,
            _pack_spec(
                HELD_OUT_KIND,
                seeds=seed_tuple,
                generations=gen_count,
                n_groups=groups,
                group_size=group_size,
                smoke=smoke,
            ),
        ),
        capture_campaign_replay(
            EVOLVED_DOL_KIND,
            evolved_dol,
            _pack_spec(
                EVOLVED_DOL_KIND,
                seeds=seed_tuple,
                generations=gen_count,
                n_groups=groups,
                group_size=group_size,
                smoke=smoke,
            ),
        ),
        capture_campaign_replay(
            MLS_KIND,
            mls,
            _pack_spec(
                MLS_KIND,
                seeds=seed_tuple,
                generations=gen_count,
                n_groups=groups,
                group_size=group_size,
                smoke=smoke,
            ),
        ),
    ]
    if price is not None:
        captures.append(
            capture_campaign_replay(
                PRICE_KIND,
                price,
                _pack_spec(
                    PRICE_KIND,
                    seeds=seed_tuple,
                    generations=gen_count,
                    n_groups=groups,
                    group_size=group_size,
                    smoke=smoke,
                ),
            )
        )
    if re_execute_replay:
        replay = verify_digest_replay(captures, re_execute=True)
    else:
        replay = verify_digest_replay(captures, replay_campaigns=None, re_execute=False)
    earned = earn_collective_intelligence_candidate_flags(
        heldout=heldout,
        evolved_dol=evolved_dol,
        mls=mls,
        export_of_fitness=export_of_fitness,
        replay=replay,
        smoke=smoke,
    )
    mapping = earned.as_mapping()
    gate = ScientificClaimGate()
    candidate = gate.decide(ClaimRequest("collective_intelligence_candidate", mapping))
    blocked = gate.decide(ClaimRequest("collective_intelligence", mapping))
    if blocked.allowed:
        raise ConfigurationError("collective_intelligence must remain blocked.")
    intelligence = gate.decide(ClaimRequest("intelligence", mapping))
    if intelligence.allowed:
        raise ConfigurationError("intelligence must remain blocked.")
    for label in ("agi", "tokyo_type1_passed", "avida_replacement"):
        if gate.decide(ClaimRequest(label, mapping)).allowed:
            raise ConfigurationError(f"{label} must remain blocked.")
    checklist = collective_intelligence_candidate_checklist(mapping)
    pack = ReplayVerifiedCiCandidatePack(
        heldout=heldout,
        evolved_dol=evolved_dol,
        mls=mls,
        export_of_fitness=export_of_fitness,
        price=price,
        replay=replay,
        earned_flags=earned.flags,
        candidate_allowed=bool(candidate.allowed),
        candidate_missing_flags=checklist.missing_flags,
        smoke=smoke,
        research_scale=earned.research_scale and not smoke,
        claim_gate_flags_auto_set=False,
    )
    _assert_ci_blocked(pack.to_dict(), gate)
    return pack


def evaluate_phase_j_claim(payload: Mapping[str, JsonValue] | object) -> ClaimDecision:
    """Runtime observation only. Intelligence claims stay blocked."""

    return evaluate_phase_i_claim(payload)
