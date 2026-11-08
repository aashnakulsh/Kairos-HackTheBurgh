"""Chronological five-session diagnostics; actual outcomes enter scoring only."""
import numpy as np
import pandas as pd
from api.contracts import ForecastRequest, FutureRow
from data.real_market import UnsupportedInput, instant


class EvaluationInputs:
    """A fold fixed one second before one original publication."""
    def __init__(self, inputs, published_at):
        self.inputs = inputs
        self.prices, self.releases, self.schedule = inputs.prices, inputs.releases, inputs.schedule
        self.cutoff = pd.Timestamp(published_at) - pd.Timedelta(seconds=1)
        if self.cutoff > pd.Timestamp(inputs.manifest["cutoff"]):
            raise UnsupportedInput("Evaluation cutoff exceeds frozen historical prices")

    def request(self, cpi_percent, model_version):
        manifest = self.inputs.manifest
        future = self.schedule[self.schedule.open > self.cutoff].head(5).date.tolist()
        if len(future) != 5:
            raise UnsupportedInput("Five future exchange sessions required")
        return ForecastRequest(target_id="SPY", segment_id="evaluation-" + future[0],
            base_date=manifest["base_date"], base_value=manifest["base_value"],
            evidence_cutoff=instant(self.cutoff), dataset_version=manifest["dataset_version"],
            model_version=model_version, history=self.inputs.historical_rows(self.cutoff),
            future=[FutureRow(date=d, cpi_percent=cpi_percent, release_indicator=int(i == 0))
                    for i, d in enumerate(future)], assumptions=manifest["assumptions"] + [
                "Evaluation conditions on the subsequently published CPI as an explicit scenario, not a known input.",
                "Chronological diagnostic, not a preregistered or leakage-free held-out backtest."])


def score(points, actuals):
    if [p.date for p in points] != [r["date"] for r in actuals] or not points:
        raise UnsupportedInput("Scoring dates must match forecast dates exactly")
    actual = np.array([r["level"] for r in actuals], dtype=float)
    bands = np.array([[p.q10, p.value, p.q90] for p in points], dtype=float)
    if not np.isfinite(actual).all() or not np.isfinite(bands).all():
        raise UnsupportedInput("Nonfinite scoring inputs")
    return dict(steps=len(points), mean_absolute_index_error=float(np.mean(abs(bands[:, 1] - actual))),
                interval_coverage=float(np.mean((actual >= bands[:, 0]) & (actual <= bands[:, 2]))),
                mean_interval_width=float(np.mean(bands[:, 2] - bands[:, 0])))
