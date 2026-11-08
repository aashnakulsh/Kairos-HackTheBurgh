"""Bounded real-data three-prompt runtime, behind unchanged HTTP contracts.

Imported only for APP_MODE=research, so fixture users need no market dependencies.
SQLite commands remain in DurableService; this runtime builds candidates only.
"""
from copy import deepcopy
from hashlib import sha256
import json

from api.backend_errors import BackendError
from api.contracts import Capabilities, Evidence, Instruction, RunResponse
from api.preset_parser import PresetParser
from api.cpi_domain import instruction_error
from api.replay import candidate as replay_candidate
from shared.fixture_service import PRESETS
from data.real_market import CUTOFF, DATES, MarketInputs
from training.chronos_adapter import ChronosAdapter, MODEL_VERSION

LABEL = "SPY / monthly headline CPI scenarios — continuous inputs (-2% to 2%), June–August 2025; conditional Chronos-2 forecasts"



class ResearchBackend:
    label = LABEL
    def __init__(self, settings, adapter=None):
        self.inputs = MarketInputs(settings.data_dir / "processed" / settings.dataset_version)
        if self.inputs.manifest["dataset_version"] != settings.dataset_version:
            raise ValueError("Configured DATASET_VERSION disagrees with the snapshot manifest")
        self.adapter = adapter if adapter is not None else ChronosAdapter(self.inputs)
        if self.adapter.model_version != MODEL_VERSION:
            raise ValueError("Research mode requires the pinned Chronos model version")
        self.parser = PresetParser(PRESETS)
        self.sessions = self.inputs.schedule.date.tolist()
        # Validate history/calendar at startup without loading weights or predicting.
        self.seed_request = self.inputs.request(0.2, self.adapter.model_version)
        self.points = [dict(date=r.date, kind="observed", value=r.level, q10=None,
                            q90=None, engine=None, segment_id=None) for r in self.seed_request.history]
        self.evidence = []
        known = self.inputs.releases[self.inputs.releases.published_at <= CUTOFF]
        for release in known.itertuples(index=False):
            self.evidence.append(Evidence(id="bls-" + release.sha256[:16],
                title=f"BLS original CPI release for {release.reference_month}", url=release.source_url,
                publication_time=release.published_at, passage_locator=release.locator).model_dump())
        self.corpus_version = "bls-" + sha256(json.dumps(self.evidence, sort_keys=True).encode()).hexdigest()[:20]
        self.warnings = [LABEL, *self.seed_request.assumptions,
            "Continuous monthly headline CPI inputs (-2% to 2%); June 11, July 15 and August 12, 2025. Examples are optional.",
            "Actual history is a separate overlay. Empirical baseline requires sufficient earlier releases."]

    def capabilities(self):
        # v1's 'live' discriminant means real inputs/engine, not a streaming feed.
        # The label and rights field explicitly describe this local historical mode.
        return Capabilities(contract_version="1", mode="live", data_label=LABEL,
            targets=["SPY"], unit="index", frequency="trading_session",
            default_viewport=dict(start_year=2025, end_year=2025),
            coverage=dict(first_session=self.points[0]["date"], last_session="2025-08-18", gaps=[]),
            supported_event_families=["headline_cpi_mom"], default_horizon_sessions=5,
            max_horizon_sessions=65, max_prompts=3, evidence_available=bool(self.evidence),
            display_rights="Local academic/educational research; public display and redistribution unreviewed. "
                "HF Data Library; Data provided for free by IEX. https://www.iex.io/legal/hist-data-terms",
            fixture_presets=list(PRESETS)).model_dump()

    def empty(self, timeline_id):
        r = self.seed_request
        return RunResponse(contract_version="1", data_label=LABEL, timeline_id=timeline_id,
            run_id=None, dataset_version=r.dataset_version, model_version=r.model_version,
            corpus_version=self.corpus_version, request_id=None, revision=0, parent_revision=None,
            changed_from=None, replace_through=None, series_mode="full", evidence_cutoff=r.evidence_cutoff,
            prompts=[], panels={}, series=dict(target_id=r.target_id, base_date=r.base_date,
                base_value=r.base_value, unit="index", frequency="trading_session", points=deepcopy(self.points))).model_dump()

    def compatible(self, run):
        r = self.seed_request
        if (run["dataset_version"] != r.dataset_version or run["model_version"] != r.model_version
            or run["corpus_version"] != self.corpus_version or run["evidence_cutoff"] != r.evidence_cutoff
            or run["series"]["target_id"] != r.target_id or run["series"]["base_date"] != r.base_date
            or run["series"]["base_value"] != r.base_value
            or [p for p in run["series"]["points"] if p["date"] < DATES[0]] != self.points):
            raise BackendError(409, "conflict", "timeline_configuration_mismatch",
                "This timeline uses different data/model settings. Restore its original configuration or create a new timeline.",
                run["revision"])

    def instruction(self, run, request, parsed):
        if request.mode == "add" and len(run["prompts"]) >= 3:
            raise BackendError(200, "unsupported", "research_prompt_limit",
                "Three prompts are supported; select an existing prompt to replace.", run["revision"], list(PRESETS))
        error = instruction_error(parsed)
        if error:
            raise BackendError(200, "unsupported", "research_scope",
                error, run["revision"], list(PRESETS))
        if not run["prompts"] and parsed.requested_start != DATES[0]:
            raise BackendError(200, "unsupported", "research_first_fork",
                "Start with a June 11, 2025 monthly headline CPI assumption.", run["revision"], list(PRESETS)[:2])
        reference = parsed.reference
        if reference and reference.startswith("date:"):
            matches = [p for p in run["prompts"] if p["effective_start"] == reference[5:]
                       and p["id"] != request.selected_prompt_id]
            if len(matches) != 1:
                raise BackendError(200, "needs_clarification", "ambiguous_reference",
                    "That release must identify one existing earlier simulated prompt.", run["revision"])
            reference = matches[0]["id"]
        if parsed.operation != "set":
            earlier = [p for p in run["prompts"] if p["effective_start"] < parsed.requested_start
                       and p["id"] != request.selected_prompt_id]
            if not earlier or (reference != "preceding" and reference not in {p["id"] for p in earlier}):
                raise BackendError(200, "needs_clarification", "broken_reference",
                    "Relative assumptions need an earlier simulated reading. Set the first CPI level explicitly.", run["revision"])
        return Instruction(date_precision="day", requested_start=parsed.requested_start, requested_end=None,
            effective_start=parsed.requested_start, effective_end=None,
            effective_at=f"{parsed.requested_start}T08:30:00-04:00",
            timezone="America/New_York", scope="release", release_dates=parsed.release_dates,
            operation=parsed.operation, value=parsed.value, unit=parsed.unit, reference=reference)

    def candidate(self, old, draft, request_id, adapter):
        self.compatible(old)
        if self.instruction(old, draft, draft.instruction) != draft.instruction:
            raise BackendError(200, "unsupported", "research_scope", "Draft is outside research coverage", old["revision"])
        if adapter.model_version != old["model_version"]:
            raise BackendError(409, "conflict", "timeline_configuration_mismatch", "Timeline model version changed", old["revision"])
        return replay_candidate(old, draft, request_id, adapter, context=self)
