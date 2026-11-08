"""Offline CPU Chronos-2 boundary for the bounded, real-data June example."""
from importlib.metadata import version
from threading import Lock

import numpy as np
import pandas as pd

from api.contracts import ForecastRequest, ForecastResult, Point
from data.real_market import UnsupportedInput

MODEL = "amazon/chronos-2"
REVISION = "29ec3766d36d6f73f0696f85560a422f50e8498c"
MODEL_VERSION = f"chronos-2-2.3.2-{REVISION[:12]}-cpu-cpi-v1"


def unsupported(engine, model_version, reason, count=0, assumptions=()):
    return ForecastResult(status="unsupported", reason=reason, engine=engine,
        model_version=model_version, support_count=count, points=[], assumptions=list(assumptions))


def validate_request(request, inputs, model_version):
    # Revalidate mutable model instances and bind all numerical inputs to our snapshot.
    request = ForecastRequest.model_validate(request.model_dump())
    expected = inputs.request(request.future[0].cpi_percent, model_version)
    for key in ("target_id", "base_date", "base_value", "evidence_cutoff", "dataset_version",
                "model_version", "history", "future"):
        if getattr(request, key) != getattr(expected, key):
            raise UnsupportedInput(f"Unsupported {key}: requires the frozen June example")
    return request


def model_frames(request):
    """Daily artificial clock represents session ordinal, never calendar-day gaps."""
    clock = pd.date_range("2000-01-01", periods=len(request.history) + len(request.future), freq="D")
    past = pd.DataFrame({"item_id": "SPY", "timestamp": clock[:len(request.history)],
        "target": [r.level for r in request.history],
        "cpi_percent": [r.cpi_percent for r in request.history],
        "release_indicator": [r.release_indicator for r in request.history]})
    future = pd.DataFrame({"item_id": "SPY", "timestamp": clock[len(request.history):],
        "cpi_percent": [r.cpi_percent for r in request.future],
        "release_indicator": [r.release_indicator for r in request.future]})
    return past, future


class ChronosAdapter:
    model_version = MODEL_VERSION
    engine = "chronos-2-cpu"

    def __init__(self, inputs, pipeline=None):
        self.inputs = inputs
        self._pipeline = pipeline
        self._lock = Lock()

    def _load(self):
        if self._pipeline is None:
            if version("chronos-forecasting") != "2.3.2":
                raise UnsupportedInput("Install pinned chronos-forecasting==2.3.2")
            from huggingface_hub import snapshot_download
            from chronos import Chronos2Pipeline
            import torch
            # Bound CPU use on the shared demo host; one warmed pipeline per adapter.
            torch.set_num_threads(4)
            path = snapshot_download(MODEL, revision=REVISION, local_files_only=True, token=False,
                                     allow_patterns=["config.json", "model.safetensors", "README.md"])
            self._pipeline = Chronos2Pipeline.from_pretrained(path, device_map="cpu", local_files_only=True)
        return self._pipeline

    def forecast_segment(self, request):
        assumptions = list(request.assumptions) + [
            "Conditional statistical forecast, not a causal CPI effect or investment advice.",
            "Pretrained weights are not certified free of post-cutoff training data; not a leakage-free backtest.",
            "Only 20 historical sessions; uncertainty is model-derived and uncalibrated on this market.",
            f"Weights {MODEL}@{REVISION}; chronos-forecasting 2.3.2; CPU; session-ordinal grid.",
            "support_count=0 means no empirical analogue support count is claimed for Chronos."]
        try:
            request = validate_request(request, self.inputs, self.model_version)
            past, future = model_frames(request)
            with self._lock:
                result = self._load().predict_df(past, future_df=future,
                    prediction_length=len(request.future), quantile_levels=[0.1, 0.5, 0.9],
                    context_length=len(request.history), cross_learning=False,
                    id_column="item_id", timestamp_column="timestamp", target="target")
            # Do not repair crossing bands, drop rows, or silently fall back to arithmetic.
            result = result.sort_values("timestamp")
            if (result.timestamp.tolist() != future.timestamp.tolist()
                or set(result.item_id) != {"SPY"}):
                raise UnsupportedInput("Model output does not match the requested five steps")
            values = result[["0.1", "0.5", "0.9"]].to_numpy(dtype=float)
            if (values.shape != (len(request.future), 3) or not np.isfinite(values).all()
                or (np.diff(values, axis=1) < 0).any()):
                raise UnsupportedInput("Model returned nonfinite or unordered bands")
            points = [Point(date=row.date, kind="simulated", value=float(v[1]), q10=float(v[0]),
                            q90=float(v[2]), engine=self.engine, segment_id=request.segment_id)
                      for row, v in zip(request.future, values)]
            return ForecastResult(status="supported", reason=None, engine=self.engine,
                model_version=self.model_version, support_count=0, points=points, assumptions=assumptions)
        except Exception as exc:
            # Boundary returns an explicit failure; raw traceback remains a caller logging concern.
            return unsupported(self.engine, self.model_version, f"{type(exc).__name__}: {exc}", assumptions=assumptions)
