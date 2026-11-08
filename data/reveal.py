"""Explicit post-forecast actuals reader; never imported by inference modules."""
import json
from pathlib import Path
import pandas as pd
from api.contracts import RevealResponse
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


def reveal_run(root, run):
    """Read actuals for the requested immutable revision; never writes timeline state."""
    root = Path(root)
    version = run["dataset_version"]
    if Path(version).name != version or version in {".", ".."}:
        raise UnsupportedInput("Invalid snapshot name")
    manifest = json.loads((root / "processed" / version / "manifest.json").read_text())
    if (manifest["dataset_version"] != version or manifest["base_date"] != run["series"]["base_date"]
        or manifest["base_value"] != run["series"]["base_value"]):
        raise UnsupportedInput("Reveal basis does not match saved forecast")
    dates = [p["date"] for p in run["series"]["points"] if p["kind"] == "simulated"]
    if not dates:
        raise UnsupportedInput("Commit a forecast before revealing actual history")
    path = root / "reveal" / version / "spy_actuals.parquet"
    if digest(path) != manifest["reveal_sha256"]:
        raise UnsupportedInput("Reveal hash mismatch")
    table = pd.read_parquet(path).set_index("date")
    points, availability = [], []
    for day in dates:
        value = None
        if day in table.index:
            row = table.loc[day]
            value = float(row.level)
            availability.append(row.available_at)
        points.append(dict(date=day, kind="gap" if value is None else "observed", value=value,
                           q10=None, q90=None, engine=None, segment_id=None))
    sources = []
    if availability:
        sources.append(dict(id="iex-" + manifest["reveal_sha256"][:16],
            title="SPY IEX close proxies; publication time represents modeled bar-end availability",
            url="https://hfdatalibrary.com/pages/download", publication_time=max(availability),
            passage_locator=f"SPY_raw_1min.parquet, sessions {dates[0]} through {dates[-1]}; derived SHA256 {manifest['reveal_sha256']}"))
    return RevealResponse(timeline_id=run["timeline_id"], revision=run["revision"],
        data_label="Actual historical IEX close proxies — local research; gaps are not filled",
        series=dict(target_id=run["series"]["target_id"], base_date=run["series"]["base_date"],
            base_value=run["series"]["base_value"], unit="index", frequency="trading_session", points=points),
        sources=sources, attribution="HF Data Library, Ahmed Elkassabgi. Data provided for free by IEX. "
            "https://www.iex.io/legal/hist-data-terms. Last-minute close proxies; bar-end availability assumed. "
            "Local academic research; public display and redistribution unreviewed.").model_dump()
