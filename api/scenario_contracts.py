"""Research plans are first-class, auditable inputs, not CPI-shaped placeholders."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import date


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid',allow_inf_nan=False,strict=True)


class ResearchSource(Strict):
    title: str
    url: str = Field(pattern=r'^https?://')
    publication_date: str | None
    excerpt: str


class AnalogueCandidate(Strict):
    date: str
    event: str
    source_url: str


class ResearchExtraction(Strict):
    status: Literal['ready','needs_clarification']
    reason: str | None
    requested_date: str | None
    horizon_sessions: int = Field(ge=1,le=65)
    title: str
    hypothesis: str
    analogues: list[AnalogueCandidate] = Field(max_length=5)
    sources: list[ResearchSource] = Field(max_length=12)

    @model_validator(mode='after')
    def valid_day(self):
        if self.status=='ready':
            if self.requested_date is None: raise ValueError('Date required')
            date.fromisoformat(self.requested_date)
        return self


class ScenarioDriver(Strict):
    feature: str
    operation: Literal['set','add','multiply']
    value: float
    transition_sessions: int = Field(ge=1,le=65)
    duration_sessions: int | None = Field(default=None,ge=1,le=65)
    recovery_sessions: int = Field(default=0,ge=0,le=65)
    basis: Literal['user_assumption','historical_analogue','llm_hypothesis']
    rationale: str
    source_urls: list[str]


class NumericalPlan(Strict):
    drivers: list[ScenarioDriver] = Field(min_length=1,max_length=8)
    explanation: str
    limitations: list[str]


class FeatureChange(Strict):
    feature: str
    start: float
    end: float
    change: float


class AnalogueMeasurement(Strict):
    event: str
    source_url: str
    event_date: str
    effective_date: str
    end_date: str
    sessions: int
    market_return_percent: float
    realized_daily_volatility_percent: float
    worst_close_return_percent: float
    feature_changes: list[FeatureChange]
    method: str


class ScenarioPlan(Strict):
    requested_date: str
    effective_date: str
    horizon_sessions: int = Field(ge=1,le=65)
    title: str
    hypothesis: str
    drivers: list[ScenarioDriver]
    explanation: str
    sources: list[ResearchSource]
    analogues: list[AnalogueMeasurement]
    limitations: list[str]
    research_model: str
    research_id: str
    dataset_version: str
    web_search_used: bool
