"""Domain-free life-loop runtime primitives (registry, attachment, coupling, contact, inherit, ablation, schedule lock)."""

from codontrace.life_loop.ablation_template import (
    ABLATION_FAIL_REASONS,
    ABLATION_MODES,
    HE02_AXIS_MAP,
    AblationApplyRecord,
    AblationAttemptCensus,
    AblationFailReason,
    AblationMode,
    AblationTemplate,
    apply_ablation,
    he02_axis_mode,
    mode_axes,
)
from codontrace.life_loop.attachment import (
    ATTACH_FAIL_REASONS,
    AttachFailReason,
    AttachmentBook,
    AttachmentSlot,
)
from codontrace.life_loop.contact import (
    CANDIDATE_MODES,
    CONTACT_FAIL_REASONS,
    TRANSFER_MODES,
    CandidateMode,
    ContactAttemptCensus,
    ContactFailReason,
    ContactTransferPolicy,
    MatchRule,
    TransferMode,
    apply_contact,
    select_contact_candidates,
)
from codontrace.life_loop.energy_coupling import (
    COUPLING_FAIL_REASONS,
    CouplingFailReason,
    EnergyCoupling,
    EnergyTransferLedgerEntry,
)
from codontrace.life_loop.inherit_attached import (
    INHERIT_FAIL_REASONS,
    INHERIT_MODES,
    InheritAttachedPolicy,
    InheritAttemptCensus,
    InheritFailReason,
    InheritMode,
    apply_birth_inherit,
)
from codontrace.life_loop.populations import (
    SCHEMA_VERSION,
    PopulationRecord,
    PopulationRegistry,
)
from codontrace.life_loop.hook_meters import (
    RELATED_TALLY_KEYS,
    HookMeter,
    HookMeterSnapshot,
    merge_fail_reason_histogram,
)
from codontrace.life_loop.phenotype import (
    PhenotypeMap,
    PhenotypeRecord,
)
from codontrace.life_loop.match_rules import (
    MATCH_FAIL_REASONS,
    MATCH_MODES,
    MatchFailReason,
    MatchMode,
    MatchOutcome,
    MatchRuleSpec,
    bind_match_rule,
    evaluate_match,
    jaccard_overlap,
    score_phenotypes,
    spec_for_mode,
)
from codontrace.life_loop.export_csv import (
    hook_meter_snapshot_to_rows,
    write_hook_meter_csv,
)

from codontrace.life_loop.schedule_lock import (
    LOCK_MODES,
    SCHEDULE_LOCK_FAIL_REASONS,
    LockMode,
    ScheduleLock,
    ScheduleLockApplyRecord,
    ScheduleLockAttemptCensus,
    ScheduleLockFailReason,
    ScheduleLockState,
    apply_replay_frame,
    apply_schedule_lock,
    resolve_member_state,
    resolve_target_members,
)


from codontrace.life_loop.topology_meters import (
    TopologyMeterSnapshot,
    betti_proxy,
    topology_continuum_structure,
)
from codontrace.life_loop.info_geometry import (
    InfoGeometryContrast,
    contrast_phenotype_maps,
    fisher_simplex_distance,
    js_divergence,
    phenotype_tag_frequencies,
)
from codontrace.life_loop.skyline_proxy import (
    SkylineSeries,
    SkylineWindow,
    skyline_ne_proxy,
)
from codontrace.life_loop.farm_orchestrator import (
    FarmApplyRecord,
    FarmPlan,
    apply_farm,
)
from codontrace.life_loop.persistent_entropy import (
    PersistentEntropySnapshot,
    persistent_entropy_proxy,
)
from codontrace.life_loop.mapper_cover import (
    MapperCoverSnapshot,
    mapper_cover_proxy,
)
from codontrace.life_loop.spectral_structure import (
    SpectralStructureSnapshot,
    spectral_laplacian_structure,
)
from codontrace.life_loop.transfer_entropy import (
    TransferEntropyResult,
    hook_meter_transfer_entropy,
)
from codontrace.life_loop.conformal_bands import (
    ConformalBandResult,
    conformal_risk_band,
)
from codontrace.life_loop.ess_invasion import (
    EssInvasionResult,
    InvasionScore,
    ess_invasion_indicator,
)
from codontrace.life_loop.sparse_recovery import (
    SparseCoefficient,
    SparseRecoveryResult,
    sparse_phenotype_recovery,
)

from codontrace.life_loop.allele_association import (
    AlleleAssociationResult,
    AlleleAssociationScore,
    allele_outcome_association,
)

__all__ = [
    "ABLATION_FAIL_REASONS",
    "ABLATION_MODES",
    "ATTACH_FAIL_REASONS",
    "AttachFailReason",
    "AttachmentBook",
    "AttachmentSlot",
    "CANDIDATE_MODES",
    "CONTACT_FAIL_REASONS",
    "COUPLING_FAIL_REASONS",
    "CandidateMode",
    "ContactAttemptCensus",
    "ContactFailReason",
    "ContactTransferPolicy",
    "CouplingFailReason",
    "EnergyCoupling",
    "EnergyTransferLedgerEntry",
    "HE02_AXIS_MAP",
    "INHERIT_FAIL_REASONS",
    "INHERIT_MODES",
    "InheritAttachedPolicy",
    "InheritAttemptCensus",
    "InheritFailReason",
    "InheritMode",
    "LOCK_MODES",
    "LockMode",
    "MatchRule",
    "SCHEMA_VERSION",
    "SCHEDULE_LOCK_FAIL_REASONS",
    "TRANSFER_MODES",
    "TransferMode",
    "AblationApplyRecord",
    "AblationAttemptCensus",
    "AblationFailReason",
    "AblationMode",
    "AblationTemplate",
    "PopulationRecord",
    "PopulationRegistry",
    "ScheduleLock",
    "ScheduleLockApplyRecord",
    "ScheduleLockAttemptCensus",
    "ScheduleLockFailReason",
    "ScheduleLockState",
    "apply_ablation",
    "apply_birth_inherit",
    "apply_contact",
    "apply_replay_frame",
    "apply_schedule_lock",
    "he02_axis_mode",
    "mode_axes",
    "resolve_member_state",
    "resolve_target_members",
    "select_contact_candidates",
    "RELATED_TALLY_KEYS",
    "HookMeter",
    "hook_meter_snapshot_to_rows",
    "write_hook_meter_csv",
    "HookMeterSnapshot",
    "merge_fail_reason_histogram",
    "PhenotypeMap",
    "PhenotypeRecord",
    "MATCH_FAIL_REASONS",
    "MATCH_MODES",
    "MatchFailReason",
    "MatchMode",
    "MatchOutcome",
    "MatchRuleSpec",
    "bind_match_rule",
    "evaluate_match",
    "jaccard_overlap",
    "score_phenotypes",
    "spec_for_mode",

    "TopologyMeterSnapshot",
    "betti_proxy",
    "topology_continuum_structure",
    "InfoGeometryContrast",
    "contrast_phenotype_maps",
    "fisher_simplex_distance",
    "js_divergence",
    "phenotype_tag_frequencies",
    "SkylineSeries",
    "SkylineWindow",
    "skyline_ne_proxy",
    "FarmApplyRecord",
    "FarmPlan",
    "apply_farm",
    "AlleleAssociationResult",
    "AlleleAssociationScore",
    "allele_outcome_association",

    "PersistentEntropySnapshot",
    "persistent_entropy_proxy",
    "MapperCoverSnapshot",
    "mapper_cover_proxy",
    "SpectralStructureSnapshot",
    "spectral_laplacian_structure",
    "TransferEntropyResult",
    "hook_meter_transfer_entropy",
    "ConformalBandResult",
    "conformal_risk_band",
    "EssInvasionResult",
    "InvasionScore",
    "ess_invasion_indicator",
    "SparseCoefficient",
    "SparseRecoveryResult",
    "sparse_phenotype_recovery",
]
