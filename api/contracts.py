"""Canonical handoff v1. Calendar, rights and persistence need service validation."""
from datetime import date, datetime
from typing import Annotated, Literal
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator


def valid_date(value: str) -> str:
    date.fromisoformat(value)
    return value


def valid_instant(value: str) -> str:
    if datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return value


Date = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$"), AfterValidator(valid_date)]
Instant = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}T.*(Z|[+-]\d{2}:\d{2})$"), AfterValidator(valid_instant)]
ID = Annotated[str, Field(min_length=1)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class Viewport(Contract):
    start_year: int = Field(ge=1, le=9999)
    end_year: int = Field(ge=1, le=9999)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_year < self.start_year:
            raise ValueError("Reversed viewport")
        return self


class InterpretRequest(Contract):
    text: str = Field(min_length=1, max_length=10000)
    mode: Literal["add", "replace"]
    selected_prompt_id: ID | None = None
    playhead: Date | None = None
    expected_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def selection(self):
        if not self.text.strip():
            raise ValueError("Prompt must contain text")
        if (self.mode == "replace") != (self.selected_prompt_id is not None):
            raise ValueError("Only replace requires selected_prompt_id")
        return self


class CommitRequest(Contract):
    draft_id: ID
    expected_revision: int = Field(ge=0)
    request_id: ID


class CreateTimelineRequest(Contract):
    target_id: Literal["SPY"]
    request_id: ID


class Instruction(Contract):
    """Backend-validated instruction; relative expressions stay relative."""
    date_precision: Literal["day", "year", "interval"]
    requested_start: Date
    requested_end: Date | None
    effective_start: Date
    effective_end: Date | None
    effective_at: Instant
    timezone: Literal["America/New_York"]
    scope: Literal["release", "interval", "recurring"]
    release_dates: list[Date]
    operation: Literal["set", "add_pp", "carry"]
    value: float | None
    unit: Literal["percent", "percentage_points"]
    reference: ID | None

    @model_validator(mode="after")
    def meaning(self):
        if self.requested_end and self.requested_end < self.requested_start:
            raise ValueError("Reversed requested interval")
        if self.effective_end and self.effective_end < self.effective_start:
            raise ValueError("Reversed effective interval")
        if self.operation == "carry":
            if self.value is not None or self.unit != "percent" or self.reference is None:
                raise ValueError("carry requires null value, percent and reference")
        elif self.value is None:
            raise ValueError("Numeric operation requires value")
        if self.operation == "add_pp" and (self.unit != "percentage_points" or self.reference is None):
            raise ValueError("add_pp requires percentage_points and reference")
        if self.operation == "set" and (self.unit != "percent" or self.reference is not None):
            raise ValueError("set requires percent and null reference")
        if self.scope == "recurring" and not self.release_dates:
            raise ValueError("Recurring instructions need explicit release dates")
        if self.scope == "interval" and self.effective_end is None:
            raise ValueError("Interval requires an end")
        if self.release_dates != sorted(set(self.release_dates)):
            raise ValueError("Release dates must be ordered and unique")
        return self


class Prompt(Instruction):
    id: ID
    display_number: int = Field(ge=1)
    creation_order: int = Field(ge=1)
    text: str
    evidence_ids: list[ID]
    resolved_value: float | None
    status: Literal["supported", "unsupported"]


class Point(Contract):
    date: Date
    kind: Literal["observed", "simulated", "gap"]
    value: float | None
    q10: float | None
    q90: float | None
    engine: str | None
    segment_id: ID | None

    @model_validator(mode="after")
    def bands(self):
        if self.kind == "simulated":
            if None in (self.value, self.q10, self.q90) or not self.engine or not self.segment_id:
                raise ValueError("Simulated point needs median, bands, engine and segment")
            if not self.q10 <= self.value <= self.q90:
                raise ValueError("Unordered quantiles")
        else:
            if self.q10 is not None or self.q90 is not None:
                raise ValueError("Only simulated points have quantiles")
            if (self.kind == "gap") != (self.value is None):
                raise ValueError("Only gap points have null values")
        return self


class Series(Contract):
    target_id: str
    base_date: Date
    base_value: float = Field(gt=0)
    unit: Literal["index"]
    frequency: Literal["trading_session"]
    points: list[Point]

    @model_validator(mode="after")
    def ordered(self):
        dates = [p.date for p in self.points]
        if dates != sorted(set(dates)):
            raise ValueError("Points must be ordered and unique")
        return self


class DescriptionRequest(Contract):
    """Frontend forwards a complete saved segment without rounding its numbers."""
    prompt_id: ID
    forecast_points: list[Point] = Field(min_length=1, max_length=65)


class DescriptionResponse(Contract):
    timeline_id: ID
    revision: int = Field(ge=1)
    run_id: ID
    prompt_id: ID
    description: str = Field(min_length=1, max_length=6000)
    provider: Literal["openai"]
    model: ID


class Evidence(Contract):
    id: ID
    title: str
    url: str = Field(pattern=r"^https?://")
    publication_time: Instant
    passage_locator: str


class Hypothesis(Contract):
    text: str
    source_ids: list[ID]
    user_assumption: bool

    @model_validator(mode="after")
    def grounded(self):
        if not self.source_ids and not self.user_assumption:
            raise ValueError("Hypothesis requires sources or user-assumption label")
        return self


class Impact(Contract):
    name: str
    emoji: str
    exposure: Literal["direct", "indirect"]
    direction: Literal["positive", "negative", "neutral"] | None
    metric_kind: Literal["proxy_change", "index_contribution", "qualitative"]
    magnitude: float | None = Field(ge=0)
    unit: Literal["percent", "percentage_points"] | None
    comparator: str | None
    horizon: str
    method: str
    source_ids: list[ID]

    @model_validator(mode="after")
    def measurement(self):
        if self.metric_kind == "qualitative":
            if self.magnitude is not None or self.unit is not None:
                raise ValueError("Qualitative exposure has no numeric magnitude/unit")
        else:
            expected = "percent" if self.metric_kind == "proxy_change" else "percentage_points"
            if self.magnitude is None or self.unit != expected or self.direction is None or not self.comparator:
                raise ValueError("Quantified impact needs magnitude, direction, correct unit and comparator")
        return self


class Panel(Contract):
    summary: str
    hypotheses: list[Hypothesis]
    evidence: list[Evidence]
    impacts: list[Impact]
    horizon: str
    comparison: str | None
    engine: str
    support_count: int = Field(ge=0)
    status: Literal["supported", "unsupported"]

    @model_validator(mode="after")
    def citations(self):
        ids = {e.id for e in self.evidence}
        for item in [*self.hypotheses, *self.impacts]:
            if not set(item.source_ids) <= ids:
                raise ValueError("Unknown panel citation")
        return self


class RunResponse(Contract):
    contract_version: Literal["1"]
    data_label: str
    timeline_id: ID
    run_id: ID | None
    dataset_version: ID
    model_version: ID
    corpus_version: ID
    request_id: ID | None
    revision: int = Field(ge=0)
    parent_revision: int | None = Field(ge=0)
    changed_from: Date | None
    replace_through: Date | None
    series_mode: Literal["full", "suffix"]
    evidence_cutoff: Instant | None
    prompts: list[Prompt]
    series: Series
    panels: dict[str, Panel]

    @model_validator(mode="after")
    def consistent(self):
        ids = [p.id for p in self.prompts]
        if len(ids) != len(set(ids)) or set(ids) != set(self.panels):
            raise ValueError("Unique prompt IDs must match panel keys")
        if len({p.display_number for p in self.prompts}) != len(ids):
            raise ValueError("Display numbers must be unique")
        if self.revision == 0 and (self.prompts or self.parent_revision is not None):
            raise ValueError("Revision zero is empty")
        if self.revision > 0 and self.parent_revision != self.revision - 1:
            raise ValueError("Revision must advance exactly once")
        if self.series_mode == "suffix":
            if self.changed_from is None or self.replace_through is None or self.parent_revision is None:
                raise ValueError("Suffix requires boundary and parent revision")
            if any(p.date < self.changed_from for p in self.series.points):
                raise ValueError("Suffix includes an earlier point")
        if self.changed_from and self.replace_through and self.replace_through < self.changed_from:
            raise ValueError("Reversed replacement bounds")
        for point in self.series.points:
            if point.kind == "simulated" and point.segment_id not in ids:
                raise ValueError("Unknown simulated segment")
        if self.evidence_cutoff:
            cutoff = datetime.fromisoformat(self.evidence_cutoff.replace("Z", "+00:00"))
            for panel in self.panels.values():
                if any(datetime.fromisoformat(e.publication_time.replace("Z", "+00:00")) > cutoff for e in panel.evidence):
                    raise ValueError("Panel evidence exceeds frozen cutoff")
        return self


class Problem(Contract):
    status: Literal["needs_clarification", "unsupported", "conflict", "invalid", "unavailable", "not_found", "draft_expired"]
    code: str
    reason: str
    choices: list[str]
    current_revision: int | None = Field(ge=0)
    retryable: bool


class ReadyDraft(Contract):
    status: Literal["ready"]
    draft_id: ID
    timeline_id: ID
    expected_revision: int = Field(ge=0)
    mode: Literal["add", "replace"]
    selected_prompt_id: ID | None
    text: str
    expires_at: Instant
    instruction: Instruction
    warnings: list[str]


class Coverage(Contract):
    first_session: Date
    last_session: Date
    gaps: list[Date]

    @model_validator(mode="after")
    def ordered(self):
        if self.last_session < self.first_session:
            raise ValueError("Reversed coverage")
        return self


class Capabilities(Contract):
    contract_version: Literal["1"]
    mode: Literal["fixture", "live"]
    data_label: str
    targets: list[str]
    unit: Literal["index"]
    frequency: Literal["trading_session"]
    default_viewport: Viewport
    coverage: Coverage
    supported_event_families: list[str]
    default_horizon_sessions: int = Field(ge=1)
    max_horizon_sessions: int = Field(ge=1)
    max_prompts: int = Field(ge=1)
    evidence_available: bool
    display_rights: str
    fixture_presets: list[str]


class RevealResponse(Contract):
    timeline_id: ID
    revision: int = Field(ge=0)
    data_label: str
    series: Series
    sources: list[Evidence]
    attribution: str

    @model_validator(mode="after")
    def actuals_only(self):
        if any(p.kind == "simulated" for p in self.series.points):
            raise ValueError("Reveal cannot contain simulated points")
        return self


class ParsedScenario(Contract):
    """Same required nullable fields from either provider; server validates meaning."""
    status: Literal["parsed", "needs_clarification", "unsupported"]
    reason: str | None
    choices: list[str]
    date_precision: Literal["day", "year", "interval"] | None
    requested_start: Date | None
    requested_end: Date | None
    scope: Literal["release", "interval", "recurring"] | None
    release_dates: list[Date]
    operation: Literal["set", "add_pp", "carry"] | None
    value: float | None
    unit: Literal["percent", "percentage_points"] | None
    reference: ID | None

    @model_validator(mode="after")
    def complete(self):
        if self.status == "parsed":
            if None in (self.date_precision, self.requested_start, self.scope, self.operation, self.unit):
                raise ValueError("Parsed scenario requires date, scope, operation and units")
            if self.operation == "set" and (self.value is None or self.unit != "percent" or self.reference is not None):
                raise ValueError("Invalid set operation")
            if self.operation == "add_pp" and (self.value is None or self.unit != "percentage_points" or self.reference is None):
                raise ValueError("Invalid relative operation")
            if self.operation == "carry" and (self.value is not None or self.unit != "percent" or self.reference is None):
                raise ValueError("Invalid carry operation")
        elif not self.reason:
            raise ValueError("Non-parsed response requires a reason")
        return self


class HistoryRow(Contract):
    date: Date
    level: float
    kind: Literal["observed", "simulated"]
    available_at: Instant | None
    cpi_percent: float
    release_indicator: Literal[0, 1]


class FutureRow(Contract):
    date: Date
    cpi_percent: float
    release_indicator: Literal[0, 1]


class ForecastRequest(Contract):
    target_id: str
    segment_id: ID
    base_date: Date
    base_value: float = Field(gt=0)
    evidence_cutoff: Instant
    dataset_version: ID
    model_version: ID
    history: list[HistoryRow] = Field(min_length=1)
    future: list[FutureRow] = Field(min_length=1, max_length=65)
    assumptions: list[str]

    @model_validator(mode="after")
    def no_future_observations(self):
        cutoff = datetime.fromisoformat(self.evidence_cutoff.replace("Z", "+00:00"))
        for row in self.history:
            if row.kind == "observed":
                if row.date > cutoff.date().isoformat() or not row.available_at or datetime.fromisoformat(row.available_at.replace("Z", "+00:00")) > cutoff:
                    raise ValueError("Observed history must be available by frozen cutoff")
        dates = [r.date for r in self.history] + [r.date for r in self.future]
        if dates != sorted(set(dates)):
            raise ValueError("History must precede ordered, unique future sessions")
        return self


class ForecastResult(Contract):
    status: Literal["supported", "unsupported"]
    reason: str | None
    engine: str
    model_version: ID
    support_count: int = Field(ge=0)
    points: list[Point]
    assumptions: list[str]

    @model_validator(mode="after")
    def output(self):
        if self.status == "unsupported" and (self.points or not self.reason):
            raise ValueError("Unsupported result requires reason and empty points")
        if self.status == "supported" and not self.points:
            raise ValueError("Supported result needs points")
        if any(p.kind != "simulated" for p in self.points):
            raise ValueError("Forecaster produces simulated points only")
        dates = [p.date for p in self.points]
        if dates != sorted(set(dates)):
            raise ValueError("Forecast sessions must be ordered and unique")
        return self


class ContractBundle(Contract):
    """Export root, not an HTTP payload."""
    create_request: CreateTimelineRequest
    interpret_request: InterpretRequest
    commit_request: CommitRequest
    draft: ReadyDraft
    run: RunResponse
    problem: Problem
    capabilities: Capabilities
    reveal: RevealResponse
    parser: ParsedScenario
    forecast_request: ForecastRequest
    forecast_result: ForecastResult
    description_request: DescriptionRequest
    description_response: DescriptionResponse
