"""P5 accept: heritable outcross locus + mating-effort ATP. Not Morran."""

from __future__ import annotations

from pathlib import Path

from codontrace.errors import ConfigurationError
from codontrace.genesis.birth import SexualRecombinationConfig
from codontrace.genesis.closed_loop_p3 import replay_bit_identical as p3_replay
from codontrace.genesis.closed_loop_p5 import ClosedLoopP5Session, replay_bit_identical
from codontrace.genesis.host_parasite_life_plugin import (
    OUTCROSS_BIT_START,
    OUTCROSS_BIT_WIDTH,
    OUTCROSS_OUT_BITS,
    OUTCROSS_SELFING_BITS,
    P5_SCOPE,
    ClosedLoopHPLifeConfig,
    decode_kappa,
    decode_outcross,
    outcross_runtime_cost,
    outcross_mates_compatible,
    resolve_copy_self_mode,
)
from codontrace.genesis.population import ReproductionConfig
from codontrace.genesis.runtime_profiles import LIFE_LOOP_EATER_GENOME

_REPO = Path(__file__).resolve().parents[2]


def _quiet_outcross() -> str:
    return LIFE_LOOP_EATER_GENOME + "100000" + OUTCROSS_OUT_BITS


def test_window_does_not_move_kappa() -> None:
    bits = _quiet_outcross()
    assert bits[:9] == "101111000"
    assert bits[9:15] == "100000"
    assert bits[15:18] == "001"
    assert len(bits) % 3 == 0
    assert decode_outcross(bits) is True
    assert decode_outcross(bits[:15] + "010") is True
    assert decode_outcross(bits[:15] + OUTCROSS_SELFING_BITS) is False
    on = ClosedLoopHPLifeConfig(enabled=True, outcross_enabled=True)
    assert resolve_copy_self_mode(bits, on) == "chamber"
    assert resolve_copy_self_mode(bits[:15] + "000", on) == "asexual"
    assert resolve_copy_self_mode(bits, ClosedLoopHPLifeConfig()) == "default"
    assert decode_outcross(bits, ablate=True) is False
    # 100000 is near zero, not +1. The high allele is a different string.
    assert abs(decode_kappa(bits) - (2.0 * (32 / 63) - 1.0)) < 1e-12
    assert decode_kappa(LIFE_LOOP_EATER_GENOME + "111111" + "001") == 1.0


def test_partial_codon_cannot_be_a_locus() -> None:
    """A 1-bit tail is not a gene. SemanticGenome refuses it, so the locus is one codon."""

    from codontrace.genome import SemanticGenome

    try:
        SemanticGenome.from_compact(_quiet_outcross() + "1")
    except ValueError as exc:
        assert "multiple of" in str(exc)
    else:
        raise AssertionError("partial codon was accepted")


def test_outcross_pays_and_recombines() -> None:
    session = ClosedLoopP5Session.boot(seed=11, outcross_bits=OUTCROSS_OUT_BITS)
    summary = session.run_ticks(1)
    assert summary["red_queen_proved"] is False
    assert summary["morran_ready"] is False
    assert summary["claim_ceiling"] == "candidate_evidence"
    assert summary["p5_scope"] == P5_SCOPE
    assert summary["two_fold_cost_sex"] is False
    assert summary["cost_name"] == "mating_effort_atp"
    assert summary["outcross_debit_events"] >= 1
    assert summary["births"] >= 2
    assert summary["recombination_births"] + summary["asexual_births"] == summary["births"]
    differed = sum(
        1
        for rec in session.runner.population.lineage
        if rec.recombination_window_differed
    )
    assert summary["recombination_births"] == differed
    assert summary["hp_world_tick_calls"] == 0
    assert summary["two_fold_cost_sex"] is session.runner.configs.sexual_recombination.two_fold_cost_sex
    assert session.runner.configs.runtime_resource_policy.respawn_enabled is False


def test_locus_is_inherited_not_a_side_bag() -> None:
    from codontrace.genome import SemanticGenome

    session = ClosedLoopP5Session.boot(seed=11, n_primary=2, n_secondary=0)
    second = next(o for o in session.runner.population.organisms if o.id == "org_a1")
    second.genome = SemanticGenome.from_compact(second.genome.to_compact()[:15] + "010")
    session.run_ticks(1)
    children = [o for o in session.runner.population.organisms if o.id not in {"org_a0", "org_a1"}]
    assert children
    assert session.recombination_births >= 1
    assert session.outcross_debit_events >= 1
    parents = {
        o.genome.to_compact()
        for o in session.runner.population.organisms
        if o.id in {"org_a0", "org_a1"}
    }
    mosaics = 0
    for child in children:
        bits = child.genome.to_compact()
        assert bits[15:18] in {"001", "010"}
        assert len(bits) % 3 == 0
        if bits not in parents:
            mosaics += 1
    assert mosaics >= 1


def test_ablation_forces_selfing_and_zero_sex_cost() -> None:
    session = ClosedLoopP5Session.boot(seed=11, outcross_ablate=True)
    summary = session.run_ticks(1)
    assert summary["outcross_debit_events"] == 0
    assert summary["recombination_births"] == 0
    assert summary["asexual_births"] >= 1
    assert summary["red_queen_proved"] is False
    assert summary["morran_ready"] is False
    assert summary["claim_ceiling"] == "candidate_evidence"


def test_selfing_allele_does_not_pay() -> None:
    cfg = ClosedLoopHPLifeConfig(enabled=True, outcross_enabled=True)
    assert outcross_runtime_cost(LIFE_LOOP_EATER_GENOME + "100000" + "000", cfg) == 0.0
    session = ClosedLoopP5Session.boot(seed=11, outcross_bits=OUTCROSS_SELFING_BITS)
    summary = session.run_ticks(1)
    assert summary["outcross_debit_events"] == 0
    assert summary["recombination_births"] == 0
    assert summary["asexual_births"] >= 1
    assert summary["red_queen_proved"] is False
    assert summary["morran_ready"] is False
    assert summary["claim_ceiling"] == "candidate_evidence"


def test_flipping_the_same_codon_leaves_the_chamber() -> None:
    from codontrace.genome import SemanticGenome

    session = ClosedLoopP5Session.boot(seed=11, n_primary=2, n_secondary=0)
    for org in session.runner.population.organisms:
        org.genome = SemanticGenome.from_compact(org.genome.to_compact()[:15] + "000")
    summary = session.run_ticks(1)
    assert summary["outcross_debit_events"] == 0
    assert summary["recombination_births"] == 0
    assert summary["asexual_births"] >= 1


def test_refused_entry_does_not_keep_the_fee() -> None:
    session = ClosedLoopP5Session.boot(
        seed=11, n_primary=2, n_secondary=0, max_population=2
    )
    summary = session.run_ticks(1)
    assert summary["births"] == 0
    assert summary["outcross_debit_events"] == 0


def test_cross_role_does_not_pair() -> None:
    session = ClosedLoopP5Session.boot(
        seed=11, n_primary=1, n_secondary=1, outcross_bits=OUTCROSS_OUT_BITS
    )
    summary = session.run_ticks(1)
    assert summary["outcross_debit_events"] >= 1
    assert summary["recombination_births"] == 0


def test_schedule_does_not_depend_on_batch_size() -> None:
    stepped = ClosedLoopP5Session.boot(seed=11)
    stepped.run_ticks(1)
    stepped.run_ticks(1)
    batched = ClosedLoopP5Session.boot(seed=11)
    batched.run_ticks(2)
    assert stepped.snapshot_digest() == batched.snapshot_digest()


def test_copy_self_codon_is_rejected_and_unmapped_roles_do_not_pair() -> None:
    try:
        ClosedLoopP5Session.boot(outcross_bits="111")
    except ConfigurationError as exc:
        assert "COPY_SELF" in str(exc)
    else:
        raise AssertionError("111 was accepted as an outcross allele")
    cfg = ClosedLoopHPLifeConfig(
        enabled=True,
        outcross_enabled=True,
        outcross_same_role_only=True,
        role_by_id=(("org_a0", "primary"),),
    )
    assert outcross_mates_compatible("org_a0", "stranger", cfg) is False


def test_negative_cost_and_disabled_roundtrip() -> None:
    try:
        ClosedLoopHPLifeConfig(outcross_runtime_atp=-3)
    except ConfigurationError as exc:
        assert "outcross_runtime_atp" in str(exc)
    else:
        raise AssertionError("negative mating cost was accepted")
    original = ClosedLoopHPLifeConfig(
        outcross_enabled=False,
        outcross_ablate=True,
        outcross_runtime_atp=2.5,
        outcross_same_role_only=False,
        outcross_bit_start=18,
    )
    restored = ClosedLoopHPLifeConfig.from_dict(original.to_dict())
    assert restored.outcross_enabled is False
    assert restored.outcross_ablate is True
    assert restored.outcross_runtime_atp == 2.5
    assert restored.outcross_same_role_only is False
    assert restored.outcross_bit_start == 18
    assert "outcross_enabled" not in ClosedLoopHPLifeConfig().to_dict()


def test_replay_and_defaults_and_engine_boundary() -> None:
    left, right = replay_bit_identical(seed=11, ticks=1)
    assert left == right
    p3_left, p3_right = p3_replay(seed=11, ticks=1)
    assert p3_left == p3_right
    assert ReproductionConfig().is_sexual is False
    assert ClosedLoopHPLifeConfig().outcross_enabled is False
    sexual = SexualRecombinationConfig()
    assert sexual.enabled is False
    assert sexual.two_fold_cost_sex is False
    assert sexual.diploid_meiosis is False
    engine = (_REPO / "src" / "codontrace" / "engine.py").read_text(encoding="utf-8").lower()
    for token in ("outcross", "infection", "parasite", "red_queen", "hostparasiteworld"):
        assert token not in engine
    assert OUTCROSS_BIT_START == 15
    assert OUTCROSS_BIT_WIDTH == 3
    source = (_REPO / "src" / "codontrace" / "genesis" / "closed_loop_p5.py").read_text(
        encoding="utf-8"
    )
    assert "HostParasiteWorld" not in source
    from codontrace.genesis.closed_loop_p3 import (
        _FOUNDER_PRIMARY,
        _FOUNDER_SECONDARY_HIGH,
    )

    assert _FOUNDER_PRIMARY[0] == LIFE_LOOP_EATER_GENOME + "111111"
    assert _FOUNDER_PRIMARY[1] == "111101000111111"
    assert _FOUNDER_SECONDARY_HIGH[0] == LIFE_LOOP_EATER_GENOME + "111111"
    assert len(_FOUNDER_PRIMARY[0]) == 15
    from dataclasses import replace

    session = ClosedLoopP5Session.boot(seed=1)
    session.runner.configs = replace(
        session.runner.configs,
        sexual_recombination=replace(
            session.runner.configs.sexual_recombination, two_fold_cost_sex=True
        ),
    )
    assert session.summary()["two_fold_cost_sex"] is True
