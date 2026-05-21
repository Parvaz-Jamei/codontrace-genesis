"""Deterministic control genome/baseline helpers for GENESIS runners."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from codontrace._types import JsonValue


def _digest(payload: dict[str, JsonValue]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class ControlGenome:
    genome_bits: str
    control_type: str
    expected_behavior_status: str
    mutation_enabled: bool = False
    reproduction_enabled: bool = False
    action_enabled: bool = True
    control_status: str = "metadata_only_not_behavioral_control"
    evidence_bearing: bool = False
    claim_allowed: bool = False
    action_filter_policy_digest: str | None = None

    @property
    def genome_digest(self) -> str:
        return _digest({"genome_bits": self.genome_bits, "control_type": self.control_type})

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "genome_bits": self.genome_bits,
            "genome_digest": self.genome_digest,
            "control_type": self.control_type,
            "expected_behavior_status": self.expected_behavior_status,
            "mutation_enabled": self.mutation_enabled,
            "reproduction_enabled": self.reproduction_enabled,
            "action_enabled": self.action_enabled,
            "control_status": self.control_status,
            "evidence_bearing": self.evidence_bearing,
            "claim_allowed": self.claim_allowed,
            "action_filter_policy_digest": self.action_filter_policy_digest,
        }


class NoOpBaselinePolicy:
    control_type = "no_op_baseline"

    def genome(self, *, codon_bits: str = "000000000") -> ControlGenome:
        status = "behavioral_wait_only" if self.control_type == "wait_only" else "metadata_only_not_behavioral_control"
        return ControlGenome(
            codon_bits,
            self.control_type,
            "wait_only_or_neutral",
            control_status=status,
            evidence_bearing=status.startswith("behavioral"),
            claim_allowed=status.startswith("behavioral"),
            action_filter_policy_digest=_digest({"control_type": self.control_type, "allowed_actions": ["WAIT"]})
            if status.startswith("behavioral")
            else None,
        )


class NeutralGenomeBaseline(NoOpBaselinePolicy):
    control_type = "neutral_genome"


class WaitOnlyBaseline(NoOpBaselinePolicy):
    control_type = "wait_only"


class RandomActionBaseline(NoOpBaselinePolicy):
    control_type = "random_action"

    def genome(self, *, codon_bits: str = "101010101") -> ControlGenome:
        return ControlGenome(
            codon_bits,
            self.control_type,
            "deterministic_seeded_random_proxy",
            control_status="metadata_only_not_behavioral_control",
            evidence_bearing=False,
            claim_allowed=False,
        )


class EnergyOnlyBaseline(NoOpBaselinePolicy):
    control_type = "energy_only"

    def genome(self, *, codon_bits: str = "000000000") -> ControlGenome:
        return ControlGenome(
            codon_bits,
            self.control_type,
            "metadata_only_energy_label_not_behavioral_filter",
            control_status="metadata_only_not_behavioral_control",
            evidence_bearing=False,
            claim_allowed=False,
        )


class RandomGenomeControl(RandomActionBaseline):
    control_type = "random_genome_control"


class FixedGenomeControl(NoOpBaselinePolicy):
    control_type = "fixed_genome_control"


class NeutralGenomeControl(NeutralGenomeBaseline):
    control_type = "neutral_genome_control"


class ShadowControl(NoOpBaselinePolicy):
    control_type = "shadow_control"


class ControlGenomeFactory:
    """Factory for standard controls; it never weakens or boosts test organisms."""

    def create(self, control_type: str, *, genome_bits: str | None = None) -> ControlGenome:
        mapping = {
            "random": RandomGenomeControl(),
            "fixed": FixedGenomeControl(),
            "neutral": NeutralGenomeControl(),
            "shadow": ShadowControl(),
            "wait_only": WaitOnlyBaseline(),
            "energy_only": EnergyOnlyBaseline(),
        }
        if control_type not in mapping:
            raise ValueError(f"Unknown control_type {control_type!r}.")
        if genome_bits is None:
            return mapping[control_type].genome()
        return mapping[control_type].genome(codon_bits=genome_bits)
