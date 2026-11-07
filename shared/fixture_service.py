"""Deterministic contract simulator, NOT a production replay/model implementation.

Only named presets and single release instructions are implemented. Synthetic
arithmetic illustrates inherited state; it is not a CPI/market return model.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from api.contracts import Capabilities, Instruction, Prompt, ReadyDraft, RunResponse

LABEL = "Synthetic example — not market data or a real forecast"
PRESETS = {
    "Set June 11 CPI to 0.4%": ("2025-06-11", "set", 0.4, None),
    "Set June 11 CPI to 0.2%": ("2025-06-11", "set", 0.2, None),
    "July 15: add 0.1 percentage points to preceding reading": ("2025-07-15", "add_pp", 0.1, "preceding"),
    "August 12: keep July simulated reading": ("2025-08-12", "carry", None, "p2"),
    "Set July 15 CPI to 0.2%": ("2025-07-15", "set", 0.2, None),
}


class FixtureError(Exception):
    def __init__(self, http, status, code, reason, revision=None, choices=None):
        self.http = http
        self.body = dict(status=status, code=code, reason=reason, choices=choices or [],
                         current_revision=revision, retryable=http == 503)


def point(day, value, prompt_id=None):
    return dict(date=day, kind="simulated" if prompt_id else "observed", value=value,
                q10=round(value - 1, 6) if prompt_id else None,
                q90=round(value + 1, 6) if prompt_id else None,
                engine="synthetic" if prompt_id else None, segment_id=prompt_id)


def sessions():
    # Explicit fixture range/calendar only. Real exchange calendar belongs to Aditya.
    day = date(2025, 6, 10)
    while day <= date(2025, 8, 18):
        if day.weekday() < 5 and day.isoformat() not in {"2025-06-19", "2025-07-04"}:
            yield day.isoformat()
        day += timedelta(days=1)


SESSIONS = list(sessions())


def capabilities():
    return Capabilities(contract_version="1", mode="fixture", data_label=LABEL,
        targets=["SPY"], unit="index", frequency="trading_session",
        default_viewport=dict(start_year=1980, end_year=2026),
        coverage=dict(first_session=SESSIONS[0], last_session=SESSIONS[-1], gaps=[]),
        supported_event_families=["cpi_release_presets"], default_horizon_sessions=5,
        max_horizon_sessions=65, max_prompts=3, evidence_available=False,
        display_rights="Synthetic fixture only; no licensed market feed loaded",
        fixture_presets=list(PRESETS)).model_dump()


def empty(timeline_id):
    return dict(contract_version="1", data_label=LABEL, timeline_id=timeline_id,
        run_id=None, dataset_version="synthetic-v1", model_version="fixture-v1", corpus_version="empty-v1",
        request_id=None, revision=0, parent_revision=None, changed_from=None,
        replace_through=None, series_mode="full", evidence_cutoff=None,
        prompts=[], panels={}, series=dict(target_id="SPY", base_date="2025-06-10",
        base_value=100, unit="index", frequency="trading_session", points=[]))


class FixtureService:
    def __init__(self, now=None):
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.timelines = {}
        self.drafts = {}
        self.completed = {}
        self.creates = {}

    def create(self, request):
        if request.request_id in self.creates:
            body, original = self.creates[request.request_id]
            if body != request.model_dump():
                raise FixtureError(409, "conflict", "request_id_reused", "Creation ID reused with different body")
            return deepcopy(original)
        timeline_id = f"fixture-{len(self.timelines) + 1}"
        run = empty(timeline_id)
        self.timelines[timeline_id] = [run]
        self.creates[request.request_id] = (request.model_dump(), deepcopy(run))
        return deepcopy(run)

    def get(self, timeline_id, revision=None):
        if timeline_id not in self.timelines:
            raise FixtureError(404, "not_found", "timeline_not_found", "Unknown timeline")
        history = self.timelines[timeline_id]
        if revision is not None and not 0 <= revision < len(history):
            raise FixtureError(404, "not_found", "revision_not_found", "Unknown revision")
        return deepcopy(history[-1 if revision is None else revision])

    def interpret(self, timeline_id, request):
        run = self.get(timeline_id)
        if request.expected_revision != run["revision"]:
            raise FixtureError(409, "conflict", "stale_revision", "Restore before reinterpreting", run["revision"])
        if request.mode == "replace" and request.selected_prompt_id not in {p["id"] for p in run["prompts"]}:
            raise FixtureError(422, "invalid", "unknown_prompt", "Unknown selected prompt", run["revision"])
        if request.text not in PRESETS:
            missing_date = request.text == "Change CPI"
            raise FixtureError(200, "needs_clarification" if missing_date else "unsupported",
                "choose_preset", "Fixture mode supports only the listed presets", run["revision"], list(PRESETS))
        day, operation, value, reference = PRESETS[request.text]
        instruction = Instruction(date_precision="day", requested_start=day, requested_end=None,
            effective_start=day, effective_end=None, effective_at=f"{day}T08:30:00-04:00",
            timezone="America/New_York", scope="release", release_dates=[day], operation=operation,
            value=value, unit="percentage_points" if operation == "add_pp" else "percent", reference=reference)
        draft = ReadyDraft(status="ready", draft_id=f"draft-{len(self.drafts) + 1}",
            timeline_id=timeline_id, expected_revision=run["revision"], mode=request.mode,
            selected_prompt_id=request.selected_prompt_id, text=request.text,
            expires_at=(self.now() + timedelta(minutes=5)).isoformat(),
            instruction=instruction, warnings=[LABEL])
        self.drafts[draft.draft_id] = draft
        return draft.model_dump()

    def commit(self, timeline_id, request):
        old = self.get(timeline_id)
        key = (timeline_id, request.request_id)
        # Completed retry precedes stale-revision and draft-expiry checks.
        if key in self.completed:
            body, original = self.completed[key]
            if body != request.model_dump():
                raise FixtureError(409, "conflict", "request_id_reused", "Request ID reused with different body", old["revision"])
            return deepcopy(original)
        if request.expected_revision != old["revision"]:
            raise FixtureError(409, "conflict", "stale_revision", "Restore before reapplying", old["revision"])
        draft = self.drafts.get(request.draft_id)
        if not draft or draft.timeline_id != timeline_id:
            raise FixtureError(404, "not_found", "draft_not_found", "Unknown draft", old["revision"])
        if datetime.fromisoformat(draft.expires_at) <= self.now():
            raise FixtureError(410, "draft_expired", "draft_expired", "Reinterpret the preserved text", old["revision"])
        if draft.expected_revision != old["revision"]:
            raise FixtureError(409, "conflict", "stale_draft", "Draft is bound to another revision", old["revision"])
        prompts = deepcopy(old["prompts"])
        previous = next((p for p in prompts if p["id"] == draft.selected_prompt_id), None)
        number = previous["display_number"] if previous else len(prompts) + 1
        if number > 3:
            raise FixtureError(200, "unsupported", "prompt_limit", "Demo supports three prompts", old["revision"])
        prompt = Prompt(**draft.instruction.model_dump(), id=previous["id"] if previous else f"p{number}",
            display_number=number, creation_order=previous["creation_order"] if previous else number,
            text=draft.text, evidence_ids=[], resolved_value=None, status="supported").model_dump()
        changed = min(previous["effective_start"], prompt["effective_start"]) if previous else prompt["effective_start"]
        prompts = [p for p in prompts if p["id"] != prompt["id"]] + [prompt]
        prompts.sort(key=lambda p: (p["effective_at"], p["creation_order"]))
        resolved = {}
        preceding = None
        for p in prompts:
            if p["operation"] == "set":
                reading = Decimal(str(p["value"]))
            else:
                ref = preceding if p["reference"] == "preceding" else resolved.get(p["reference"])
                if ref is None:
                    raise FixtureError(200, "needs_clarification", "broken_reference", "Reference must precede this prompt", old["revision"])
                reading = ref + (Decimal(str(p["value"])) if p["operation"] == "add_pp" else 0)
            p["resolved_value"] = float(reading)
            resolved[p["id"]] = preceding = reading
        # Generate a full deterministic candidate, then derive suffix. Production must
        # checkpoint/replay model state; this simple toy arithmetic proves only the contract.
        first = prompts[0]["effective_start"]
        last_index = SESSIONS.index(prompts[-1]["effective_start"])
        end_index = min(last_index + 4, len(SESSIONS) - 1)
        points, level, active = [], Decimal("100"), None
        for day in SESSIONS[:end_index + 1]:
            activations = [p for p in prompts if p["effective_start"] == day]
            if activations:
                active = activations[-1]
            if day < first:
                points.append(point(day, 100.0))
            else:
                level += Decimal(str(active["resolved_value"]))
                points.append(point(day, float(level), active["id"]))
        run = deepcopy(old)
        run.update(revision=old["revision"] + 1, parent_revision=old["revision"],
            run_id=f"{timeline_id}-run-{old['revision'] + 1}",
            request_id=request.request_id, changed_from=changed, prompts=prompts,
            evidence_cutoff=min(old["evidence_cutoff"] or f"{first}T12:29:59Z", f"{first}T12:29:59Z"),
            replace_through=max([changed] + [p["date"] for p in old["series"]["points"] + points]))
        run["series"]["points"] = points
        run["panels"] = {p["id"]: dict(summary=f"{LABEL}. Resolved CPI assumption {p['resolved_value']}%.",
            hypotheses=[], evidence=[], impacts=[], horizon="Five sessions after final prompt; earlier segments bridge to next prompt",
            comparison=None, engine="synthetic", support_count=0, status="supported") for p in prompts}
        RunResponse.model_validate(run)
        result = deepcopy(run)
        if old["revision"] > 0:
            result["series_mode"] = "suffix"
            result["series"]["points"] = [p for p in points if p["date"] >= changed]
        RunResponse.model_validate(result)
        self.timelines[timeline_id].append(deepcopy(run))
        self.completed[key] = (request.model_dump(), deepcopy(result))
        return result

    def reveal(self, timeline_id, revision):
        run = self.get(timeline_id, revision)
        series = deepcopy(run["series"])
        series["points"] = [point(p["date"], 100 + i * 0.05) for i, p in enumerate(series["points"]) if p["kind"] == "simulated"]
        return dict(timeline_id=timeline_id, revision=revision, data_label=LABEL,
                    series=series, sources=[], attribution="Synthetic reveal fixture; no actual market observations")
