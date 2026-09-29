"""Instrument check: costless sex must persist; costly sex must decline; parasite must engage."""

from sex_arms import run_arm

CASES = (
    ("asex_noparasite", dict(mode="asex", parasite=False, cost_ratio=1.0)),
    ("sex_costless_noparasite", dict(mode="sex", parasite=False, cost_ratio=1.0)),
    ("sex_cost_noparasite", dict(mode="sex", parasite=False, cost_ratio=2.0)),
    ("sex_costless_parasite", dict(mode="sex", parasite=True, cost_ratio=1.0)),
    ("sex_cost_parasite", dict(mode="sex", parasite=True, cost_ratio=2.0)),
    ("sex_cost_ledger_parasite", dict(mode="sex", parasite=True, cost_ratio=2.0, delta=0.5)),
)

for tag, kwargs in CASES:
    row = run_arm(6000, generations=300, **kwargs)
    print(
        f"{tag:<26} final={row['sexual_final']:.4f} auc={row['sexual_auc']:.4f} "
        f"extinct_at={row['extinction_generation']:>4} infected={row['infected_mean']:.3f} "
        f"div={row['diversity_final']:.0f} rho={row['rho']:.3f} ledger={row['ledger_residual']:.1e}",
        flush=True,
    )
