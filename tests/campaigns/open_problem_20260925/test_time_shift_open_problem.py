"""SF-style tests for open_problem_20260925 time-shift FRQ vs ERQ campaign."""

from __future__ import annotations

from pathlib import Path

from codontrace.contracts.banned import BANNED_DOMAIN_TOKENS
from codontrace.genesis.campaigns.open_problem_20260925_time_shift import (
    CLAIMGATE_REFUSES,
    DOIS,
    run_open_problem_campaign,
    write_campaign_results,
)
from codontrace.life_loop.time_shift_assay import (
    classify_shift_pattern,
    run_mechanism_archive,
)

REPO = Path(__file__).resolve().parents[3]
RESULTS = REPO / "outputs" / "campaigns" / "open_problem_20260925" / "results.json"
ASSAY_SRC = REPO / "src" / "codontrace" / "life_loop" / "time_shift_assay.py"


def test_dois_are_the_verified_seed_set() -> None:
    assert DOIS["primary"] == "10.1038/nature06291"
    assert DOIS["modes"] == "10.1098/rspb.2014.1382"
    assert DOIS["theory_review"] == "10.1111/jeb.13981"


def test_classifier_structural_labels() -> None:
    assert classify_shift_pattern(0.2, 0.9, 0.3) == "peak_contemp"
    assert classify_shift_pattern(0.2, 0.5, 0.8) == "mono_rise"
    assert classify_shift_pattern(0.5, 0.5, 0.5) == "flat"


def test_mechanism_arms_and_nulls() -> None:
    c = run_mechanism_archive(mechanism="match_linked_cycle", steps=48, seed=7, lag=4)
    e = run_mechanism_archive(mechanism="trait_escalation", steps=48, seed=7, lag=4)
    assert c["pattern"] == "peak_contemp"
    assert e["pattern"] == "mono_rise"
    for arm in ("content_null", "structure_null", "dual_null"):
        n = run_mechanism_archive(
            mechanism="match_linked_cycle", steps=48, seed=7, lag=4, ablation=arm
        )
        assert n["pattern"] == "flat"


def test_assay_source_has_no_banned_tokens() -> None:
    text = ASSAY_SRC.read_text(encoding="utf-8").casefold()
    for tok in BANNED_DOMAIN_TOKENS:
        assert tok.casefold() not in text


def test_campaign_pack_fields_and_honesty() -> None:
    pack = run_open_problem_campaign(
        seeds_main=(101, 202, 303, 404),
        seeds_live=(11, 22),
    )
    assert pack["red_queen_proved"] is False
    assert pack["arms_race_proved"] is False
    assert pack["engineering_green"] is True
    assert set(pack["claimgate_refuses"]) >= set(CLAIMGATE_REFUSES)
    by_id = {r["id"]: r for r in pack["records"]}
    ts1 = by_id["SF_TS1_time_shift_frq_erq_discrimination"]
    ts2 = by_id["SF_TS2_live_world_genome_archive_witness"]
    for key in (
        "doi",
        "literature_prediction",
        "why_unsolved",
        "success_criterion",
        "null_arms",
        "n_seeds",
        "hypothesis_supported",
        "honesty",
        "claim_ceiling",
        "result",
    ):
        assert key in ts1 and key in ts2
    assert ts1["engineering_green"] is True
    assert ts1["hypothesis_supported"] is True
    assert ts1["result"] == "PASS"
    assert ts1["red_queen_proved"] is False
    assert ts2["engineering_green"] is True
    assert ts2["hypothesis_supported"] is False
    assert ts2["claim_ceiling"] == "runtime_observation"


def test_write_results_json(tmp_path: Path) -> None:
    out = tmp_path / "results.json"
    pack = write_campaign_results(
        out, seeds_main=(101, 202, 303, 404), seeds_live=(11, 22)
    )
    assert out.is_file()
    assert pack["campaign_digest"].startswith("op_ts_campaign:")


def test_repo_results_artifact_present() -> None:
    # Written by campaign runner during delivery; skip if absent in thin checkouts.
    if not RESULTS.is_file():
        pack = write_campaign_results(RESULTS)
    else:
        import json

        pack = json.loads(RESULTS.read_text(encoding="utf-8"))
    assert pack["schema"] == "open_problem_20260925_time_shift_v1"
    assert pack["red_queen_proved"] is False
