"""Shared wire contract v1. No routes, database or model calls yet."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class InterpretRequest(Contract):
    text: str
    mode: Literal["add", "replace"]
    selected_prompt_id: str | None
    playhead: str | None
    expected_revision: int = Field(ge=0)


class CommitRequest(Contract):
    draft_id: str
    expected_revision: int = Field(ge=0)
    request_id: str


class Prompt(Contract):
    id: str
    display_number: int = Field(ge=1)
    text: str
    date_precision: Literal["day", "year", "interval"]
    requested_start: str
    requested_end: str | None
    effective_start: str
    effective_end: str | None
    scope: Literal["release", "interval", "recurring"]
    operation: Literal["set", "add_pp", "carry"]
    value: float | None
    unit: Literal["percent", "percentage_points"]
    reference: str | None
    status: Literal["supported", "unsupported"]


class Point(Contract):
    date: str
    kind: Literal["observed", "simulated", "gap"]
    value: float | None
    q10: float | None
    q90: float | None
    engine: str | None
    segment_id: str | None


class Series(Contract):
    target_id: str
    base_date: str
    base_value: float
    unit: Literal["index"]
    frequency: Literal["trading_session"]
    points: list[Point]


class Evidence(Contract):
    id: str
    title: str
    url: str
    publication_time: str
    passage_locator: str


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
    source_ids: list[str]


class Panel(Contract):
    summary: str
    hypotheses: list[str]
    evidence: list[Evidence]
    impacts: list[Impact]
    horizon: str
    comparison: str | None
    engine: str
    support_count: int = Field(ge=0)
    status: Literal["supported", "unsupported"]


class RunResponse(Contract):
    contract_version: Literal["1"]
    data_label: str
    timeline_id: str
    revision: int = Field(ge=0)
    parent_revision: int | None
    changed_from: str | None
    replace_through: str | None
    series_mode: Literal["full", "suffix"]
    prompts: list[Prompt]
    series: Series
    panels: dict[str, Panel]


class Problem(Contract):
    status: Literal["needs_clarification", "unsupported", "conflict", "invalid", "unavailable"]
    reason: str
    choices: list[str]


class ContractBundle(Contract):
    """Export root, not an HTTP payload."""
    interpret_request: InterpretRequest
    commit_request: CommitRequest
    run: RunResponse
    problem: Problem
