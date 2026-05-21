"""ODD reporting for GENESIS agent-based experiments."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass

from codontrace._types import JsonValue
from codontrace.genesis.engine import GenesisEngineConfig, GenesisExperimentSpec

MANDATORY_ODD_SECTIONS = (
    "Purpose",
    "Entities",
    "State variables",
    "Scales",
    "Process overview and scheduling",
    "Design concepts",
    "Initialization",
    "Input data",
    "Submodels",
    "Assumptions",
    "Limitations",
    "Claim level",
)


@dataclass(frozen=True, slots=True)
class ODDSection:
    title: str
    content: tuple[str, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        return {"title": self.title, "content": list(self.content)}


@dataclass(frozen=True, slots=True)
class GenesisODDReport:
    report_id: str
    spec_digest: str
    claim_level: str
    sections: tuple[ODDSection, ...]

    def section_titles(self) -> tuple[str, ...]:
        return tuple(section.title for section in self.sections)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "report_id": self.report_id,
            "spec_digest": self.spec_digest,
            "claim_level": self.claim_level,
            "sections": [section.to_dict() for section in self.sections],
        }

    def digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class ODDExporter:
    """Explicit ODD exporter; no file I/O."""

    heading_prefix: str = "##"

    def export_markdown(self, report: GenesisODDReport) -> str:
        lines = [
            f"# GENESIS ODD Report: {report.report_id}",
            "",
            f"Spec digest: `{report.spec_digest}`",
            "",
        ]
        for section in report.sections:
            lines.append(f"{self.heading_prefix} {section.title}")
            lines.extend(f"- {item}" for item in section.content)
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def build_odd_report(
    spec: GenesisExperimentSpec, engine_config: GenesisEngineConfig | None = None
) -> GenesisODDReport:
    config = engine_config or spec.engine_config
    sections = (
        ODDSection(
            "Purpose", ("Reproducible research-alpha artificial-life/evolution experiment",)
        ),
        ODDSection(
            "Entities",
            (
                "GenesisOrganism",
                "PopulationState",
                "World2D / ElementGrid bridge",
                "Capsule/Nexus",
                "CausalGraph",
            ),
        ),
        ODDSection(
            "State variables",
            (
                "genome",
                "ATP_runtime",
                "ATP_learning",
                "memory",
                "causal_graph_digest",
                "position",
                "fitness",
                "behavior_descriptor",
            ),
        ),
        ODDSection(
            "Scales",
            (
                f"world={spec.world_width}x{spec.world_height}",
                f"ticks={spec.tick_count}",
                f"population_max={spec.population_max}",
            ),
        ),
        ODDSection(
            "Process overview and scheduling",
            (
                "ribosome translation",
                "organism tick",
                "population tick",
                "reproduction",
                "mutation",
                "selection",
                "memory/causal update",
                "capsule emission/adoption",
                "QD update",
            ),
        ),
        ODDSection(
            "Design concepts",
            (
                "determinism",
                "local interaction",
                "quality diversity",
                "bounded causal evidence",
                "claim gating",
            ),
        ),
        ODDSection(
            "Initialization", (f"seed={spec.seed}", f"genome_count={len(spec.genome_bits)}")
        ),
        ODDSection("Input data", ("No hidden external provider input in the simulation hot loop",)),
        ODDSection(
            "Submodels",
            (
                "Ribosome",
                "World2D",
                "ElementGrid bridge",
                "CausalGraph scaffold",
                "Capsule/Stigmergy scaffold",
                "Selection/QD policies",
            ),
        ),
        ODDSection(
            "Assumptions",
            (
                "Research-alpha contracts",
                "Provider-neutral external review",
                "Deterministic artifact digests",
            ),
        ),
        ODDSection(
            "Limitations",
            (
                "Not a proof of artificial life",
                "Not full open-ended evolution",
                "Not true causal discovery",
                "ElementGrid source-of-truth is experimental",
            ),
        ),
        ODDSection("Claim level", (config.claim_level,)),
    )
    return GenesisODDReport(
        report_id=f"odd:{spec.digest()[:16]}",
        spec_digest=spec.digest(),
        claim_level=config.claim_level,
        sections=sections,
    )


def _digest(payload: Mapping[str, JsonValue]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
