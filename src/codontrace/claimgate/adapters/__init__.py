"""External evidence adapters. Skeletons do not claim full simulator support."""

from codontrace.claimgate.adapters.avida import bundle_from_avida_runs, parse_avida_dat
from codontrace.claimgate.adapters.biomedical import (
    BLOCKED_BIOMEDICAL_CLAIMS,
    BiomedicalStudy,
    CredibilityWorksheet,
    RiskBar,
    assess_risk_bar,
    attach_credibility_worksheet,
    audit_biomedical_study,
    audit_biomedical_study_file,
    biomedical_risk_bar_payload,
    bundle_from_biomedical_cou,
    bundle_from_device_model_cou,
    credibility_worksheet,
)
from codontrace.claimgate.adapters.codontrace import (
    bundle_from_hard_experiment_01,
    committed_results_v2_path,
    committed_results_v3_path,
)
from codontrace.claimgate.adapters.codontrace_he02 import (
    bundle_from_hard_experiment_02,
)
from codontrace.claimgate.adapters.codontrace_he02 import (
    committed_pilot_v1_path as committed_he02_pilot_v1_path,
)
from codontrace.claimgate.adapters.codontrace_he02 import (
    committed_results_v1_path as committed_he02_results_v1_path,
)
from codontrace.claimgate.adapters.codontrace_he03 import (
    bundle_from_hard_experiment_03,
)
from codontrace.claimgate.adapters.codontrace_he03 import (
    committed_pilot_v1_path as committed_he03_pilot_v1_path,
)
from codontrace.claimgate.adapters.codontrace_he03 import (
    committed_results_v1_path as committed_he03_results_v1_path,
)
from codontrace.claimgate.adapters.esp32_bridge import (
    MqttEsp32Transport,
    SensorReading,
    SerialEsp32Transport,
    SimEsp32Bridge,
    STRDisparityResult,
    TransportEsp32Bridge,
    compute_str_disparity,
    parse_sensor_payload,
    str_stop_criterion_met,
)
from codontrace.claimgate.adapters.he01_arm_roles import ARM_ROLES as HE01_ARM_ROLES
from codontrace.claimgate.adapters.he01_arm_roles import canonical_role as he01_canonical_role
from codontrace.claimgate.adapters.host_parasite import (
    BLOCKED_HOST_PARASITE_CLAIMS,
    DECLARED_INTERVENTION_KINDS,
    DeclaredIntervention,
    DeclaredInterventionMenu,
    DynamicsLabels,
    InterventionFalsificationResult,
    MultilevelTransitionWorksheet,
    assert_transition_claim_allowed,
    attach_declared_intervention_menu,
    attach_phase3_honesty,
    bundle_from_host_parasite_cou,
    declared_cou_risk_labels,
    declared_dynamics_labels,
    declared_intervention_menu,
    multilevel_transition_worksheet,
    run_intervention_falsification,
)
from codontrace.claimgate.adapters.host_parasite import (
    assert_claim_allowed as assert_host_parasite_claim_allowed,
)
from codontrace.claimgate.adapters.mabe2 import bundle_from_mabe2_csv, parse_mabe2_csv
from codontrace.claimgate.adapters.roles import ROLE_ALIASES, SCHEMA_ROLES, canonical_role

__all__ = [
    "attach_phase3_honesty",
    "assert_transition_claim_allowed",
    "BLOCKED_BIOMEDICAL_CLAIMS",
    "BLOCKED_HOST_PARASITE_CLAIMS",
    "DECLARED_INTERVENTION_KINDS",
    "DeclaredIntervention",
    "DeclaredInterventionMenu",
    "MultilevelTransitionWorksheet",
    "InterventionFalsificationResult",
    "DynamicsLabels",
    "BiomedicalStudy",
    "CredibilityWorksheet",
    "RiskBar",
    "assess_risk_bar",
    "attach_credibility_worksheet",
    "audit_biomedical_study",
    "audit_biomedical_study_file",
    "biomedical_risk_bar_payload",
    "credibility_worksheet",
    "MqttEsp32Transport",
    "SensorReading",
    "SerialEsp32Transport",
    "SimEsp32Bridge",
    "STRDisparityResult",
    "TransportEsp32Bridge",
    "HE01_ARM_ROLES",
    "ROLE_ALIASES",
    "SCHEMA_ROLES",
    "bundle_from_avida_runs",
    "assert_host_parasite_claim_allowed",
    "attach_declared_intervention_menu",
    "bundle_from_biomedical_cou",
    "bundle_from_host_parasite_cou",
    "declared_cou_risk_labels",
    "declared_dynamics_labels",
    "declared_intervention_menu",
    "multilevel_transition_worksheet",
    "run_intervention_falsification",
    "bundle_from_device_model_cou",
    "bundle_from_hard_experiment_01",
    "bundle_from_hard_experiment_02",
    "bundle_from_hard_experiment_03",
    "canonical_role",
    "committed_he02_pilot_v1_path",
    "committed_he02_results_v1_path",
    "committed_he03_pilot_v1_path",
    "committed_he03_results_v1_path",
    "bundle_from_mabe2_csv",
    "committed_results_v2_path",
    "committed_results_v3_path",
    "compute_str_disparity",
    "he01_canonical_role",
    "parse_avida_dat",
    "parse_mabe2_csv",
    "parse_sensor_payload",
    "str_stop_criterion_met",
]
