"""Explicit post-forecast actuals reader; never imported by inference modules."""
import json
from pathlib import Path
import pandas as pd
from data.real_market import digest, UnsupportedInput


def read_reveal(root, dataset_version, dates):
    root = Path(root)
    manifest = json.loads((root / "processed" / dataset_version / "manifest.json").read_text())
    path = root / "reveal" / dataset_version / "spy_actuals.parquet"
    if digest(path) != manifest["reveal_sha256"]:
        raise UnsupportedInput("Reveal hash mismatch")
    table = pd.read_parquet(path).set_index("date")
    if any(d not in table.index for d in dates):
        raise UnsupportedInput("Requested actual close is missing")
    return table.loc[dates].reset_index()[["date", "level", "available_at"]].to_dict("records")
