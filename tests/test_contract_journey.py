"""HTTP fixture tests, not live-provider/production persistence tests."""
import copy
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi.testclient import TestClient
from pydantic import ValidationError
from api.fixture_app import create_app
from api.contracts import (RunResponse, ReadyDraft, RevealResponse, Problem, ForecastRequest,
                           Point, Instruction, Impact, ParsedScenario)
from shared.fixture_service import PRESETS

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / "shared/fixtures" / f"{name}.json").read_text(encoding="utf-8"))


class JourneyTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        result = self.client.post("/api/timelines", json={"target_id": "SPY", "request_id": "create"})
        self.assertEqual(result.status_code, 201)
        self.tid = result.json()["timeline_id"]
        self.url = f"/api/timelines/{self.tid}"
        self.clock = datetime(2026, 11, 7, 22, 0, tzinfo=timezone.utc)
        self.app.state.fixture_service.now = lambda: self.clock
        self.texts = list(PRESETS)

    def submit(self, text, revision, selected=None, request_id=None):
        interpreted = self.client.post(self.url + "/interpret", json=dict(text=text,
            expected_revision=revision, mode="replace" if selected else "add", selected_prompt_id=selected))
        self.assertEqual(interpreted.status_code, 200)
        draft = ReadyDraft.model_validate(interpreted.json())
        body = dict(draft_id=draft.draft_id, expected_revision=revision, request_id=request_id or f"req-{revision}")
        response = self.client.post(self.url + "/commit", json=body)
        return response, body

    def three(self):
        for revision, text in enumerate([self.texts[0], self.texts[2], self.texts[3]]):
            response, _ = self.submit(text, revision)
            self.assertEqual(response.status_code, 200)
            RunResponse.model_validate(response.json())
        return self.client.get(self.url).json()

    def test_three_prompt_edit_preserves_branch_prefix_and_ids(self):
        before = self.three()
        self.assertEqual([p["resolved_value"] for p in before["prompts"]], [0.4, 0.5, 0.5])
        response, _ = self.submit(self.texts[1], 3, "p1")
        result = response.json()
        RunResponse.model_validate(result)
        self.assertEqual(result["series_mode"], "suffix")
        self.assertEqual(result["changed_from"], "2025-06-11")
        self.assertEqual([p["id"] for p in result["prompts"]], ["p1", "p2", "p3"])
        self.assertEqual([p["resolved_value"] for p in result["prompts"]], [0.2, 0.3, 0.3])
        self.assertEqual(result["prompts"][1]["value"], 0.1)  # relative expression retained
        after = self.client.get(self.url).json()
        prefix = lambda run: [p for p in run["series"]["points"] if p["date"] < result["changed_from"]]
        self.assertEqual(prefix(before), prefix(after))
        self.assertNotEqual(before["series"]["points"][-1]["value"], after["series"]["points"][-1]["value"])
        self.assertEqual(before, self.client.get(self.url + "/revisions/3").json())
        self.assertEqual(before["evidence_cutoff"], after["evidence_cutoff"])

    def test_duplicate_before_stale_and_expiry_and_different_body_conflict(self):
        response, body = self.submit(self.texts[0], 0)
        self.clock += timedelta(minutes=10)
        retry = self.client.post(self.url + "/commit", json=body)
        self.assertEqual(response.json(), retry.json())
        self.assertEqual(self.client.get(self.url).json()["revision"], 1)
        conflict = self.client.post(self.url + "/commit", json=dict(body, draft_id="different"))
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "request_id_reused")

    def test_stale_commit_preserves_state(self):
        self.submit(self.texts[0], 0)
        before = self.client.get(self.url).json()
        response = self.client.post(self.url + "/commit", json=dict(draft_id="anything", expected_revision=0, request_id="new"))
        self.assertEqual(response.status_code, 409)
        Problem.model_validate(response.json())
        self.assertEqual(before, self.client.get(self.url).json())

    def test_unsupported_and_clarification_preserve_state(self):
        before = self.client.get(self.url).json()
        for text, status in [("Alternate president in 1900", "unsupported"), ("Change CPI", "needs_clarification")]:
            response = self.client.post(self.url + "/interpret", json=dict(text=text, mode="add", expected_revision=0))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], status)
            self.assertEqual(before, self.client.get(self.url).json())

    def test_reveal_is_separate_read_and_actual_style(self):
        self.three()
        before = self.client.get(self.url).json()
        response = self.client.get(self.url + "/revisions/3/reveal")
        reveal = RevealResponse.model_validate(response.json())
        self.assertTrue(all(p.kind == "observed" for p in reveal.series.points))
        self.assertEqual(before, self.client.get(self.url).json())

    def test_move_dates_both_directions_uses_earliest_start(self):
        self.submit(self.texts[0], 0)
        later, _ = self.submit(self.texts[4], 1, "p1")
        self.assertEqual(later.json()["changed_from"], "2025-06-11")
        self.assertEqual(later.json()["prompts"][0]["id"], "p1")
        self.assertEqual(later.json()["series"]["points"][0]["kind"], "observed")
        earlier, _ = self.submit(self.texts[1], 2, "p1")
        self.assertEqual(earlier.json()["changed_from"], "2025-06-11")

    def test_edit_second_keeps_simulated_prefix(self):
        before = self.three()
        response, _ = self.submit(self.texts[4], 3, "p2")
        self.assertEqual(response.json()["changed_from"], "2025-07-15")
        after = self.client.get(self.url).json()
        self.assertEqual([p for p in before["series"]["points"] if p["date"] < "2025-07-15"],
                         [p for p in after["series"]["points"] if p["date"] < "2025-07-15"])

    def test_moving_first_fork_earlier_tightens_cutoff(self):
        self.submit(self.texts[4], 0)
        response, _ = self.submit(self.texts[0], 1, "p1")
        self.assertEqual(response.json()["evidence_cutoff"], "2025-06-11T12:29:59Z")

    def test_draft_expiry_unknown_id_invalid_input(self):
        draft = self.client.post(self.url + "/interpret", json=dict(text=self.texts[0], mode="add", expected_revision=0)).json()
        self.clock += timedelta(minutes=6)
        response = self.client.post(self.url + "/commit", json=dict(draft_id=draft["draft_id"], expected_revision=0, request_id="late"))
        self.assertEqual(response.status_code, 410)
        self.assertEqual(self.client.get(self.url).json()["revision"], 0)
        self.assertEqual(self.client.get(self.url + "/revisions/99").status_code, 404)
        bad = self.client.post(self.url + "/interpret", json=dict(text=self.texts[0], mode="replace", expected_revision=0))
        self.assertEqual(bad.status_code, 422)
        Problem.model_validate(bad.json())

    def test_broken_reference_does_not_commit(self):
        response, _ = self.submit(self.texts[3], 0)
        self.assertEqual(response.json()["status"], "needs_clarification")
        self.assertEqual(self.client.get(self.url).json()["revision"], 0)

    def test_journey_manifest_matches_http_and_fixtures(self):
        client = TestClient(create_app())
        client.app.state.fixture_service.now = lambda: self.clock
        steps = json.loads((ROOT / "shared/journey.json").read_text(encoding="utf-8"))
        for step in steps:
            body = fixture(step["request"][:-5]) if step["request"] else None
            response = client.request(step["method"], step["path"], **({"json": body} if body else {}))
            self.assertEqual(response.status_code, step["http"])
            self.assertEqual(response.json(), fixture(step["response"][:-5]))


class SchemaTests(unittest.TestCase):
    def test_parser_provider_examples_match(self):
        self.assertEqual(ParsedScenario.model_validate(fixture("parser-openai")), ParsedScenario.model_validate(fixture("parser-ollama")))

    def test_forecast_rejects_future_targets_and_observation_leakage(self):
        value = fixture("forecast-request")
        ForecastRequest.model_validate(value)
        bad = copy.deepcopy(value)
        bad["future"][0]["level"] = 110
        with self.assertRaises(ValidationError):
            ForecastRequest.model_validate(bad)
        bad = copy.deepcopy(value)
        bad["history"][0]["available_at"] = "2025-06-12T20:00:00Z"
        with self.assertRaises(ValidationError):
            ForecastRequest.model_validate(bad)

    def test_invalid_date_quantiles_and_units(self):
        point = fixture("forecast-result")["points"][0]
        for change in [dict(date="2025-02-30"), dict(q10=500), dict(value=None)]:
            with self.assertRaises(ValidationError):
                Point.model_validate(dict(point, **change))
        instruction = fixture("second-run-draft")["instruction"]
        with self.assertRaises(ValidationError):
            Instruction.model_validate(dict(instruction, unit="percent"))

    def test_qualitative_has_no_percentage(self):
        impact = fixture("panel-example")["impacts"][0]
        with self.assertRaises(ValidationError):
            Impact.model_validate(dict(impact, magnitude=1.2))


if __name__ == "__main__":
    unittest.main()
