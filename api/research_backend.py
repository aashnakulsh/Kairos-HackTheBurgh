"""Bounded real-data June runtime, behind the unchanged HTTP contracts.

Imported only for APP_MODE=research, so fixture users need no market dependencies.
SQLite commands remain in DurableService; this runtime builds candidates only.
"""
from copy import deepcopy
from hashlib import sha256
import json

from api.backend_errors import BackendError
from api.contracts import Capabilities, Evidence, Instruction, Prompt, RunResponse
from api.preset_parser import PresetParser
from api.replay import forecast_points
from data.real_market import CUTOFF, DATES, MarketInputs
from training.chronos_adapter import ChronosAdapter, MODEL_VERSION

LABEL = "Local historical research — IEX SPY data with conditional Chronos-2 forecasts"
PRESETS = {
    "Set June 11 CPI to 0.4%": (DATES[0], "set", 0.4, None),
    "Set June 11 CPI to 0.2%": (DATES[0], "set", 0.2, None),
}


class ResearchBackend:
    def __init__(self, settings, adapter=None):
        self.inputs = MarketInputs(settings.data_dir / "processed" / settings.dataset_version)
        if self.inputs.manifest["dataset_version"] != settings.dataset_version:
            raise ValueError("Configured DATASET_VERSION disagrees with the snapshot manifest")
        self.adapter = adapter if adapter is not None else ChronosAdapter(self.inputs)
        if self.adapter.model_version != MODEL_VERSION:
            raise ValueError("Research mode requires the pinned Chronos model version")
        self.parser = PresetParser(PRESETS)
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
            "Only one June 11 CPI prompt and its replacement are supported over five sessions.",
            "HTTP actual-history reveal is not enabled; empirical baseline has insufficient earlier releases."]

    def capabilities(self):
        # v1's 'live' discriminant means real inputs/engine, not a streaming feed.
        # The label and rights field explicitly describe this local historical mode.
        return Capabilities(contract_version="1", mode="live", data_label=LABEL,
            targets=["SPY"], unit="index", frequency="trading_session",
            default_viewport=dict(start_year=2025, end_year=2025),
            coverage=dict(first_session=self.points[0]["date"], last_session=DATES[-1], gaps=[]),
            supported_event_families=["cpi_release_presets"], default_horizon_sessions=5,
            max_horizon_sessions=5, max_prompts=1, evidence_available=bool(self.evidence),
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
        if (request.mode == "add" and run["prompts"]):
            raise BackendError(200, "unsupported", "research_prompt_limit",
                "Research mode supports one June prompt. Select p1 to replace it.", run["revision"], list(PRESETS))
        if (parsed.scope != "release" or parsed.date_precision != "day"
            or parsed.requested_start != DATES[0] or parsed.requested_end is not None
            or parsed.release_dates != [DATES[0]] or parsed.operation != "set"
            or parsed.unit != "percent" or parsed.reference is not None or parsed.value not in {0.2, 0.4}):
            raise BackendError(200, "unsupported", "research_scope",
                "Research mode supports the June 11 CPI 0.4% and 0.2% presets only.", run["revision"], list(PRESETS))
        return Instruction(date_precision="day", requested_start=DATES[0], requested_end=None,
            effective_start=DATES[0], effective_end=None, effective_at="2025-06-11T08:30:00-04:00",
            timezone="America/New_York", scope="release", release_dates=[DATES[0]],
            operation="set", value=parsed.value, unit="percent", reference=None)

    def candidate(self, old, draft, request_id, adapter):
        self.compatible(old)
        # Validate persisted drafts too (a server may have restarted in another mode).
        expected = self.instruction(old, draft, draft.instruction)
        if expected != draft.instruction:
            raise BackendError(200, "unsupported", "research_scope", "Draft is outside June research coverage", old["revision"])
        if adapter.model_version != old["model_version"]:
            raise BackendError(409, "conflict", "timeline_configuration_mismatch", "Timeline model version changed", old["revision"])
        if draft.mode == "replace" and draft.selected_prompt_id != "p1":
            raise BackendError(422, "invalid", "unknown_prompt", "Unknown selected prompt", old["revision"])
        request = self.inputs.request(draft.instruction.value, adapter.model_version)
        request.segment_id = "p1"
        result = forecast_points(request, adapter, old["revision"])
        if result.engine != "chronos-2-cpu":
            raise BackendError(503, "unavailable", "forecast_failed", "Research forecast returned the wrong engine", old["revision"])
        prompt = Prompt(**draft.instruction.model_dump(), id="p1", display_number=1, creation_order=1,
            text=draft.text, evidence_ids=[e["id"] for e in self.evidence],
            resolved_value=draft.instruction.value, status="supported")
        run = deepcopy(old)
        run.update(revision=old["revision"] + 1, parent_revision=old["revision"],
            run_id=f"{old['timeline_id']}-run-{old['revision'] + 1}", request_id=request_id,
            changed_from=DATES[0], replace_through=DATES[-1], series_mode="full", prompts=[prompt.model_dump()],
            panels={"p1": dict(summary=f"{LABEL}. Hypothetical June CPI: {prompt.resolved_value}%.",
                hypotheses=[], evidence=deepcopy(self.evidence), impacts=[],
                horizon="; ".join(result.assumptions),
                comparison="Empirical baseline unavailable: insufficient earlier original CPI releases.",
                engine=result.engine, support_count=result.support_count, status="supported")})
        run["series"]["points"] = deepcopy(self.points) + [p.model_dump() for p in result.points]
        RunResponse.model_validate(run)
        response = deepcopy(run)
        if old["revision"] > 0:
            response["series_mode"] = "suffix"
            response["series"]["points"] = [p.model_dump() for p in result.points]
        RunResponse.model_validate(response)
        return run, response
