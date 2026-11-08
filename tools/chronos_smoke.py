"""Optional CPU-only host check with synthetic numbers, not the market adapter.

Run download, load and forecast separately. Backend tests never import this file.
"""
import argparse
from importlib.metadata import version
import os
from pathlib import Path

MODEL = "amazon/chronos-2"
REVISION = "29ec3766d36d6f73f0696f85560a422f50e8498c"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["download", "load", "forecast"])
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--revision", default=REVISION)
    args = parser.parse_args()
    if args.offline:
        # Set before importing the Hub or transformers.
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from huggingface_hub import snapshot_download
    snapshot = snapshot_download(MODEL, revision=args.revision,
        local_files_only=args.offline, token=False,
        allow_patterns=["config.json", "model.safetensors", "README.md"])
    print(f"Snapshot: {Path(snapshot).resolve()}")
    print(f"chronos-forecasting={version('chronos-forecasting')}; revision={args.revision}")
    if args.action == "download":
        print("PASS: weights cached; model loading and inference have NOT been checked")
        return
    from chronos import Chronos2Pipeline
    pipeline = Chronos2Pipeline.from_pretrained(snapshot, device_map="cpu", local_files_only=True)
    print("PASS: Chronos-2 loaded on CPU")
    if args.action == "load":
        return
    import numpy as np
    import pandas as pd
    # Regular artificial steps, not real exchange sessions or market observations.
    steps = np.arange(96, dtype=float)
    context = pd.DataFrame({"id": "synthetic", "timestamp": pd.date_range("2000-01-01", periods=96),
        "target": 100 + steps * 0.05 + np.sin(steps / 6)})
    result = pipeline.predict_df(context, prediction_length=5, quantile_levels=[0.1, 0.5, 0.9],
        id_column="id", timestamp_column="timestamp", target="target")
    values = result[["0.1", "0.5", "0.9"]].to_numpy()
    if values.shape != (5, 3) or not np.isfinite(values).all() or not (np.diff(values, axis=1) >= 0).all():
        raise RuntimeError("Expected exactly five finite, ordered q10/q50/q90 rows")
    print(result[["timestamp", "0.1", "0.5", "0.9"]].to_string(index=False))
    print("PASS: five synthetic steps, finite q10 <= q50 <= q90; not a market forecast")


if __name__ == "__main__":
    main()
