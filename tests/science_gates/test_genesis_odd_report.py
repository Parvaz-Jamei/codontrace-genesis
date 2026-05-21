from codontrace.genesis import GenesisEngineConfig, GenesisExperimentSpec
from codontrace.genesis.odd import MANDATORY_ODD_SECTIONS, ODDExporter, build_odd_report


def test_odd_report_has_mandatory_sections_and_digest_changes_with_spec():
    spec = GenesisExperimentSpec(seed=1, tick_count=2)
    report = build_odd_report(spec, GenesisEngineConfig(claim_level="custom_claim"))
    titles = set(report.section_titles())

    assert set(MANDATORY_ODD_SECTIONS).issubset(titles)
    assert report.claim_level == "custom_claim"
    assert (
        "Not a proof of artificial life"
        in next(section for section in report.sections if section.title == "Limitations").content
    )

    changed = build_odd_report(GenesisExperimentSpec(seed=2, tick_count=2))
    assert report.digest() != changed.digest()
    assert "GENESIS ODD Report" in ODDExporter().export_markdown(report)
