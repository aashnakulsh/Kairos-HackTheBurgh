"""Optional offline CPU chronological diagnostics, with separately loaded outcomes."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.real_market import MarketInputs, UnsupportedInput
from data.reveal import read_reveal
from training.baseline import EmpiricalBaseline
from training.chronos_adapter import ChronosAdapter
from training.evaluation import EvaluationInputs, score


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", type=Path, default=Path("data/local"))
    p.add_argument("--dataset-version", required=True)
    p.add_argument("--from-date", default="2024-01-01")
    p.add_argument("--through-date", default="2025-06-11")
    p.add_argument("--baseline-only", action="store_true")
    args = p.parse_args()
    inputs = MarketInputs(args.data_dir / "processed" / args.dataset_version)
    records, pipeline = [], None
    for release in inputs.releases.itertuples(index=False):
        day = release.published_at[:10]
        if not args.from_date <= day <= args.through_date:
            continue
        fold = EvaluationInputs(inputs, release.published_at)
        adapters = [EmpiricalBaseline(fold, mode) for mode in ("reference", "analogue")]
        if not args.baseline_only:
            adapters.append(ChronosAdapter(fold, pipeline=pipeline))
        for adapter in adapters:
            record = dict(publication_date=day, scenario_cpi=float(release.cpi_percent), engine=adapter.engine)
            try:
                request = fold.request(float(release.cpi_percent), adapter.model_version)
                result = adapter.forecast_segment(request)
                if isinstance(adapter, ChronosAdapter):
                    pipeline = adapter._pipeline
                record.update(result=result.model_dump(), evidence_cutoff=request.evidence_cutoff,
                              history_start=request.history[0].date, history_sessions=len(request.history))
                if result.status == "supported":
                    # Actuals are deliberately read only after the forecast has completed.
                    actuals = read_reveal(args.data_dir, args.dataset_version, [p.date for p in result.points])
                    record["metrics"] = score(result.points, actuals)
            except UnsupportedInput as exc:
                record["unsupported_reason"] = str(exc)
            records.append(record)
            print(day, adapter.engine, record.get("metrics", record.get("unsupported_reason", record.get("result", {}).get("reason"))))
    report = dict(dataset_version=args.dataset_version, records=records,
                  disclosure="Descriptive chronological diagnostic; current split-adjusted price vintage and pretrained weights may contain later information. Conditional on factual CPI scenario. Overlapping outcome windows are not independent.")
    output = args.data_dir / "results" / args.dataset_version / "evaluation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(output)


if __name__ == "__main__":
    main()
