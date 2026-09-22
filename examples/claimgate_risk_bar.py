"""Print the committed risk-bar rows. Does not grade a device."""

from codontrace.claimgate.adapters.biomedical import biomedical_risk_bar_payload

payload = biomedical_risk_bar_payload()
print(payload["digest"])
rows = payload["rows"]
if isinstance(rows, list):
    for row in rows:
        if isinstance(row, dict):
            print(
                row["name"],
                row["claim_level"],
                row["model_risk"],
                row["met"],
                row["blocking_gaps"],
            )
