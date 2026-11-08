"""Run the two real-data scenarios offline, optionally reveal actuals afterward."""
import argparse
import json
import os
from pathlib import Path
import sys
from time import perf_counter
from importlib.metadata import version

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.real_market import MarketInputs, DATES
from training.chronos_adapter import ChronosAdapter
from training.baseline import EmpiricalBaseline


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", type=Path, default=Path(os.environ.get("DATA_DIR", "data/local")))
    p.add_argument("--dataset-version")
    p.add_argument("--cpi", type=float, nargs="+", default=[0.4, 0.2])
    p.add_argument("--reveal", action="store_true")
    args = p.parse_args()
    # Explicit offline flags before lazy Hugging Face imports. No paid or Hub calls.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    dataset = args.dataset_version or (args.data_dir / "processed/latest.txt").read_text().strip()
    inputs = MarketInputs(args.data_dir / "processed" / dataset)
    adapter = ChronosAdapter(inputs)
    report = dict(dataset_version=dataset, scenarios=[], inference_environment={p: version(p) for p in
        ["chronos-forecasting", "torch", "transformers", "accelerate", "huggingface-hub", "numpy", "pandas"]})
    succeeded = True
    for cpi in args.cpi:
        request = inputs.request(cpi, adapter.model_version)
        started = perf_counter()
        result = adapter.forecast_segment(request)
        duration = perf_counter() - started
        scenario = dict(cpi=cpi, request=request.model_dump(), result=result.model_dump(), seconds=duration)
        print(f"CPI {cpi}%: {result.status}, {duration:.2f}s, {result.engine}")
        if result.reason:
            print(result.reason)
        for point in result.points:
            print(f"  {point.date}: q10={point.q10:.4f} q50={point.value:.4f} q90={point.q90:.4f}")
        succeeded &= result.status == "supported" and [r.date for r in result.points] == DATES
        scenario["baselines"] = {}
        for mode in ("reference", "analogue"):
            baseline = EmpiricalBaseline(inputs, mode)
            b = baseline.forecast_segment(inputs.request(cpi, baseline.model_version))
            scenario["baselines"][mode] = b.model_dump()
            print(f"  {baseline.engine}: {b.status}; count={b.support_count}; {b.reason}")
        report["scenarios"].append(scenario)
    if args.reveal:
        from data.reveal import read_reveal
        report["reveal"] = read_reveal(args.data_dir, dataset, DATES)
        print("Separate actual-history reveal:", report["reveal"])
    output = args.data_dir / "results" / dataset
    output.mkdir(parents=True, exist_ok=True)
    (output / "forecast.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Requests, responses and provenance: {output / 'forecast.json'}")
    if not succeeded:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
