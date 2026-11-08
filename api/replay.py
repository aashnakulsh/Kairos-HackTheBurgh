"""Three single-release prompts; immutable prefix checkpoints and segmented inference.

The session grid and observed levels are explicitly synthetic. Real session/data
loading belongs to Aditya; this coordinator must not be enabled as a real feed.
"""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from api.backend_errors import BackendError
from api.contracts import ForecastRequest, ForecastResult, HistoryRow, Prompt, RunResponse
from api.synthetic_forecast import LABEL
from shared.fixture_service import SESSIONS, point


def candidate(old, draft, request_id, adapter):
    prompts = deepcopy(old["prompts"])
    previous = next((p for p in prompts if p["id"] == draft.selected_prompt_id), None)
    if draft.mode == "replace" and previous is None:
        raise BackendError(422, "invalid", "unknown_prompt", "Unknown selected prompt", old["revision"])
    number = previous["display_number"] if previous else len(prompts) + 1
    if number > 3:
        raise BackendError(200, "unsupported", "prompt_limit", "Demo supports three prompts", old["revision"])
    prompt = Prompt(**draft.instruction.model_dump(), id=previous["id"] if previous else f"p{number}",
        display_number=number, creation_order=previous["creation_order"] if previous else number,
        text=draft.text, evidence_ids=[], resolved_value=None, status="supported").model_dump()
    changed = min(previous["effective_start"], prompt["effective_start"]) if previous else prompt["effective_start"]
    prompts = [p for p in prompts if p["id"] != prompt["id"]] + [prompt]
    prompts.sort(key=lambda p: (datetime.fromisoformat(p["effective_at"]), p["creation_order"]))
    resolved, preceding = {}, None
    for p in prompts:
        if p["operation"] == "set":
            reading = Decimal(str(p["value"]))
        else:
            ref = preceding if p["reference"] == "preceding" else resolved.get(p["reference"])
            if ref is None:
                raise BackendError(200, "needs_clarification", "broken_reference",
                    "Reference must precede this prompt", old["revision"])
            reading = ref + (Decimal(str(p["value"])) if p["operation"] == "add_pp" else 0)
        p["resolved_value"] = float(reading)
        resolved[p["id"]] = preceding = reading

    first = prompts[0]["effective_start"]
    cutoff = min(old["evidence_cutoff"] or f"{first}T12:29:59Z", f"{first}T12:29:59Z")
    end = SESSIONS.index(prompts[-1]["effective_start"]) + 5
    if end > len(SESSIONS) or end - SESSIONS.index(first) > 65:
        raise BackendError(200, "unsupported", "horizon_coverage", "Requested horizon exceeds synthetic coverage")
    # The old full snapshot is the release-only checkpoint. Never rerun its prefix.
    points = deepcopy([p for p in old["series"]["points"] if p["date"] < changed])
    present = {p["date"] for p in points}
    for day in SESSIONS:
        if day >= first:
            break
        if day not in present:
            points.append(point(day, 100.0))
    points.sort(key=lambda p: p["date"])
    # Retained observed chart points after a previously frozen cutoff (a fork moved
    # later) are display-only. They never enter model history or advance evidence.
    history = []
    for p in points:
        available = f"{p['date']}T20:00:00Z" if p["kind"] == "observed" else None
        if available and available > cutoff:
            continue
        active = next((q for q in reversed(prompts) if q["effective_start"] <= p["date"]), None)
        history.append(HistoryRow(date=p["date"], level=p["value"], kind=p["kind"],
            available_at=available, cpi_percent=active["resolved_value"] if active else 0.0,
            release_indicator=int(any(q["effective_start"] == p["date"] for q in prompts))))

    # A new event can extend a previous five-session tail across a bridge. Infer
    # that bridge from the saved median checkpoint before activating the event.
    replay_start = changed
    if points and points[-1]["date"] < changed:
        next_index = SESSIONS.index(points[-1]["date"]) + 1
        if next_index < len(SESSIONS):
            replay_start = min(changed, SESSIONS[next_index])
    groups = []
    for day in SESSIONS[:end]:
        if day < first or day < replay_start:
            continue
        active = next(p for p in reversed(prompts) if p["effective_start"] <= day)
        if not groups or groups[-1][0]["id"] != active["id"]:
            groups.append((active, []))
        groups[-1][1].append(dict(date=day, cpi_percent=active["resolved_value"],
            release_indicator=int(day == active["effective_start"])))
    panels = deepcopy(old["panels"])
    for active, future in groups:
        forecast_request = ForecastRequest(target_id=old["series"]["target_id"], segment_id=active["id"],
            base_date=old["series"]["base_date"], base_value=old["series"]["base_value"],
            evidence_cutoff=cutoff, dataset_version=old["dataset_version"],
            model_version=adapter.model_version, history=history, future=future,
            assumptions=[LABEL, "Carry the active CPI reading until the next explicit intervention",
                "Bands conditional on the preceding simulated median"])
        try:
            raw = adapter.forecast_segment(forecast_request)
            result = ForecastResult.model_validate(raw.model_dump() if isinstance(raw, ForecastResult) else raw)
            if result.status == "unsupported":
                raise BackendError(200, "unsupported", "forecast_unsupported", result.reason, old["revision"])
            if ([p.date for p in result.points] != [r["date"] for r in future]
                    or result.model_version != adapter.model_version
                    or any(p.segment_id != active["id"] or p.engine != result.engine for p in result.points)):
                raise ValueError("Adapter output does not match requested segment")
        except BackendError:
            raise
        except Exception as exc:
            raise BackendError(503, "unavailable", "forecast_failed",
                "Numerical adapter failed validation or execution; committed state is unchanged", old["revision"]) from exc
        points.extend(p.model_dump() for p in result.points)
        history = list(forecast_request.history) + [HistoryRow(date=p.date, level=p.value,
            kind="simulated", available_at=None, cpi_percent=row["cpi_percent"],
            release_indicator=row["release_indicator"]) for p, row in zip(result.points, future)]
        panels[active["id"]] = dict(summary=f"{LABEL}. Resolved CPI assumption {active['resolved_value']}%.",
            hypotheses=[], evidence=[], impacts=[], horizon="; ".join(result.assumptions),
            comparison=None, engine=result.engine, support_count=result.support_count, status="supported")
    # Same-date instructions can be superseded without producing a numerical segment.
    for p in prompts:
        if p["id"] not in panels or not any(x["segment_id"] == p["id"] for x in points):
            panels[p["id"]] = dict(summary=f"{LABEL}. Resolved CPI assumption {p['resolved_value']}%; superseded at activation.",
                hypotheses=[], evidence=[], impacts=[], horizon="No active segment", comparison=None,
                engine="synthetic", support_count=0, status="supported")
    run = deepcopy(old)
    run.update(revision=old["revision"] + 1, parent_revision=old["revision"],
        run_id=f"{old['timeline_id']}-run-{old['revision'] + 1}", request_id=request_id,
        model_version=adapter.model_version, changed_from=changed, prompts=prompts, panels=panels,
        evidence_cutoff=cutoff, series_mode="full",
        replace_through=max([changed] + [p["date"] for p in old["series"]["points"] + points]))
    run["series"]["points"] = points
    RunResponse.model_validate(run)
    response = deepcopy(run)
    old_prefix = [p for p in old["series"]["points"] if p["date"] < changed]
    new_prefix = [p for p in points if p["date"] < changed]
    if old["revision"] > 0 and old_prefix == new_prefix:
        response["series_mode"] = "suffix"
        response["series"]["points"] = [p for p in points if p["date"] >= changed]
    RunResponse.model_validate(response)
    return run, response
