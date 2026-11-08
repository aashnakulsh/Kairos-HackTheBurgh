"""Replaceable numerical boundary. Arithmetic below is ONLY a synthetic test double."""
from decimal import Decimal
from typing import Protocol
from api.contracts import ForecastRequest, ForecastResult, Point

LABEL = "Synthetic example — not market data or a real forecast"


class NumericalAdapter(Protocol):
    model_version: str

    def forecast_segment(self, request: ForecastRequest) -> ForecastResult: ...


class SyntheticAdapter:
    model_version = "synthetic-arithmetic-v1"

    def forecast_segment(self, request):
        level = Decimal(str(request.history[-1].level))
        points = []
        for row in request.future:
            level += Decimal(str(row.cpi_percent))
            points.append(Point(date=row.date, kind="simulated", value=float(level),
                q10=float(level - 1), q90=float(level + 1), engine="synthetic",
                segment_id=request.segment_id))
        return ForecastResult(status="supported", reason=None, engine="synthetic",
            model_version=self.model_version, support_count=0, points=points,
            assumptions=[LABEL, "Bands conditional on the preceding simulated median"])
