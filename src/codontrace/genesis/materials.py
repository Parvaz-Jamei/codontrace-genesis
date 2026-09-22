"""CodonTrace Genesis Phase G real-materials / chemistry-effect substrate.

Opt-in named materials with organism-facing effect coefficients (energy yield,
toxicity, viscosity/diffusion, permeability, signaling potency, scarcity) plus
a small stoichiometric reaction subset, chemostat-named pools, and
diffusion/decay hooks. Disabled by default so Phase A–E presets and pinned
digests stay stable.

This is **not** an Earth chemistry simulator, KEGG/BiGG GEM solver, or
molecular-dynamics engine. ``MaterialSpec.external_ontology_id`` is a schema
hook for a later ChEBI/KEGG/BiGG table bind. Effect coefficients are
software knobs, not proved wet-lab equivalents.

Literature grounding (software capability / runtime observation only):

- Avida resource/reaction/merit metabolism (Ofria & Wilke 2004; Avida-ED;
  BMC Evol Biol 2021 metabolic signaling; nutrient→intracellular profiles
  ASMI 2022). Phase C already supplies chemostat inflow/outflow; this module
  extends those pools to *named* materials with effect coefficients.
- Chemostat: Novick & Szilard 1950; Avida ``RESOURCE`` unused-outflow then
  inflow (reused via ``apply_chemostat_step``).
- Artificial chemistry / autocatalytic ecosystems (Combinatory Chemistry;
  npj Complexity 2025 spatial ACE; Evolvable Chemotons arXiv 2510.14282).
  A 2–3 material autocatalytic cycle is an optional measurement demo, not a
  claim of evolved chemotons or spatial ACE.
- Coevolution of cellularity and metabolism: membrane permeability gates
  uptake of both nutrients and toxins.

Claim ceiling: ``runtime_observation`` / software capability only.
Blocked: ``realistic_chemistry_proved``, ``wet_lab_equivalent``, GEM/MD
equivalence, intelligence, Avida-replacement.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from codontrace._types import JsonValue
from codontrace.errors import ConfigurationError
from codontrace.genesis.canonical import canonical_digest, require_finite_float
from codontrace.genesis.claim_gate import ClaimDecision, ClaimRequest, ScientificClaimGate
from codontrace.genesis.environment import (
    apply_chemostat_step,
    decay_local_patches,
    diffuse_local_patches,
)
from codontrace.trace import Trace, WorldEvent
from codontrace.world import World2D

_MATERIALS_CLAIM_CEILING = "runtime_observation"
_PACK_SCHEMA = "materials_evidence_pack_v1"
_SPATIAL_MODES = frozenset({"global_pool", "local_patches", "global_and_local"})
_MATERIAL_KINDS = frozenset(
    {"nutrient", "toxin", "catalyst", "signal", "waste", "intermediate"}
)
_FORBIDDEN_PACK_CLAIMS = frozenset(
    {
        "realistic_chemistry_proved",
        "wet_lab_equivalent",
        "kegg_solver_equivalent",
        "bigg_gem_equivalent",
    }
)

WORLD_EVENT_MATERIAL_INFLOW = "material_inflow"
WORLD_EVENT_MATERIAL_OUTFLOW = "material_outflow"
WORLD_EVENT_MATERIAL_REACTION = "material_reaction"
WORLD_EVENT_MATERIAL_UPTAKE = "material_uptake"
WORLD_EVENT_MATERIAL_EXCRETE = "material_excrete"

LITERATURE_CHECKLIST: tuple[tuple[str, str], ...] = (
    (
        "avida_resource_reaction_merit",
        "Ofria & Wilke 2004 Artificial Life 10(2): environment = resources + "
        "reactions; merit/metabolism as software accounting. Avida-ED resource "
        "modes. BMC Evol Biol 2021 metabolic signaling; ASMI 2022 "
        "nutrient→intracellular profiles. Mapped to named MaterialSpec effect "
        "coefficients and eat/absorb → ATP/merit records. Not an Avida ISA clone.",
    ),
    (
        "chemostat_novick_szilard_named_materials",
        "Novick & Szilard 1950 chemostat; Phase C already implements Avida "
        "RESOURCE unused-outflow then inflow. Phase G extends that update to "
        "named materials (initial/inflow/outflow on MaterialSpec).",
    ),
    (
        "artificial_chemistry_autocatalytic_ecosystems",
        "Combinatory Chemistry; npj Complexity 2025 spatial ACE; Evolvable "
        "Chemotons arXiv 2510.14282. Optional 2–3 material autocatalytic cycle "
        "plus spatial-coexistence *measurement*. Not a claim that chemotons or "
        "spatial ACE evolved.",
    ),
    (
        "cellularity_metabolism_coevolution",
        "Membrane permeability (cellularity knob) gates uptake of nutrients and "
        "toxins. Literature on coevolution of cellularity and metabolism is the "
        "design rationale; this is a software gate, not evolved membranes.",
    ),
    (
        "deferred_kegg_bigg_md",
        "Full KEGG/BiGG GEM solvers and molecular dynamics are explicitly "
        "deferred. MaterialSpec.external_ontology_id / units / "
        "effect_coefficients are schema hooks for a later real-substance table "
        "bind. biological_accuracy_claimed is always false.",
    ),
)


class MaterialKind(StrEnum):
    """Named-material roles. Software labels, not chemical proof."""

    NUTRIENT = "nutrient"
    TOXIN = "toxin"
    CATALYST = "catalyst"
    SIGNAL = "signal"
    WASTE = "waste"
    INTERMEDIATE = "intermediate"


@dataclass(frozen=True, slots=True)
class MaterialSpec:
    """One named material with organism-facing effect coefficients.

    ``external_ontology_id`` is an optional ChEBI/KEGG/BiGG hook for a future
    table bind. Filling it does **not** claim biological accuracy or that a
    GEM solver is running.
    """

    name: str
    kind: str = "nutrient"
    energy_yield: float = 0.0
    toxicity: float = 0.0
    viscosity: float = 0.0
    diffusion_rate: float = 0.0
    permeability: float = 1.0
    signaling_potency: float = 0.0
    scarcity: float = 0.0
    decay_rate: float = 0.0
    initial: float = 0.0
    inflow: float = 0.0
    outflow: float = 0.0
    unlimited: bool = False
    units: str = "arbitrary_mass"
    external_ontology_id: str = ""
    external_id: str = ""
    effect_coefficients: dict[str, float] = field(default_factory=dict)
    lethal_toxicity_threshold: float = 0.0
    description: str = ""
    biological_accuracy_claimed: bool = False

    def __post_init__(self) -> None:
        if not self.name or any(char.isspace() for char in self.name):
            raise ConfigurationError("MaterialSpec.name must be a non-empty token.")
        if self.kind not in _MATERIAL_KINDS:
            raise ConfigurationError(
                f"MaterialSpec.kind must be one of {sorted(_MATERIAL_KINDS)!r}."
            )
        if self.biological_accuracy_claimed:
            raise ConfigurationError(
                "MaterialSpec.biological_accuracy_claimed must stay False; "
                "this substrate is not wet-lab equivalent."
            )
        _set_finite(self, "energy_yield", self.energy_yield)
        _set_finite(self, "toxicity", self.toxicity)
        _set_finite(self, "viscosity", self.viscosity, probability=True)
        _set_finite(self, "diffusion_rate", self.diffusion_rate, probability=True)
        _set_finite(self, "permeability", self.permeability, probability=True)
        _set_finite(self, "signaling_potency", self.signaling_potency)
        _set_finite(self, "scarcity", self.scarcity)
        _set_finite(self, "decay_rate", self.decay_rate, probability=True)
        _set_finite(self, "initial", self.initial)
        _set_finite(self, "inflow", self.inflow)
        _set_finite(self, "outflow", self.outflow, probability=True)
        _set_finite(self, "lethal_toxicity_threshold", self.lethal_toxicity_threshold)
        coeffs: dict[str, float] = {}
        for key, value in self.effect_coefficients.items():
            if not key:
                raise ConfigurationError("effect_coefficients keys must be non-empty.")
            coeffs[str(key)] = require_finite_float(
                f"effect_coefficients.{key}", value, non_negative=True
            )
        object.__setattr__(self, "effect_coefficients", dict(sorted(coeffs.items())))
        if not self.units:
            raise ConfigurationError("MaterialSpec.units must not be empty.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "kind": self.kind,
            "energy_yield": self.energy_yield,
            "toxicity": self.toxicity,
            "viscosity": self.viscosity,
            "diffusion_rate": self.diffusion_rate,
            "permeability": self.permeability,
            "signaling_potency": self.signaling_potency,
            "scarcity": self.scarcity,
            "decay_rate": self.decay_rate,
            "initial": self.initial,
            "inflow": self.inflow,
            "outflow": self.outflow,
            "unlimited": self.unlimited,
            "units": self.units,
            "external_ontology_id": self.external_ontology_id,
            "external_id": self.external_id,
            "effect_coefficients": dict(self.effect_coefficients),
            "lethal_toxicity_threshold": self.lethal_toxicity_threshold,
            "description": self.description,
            "biological_accuracy_claimed": False,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> MaterialSpec:
        coeffs_raw = data.get("effect_coefficients", {})
        coeffs: dict[str, float] = {}
        if coeffs_raw:
            if not isinstance(coeffs_raw, Mapping):
                raise ConfigurationError("effect_coefficients must be an object.")
            for key, value in coeffs_raw.items():
                if isinstance(value, bool) or not isinstance(value, int | float):
                    raise ConfigurationError("effect_coefficients values must be numeric.")
                coeffs[str(key)] = float(value)
        return cls(
            name=_str(data, "name"),
            kind=_str(data, "kind", "nutrient"),
            energy_yield=_float(data, "energy_yield", 0.0),
            toxicity=_float(data, "toxicity", 0.0),
            viscosity=_float(data, "viscosity", 0.0),
            diffusion_rate=_float(data, "diffusion_rate", 0.0),
            permeability=_float(data, "permeability", 1.0),
            signaling_potency=_float(data, "signaling_potency", 0.0),
            scarcity=_float(data, "scarcity", 0.0),
            decay_rate=_float(data, "decay_rate", 0.0),
            initial=_float(data, "initial", 0.0),
            inflow=_float(data, "inflow", 0.0),
            outflow=_float(data, "outflow", 0.0),
            unlimited=_bool(data, "unlimited", False),
            units=_str(data, "units", "arbitrary_mass"),
            external_ontology_id=_str(data, "external_ontology_id", ""),
            external_id=_str(data, "external_id", ""),
            effect_coefficients=coeffs,
            lethal_toxicity_threshold=_float(data, "lethal_toxicity_threshold", 0.0),
            description=_str(data, "description", ""),
            biological_accuracy_claimed=False,
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MaterialReactionSpec:
    """Simple stoichiometric chemical-reaction-network subset.

    Extent is a mass-action-style discrete fire, not a stiff ODE GEM solver.
    ``catalyst`` names a material that must be present (world pool, local cell,
    or organism inventory) to enable the reaction when
    ``MaterialsConfig.catalyst_enables_reactions`` is set.
    """

    name: str
    reactants: dict[str, float] = field(default_factory=dict)
    products: dict[str, float] = field(default_factory=dict)
    rate: float = 0.0
    catalyst: str = ""
    autocatalytic: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ConfigurationError("MaterialReactionSpec.name must not be empty.")
        object.__setattr__(self, "reactants", _finite_amount_map(self.reactants, "reactants"))
        object.__setattr__(self, "products", _finite_amount_map(self.products, "products"))
        object.__setattr__(
            self, "rate", require_finite_float("reaction_rate", self.rate, non_negative=True)
        )
        if not self.reactants and not self.products:
            raise ConfigurationError("MaterialReactionSpec needs reactants or products.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "reactants": dict(self.reactants),
            "products": dict(self.products),
            "rate": self.rate,
            "catalyst": self.catalyst,
            "autocatalytic": self.autocatalytic,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> MaterialReactionSpec:
        return cls(
            name=_str(data, "name"),
            reactants=_float_map(data, "reactants"),
            products=_float_map(data, "products"),
            rate=_float(data, "rate", 0.0),
            catalyst=_str(data, "catalyst", ""),
            autocatalytic=_bool(data, "autocatalytic", False),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MaterialsConfig:
    """Opt-in named-materials world. Default disabled (digest-stable)."""

    enabled: bool = False
    materials: tuple[MaterialSpec, ...] = ()
    reactions: tuple[MaterialReactionSpec, ...] = ()
    spatial_mode: str = "global_and_local"
    patch_cells: tuple[tuple[int, int], ...] = ()
    default_membrane_permeability: float = 1.0
    uptake_rate: float = 1.0
    excretion_rate: float = 0.25
    passive_nutrient_uptake: bool = False
    eat_absorbs_nutrients: bool = True
    toxin_passive_uptake: bool = True
    signal_passive_uptake: bool = True
    diffusion_rate: float = 0.0
    decay_rate: float = 0.0
    inherit_intracellular: bool = False
    catalyst_enables_reactions: bool = True
    merit_from_energy_yield: bool = True

    def __post_init__(self) -> None:
        if self.spatial_mode not in _SPATIAL_MODES:
            raise ConfigurationError(
                f"spatial_mode must be one of {sorted(_SPATIAL_MODES)!r}."
            )
        object.__setattr__(
            self,
            "default_membrane_permeability",
            require_finite_float(
                "default_membrane_permeability",
                self.default_membrane_permeability,
                non_negative=True,
                probability=True,
            ),
        )
        object.__setattr__(
            self,
            "uptake_rate",
            require_finite_float("uptake_rate", self.uptake_rate, non_negative=True),
        )
        object.__setattr__(
            self,
            "excretion_rate",
            require_finite_float(
                "excretion_rate", self.excretion_rate, non_negative=True, probability=True
            ),
        )
        object.__setattr__(
            self,
            "diffusion_rate",
            require_finite_float(
                "diffusion_rate", self.diffusion_rate, non_negative=True, probability=True
            ),
        )
        object.__setattr__(
            self,
            "decay_rate",
            require_finite_float(
                "decay_rate", self.decay_rate, non_negative=True, probability=True
            ),
        )
        names = [item.name for item in self.materials]
        if len(names) != len(set(names)):
            raise ConfigurationError("MaterialSpec names must be unique.")
        known = set(names)
        for reaction in self.reactions:
            for token in (*reaction.reactants, *reaction.products):
                if token not in known:
                    raise ConfigurationError(
                        f"Reaction {reaction.name!r} references unknown material {token!r}."
                    )
            if reaction.catalyst and reaction.catalyst not in known:
                raise ConfigurationError(
                    f"Reaction {reaction.name!r} catalyst {reaction.catalyst!r} is unknown."
                )
        cells: list[tuple[int, int]] = []
        for item in self.patch_cells:
            if len(item) != 2 or isinstance(item[0], bool) or isinstance(item[1], bool):
                raise ConfigurationError("patch_cells must be (x, y) integer pairs.")
            cells.append((int(item[0]), int(item[1])))
        object.__setattr__(self, "patch_cells", tuple(cells))

    @property
    def uses_global_pool(self) -> bool:
        return self.enabled and self.spatial_mode in {"global_pool", "global_and_local"}

    @property
    def uses_local_patches(self) -> bool:
        return self.enabled and self.spatial_mode in {"local_patches", "global_and_local"}

    def spec_by_name(self) -> dict[str, MaterialSpec]:
        return {item.name: item for item in self.materials}

    @classmethod
    def research_defaults(
        cls,
        *,
        patch_cells: Sequence[tuple[int, int]] = ((0, 0), (1, 0)),
        membrane_permeability: float = 0.75,
        toxin_cell: tuple[int, int] = (2, 0),
        include_toxin_patch: bool = True,
    ) -> MaterialsConfig:
        """Nutrient + toxin + catalyst overlay with ChEBI schema hooks.

        Ontology ids are labels for a future bind, not a claim that glucose or
        ammonia chemistry is simulated.
        """

        nourish = MaterialSpec(
            name="nourish",
            kind="nutrient",
            energy_yield=2.0,
            permeability=0.8,
            initial=12.0,
            inflow=1.0,
            outflow=0.01,
            diffusion_rate=0.0,
            units="arbitrary_mass",
            external_ontology_id="CHEBI:17234",
            description="Nutrient proxy with optional glucose ChEBI hook. Not glucose chemistry.",
            effect_coefficients={"merit_per_unit": 1.0},
        )
        toxin = MaterialSpec(
            name="toxin",
            kind="toxin",
            toxicity=1.5,
            permeability=0.5,
            initial=2.0,
            inflow=0.0,
            outflow=0.01,
            lethal_toxicity_threshold=4.0,
            units="arbitrary_mass",
            external_ontology_id="CHEBI:16134",
            description="Toxin proxy with optional ammonia ChEBI hook. Not ammonia chemistry.",
        )
        catalyst = MaterialSpec(
            name="catalyst",
            kind="catalyst",
            permeability=0.2,
            scarcity=1.0,
            initial=1.0,
            viscosity=0.3,
            inflow=0.0,
            outflow=0.0,
            units="arbitrary_mass",
            description="Catalyst proxy. Not an enzyme or GEM species.",
        )
        cells = tuple(patch_cells)
        if include_toxin_patch and toxin_cell not in cells:
            cells = (*cells, toxin_cell)
        return cls(
            enabled=True,
            materials=(nourish, toxin, catalyst),
            spatial_mode="global_and_local",
            patch_cells=cells,
            default_membrane_permeability=membrane_permeability,
            eat_absorbs_nutrients=True,
            toxin_passive_uptake=True,
        )

    @classmethod
    def autocatalytic_cycle(
        cls,
        *,
        patch_cells: Sequence[tuple[int, int]] = ((0, 0), (1, 0), (2, 0)),
        membrane_permeability: float = 0.75,
        rate: float = 0.4,
    ) -> MaterialsConfig:
        """Minimal 3-material autocatalytic cycle for measurement-only demos.

        ``A + B → 2A`` (autocatalytic) and slow ``A → W`` waste. Spatial
        coexistence of A-rich vs B-rich cells can be measured; that is not a
        spatial-ACE or chemoton claim (npj Complexity 2025 cited as design note).
        """

        seed = MaterialSpec(
            name="A",
            kind="catalyst",
            energy_yield=0.5,
            permeability=0.6,
            initial=2.0,
            inflow=0.0,
            outflow=0.0,
            description="Autocatalytic seed/product. Not a chemoton.",
        )
        food = MaterialSpec(
            name="B",
            kind="nutrient",
            energy_yield=1.0,
            permeability=0.8,
            initial=10.0,
            inflow=1.0,
            outflow=0.01,
            description="Food feedstock for the autocatalytic fire.",
        )
        waste = MaterialSpec(
            name="W",
            kind="waste",
            permeability=1.0,
            initial=0.0,
            inflow=0.0,
            outflow=0.01,
            decay_rate=0.0,
            description="Waste sink. Not a KEGG compound.",
        )
        grow = MaterialReactionSpec(
            name="autocatalytic_A",
            reactants={"A": 1.0, "B": 1.0},
            products={"A": 2.0},
            rate=rate,
            catalyst="A",
            autocatalytic=True,
        )
        leak = MaterialReactionSpec(
            name="A_to_waste",
            reactants={"A": 1.0},
            products={"W": 1.0},
            rate=0.05,
        )
        return cls(
            enabled=True,
            materials=(seed, food, waste),
            reactions=(grow, leak),
            spatial_mode="global_and_local",
            patch_cells=tuple(patch_cells),
            default_membrane_permeability=membrane_permeability,
            eat_absorbs_nutrients=True,
            catalyst_enables_reactions=True,
            diffusion_rate=0.15,
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "materials": [item.to_dict() for item in self.materials],
            "reactions": [item.to_dict() for item in self.reactions],
            "spatial_mode": self.spatial_mode,
            "patch_cells": [[x, y] for x, y in self.patch_cells],
            "default_membrane_permeability": self.default_membrane_permeability,
            "uptake_rate": self.uptake_rate,
            "excretion_rate": self.excretion_rate,
            "passive_nutrient_uptake": self.passive_nutrient_uptake,
            "eat_absorbs_nutrients": self.eat_absorbs_nutrients,
            "toxin_passive_uptake": self.toxin_passive_uptake,
            "signal_passive_uptake": self.signal_passive_uptake,
            "diffusion_rate": self.diffusion_rate,
            "decay_rate": self.decay_rate,
            "inherit_intracellular": self.inherit_intracellular,
            "catalyst_enables_reactions": self.catalyst_enables_reactions,
            "merit_from_energy_yield": self.merit_from_energy_yield,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> MaterialsConfig:
        materials_raw = data.get("materials", [])
        if not isinstance(materials_raw, list):
            raise ConfigurationError("materials must be a list.")
        reactions_raw = data.get("reactions", [])
        if not isinstance(reactions_raw, list):
            raise ConfigurationError("reactions must be a list.")
        cells_raw = data.get("patch_cells", [])
        cells: list[tuple[int, int]] = []
        if cells_raw:
            if not isinstance(cells_raw, list):
                raise ConfigurationError("patch_cells must be a list.")
            for item in cells_raw:
                if not isinstance(item, list) or len(item) != 2:
                    raise ConfigurationError("patch_cells entries must be [x, y].")
                x, y = item
                if (
                    isinstance(x, bool)
                    or isinstance(y, bool)
                    or not isinstance(x, int)
                    or not isinstance(y, int)
                ):
                    raise ConfigurationError("patch_cells coordinates must be integers.")
                cells.append((x, y))
        return cls(
            enabled=_bool(data, "enabled", False),
            materials=tuple(
                MaterialSpec.from_dict(item) for item in materials_raw if isinstance(item, Mapping)
            ),
            reactions=tuple(
                MaterialReactionSpec.from_dict(item)
                for item in reactions_raw
                if isinstance(item, Mapping)
            ),
            spatial_mode=_str(data, "spatial_mode", "global_and_local"),
            patch_cells=tuple(cells),
            default_membrane_permeability=_float(data, "default_membrane_permeability", 1.0),
            uptake_rate=_float(data, "uptake_rate", 1.0),
            excretion_rate=_float(data, "excretion_rate", 0.25),
            passive_nutrient_uptake=_bool(data, "passive_nutrient_uptake", False),
            eat_absorbs_nutrients=_bool(data, "eat_absorbs_nutrients", True),
            toxin_passive_uptake=_bool(data, "toxin_passive_uptake", True),
            signal_passive_uptake=_bool(data, "signal_passive_uptake", True),
            diffusion_rate=_float(data, "diffusion_rate", 0.0),
            decay_rate=_float(data, "decay_rate", 0.0),
            inherit_intracellular=_bool(data, "inherit_intracellular", False),
            catalyst_enables_reactions=_bool(data, "catalyst_enables_reactions", True),
            merit_from_energy_yield=_bool(data, "merit_from_energy_yield", True),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MaterialBindingSchema:
    """Export schema for later real-substance tables. Not a solver."""

    schema_version: str = "material_binding_schema_v1"
    supports_external_ontology_id: bool = True
    supported_ontologies: tuple[str, ...] = ("CHEBI", "KEGG", "BiGG")
    units_field: str = "units"
    effect_coefficients_field: str = "effect_coefficients"
    gem_solver_implemented: bool = False
    molecular_dynamics_implemented: bool = False
    biological_accuracy_claimed: bool = False
    claim_ceiling: str = _MATERIALS_CLAIM_CEILING

    def __post_init__(self) -> None:
        if self.gem_solver_implemented or self.molecular_dynamics_implemented:
            raise ConfigurationError("GEM/MD solvers are deferred; flags must stay False.")
        if self.biological_accuracy_claimed:
            raise ConfigurationError("biological_accuracy_claimed must stay False.")
        if self.claim_ceiling != _MATERIALS_CLAIM_CEILING:
            raise ConfigurationError("MaterialBindingSchema ceiling is runtime_observation only.")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "supports_external_ontology_id": self.supports_external_ontology_id,
            "supported_ontologies": list(self.supported_ontologies),
            "units_field": self.units_field,
            "effect_coefficients_field": self.effect_coefficients_field,
            "gem_solver_implemented": False,
            "molecular_dynamics_implemented": False,
            "biological_accuracy_claimed": False,
            "claim_ceiling": self.claim_ceiling,
        }


@dataclass(slots=True)
class MaterialsOrganismState:
    """Intracellular inventory and cellularity knob. Absent on default organisms."""

    enabled: bool = True
    organism_id: str = ""
    membrane_permeability: float = 1.0
    intracellular: dict[str, float] = field(default_factory=dict)
    cumulative_absorbed: dict[str, float] = field(default_factory=dict)
    cumulative_excreted: dict[str, float] = field(default_factory=dict)
    atp_from_materials: float = 0.0
    atp_drained_by_toxins: float = 0.0
    merit_from_materials: float = 0.0
    toxin_lethal: bool = False
    inherit_intracellular: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "enabled": self.enabled,
            "organism_id": self.organism_id,
            "membrane_permeability": self.membrane_permeability,
            "intracellular": dict(sorted(self.intracellular.items())),
            "cumulative_absorbed": dict(sorted(self.cumulative_absorbed.items())),
            "cumulative_excreted": dict(sorted(self.cumulative_excreted.items())),
            "atp_from_materials": self.atp_from_materials,
            "atp_drained_by_toxins": self.atp_drained_by_toxins,
            "merit_from_materials": self.merit_from_materials,
            "toxin_lethal": self.toxin_lethal,
            "inherit_intracellular": self.inherit_intracellular,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> MaterialsOrganismState:
        return cls(
            enabled=_bool(data, "enabled", True),
            organism_id=_str(data, "organism_id", ""),
            membrane_permeability=_float(data, "membrane_permeability", 1.0),
            intracellular=_float_map(data, "intracellular"),
            cumulative_absorbed=_float_map(data, "cumulative_absorbed"),
            cumulative_excreted=_float_map(data, "cumulative_excreted"),
            atp_from_materials=_float(data, "atp_from_materials", 0.0),
            atp_drained_by_toxins=_float(data, "atp_drained_by_toxins", 0.0),
            merit_from_materials=_float(data, "merit_from_materials", 0.0),
            toxin_lethal=_bool(data, "toxin_lethal", False),
            inherit_intracellular=_bool(data, "inherit_intracellular", False),
        )


@dataclass(frozen=True, slots=True)
class MaterialsState:
    """Runtime named-material pools and optional spatial grids."""

    tick: int = 0
    pools: dict[str, float] = field(default_factory=dict)
    grids: dict[str, dict[tuple[int, int], float]] = field(default_factory=dict)
    cumulative_inflow: dict[str, float] = field(default_factory=dict)
    cumulative_outflow: dict[str, float] = field(default_factory=dict)
    cumulative_consumed: dict[str, float] = field(default_factory=dict)
    cumulative_reacted: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.tick < 0:
            raise ConfigurationError("MaterialsState.tick must be non-negative.")
        object.__setattr__(self, "pools", _finite_amount_map(self.pools, "pools"))
        normalized_grids: dict[str, dict[tuple[int, int], float]] = {}
        for name, cells in self.grids.items():
            if not name:
                raise ConfigurationError("grid material names must be non-empty.")
            cell_map: dict[tuple[int, int], float] = {}
            for position, amount in cells.items():
                if len(position) != 2:
                    raise ConfigurationError("grid keys must be (x, y).")
                cell_map[(int(position[0]), int(position[1]))] = require_finite_float(
                    f"grids.{name}", amount, non_negative=True
                )
            normalized_grids[str(name)] = dict(sorted(cell_map.items()))
        object.__setattr__(self, "grids", dict(sorted(normalized_grids.items())))
        object.__setattr__(
            self, "cumulative_inflow", _finite_amount_map(self.cumulative_inflow, "cumulative_inflow")
        )
        object.__setattr__(
            self,
            "cumulative_outflow",
            _finite_amount_map(self.cumulative_outflow, "cumulative_outflow"),
        )
        object.__setattr__(
            self,
            "cumulative_consumed",
            _finite_amount_map(self.cumulative_consumed, "cumulative_consumed"),
        )
        object.__setattr__(
            self,
            "cumulative_reacted",
            _finite_amount_map(self.cumulative_reacted, "cumulative_reacted"),
        )

    @classmethod
    def initialize(cls, config: MaterialsConfig, *, tick: int = 0) -> MaterialsState:
        pools = {spec.name: spec.initial for spec in config.materials}
        grids: dict[str, dict[tuple[int, int], float]] = {}
        if config.uses_local_patches and config.patch_cells:
            cells = config.patch_cells
            for spec in config.materials:
                if spec.kind == "toxin" and len(cells) >= 3:
                    grids[spec.name] = {cells[-1]: spec.initial}
                elif spec.kind == "nutrient":
                    share = spec.initial / len(cells) if spec.initial > 0 else 0.0
                    grids[spec.name] = {
                        cell: round(share, 10) for cell in cells[:-1] or cells if share > 0
                    }
                elif spec.kind in {"catalyst", "intermediate"} and spec.initial > 0:
                    grids[spec.name] = {cells[0]: spec.initial}
                elif spec.initial > 0:
                    share = spec.initial / len(cells)
                    grids[spec.name] = {cell: round(share, 10) for cell in cells if share > 0}
        return cls(
            tick=tick,
            pools=pools,
            grids=grids,
            cumulative_inflow={spec.name: 0.0 for spec in config.materials},
            cumulative_outflow={spec.name: 0.0 for spec in config.materials},
            cumulative_consumed={spec.name: 0.0 for spec in config.materials},
            cumulative_reacted={spec.name: 0.0 for spec in config.materials},
        )

    def to_dict(self) -> dict[str, JsonValue]:
        grids_payload: dict[str, JsonValue] = {}
        for name, cells in sorted(self.grids.items()):
            grids_payload[name] = [[x, y, amount] for (x, y), amount in sorted(cells.items())]
        return {
            "tick": self.tick,
            "pools": dict(sorted(self.pools.items())),
            "grids": grids_payload,
            "cumulative_inflow": dict(sorted(self.cumulative_inflow.items())),
            "cumulative_outflow": dict(sorted(self.cumulative_outflow.items())),
            "cumulative_consumed": dict(sorted(self.cumulative_consumed.items())),
            "cumulative_reacted": dict(sorted(self.cumulative_reacted.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> MaterialsState:
        grids_raw = data.get("grids", {})
        grids: dict[str, dict[tuple[int, int], float]] = {}
        if grids_raw:
            if not isinstance(grids_raw, Mapping):
                raise ConfigurationError("grids must be an object.")
            for name, cells_raw in grids_raw.items():
                if not isinstance(cells_raw, list):
                    raise ConfigurationError("grid values must be lists of [x, y, amount].")
                cell_map: dict[tuple[int, int], float] = {}
                for item in cells_raw:
                    if not isinstance(item, list) or len(item) != 3:
                        raise ConfigurationError("grid entries must be [x, y, amount].")
                    x, y, amount = item
                    if (
                        isinstance(x, bool)
                        or isinstance(y, bool)
                        or not isinstance(x, int)
                        or not isinstance(y, int)
                    ):
                        raise ConfigurationError("grid coordinates must be integers.")
                    if isinstance(amount, bool) or not isinstance(amount, int | float):
                        raise ConfigurationError("grid amounts must be numeric.")
                    cell_map[(x, y)] = float(amount)
                grids[str(name)] = cell_map
        return cls(
            tick=_int(data, "tick", 0),
            pools=_float_map(data, "pools"),
            grids=grids,
            cumulative_inflow=_float_map(data, "cumulative_inflow"),
            cumulative_outflow=_float_map(data, "cumulative_outflow"),
            cumulative_consumed=_float_map(data, "cumulative_consumed"),
            cumulative_reacted=_float_map(data, "cumulative_reacted"),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MaterialEvent:
    """Digest-backed record for one materials mutation this tick."""

    tick: int
    event_type: str
    material: str | None = None
    amount: float = 0.0
    organism_id: str | None = None
    position: tuple[int, int] | None = None
    status: str = "measured"
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_type:
            raise ConfigurationError("MaterialEvent.event_type must not be empty.")
        _set_finite(self, "amount", self.amount, name="MaterialEvent.amount")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": "material_event_v1",
            "tick": self.tick,
            "event_type": self.event_type,
            "material": self.material,
            "amount": self.amount,
            "organism_id": self.organism_id,
            "position": None if self.position is None else [self.position[0], self.position[1]],
            "status": self.status,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> MaterialEvent:
        raw_pos = data.get("position")
        pos = None
        if isinstance(raw_pos, list) and len(raw_pos) == 2:
            pos = (int(raw_pos[0]), int(raw_pos[1]))
        meta_raw = data.get("metadata", {})
        metadata = dict(meta_raw) if isinstance(meta_raw, Mapping) else {}
        material_raw = data.get("material")
        organism_raw = data.get("organism_id")
        return cls(
            tick=_int(data, "tick", 0),
            event_type=_str(data, "event_type", "unknown"),
            material=None if material_raw is None else str(material_raw),
            amount=_float(data, "amount", 0.0),
            organism_id=None if organism_raw is None else str(organism_raw),
            position=pos,
            status=_str(data, "status", "measured"),
            metadata={str(key): value for key, value in metadata.items()},
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MaterialsSnapshot:
    """Per-tick named-material levels for trajectory digests and replay."""

    tick: int
    pools: dict[str, float]
    patch_total: dict[str, float]
    patch_cells: int
    reacted: dict[str, float] = field(default_factory=dict)
    inflow_applied: dict[str, float] = field(default_factory=dict)
    outflow_removed: dict[str, float] = field(default_factory=dict)
    consumed: dict[str, float] = field(default_factory=dict)
    autocatalytic_extent: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "pools", _finite_amount_map(self.pools, "pools"))
        object.__setattr__(
            self, "patch_total", _finite_amount_map(self.patch_total, "patch_total")
        )
        object.__setattr__(
            self,
            "autocatalytic_extent",
            require_finite_float("autocatalytic_extent", self.autocatalytic_extent, non_negative=True),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "schema_version": "materials_snapshot_v1",
            "tick": self.tick,
            "pools": dict(sorted(self.pools.items())),
            "patch_total": dict(sorted(self.patch_total.items())),
            "patch_cells": self.patch_cells,
            "reacted": dict(sorted(self.reacted.items())),
            "inflow_applied": dict(sorted(self.inflow_applied.items())),
            "outflow_removed": dict(sorted(self.outflow_removed.items())),
            "consumed": dict(sorted(self.consumed.items())),
            "autocatalytic_extent": self.autocatalytic_extent,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, JsonValue]) -> MaterialsSnapshot:
        return cls(
            tick=_int(data, "tick", 0),
            pools=_float_map(data, "pools"),
            patch_total=_float_map(data, "patch_total"),
            patch_cells=_int(data, "patch_cells", 0),
            reacted=_float_map(data, "reacted"),
            inflow_applied=_float_map(data, "inflow_applied"),
            outflow_removed=_float_map(data, "outflow_removed"),
            consumed=_float_map(data, "consumed"),
            autocatalytic_extent=_float(data, "autocatalytic_extent", 0.0),
        )

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MaterialsStepResult:
    """World-independent materials tick: state, events, snapshot, WorldEvents."""

    state: MaterialsState
    events: tuple[MaterialEvent, ...]
    snapshot: MaterialsSnapshot
    world_events: tuple[WorldEvent, ...]


@dataclass(frozen=True, slots=True)
class MaterialsReplayVerification:
    """Replay check for a materials trajectory digest."""

    matched: bool
    expected_digest: str
    observed_digest: str
    snapshot_count: int
    claim_ceiling: str = _MATERIALS_CLAIM_CEILING

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "matched": self.matched,
            "expected_digest": self.expected_digest,
            "observed_digest": self.observed_digest,
            "snapshot_count": self.snapshot_count,
            "claim_ceiling": self.claim_ceiling,
        }


@dataclass(frozen=True, slots=True)
class SpatialCoexistenceObservation:
    """npj Complexity 2025 ACE *measurement* note: A-rich vs B-rich cells.

    Recording coexistence is not a claim that a spatial autocatalytic
    ecosystem evolved.
    """

    material_a: str
    material_b: str
    cells_a_rich: int
    cells_b_rich: int
    cells_both: int
    threshold: float
    coexistence_observed: bool
    claim_ceiling: str = _MATERIALS_CLAIM_CEILING
    spatial_ace_evolved: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "material_a": self.material_a,
            "material_b": self.material_b,
            "cells_a_rich": self.cells_a_rich,
            "cells_b_rich": self.cells_b_rich,
            "cells_both": self.cells_both,
            "threshold": self.threshold,
            "coexistence_observed": self.coexistence_observed,
            "claim_ceiling": self.claim_ceiling,
            "spatial_ace_evolved": False,
        }


@dataclass(frozen=True, slots=True)
class MaterialsObservation:
    """Runtime observation of one materials-enabled run. Not chemistry proof."""

    materials_config_digest: str
    trajectory_digest: str
    ticks: int
    material_events: int
    unique_materials: tuple[str, ...]
    pool_series: dict[str, tuple[float, ...]]
    uptake_events: int
    toxin_drain_events: int
    reaction_events: int
    autocatalytic_extent_total: float
    spatial_coexistence: SpatialCoexistenceObservation | None
    replay_digest: str
    claim_ceiling: str = _MATERIALS_CLAIM_CEILING
    realistic_chemistry_proved: bool = False
    wet_lab_equivalent: bool = False

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "materials_config_digest": self.materials_config_digest,
            "trajectory_digest": self.trajectory_digest,
            "ticks": self.ticks,
            "material_events": self.material_events,
            "unique_materials": list(self.unique_materials),
            "pool_series": {key: list(values) for key, values in sorted(self.pool_series.items())},
            "uptake_events": self.uptake_events,
            "toxin_drain_events": self.toxin_drain_events,
            "reaction_events": self.reaction_events,
            "autocatalytic_extent_total": self.autocatalytic_extent_total,
            "spatial_coexistence": None
            if self.spatial_coexistence is None
            else self.spatial_coexistence.to_dict(),
            "replay_digest": self.replay_digest,
            "claim_ceiling": self.claim_ceiling,
            "realistic_chemistry_proved": False,
            "wet_lab_equivalent": False,
        }

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class MaterialsEvidencePack:
    """First-class JSON+digest export for Phase G runtime observations."""

    observation: MaterialsObservation
    binding_schema: MaterialBindingSchema
    literature_checklist: tuple[tuple[str, str], ...] = LITERATURE_CHECKLIST
    run_digest: str = ""
    claim_ceiling: str = _MATERIALS_CLAIM_CEILING
    schema_version: str = _PACK_SCHEMA
    digest: str = ""

    def __post_init__(self) -> None:
        if self.claim_ceiling != _MATERIALS_CLAIM_CEILING:
            raise ConfigurationError("MaterialsEvidencePack ceiling is runtime_observation only.")
        if self.claim_ceiling in _FORBIDDEN_PACK_CLAIMS:
            raise ConfigurationError("MaterialsEvidencePack must never claim realistic chemistry.")
        computed = canonical_digest(self._payload())
        if self.digest and self.digest != computed:
            raise ConfigurationError("MaterialsEvidencePack digest mismatch.")
        object.__setattr__(self, "digest", computed)

    def _payload(self) -> dict[str, JsonValue]:
        return {
            "schema_version": self.schema_version,
            "observation": self.observation.to_dict(),
            "binding_schema": self.binding_schema.to_dict(),
            "literature_checklist": [[name, detail] for name, detail in self.literature_checklist],
            "run_digest": self.run_digest,
            "claim_ceiling": self.claim_ceiling,
            "realistic_chemistry_proved": False,
            "wet_lab_equivalent": False,
            "kegg_solver_implemented": False,
            "molecular_dynamics_implemented": False,
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {**self._payload(), "digest": self.digest}

    def to_json(self) -> str:
        from codontrace._numeric import finite_json_dumps

        return finite_json_dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def apply_stoichiometric_reaction(
    amounts: Mapping[str, float],
    reaction: MaterialReactionSpec,
    *,
    catalyst_amount: float = 0.0,
    require_catalyst: bool = False,
) -> tuple[dict[str, float], float]:
    """Fire one discrete mass-action-style extent. Conserves stoich mass locally.

    Returns ``(new_amounts, extent)``. Extent 0 means the reaction did not fire.
    """

    pools = {str(key): float(value) for key, value in amounts.items()}
    if require_catalyst and reaction.catalyst and catalyst_amount <= 0:
        return pools, 0.0
    if reaction.rate <= 0:
        return pools, 0.0
    limiting = float("inf")
    mass_product = 1.0
    for name, stoich in reaction.reactants.items():
        available = pools.get(name, 0.0)
        if stoich <= 0:
            continue
        limiting = min(limiting, available / stoich)
        mass_product *= max(available, 0.0)
    if limiting <= 0 or limiting == float("inf"):
        return pools, 0.0
    # Catalyst is an enablement gate, not a GEM enzyme-kinetics term.
    extent = round(max(0.0, min(limiting, reaction.rate * mass_product)), 10)
    if extent <= 0:
        return pools, 0.0
    for name, stoich in reaction.reactants.items():
        pools[name] = round(max(0.0, pools.get(name, 0.0) - extent * stoich), 10)
    for name, stoich in reaction.products.items():
        pools[name] = round(pools.get(name, 0.0) + extent * stoich, 10)
    return pools, extent


def materials_trajectory_digest(snapshots: Sequence[MaterialsSnapshot]) -> str:
    return canonical_digest({"snapshots": [item.to_dict() for item in snapshots]})


def verify_materials_trajectory_replay(
    expected: Sequence[MaterialsSnapshot],
    observed: Sequence[MaterialsSnapshot],
) -> MaterialsReplayVerification:
    expected_digest = materials_trajectory_digest(expected)
    observed_digest = materials_trajectory_digest(observed)
    return MaterialsReplayVerification(
        matched=expected_digest == observed_digest and len(expected) == len(observed),
        expected_digest=expected_digest,
        observed_digest=observed_digest,
        snapshot_count=len(observed),
    )


def snapshots_from_generation_results(results: Sequence[object]) -> tuple[MaterialsSnapshot, ...]:
    snapshots: list[MaterialsSnapshot] = []
    for item in results:
        snapshot = getattr(item, "materials_snapshot", None)
        if snapshot is None:
            generation = getattr(item, "generation_result", None)
            snapshot = None
            if generation is not None:
                snapshot = getattr(generation, "materials_snapshot", None)
        if isinstance(snapshot, MaterialsSnapshot):
            snapshots.append(snapshot)
    return tuple(snapshots)


materials_snapshots_from_generation_results = snapshots_from_generation_results


def measure_spatial_coexistence(
    state: MaterialsState,
    *,
    material_a: str,
    material_b: str,
    threshold: float = 0.5,
) -> SpatialCoexistenceObservation:
    cells_a = state.grids.get(material_a, {})
    cells_b = state.grids.get(material_b, {})
    positions = set(cells_a) | set(cells_b)
    a_rich = 0
    b_rich = 0
    both = 0
    for position in positions:
        a_amt = float(cells_a.get(position, 0.0))
        b_amt = float(cells_b.get(position, 0.0))
        a_ok = a_amt >= threshold
        b_ok = b_amt >= threshold
        if a_ok:
            a_rich += 1
        if b_ok:
            b_rich += 1
        if a_ok and b_ok:
            both += 1
    return SpatialCoexistenceObservation(
        material_a=material_a,
        material_b=material_b,
        cells_a_rich=a_rich,
        cells_b_rich=b_rich,
        cells_both=both,
        threshold=threshold,
        coexistence_observed=a_rich > 0 and b_rich > 0,
    )


def copy_materials_organism_state(
    state: MaterialsOrganismState | None,
) -> MaterialsOrganismState | None:
    if state is None:
        return None
    return MaterialsOrganismState.from_dict(state.to_dict())


def inherit_materials_organism_state(
    parent_state: MaterialsOrganismState | None,
    *,
    child_id: str,
    inherit_intracellular: bool,
    default_permeability: float,
) -> MaterialsOrganismState | None:
    if parent_state is None:
        return None
    child = copy_materials_organism_state(parent_state)
    if child is None:
        return None
    child.organism_id = child_id
    child.atp_from_materials = 0.0
    child.atp_drained_by_toxins = 0.0
    child.merit_from_materials = 0.0
    child.toxin_lethal = False
    child.cumulative_absorbed = {}
    child.cumulative_excreted = {}
    keep_inventory = inherit_intracellular or parent_state.inherit_intracellular
    if not keep_inventory:
        child.intracellular = {}
    child.membrane_permeability = parent_state.membrane_permeability
    return child


def build_materials_organism_state(
    config: MaterialsConfig,
    *,
    organism_id: str,
) -> MaterialsOrganismState | None:
    if not config.enabled:
        return None
    return MaterialsOrganismState(
        enabled=True,
        organism_id=organism_id,
        membrane_permeability=config.default_membrane_permeability,
        inherit_intracellular=config.inherit_intracellular,
    )


def attach_materials_to_organisms(
    organisms: Sequence[Any],
    config: MaterialsConfig,
) -> tuple[Any, ...]:
    if not config.enabled:
        return tuple(organisms)
    attached = []
    for organism in organisms:
        if getattr(organism, "materials_state", None) is None:
            organism.materials_state = build_materials_organism_state(
                config, organism_id=str(getattr(organism, "id", ""))
            )
        attached.append(organism)
    return tuple(attached)


def apply_organism_material_coupling(
    organism: Any,
    working_pools: dict[str, float],
    working_grids: dict[str, dict[tuple[int, int], float]],
    config: MaterialsConfig,
    *,
    tick: int,
    did_eat: bool,
) -> list[MaterialEvent]:
    """Absorb / toxin-drain / excrete for one organism. Mutates working maps + ATP."""

    if not config.enabled:
        return []
    state = getattr(organism, "materials_state", None)
    if not isinstance(state, MaterialsOrganismState):
        organism.materials_state = build_materials_organism_state(
            config, organism_id=str(getattr(organism, "id", ""))
        )
        state = organism.materials_state
    if state is None:
        return []
    events: list[MaterialEvent] = []
    position = getattr(organism, "position", (0, 0))
    membrane = min(1.0, max(0.0, state.membrane_permeability))
    atp = getattr(organism, "atp_state", None)

    for spec in config.materials:
        allow = False
        if spec.kind == "nutrient":
            allow = (did_eat and config.eat_absorbs_nutrients) or config.passive_nutrient_uptake
        elif spec.kind == "toxin":
            allow = config.toxin_passive_uptake
        elif spec.kind == "signal":
            allow = config.signal_passive_uptake
        elif spec.kind in {"catalyst", "intermediate", "waste"}:
            allow = did_eat or config.passive_nutrient_uptake
        if not allow:
            continue
        available = _local_or_pool_amount(
            spec.name, position, working_pools, working_grids, config
        )
        if available <= 0:
            continue
        gate = membrane * spec.permeability
        take = round(min(available, config.uptake_rate) * gate, 10)
        if take <= 0:
            continue
        _debit_local_or_pool(spec.name, position, take, working_pools, working_grids, config)
        state.intracellular[spec.name] = round(state.intracellular.get(spec.name, 0.0) + take, 10)
        state.cumulative_absorbed[spec.name] = round(
            state.cumulative_absorbed.get(spec.name, 0.0) + take, 10
        )
        events.append(
            MaterialEvent(
                tick=tick,
                event_type="uptake",
                material=spec.name,
                amount=take,
                organism_id=str(getattr(organism, "id", "")),
                position=position,
                metadata={"kind": spec.kind, "membrane_permeability": membrane},
            )
        )
        if spec.energy_yield > 0 and atp is not None:
            credit = round(take * spec.energy_yield, 10)
            if credit > 0:
                atp.credit_runtime(
                    credit,
                    tick=tick,
                    organism_id=str(getattr(organism, "id", "")),
                    codon="000",
                    action="MATERIAL_ABSORB",
                    reason="material_energy_yield",
                )
                state.atp_from_materials = round(state.atp_from_materials + credit, 10)
                if config.merit_from_energy_yield:
                    merit_scale = float(spec.effect_coefficients.get("merit_per_unit", 1.0))
                    state.merit_from_materials = round(
                        state.merit_from_materials + take * merit_scale, 10
                    )
        if spec.toxicity > 0 and atp is not None:
            drain = round(take * spec.toxicity, 10)
            payable = min(atp.runtime_available, drain)
            if payable > 0:
                atp.debit_runtime(
                    payable,
                    tick=tick,
                    organism_id=str(getattr(organism, "id", "")),
                    codon="000",
                    action="MATERIAL_TOXIN",
                    reason="material_toxicity",
                )
                state.atp_drained_by_toxins = round(state.atp_drained_by_toxins + payable, 10)
                events.append(
                    MaterialEvent(
                        tick=tick,
                        event_type="toxin_drain",
                        material=spec.name,
                        amount=payable,
                        organism_id=str(getattr(organism, "id", "")),
                        position=position,
                    )
                )
        if spec.kind == "toxin" and spec.lethal_toxicity_threshold > 0:
            if state.intracellular.get(spec.name, 0.0) >= spec.lethal_toxicity_threshold:
                state.toxin_lethal = True
                if atp is not None and atp.runtime_available > 0:
                    atp.debit_runtime(
                        atp.runtime_available,
                        tick=tick,
                        organism_id=str(getattr(organism, "id", "")),
                        codon="000",
                        action="MATERIAL_TOXIN",
                        reason="material_toxicity_lethal",
                    )
                events.append(
                    MaterialEvent(
                        tick=tick,
                        event_type="toxin_lethal",
                        material=spec.name,
                        amount=state.intracellular.get(spec.name, 0.0),
                        organism_id=str(getattr(organism, "id", "")),
                        position=position,
                    )
                )

    if config.excretion_rate > 0:
        for name, amount in list(state.intracellular.items()):
            spec = config.spec_by_name().get(name)
            if spec is None or spec.kind not in {"waste", "intermediate"}:
                continue
            dump = round(amount * config.excretion_rate, 10)
            if dump <= 0:
                continue
            state.intracellular[name] = round(amount - dump, 10)
            if state.intracellular[name] <= 0:
                state.intracellular.pop(name, None)
            state.cumulative_excreted[name] = round(
                state.cumulative_excreted.get(name, 0.0) + dump, 10
            )
            _credit_local_or_pool(name, position, dump, working_pools, working_grids, config)
            events.append(
                MaterialEvent(
                    tick=tick,
                    event_type="excrete",
                    material=name,
                    amount=dump,
                    organism_id=str(getattr(organism, "id", "")),
                    position=position,
                )
            )
    return events


def catalyst_amount_for_reaction(
    reaction: MaterialReactionSpec,
    *,
    pools: Mapping[str, float],
    grids: Mapping[str, Mapping[tuple[int, int], float]],
    organisms: Sequence[Any],
    position: tuple[int, int] | None,
) -> float:
    if not reaction.catalyst:
        return 1.0
    total = float(pools.get(reaction.catalyst, 0.0))
    if position is not None:
        total += float(grids.get(reaction.catalyst, {}).get(position, 0.0))
    for organism in organisms:
        state = getattr(organism, "materials_state", None)
        if isinstance(state, MaterialsOrganismState):
            total += float(state.intracellular.get(reaction.catalyst, 0.0))
    return total


def step_materials(
    state: MaterialsState,
    config: MaterialsConfig,
    *,
    tick: int,
    consumed: Mapping[str, float] | None = None,
    organisms: Sequence[Any] = (),
    world: World2D | None = None,
) -> MaterialsStepResult:
    """Advance named-material chemostat, CRN, diffusion, and decay one tick.

    Order: consumed (already applied during organism coupling) → reactions →
    unused outflow then inflow (Avida RESOURCE / Novick–Szilard) → decay →
    diffusion. Does not mutate World2D resource cells (lumen food stays Phase A).
    """

    env_trace = Trace()
    events: list[MaterialEvent] = []
    consumed_map = {key: float(value) for key, value in dict(consumed or {}).items()}
    pools = dict(state.pools)
    grids = {name: dict(cells) for name, cells in state.grids.items()}
    inflow_applied: dict[str, float] = {}
    outflow_removed: dict[str, float] = {}
    reacted: dict[str, float] = {}
    autocatalytic_extent = 0.0
    cumulative_inflow = dict(state.cumulative_inflow)
    cumulative_outflow = dict(state.cumulative_outflow)
    cumulative_consumed = dict(state.cumulative_consumed)
    cumulative_reacted = dict(state.cumulative_reacted)

    for name, used in consumed_map.items():
        cumulative_consumed[name] = round(cumulative_consumed.get(name, 0.0) + used, 10)

    fire_local = config.uses_local_patches and any(
        amount > 0 for cells in grids.values() for amount in cells.values()
    )
    if config.reactions and fire_local:
        positions = sorted({pos for cells in grids.values() for pos in cells})
        if not positions and config.patch_cells:
            positions = list(config.patch_cells)
        for position in positions:
            cell_amounts = {
                spec.name: grids.get(spec.name, {}).get(position, 0.0)
                for spec in config.materials
            }
            for reaction in config.reactions:
                catalyst = catalyst_amount_for_reaction(
                    reaction,
                    pools=pools,
                    grids=grids,
                    organisms=organisms,
                    position=position,
                )
                new_amounts, extent = apply_stoichiometric_reaction(
                    cell_amounts,
                    reaction,
                    catalyst_amount=catalyst,
                    require_catalyst=config.catalyst_enables_reactions and bool(reaction.catalyst),
                )
                if extent <= 0:
                    continue
                cell_amounts = new_amounts
                reacted[reaction.name] = round(reacted.get(reaction.name, 0.0) + extent, 10)
                if reaction.autocatalytic:
                    autocatalytic_extent = round(autocatalytic_extent + extent, 10)
                events.append(
                    MaterialEvent(
                        tick=tick,
                        event_type="reaction",
                        material=reaction.name,
                        amount=extent,
                        position=position,
                        metadata={"autocatalytic": reaction.autocatalytic},
                    )
                )
                env_trace.append_world_event(
                    _world_event(
                        WORLD_EVENT_MATERIAL_REACTION,
                        tick=tick,
                        sequence=env_trace.next_sequence(),
                        amount=extent,
                        reason="material_reaction",
                        metadata={
                            "reaction": reaction.name,
                            "autocatalytic": reaction.autocatalytic,
                        },
                        position=position,
                    )
                )
            for name, amount in cell_amounts.items():
                grids.setdefault(name, {})
                if amount > 0:
                    grids[name][position] = amount
                else:
                    grids[name].pop(position, None)
    elif config.reactions and config.uses_global_pool:
        # Local CRN already fired for global_and_local; pool-only mode fires here.
        for reaction in config.reactions:
            catalyst = catalyst_amount_for_reaction(
                reaction, pools=pools, grids=grids, organisms=organisms, position=None
            )
            pools, extent = apply_stoichiometric_reaction(
                pools,
                reaction,
                catalyst_amount=catalyst,
                require_catalyst=config.catalyst_enables_reactions and bool(reaction.catalyst),
            )
            if extent <= 0:
                continue
            reacted[reaction.name] = round(reacted.get(reaction.name, 0.0) + extent, 10)
            if reaction.autocatalytic:
                autocatalytic_extent = round(autocatalytic_extent + extent, 10)
            events.append(
                MaterialEvent(
                    tick=tick,
                    event_type="reaction",
                    material=reaction.name,
                    amount=extent,
                    metadata={"autocatalytic": reaction.autocatalytic, "scope": "global_pool"},
                )
            )
            env_trace.append_world_event(
                _world_event(
                    WORLD_EVENT_MATERIAL_REACTION,
                    tick=tick,
                    sequence=env_trace.next_sequence(),
                    amount=extent,
                    reason="material_reaction",
                    metadata={"reaction": reaction.name, "scope": "global_pool"},
                )
            )

    for spec in config.materials:
        used = consumed_map.get(spec.name, 0.0)
        if spec.unlimited or not config.uses_global_pool:
            used = 0.0
        new_amount, removed, added = apply_chemostat_step(
            pools.get(spec.name, spec.initial),
            inflow=0.0 if spec.unlimited else spec.inflow,
            outflow=0.0 if spec.unlimited else spec.outflow,
            consumed=used,
            unlimited=spec.unlimited,
        )
        pools[spec.name] = new_amount
        inflow_applied[spec.name] = added
        outflow_removed[spec.name] = removed
        cumulative_inflow[spec.name] = round(cumulative_inflow.get(spec.name, 0.0) + added, 10)
        cumulative_outflow[spec.name] = round(cumulative_outflow.get(spec.name, 0.0) + removed, 10)
        events.append(
            MaterialEvent(
                tick=tick,
                event_type="chemostat_update",
                material=spec.name,
                amount=new_amount,
                metadata={
                    "inflow": added,
                    "outflow_removed": removed,
                    "consumed": consumed_map.get(spec.name, 0.0),
                    "unlimited": spec.unlimited,
                },
            )
        )
        if added > 0:
            env_trace.append_world_event(
                _world_event(
                    WORLD_EVENT_MATERIAL_INFLOW,
                    tick=tick,
                    sequence=env_trace.next_sequence(),
                    amount=added,
                    reason="material_chemostat_inflow",
                    metadata={"material": spec.name},
                )
            )
        if removed > 0:
            env_trace.append_world_event(
                _world_event(
                    WORLD_EVENT_MATERIAL_OUTFLOW,
                    tick=tick,
                    sequence=env_trace.next_sequence(),
                    amount=removed,
                    reason="material_chemostat_outflow",
                    metadata={"material": spec.name},
                )
            )

    if config.uses_local_patches:
        width = 6
        height = 4
        walls: set[tuple[int, int]] = set()
        if world is not None:
            width = world.width
            height = world.height
            walls = set(world.walls)
        for spec in config.materials:
            cells = dict(grids.get(spec.name, {}))
            decay = spec.decay_rate if spec.decay_rate > 0 else config.decay_rate
            if decay > 0 and cells:
                cells = decay_local_patches(cells, rate=decay)
                events.append(
                    MaterialEvent(
                        tick=tick,
                        event_type="decay",
                        material=spec.name,
                        amount=round(sum(cells.values()), 10),
                        metadata={"rate": decay},
                    )
                )
            move = spec.diffusion_rate if spec.diffusion_rate > 0 else config.diffusion_rate
            move = round(move * (1.0 - spec.viscosity), 10)
            if move > 0 and cells:
                cells = diffuse_local_patches(
                    cells, width=width, height=height, rate=move, walls=walls
                )
                events.append(
                    MaterialEvent(
                        tick=tick,
                        event_type="diffusion",
                        material=spec.name,
                        amount=round(sum(cells.values()), 10),
                        metadata={"rate": move, "viscosity": spec.viscosity},
                    )
                )
            grids[spec.name] = cells

    for name, extent in reacted.items():
        cumulative_reacted[name] = round(cumulative_reacted.get(name, 0.0) + extent, 10)

    patch_total = {
        name: round(sum(cells.values()), 10)
        for name, cells in grids.items()
        if any(amount > 0 for amount in cells.values())
    }
    patch_cells = len({pos for cells in grids.values() for pos in cells})
    snapshot = MaterialsSnapshot(
        tick=tick,
        pools=dict(sorted(pools.items())),
        patch_total=dict(sorted(patch_total.items())),
        patch_cells=patch_cells,
        reacted=dict(sorted(reacted.items())),
        inflow_applied=inflow_applied,
        outflow_removed=outflow_removed,
        consumed=dict(sorted(consumed_map.items())),
        autocatalytic_extent=autocatalytic_extent,
    )
    new_state = MaterialsState(
        tick=tick,
        pools=pools,
        grids=grids,
        cumulative_inflow=cumulative_inflow,
        cumulative_outflow=cumulative_outflow,
        cumulative_consumed=cumulative_consumed,
        cumulative_reacted=cumulative_reacted,
    )
    return MaterialsStepResult(
        state=new_state,
        events=tuple(events),
        snapshot=snapshot,
        world_events=env_trace.world_events,
    )


def summarize_materials_observation(
    result: object,
    *,
    config: MaterialsConfig | None = None,
) -> MaterialsObservation:
    if result is None:
        raise TypeError("summarize_materials_observation requires a run result, not None.")
    if not hasattr(result, "ticks"):
        raise TypeError(
            "summarize_materials_observation expected an object with a ticks collection."
        )
    ticks = result.ticks
    snapshots = snapshots_from_generation_results(ticks)
    events: list[MaterialEvent] = []
    for tick in ticks:
        generation = getattr(tick, "generation_result", None)
        records = ()
        if generation is not None:
            records = getattr(generation, "materials_records", ()) or ()
        else:
            records = getattr(tick, "materials_records", ()) or ()
        for record in records:
            if isinstance(record, MaterialEvent):
                events.append(record)
    pool_series: dict[str, list[float]] = {}
    materials_seen: list[str] = []
    for snapshot in snapshots:
        for name, amount in snapshot.pools.items():
            pool_series.setdefault(name, []).append(amount)
            materials_seen.append(name)
    uptake = sum(1 for event in events if event.event_type == "uptake")
    toxin_drain = sum(1 for event in events if event.event_type in {"toxin_drain", "toxin_lethal"})
    reactions = sum(1 for event in events if event.event_type == "reaction")
    auto_total = round(sum(snapshot.autocatalytic_extent for snapshot in snapshots), 10)
    coexistence = None
    last_state = None
    for tick in reversed(tuple(ticks)):
        generation = getattr(tick, "generation_result", None)
        population = None
        if generation is not None:
            population = getattr(generation, "population", None)
        if population is not None:
            last_state = getattr(population, "materials", None)
            if isinstance(last_state, MaterialsState):
                break
    if isinstance(last_state, MaterialsState) and "A" in last_state.pools and "B" in last_state.pools:
        coexistence = measure_spatial_coexistence(last_state, material_a="A", material_b="B")
    config_digest = config.digest() if config is not None else ""
    if not config_digest:
        spec = getattr(result, "spec", None)
        population_configs = None if spec is None else getattr(spec, "population_configs", None)
        mats = None
        if population_configs is not None:
            mats = getattr(population_configs, "materials", None)
        if mats is not None and getattr(mats, "enabled", False):
            config_digest = mats.digest()
    run_digest = ""
    digest_fn = getattr(result, "digest", None)
    if callable(digest_fn):
        run_digest = str(digest_fn())
    return MaterialsObservation(
        materials_config_digest=config_digest,
        trajectory_digest=materials_trajectory_digest(snapshots),
        ticks=len(snapshots),
        material_events=len(events),
        unique_materials=tuple(dict.fromkeys(materials_seen)),
        pool_series={key: tuple(values) for key, values in pool_series.items()},
        uptake_events=uptake,
        toxin_drain_events=toxin_drain,
        reaction_events=reactions,
        autocatalytic_extent_total=auto_total,
        spatial_coexistence=coexistence,
        replay_digest=run_digest,
    )


def build_materials_evidence_pack(
    result: object,
    *,
    config: MaterialsConfig | None = None,
    binding_schema: MaterialBindingSchema | None = None,
) -> MaterialsEvidencePack:
    observation = summarize_materials_observation(result, config=config)
    run_digest = observation.replay_digest
    return MaterialsEvidencePack(
        observation=observation,
        binding_schema=binding_schema or MaterialBindingSchema(),
        run_digest=run_digest,
    )


def evaluate_materials_claim(pack: MaterialsEvidencePack) -> ClaimDecision:
    """Always ceiling ``runtime_observation``. Realistic-chemistry claims stay blocked."""

    gate = ScientificClaimGate()
    for blocked_name in (
        "realistic_chemistry_proved",
        "wet_lab_equivalent",
        "kegg_solver_equivalent",
    ):
        blocked = gate.decide(ClaimRequest(blocked_name, {}))
        if blocked.allowed:
            raise ConfigurationError(f"ClaimGate must not allow {blocked_name}.")
    return gate.decide(
        ClaimRequest(
            "runtime_observation",
            {
                "materials_records": pack.observation.material_events > 0
                or pack.observation.ticks > 0
            },
            manifest_digest=pack.digest,
            evidence_digests=(pack.digest, pack.run_digest) if pack.run_digest else (pack.digest,),
        )
    )


def _local_or_pool_amount(
    name: str,
    position: tuple[int, int],
    pools: Mapping[str, float],
    grids: Mapping[str, Mapping[tuple[int, int], float]],
    config: MaterialsConfig,
) -> float:
    local = float(grids.get(name, {}).get(position, 0.0))
    if config.uses_local_patches and local > 0:
        return local
    if config.uses_global_pool:
        return float(pools.get(name, 0.0))
    return local


def _debit_local_or_pool(
    name: str,
    position: tuple[int, int],
    amount: float,
    pools: dict[str, float],
    grids: dict[str, dict[tuple[int, int], float]],
    config: MaterialsConfig,
) -> None:
    remaining = amount
    if config.uses_local_patches:
        cells = grids.setdefault(name, {})
        local = cells.get(position, 0.0)
        take = min(local, remaining)
        if take > 0:
            leftover = round(local - take, 10)
            if leftover > 0:
                cells[position] = leftover
            else:
                cells.pop(position, None)
            remaining = round(remaining - take, 10)
    if remaining > 0 and config.uses_global_pool:
        pool = pools.get(name, 0.0)
        take = min(pool, remaining)
        pools[name] = round(pool - take, 10)


def _credit_local_or_pool(
    name: str,
    position: tuple[int, int],
    amount: float,
    pools: dict[str, float],
    grids: dict[str, dict[tuple[int, int], float]],
    config: MaterialsConfig,
) -> None:
    if config.uses_local_patches:
        cells = grids.setdefault(name, {})
        cells[position] = round(cells.get(position, 0.0) + amount, 10)
        return
    pools[name] = round(pools.get(name, 0.0) + amount, 10)


def _world_event(
    event_type: str,
    *,
    tick: int,
    sequence: int,
    amount: float = 0.0,
    reason: str = "",
    metadata: dict[str, JsonValue] | None = None,
    position: tuple[int, int] | None = None,
) -> WorldEvent:
    return WorldEvent(
        schema_version=1,
        step=tick,
        sequence=sequence,
        event_type=event_type,
        position=position,
        source="materials",
        reason=reason,
        amount=amount,
        metadata=dict(metadata or {}),
    )


def _set_finite(
    obj: object,
    field_name: str,
    value: float,
    *,
    probability: bool = False,
    name: str | None = None,
) -> None:
    object.__setattr__(
        obj,
        field_name,
        require_finite_float(
            name or field_name, value, non_negative=True, probability=probability
        ),
    )


def _finite_amount_map(values: Mapping[str, float], name: str) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, value in values.items():
        if not key:
            raise ConfigurationError(f"{name} keys must be non-empty.")
        normalized[str(key)] = require_finite_float(f"{name}.{key}", value, non_negative=True)
    return dict(sorted(normalized.items()))


def _float_map(data: Mapping[str, JsonValue], key: str) -> dict[str, float]:
    raw = data.get(key, {})
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ConfigurationError(f"{key} must be an object.")
    out: dict[str, float] = {}
    for item_key, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ConfigurationError(f"{key} values must be numeric.")
        out[str(item_key)] = require_finite_float(
            f"{key}.{item_key}", float(value), non_negative=True
        )
    return out


def _bool(data: Mapping[str, JsonValue], key: str, default: bool) -> bool:
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{key} must be a boolean.")
    return value


def _float(data: Mapping[str, JsonValue], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ConfigurationError(f"{key} must be numeric.")
    return require_finite_float(key, value, non_negative=True)


def _int(data: Mapping[str, JsonValue], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{key} must be an integer.")
    return int(value)


def _str(data: Mapping[str, JsonValue], key: str, default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str):
        if default is not None and key not in data:
            return default
        raise ConfigurationError(f"{key} must be a string.")
    return value
