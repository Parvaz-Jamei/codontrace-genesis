"""External evidence adapters. Skeletons do not claim full simulator support."""

from codontrace.claimgate.adapters.avida import bundle_from_avida_runs, parse_avida_dat
from codontrace.claimgate.adapters.biomedical import (
    BLOCKED_BIOMEDICAL_CLAIMS,
    bundle_from_biomedical_cou,
)
from codontrace.claimgate.adapters.codontrace_he02 import (
    bundle_from_hard_experiment_02,
    committed_pilot_v1_path as committed_he02_pilot_v1_path,
    committed_results_v1_path as committed_he02_results_v1_path,
)
from codontrace.claimgate.adapters.codontrace_he03 import (
    bundle_from_hard_experiment_03,
    committed_pilot_v1_path as committed_he03_pilot_v1_path,
    committed_results_v1_path as committed_he03_results_v1_path,
)
from codontrace.claimgate.adapters.codontrace import (
    bundle_from_hard_experiment_01,
    committed_results_v2_path,
    committed_results_v3_path,
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
from codontrace.claimgate.adapters.mabe2 import bundle_from_mabe2_csv, parse_mabe2_csv

__all__ = [
    "BLOCKED_BIOMEDICAL_CLAIMS",
    "MqttEsp32Transport",
    "SensorReading",
    "SerialEsp32Transport",
    "SimEsp32Bridge",
    "STRDisparityResult",
    "TransportEsp32Bridge",
    "bundle_from_avida_runs",
    "bundle_from_biomedical_cou",
    "bundle_from_hard_experiment_01",
    "bundle_from_hard_experiment_02",
    "bundle_from_hard_experiment_03",
    "committed_he02_pilot_v1_path",
    "committed_he02_results_v1_path",
    "committed_he03_pilot_v1_path",
    "committed_he03_results_v1_path",
    "bundle_from_mabe2_csv",
    "committed_results_v2_path",
    "committed_results_v3_path",
    "compute_str_disparity",
    "parse_avida_dat",
    "parse_mabe2_csv",
    "parse_sensor_payload",
    "str_stop_criterion_met",
]
