"""Build reproducible payloads and journey manifest; --check detects stale files."""
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from api.contracts import CreateTimelineRequest, InterpretRequest, CommitRequest
from shared.fixture_service import FixtureService, capabilities, PRESETS

DEST = ROOT / "shared/fixtures"
DEST.mkdir(parents=True, exist_ok=True)
manifest = {}


def write(path, value):
    content = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            raise SystemExit(f"Stale fixture: {path}")
    else:
        path.write_text(content, encoding="utf-8")


def save(name, model, value):
    manifest[f"{name}.json"] = model
    write(DEST / f"{name}.json", value)
    return value


service = FixtureService(now=lambda: datetime(2026, 11, 7, 22, 0, tzinfo=timezone.utc))
save("capabilities", "Capabilities", capabilities())
create = save("create-request", "CreateTimelineRequest", dict(target_id="SPY", request_id="create-001"))
empty = save("empty", "RunResponse", service.create(CreateTimelineRequest(**create)))
tid = empty["timeline_id"]
journey = [dict(method="GET", path="/api/capabilities", request=None, response="capabilities.json", http=200),
           dict(method="POST", path="/api/timelines", request="create-request.json", response="empty.json", http=201)]
texts = list(PRESETS)
for n, text in enumerate([texts[0], texts[2], texts[3], texts[1]], 1):
    replace = n == 4
    name = ["first-run", "second-run", "third-run", "replace-first"][n-1]
    body = dict(text=text, mode="replace" if replace else "add", expected_revision=n-1,
                selected_prompt_id="p1" if replace else None, playhead=None)
    save(f"{name}-interpret", "InterpretRequest", body)
    draft = service.interpret(tid, InterpretRequest(**body))
    save(f"{name}-draft", "ReadyDraft", draft)
    commit = dict(draft_id=draft["draft_id"], expected_revision=n-1, request_id=f"commit-{n:03}")
    save(f"{name}-commit", "CommitRequest", commit)
    result = save(name, "RunResponse", service.commit(tid, CommitRequest(**commit)))
    journey.extend([
        dict(method="POST", path=f"/api/timelines/{tid}/interpret", request=f"{name}-interpret.json", response=f"{name}-draft.json", http=200),
        dict(method="POST", path=f"/api/timelines/{tid}/commit", request=f"{name}-commit.json", response=f"{name}.json", http=200)])
save("restore", "RunResponse", service.get(tid))
save("previous-branch", "RunResponse", service.get(tid, 3))
save("reveal", "RevealResponse", service.reveal(tid, 4))
journey.append(dict(method="GET", path=f"/api/timelines/{tid}/revisions/4/reveal", request=None, response="reveal.json", http=200))
first = service.get(tid, 1)
edit = copy.deepcopy(first)
edit.update(revision=2, parent_revision=1, run_id=f"{tid}-run-2", request_id="short-example", series_mode="suffix")
edit["series"]["points"] = [p for p in edit["series"]["points"] if p["date"] == "2025-06-11"]
save("shorter-suffix", "RunResponse", edit)
edit = copy.deepcopy(edit)
edit["series"]["points"] = []
edit["prompts"][0]["status"] = "unsupported"
edit["panels"]["p1"].update(status="unsupported", summary="Explicitly accepted synthetic qualitative-only revision; no numeric suffix.")
save("empty-suffix", "RunResponse", edit)
for name, status, code, reason, choices, revision, retryable in [
    ("clarification", "needs_clarification", "choose_release", "Choose a CPI release", [texts[0]], 0, False),
    ("unsupported", "unsupported", "unsupported_event", "No supported quantitative lever", [], 4, False),
    ("conflict", "conflict", "stale_revision", "Restore before reapplying", [], 4, False),
    ("unavailable", "unavailable", "provider_unavailable", "No supported provider or preset", [], 4, True),
]:
    save(name, "Problem", dict(status=status, code=code, reason=reason, choices=choices,
                              current_revision=revision, retryable=retryable))
source = dict(id="synthetic-source", title="Synthetic exposure fixture (not evidence)",
    url="https://example.com/synthetic", publication_time="2025-06-10T12:00:00Z", passage_locator="Example only")
panel = copy.deepcopy(first["panels"]["p1"])
panel["evidence"] = [source]
panel["hypotheses"] = [dict(text="Possible mechanism, synthetic example only", source_ids=[], user_assumption=True)]
base_impact = dict(name="Airlines (synthetic)", emoji="✈", exposure="indirect", direction=None,
    metric_kind="qualitative", magnitude=None, unit=None, comparator=None,
    horizon="5 sessions", method="Synthetic display example", source_ids=[source["id"]])
panel["impacts"] = [base_impact, dict(base_impact, name="Example sector proxy", direction="positive",
    metric_kind="proxy_change", magnitude=1.2, unit="percent", comparator="Own starting proxy level")]
save("panel-example", "Panel", panel)
parsed = dict(status="parsed", reason=None, choices=[], date_precision="day",
    requested_start="2025-06-11", requested_end=None, scope="release", release_dates=["2025-06-11"],
    operation="set", value=0.4, unit="percent", reference=None)
save("parser-openai", "ParsedScenario", parsed)
save("parser-ollama", "ParsedScenario", parsed)
forecast = dict(target_id="SPY", segment_id="p1", base_date="2025-06-10", base_value=100,
    evidence_cutoff="2025-06-11T12:29:59Z", dataset_version="synthetic-v1", model_version="fixture-v1",
    history=[dict(date="2025-06-10", level=100, kind="observed", available_at="2025-06-10T20:00:00Z",
                  cpi_percent=0.1, release_indicator=0)],
    future=[dict(date="2025-06-11", cpi_percent=0.4, release_indicator=1)], assumptions=["Synthetic input only"])
save("forecast-request", "ForecastRequest", forecast)
save("forecast-result", "ForecastResult", dict(status="supported", reason=None, engine="synthetic",
    model_version="fixture-v1", support_count=0, points=[first["series"]["points"][1]], assumptions=["Synthetic result only"]))
save("forecast-unsupported", "ForecastResult", dict(status="unsupported", reason="Insufficient coverage",
    engine="baseline", model_version="fixture-v1", support_count=0, points=[], assumptions=[]))
write(DEST / "manifest.json", manifest)
write(ROOT / "shared/journey.json", journey)
print(f"{'Checked' if '--check' in sys.argv else 'Built'} {len(manifest)} typed fixtures and journey manifest.")
