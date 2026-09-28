def _pressure_from_ecology(eco: Mapping[str, float], *, generation_index: int) -> float:
    """Shared realised antagonist pressure from closed-loop ecology (not smoke RNG)."""

    scale = ecology_scale(eco)
    drive = (
        0.35 * math.tanh(float(eco.get("mean_atp", 0.0)) / 8.0)
        + 0.25 * math.tanh(float(eco.get("n_alive", 0.0)) / 4.0)
        + 0.15 * math.sin(float(eco.get("resource_loc_fp", 0.0)) / 13.0)
        + 0.10 * scale
    )
    return float((0.2 * generation_index + drive * math.pi) % (2.0 * math.pi))
