"""Completed CPI-release windows only; no reveal-reader import or synthetic fill."""
import numpy as np
import pandas as pd
from api.contracts import ForecastResult, Point
from training.chronos_adapter import unsupported, validate_request

FLOOR = 8
TOLERANCE_PP = 0.1


def completed_windows(prices, releases, schedule, cutoff):
    """Require preceding close, all five closes and the publication before cutoff."""
    cutoff = pd.Timestamp(cutoff)
    p = prices[pd.to_datetime(prices.available_at) <= cutoff].set_index("date")
    r = releases[pd.to_datetime(releases.published_at) <= cutoff].sort_values("published_at")
    if r.published_at.duplicated().any() or r.reference_month.duplicated().any():
        raise ValueError("Baseline requires distinct release vintages")
    windows = []
    previous = None
    for release in r.itertuples(index=False):
        period = pd.Period(release.reference_month, freq="M")
        delta = (float(release.cpi_percent - previous[0]) if previous is not None
                 and previous[1] + 1 == period else None)
        eligible = schedule[schedule.close >= pd.Timestamp(release.published_at)]
        dates = eligible.head(5).date.tolist()
        earlier = schedule[schedule.close < pd.Timestamp(release.published_at)]
        if len(dates) == 5 and not earlier.empty:
            base_date = earlier.date.iloc[-1]
            if all(d in p.index for d in [base_date, *dates]):
                values = p.loc[dates].level.to_numpy(dtype=float) / float(p.loc[base_date].level)
                if np.isfinite(values).all() and (values > 0).all():
                    windows.append(dict(date=dates[0], ratios=values,
                        delta=delta))
        previous = (release.cpi_percent, period)
    return windows


class EmpiricalBaseline:
    def __init__(self, inputs, mode="analogue"):
        if mode not in {"reference", "analogue"}:
            raise ValueError("Unknown baseline mode")
        self.inputs, self.mode = inputs, mode
        self.engine = f"empirical-{mode}"
        self.model_version = f"empirical-{mode}-five-floor8-tol0.1-v1"

    def forecast_segment(self, request):
        assumptions = list(request.assumptions) + [
            "Five-session empirical level distribution, not a causal CPI effect.",
            f"Fixed pre-evaluation floor: {FLOOR} distinct releases; analogue tolerance +/-{TOLERANCE_PP} percentage points.",
            "Reference ignores hypothetical CPI; analogue matches change from previously published reading."]
        try:
            if len(request.future) != 5 or any(r.kind != "observed" for r in request.history):
                return unsupported(self.engine, self.model_version,
                    "Baseline supports five sessions from observed history only", assumptions=assumptions)
            request = validate_request(request, self.inputs, self.model_version)
            windows = completed_windows(self.inputs.prices, self.inputs.releases,
                self.inputs.schedule, request.evidence_cutoff)
            if self.mode == "analogue":
                delta = request.future[0].cpi_percent - request.history[-1].cpi_percent
                windows = [w for w in windows if w["delta"] is not None
                           and abs(w["delta"] - delta) <= TOLERANCE_PP + 1e-12]
            assumptions.append("Eligible release dates: " + (", ".join(w["date"] for w in windows) or "none"))
            if len(windows) < FLOOR:
                return unsupported(self.engine, self.model_version,
                    f"Only {len(windows)} eligible distinct releases; {FLOOR} required. Obtain earlier CPI vintages.",
                    len(windows), assumptions)
            paths = np.stack([w["ratios"] for w in windows]) * request.history[-1].level
            bands = np.quantile(paths, [0.1, 0.5, 0.9], axis=0).T
            points = [Point(date=r.date, kind="simulated", value=float(v[1]), q10=float(v[0]), q90=float(v[2]),
                engine=self.engine, segment_id=request.segment_id) for r, v in zip(request.future, bands)]
            return ForecastResult(status="supported", reason=None, engine=self.engine,
                model_version=self.model_version, support_count=len(windows), points=points, assumptions=assumptions)
        except Exception as exc:
            return unsupported(self.engine, self.model_version, f"{type(exc).__name__}: {exc}", assumptions=assumptions)
