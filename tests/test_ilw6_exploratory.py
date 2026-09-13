"""ILW-6 exploratory phylogeny / MODES-style probes (promotion-free)."""

from __future__ import annotations

import pytest

from codontrace.genesis.ilw import CLAIM_CEILING, SCIENTIFIC_NAME, IlwChainRuntime
from codontrace.genesis.ilw.exploratory import (
    ILW6_FORBIDDEN_PROMOTIONS,
    ILW6_SCHEMA,
    ILW6_STATUS,
    Ilw6ExploratoryError,
    build_capsule_genealogy,
    build_organism_phylogeny,
    join_organism_capsule_phylogenies,
    learnability_probe,
    modes_style_novelty_probe,
    run_ilw6_exploratory,
    run_ilw6_exploratory_smoke,
)


def _finished_runtime(run_id: str = "ilw6-test", seed: int = 11) -> IlwChainRuntime:
    rt = IlwChainRuntime.s0(run_id=run_id, seed=seed)
    rt.bootstrap(2)
    rt.run()
    return rt


def test_organism_phylogeny_and_capsule_genealogy_build():
    rt = _finished_runtime("ilw6-trees")
    org = build_organism_phylogeny(rt)
    cap = build_capsule_genealogy(rt)
    assert len(org) == len(rt.lineage_records)
    assert len(cap) == len(rt.capsule_genealogy)
    assert all(n.organism_id for n in org)
    assert all(n.lineage_id for n in org)
    assert all(n.capsule_id for n in cap)
    # Founders have null parent; births may have parents.
    founders = [n for n in org if n.parent_id is None]
    assert len(founders) >= 1


def test_join_organism_capsule_trees_share_keys():
    rt = _finished_runtime("ilw6-join")
    org = build_organism_phylogeny(rt)
    cap = build_capsule_genealogy(rt)
    rows = join_organism_capsule_phylogenies(org, cap)
    assert len(rows) >= 1
    # At least one row links both sides when capsules exist.
    if cap:
        linked = [r for r in rows if r.organism_id and r.capsule_id]
        assert linked, "expected joinable organism↔capsule rows"
        for row in linked:
            assert row.lineage_id
            assert "|" in row.join_key
            assert row.genome_digest
            assert row.payload_digest


def test_modes_style_and_learnability_are_exploratory():
    rt = _finished_runtime("ilw6-probes")
    org = build_organism_phylogeny(rt)
    points = modes_style_novelty_probe(org, persistence_window_generations=0)
    # window=0 always emits a point per observed generation
    gens = {n.generation for n in org}
    assert len(points) == len(gens)
    learn = learnability_probe(rt)
    assert learn.exploratory_only is True
    assert learn.mesoudi_cce_claim is False
    assert learn.mesoudi_cce_criteria_passed == ()
    assert learn.learnability_ratio >= 0.0


def test_export_digest_stable_and_promotions_empty():
    report = run_ilw6_exploratory_smoke(run_id="ilw6-export", seed=11)
    payload = report.export()
    assert payload["schema_version"] == ILW6_SCHEMA
    assert payload["status"] == ILW6_STATUS
    assert payload["exploratory_only"] is True
    assert payload["claim_ceiling"] == CLAIM_CEILING == "runtime_observation"
    assert payload["scientific_name"] == SCIENTIFIC_NAME
    assert payload["claim_promotions"] == []
    assert payload["ladder_promotion"] is None
    assert payload["scientific_claim_emitted"] is False
    assert payload["cce_claimed"] is False
    assert payload["intelligence_claimed"] is False
    assert payload["export_digest"].startswith("ilw6_exploratory:")
    # Re-run identical seed → same export digest.
    report_b = run_ilw6_exploratory_smoke(run_id="ilw6-export", seed=11)
    assert report.digest() == report_b.digest()
    assert report_b.export()["export_digest"] == payload["export_digest"]
    # Forbidden promotion labels listed but not asserted as claims.
    assert set(payload["forbidden_promotions"]) >= ILW6_FORBIDDEN_PROMOTIONS
    assert "exploratory_only" in " ".join(payload["limitations"]) or any(
        "exploratory" in lim for lim in payload["limitations"]
    )


def test_run_ilw6_from_finished_runtime_matches_smoke_shape():
    rt = _finished_runtime("ilw6-rt")
    report = run_ilw6_exploratory(rt, persistence_window_generations=1)
    payload = report.export()
    assert payload["organism_node_count"] == len(rt.lineage_records)
    assert payload["capsule_node_count"] == len(rt.capsule_genealogy)
    assert payload["join_row_count"] == len(report.join_rows)
    assert isinstance(payload["modes_style_points"], list)
    assert payload["learnability_probe"]["mesoudi_cce_claim"] is False


def test_export_rejects_tampered_promotions():
    report = run_ilw6_exploratory_smoke(run_id="ilw6-tamper", seed=11)
    # Construct a sibling report with promotions would fail at export — mutate dict path.
    payload = report.to_dict()
    payload["claim_promotions"] = ["intelligence"]
    # Direct export path on a forged mapping is guarded by Ilw6ExploratoryReport.export;
    # forging via replace on frozen dataclass is not allowed — check Error API instead.
    from dataclasses import replace

    bad = replace(report, claim_promotions=("intelligence",))
    with pytest.raises(Ilw6ExploratoryError):
        bad.export()
