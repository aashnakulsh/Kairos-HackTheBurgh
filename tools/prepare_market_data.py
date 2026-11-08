"""Audit local raw files and prepare a frozen June 11 research snapshot."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.real_market import build


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", type=Path, default=Path(os.environ.get("DATA_DIR", "data/local")))
    args = p.parse_args()
    directory, manifest = build(args.data_dir)
    print(f"Snapshot: {directory}")
    print(json.dumps(manifest["audit"], indent=2))
    print("Missing inputs:", "; ".join(manifest["missing_inputs"]))
    print("Local research snapshot prepared. The durable API uses it only with APP_MODE=research and an explicit DATASET_VERSION.")


if __name__ == "__main__":
    main()
