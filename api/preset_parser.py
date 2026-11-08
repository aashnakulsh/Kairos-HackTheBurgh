"""Parser boundary for later server-side OpenAI/Ollama implementations."""
from typing import Protocol
from api.contracts import InterpretRequest, ParsedScenario
from shared.fixture_service import PRESETS


class ScenarioParser(Protocol):
    def parse(self, request: InterpretRequest) -> ParsedScenario: ...


class PresetParser:
    def __init__(self, presets=None):
        self.presets = PRESETS if presets is None else presets

    def parse(self, request):
        common = dict(reason=None, choices=[], date_precision=None, requested_start=None,
            requested_end=None, scope=None, release_dates=[], operation=None,
            value=None, unit=None, reference=None)
        if request.text not in self.presets:
            return ParsedScenario(**dict(common,
                status="needs_clarification" if request.text == "Change CPI" else "unsupported",
                reason="This milestone supports the listed deterministic CPI presets only",
                choices=list(self.presets)))
        day, operation, value, reference = self.presets[request.text]
        return ParsedScenario(**dict(common, status="parsed", date_precision="day",
            requested_start=day, scope="release", release_dates=[day], operation=operation,
            value=value, unit="percentage_points" if operation == "add_pp" else "percent",
            reference=reference))
