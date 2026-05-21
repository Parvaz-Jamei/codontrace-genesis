from codontrace.genesis import ActionPluginSpec, PluginManifest, PluginValidationResult, canonical_digest
from codontrace.genesis.phase_b_scientific_maturity import PluginValidationResult as PhaseBPluginValidationResult


def D(name: str) -> str:
    return canonical_digest({"plugin": name})


def test_valid_plugin_spec_is_digest_backed_public_api():
    plugin = ActionPluginSpec("act", "1.0", ("MOVE",))
    assert plugin.extension_point == "action_primitive"
    assert plugin.digest() == ActionPluginSpec("act", "1.0", ("MOVE",)).digest()


def test_disabled_plugin_reports_status_not_missing_output():
    manifest = PluginManifest("act", "action_primitive", "1.0", "", enabled=False)
    assert manifest.status == "disabled_by_config"
    assert manifest.to_dict()["config_digest"] == "disabled_by_config"


def test_plugin_validation_rejects_missing_or_nondeterministic_config_digest():
    invalid = PhaseBPluginValidationResult("p", "action_plugin", "not_run:config", validation_passed=True)
    assert invalid.status == "rejected"
    assert not invalid.validation_passed
    valid = PhaseBPluginValidationResult("p", "action_plugin", D("config"), validation_passed=True)
    assert valid.status == "measured"


def test_plugin_validation_report_keeps_digest_surface_public():
    report = PluginValidationResult(D("plugin"), True, ("ok",))
    assert report.passed
    assert report.digest()
