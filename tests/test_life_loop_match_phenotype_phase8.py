"""Phase 8: gene→phenotype→MatchRule (domain-free matching; thin HP wire)."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from codontrace.errors import ConfigurationError
from codontrace.genesis.host_parasite_world import (
    MATCH_RULE_IDS,
    HostParasiteProfile,
    HostParasiteWorld,
    _BAIC_PINS as _BAIC,
)
from codontrace.life_loop import (
    ContactTransferPolicy,
    HookMeter,
    MatchRuleSpec,
    PhenotypeMap,
    PhenotypeRecord,
    apply_contact,
    bind_match_rule,
    evaluate_match,
    jaccard_overlap,
    score_phenotypes,
    spec_for_mode,
)

REPO = Path(__file__).resolve().parents[1]
PHENOTYPE_SRC = REPO / "src" / "codontrace" / "life_loop" / "phenotype.py"
MATCH_SRC = REPO / "src" / "codontrace" / "life_loop" / "match_rules.py"
WORLD_SRC = REPO / "src" / "codontrace" / "genesis" / "host_parasite_world.py"
ENGINE_SRC = REPO / "src" / "codontrace" / "engine.py"

_BANNED_CONTIGUOUS = (
    "infection",
    "infect",
    "virulence",
    "parasite",
    "symbiont",
    "vaccine",
    "phage",
    "crispr",
    "claimgate",
)


def _sha(rel: str) -> str:
    return hashlib.sha256((REPO / rel).read_bytes()).hexdigest()


def test_phenotype_round_trip_and_digest() -> None:
    rec = PhenotypeRecord(member_id="m1", feature_tags=("b", "a"))
    assert rec.feature_tags == ("a", "b")
    again = PhenotypeRecord.from_dict(rec.to_dict())
    assert again.digest == rec.digest
    book = PhenotypeMap.from_tag_mapping(
        "map_a", {"m1": ("x", "y"), "m2": ("x",)}
    )
    book2 = PhenotypeMap.from_dict(book.to_dict())
    assert book2.digest == book.digest
    assert book2.get("m1") is not None


def test_phenotype_tampered_digest_and_banned_refuse() -> None:
    rec = PhenotypeRecord(member_id="m1", feature_tags=("t1",))
    payload = rec.to_dict()
    payload["digest"] = "0" * 64
    with pytest.raises(ConfigurationError, match="digest mismatch"):
        PhenotypeRecord.from_dict(payload)
    with pytest.raises(ConfigurationError, match="banned fragment"):
        PhenotypeRecord(member_id="parasite_1", feature_tags=("t1",))
    with pytest.raises(ConfigurationError, match="banned fragment"):
        PhenotypeRecord(member_id="ok", feature_tags=("infect_tag",))


def test_jaccard_monotonicity_and_empty() -> None:
    assert jaccard_overlap(frozenset(), frozenset()) == 0.0
    tags_a = frozenset({"1", "2", "3"})
    low = jaccard_overlap(tags_a, frozenset({"1"}))
    mid = jaccard_overlap(tags_a, frozenset({"1", "2"}))
    high = jaccard_overlap(tags_a, tags_a)
    assert low < mid < high
    assert high == pytest.approx(1.0)


def test_score_feature_overlap_threshold_and_scale() -> None:
    left = PhenotypeRecord(member_id="a", feature_tags=("t1", "t2"))
    right = PhenotypeRecord(member_id="b", feature_tags=("t1",))
    spec = MatchRuleSpec(
        spec_id="s1", mode="feature_overlap", threshold=0.6, score_scale=1.0
    )
    out = score_phenotypes(left, right, spec)
    assert out.raw_overlap == pytest.approx(0.5)
    assert out.passed is False
    assert out.reason == "below_threshold"
    assert out.score == 0.0

    spec_ok = MatchRuleSpec(
        spec_id="s2", mode="feature_overlap", threshold=0.2, score_scale=0.5
    )
    out_ok = score_phenotypes(left, right, spec_ok)
    assert out_ok.passed is True
    assert out_ok.score == pytest.approx(0.25)

    missing = score_phenotypes(None, right, spec_ok)
    assert missing.reason == "missing_phenotype"
    assert missing.passed is False


def test_allele_match_flag_and_equality() -> None:
    with pytest.raises(ConfigurationError, match="allele_mode_enabled"):
        MatchRuleSpec(spec_id="bad", mode="allele_match", allele_mode_enabled=False)

    left = PhenotypeRecord(member_id="a", feature_tags=("k1", "k2"))
    right = PhenotypeRecord(member_id="b", feature_tags=("k1", "k2"))
    other = PhenotypeRecord(member_id="c", feature_tags=("k1",))
    spec = MatchRuleSpec(
        spec_id="al", mode="allele_match", allele_mode_enabled=True
    )
    assert score_phenotypes(left, right, spec).passed is True
    mis = score_phenotypes(left, other, spec)
    assert mis.passed is False
    assert mis.reason == "allele_mismatch"


def test_bind_match_rule_gates_contact() -> None:
    book = PhenotypeMap.from_tag_mapping(
        "map_c", {"actor_a": ("t1", "t2"), "other_b": ("t1",)}
    )
    spec = MatchRuleSpec(
        spec_id="gate", mode="feature_overlap", threshold=0.9, score_scale=1.0
    )
    rule = bind_match_rule(spec, book)
    policy = ContactTransferPolicy(rule_id="r1", transfer_mode="none")
    _payloads, _book, event, reason, _census = apply_contact(
        policy,
        actor_id="actor_a",
        other_id="other_b",
        tick=1,
        member_ids=("actor_a", "other_b"),
        match_rule=rule,
    )
    assert reason == "match_failed"
    assert event is None

    spec2 = MatchRuleSpec(
        spec_id="gate2", mode="feature_overlap", threshold=0.1, score_scale=1.0
    )
    rule2 = bind_match_rule(spec2, book)
    _payloads, _book, event2, reason2, _census = apply_contact(
        policy,
        actor_id="actor_a",
        other_id="other_b",
        tick=2,
        member_ids=("actor_a", "other_b"),
        match_rule=rule2,
    )
    assert reason2 == "success"
    assert event2 is not None
    assert event2.score == pytest.approx(0.5)


def test_always_never_ignore_empty_map() -> None:
    empty = PhenotypeMap(map_id="empty")
    always = bind_match_rule(spec_for_mode("always"), empty)
    never = bind_match_rule(spec_for_mode("never"), empty)
    assert always("x", "y") == 1.0
    assert never("x", "y") == 0.0


def test_hook_meter_match_channels() -> None:
    meter = HookMeter(meter_id="meter_m")
    meter.record_match_outcome(passed=True, score=0.75)
    meter.record_match_outcome(passed=False)
    snap = meter.snapshot()
    assert snap.related_counts["match_pass"] == 1
    assert snap.related_counts["match_fail"] == 1
    assert snap.related_totals["match_score_sum"] == pytest.approx(0.75)


def test_host_parasite_world_feature_overlap_wire() -> None:
    profile = HostParasiteProfile(
        profile_id="hp_p8",
        seed=8,
        match_rule_id="feature_overlap",
        match_threshold=0.1,
        phenotype_tags={
            "a0": ("u1", "u2"),
            "a1": ("z",),
            "b0": ("u1",),
        },
        ablation_preset="none",
    )
    assert "feature_overlap" in MATCH_RULE_IDS
    world = HostParasiteWorld(profile=profile)
    summary = world.run(ticks=2)
    assert summary["red_queen_proved"] is False
    assert summary["raises_claim_ladder"] is False
    snap = world.meter.snapshot()
    assert snap.related_counts.get("match_pass", 0) >= 1
    assert snap.related_totals.get("match_score_sum", 0.0) > 0.0


def test_host_parasite_world_never_still_works() -> None:
    world = HostParasiteWorld(
        profile=HostParasiteProfile(
            profile_id="hp_never", seed=1, match_rule_id="never"
        )
    )
    world.tick()
    snap = world.meter.snapshot()
    assert snap.related_counts.get("match_fail", 0) >= 1
    assert snap.contact_fail_reasons.get("match_failed", 0) >= 1


def test_static_audit_new_modules_and_engine_untouched() -> None:
    for src in (PHENOTYPE_SRC, MATCH_SRC):
        text = src.read_text(encoding="utf-8").casefold()
        for token in _BANNED_CONTIGUOUS:
            assert token not in text, f"{src.name} contains {token}"
        tree = ast.parse(src.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "claimgate" not in alias.name.casefold()
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "claimgate" not in node.module.casefold()
                assert "host_parasite" not in node.module.casefold()
    world_text = WORLD_SRC.read_text(encoding="utf-8")
    assert "class Infection" not in world_text
    assert "Env.step" not in world_text
    assert "peer-as-novelty-yardstick" not in world_text.casefold()
    engine = ENGINE_SRC.read_text(encoding="utf-8")
    assert "MatchRuleSpec" not in engine
    assert "PhenotypeMap" not in engine
    for rel, expected in _BAIC:
        assert _sha(rel) == expected, f"BAIC pin drift {rel}"


def test_evaluate_match_via_map() -> None:
    book = PhenotypeMap.from_tag_mapping("m", {"a": ("1",), "b": ("1", "2")})
    spec = MatchRuleSpec(spec_id="e", mode="feature_overlap", threshold=0.0)
    out = evaluate_match(spec, book, "a", "b")
    assert out.passed is True
    assert out.score == pytest.approx(0.5)
