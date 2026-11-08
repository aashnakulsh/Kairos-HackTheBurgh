"""Focused narration-relay checks. Synthetic forecasts and mocked OpenAI only."""
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient
from api.app import create_app
from api.descriptions import OpenAIDescriptionProvider
from api.settings import Settings


class DescriptionTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.settings = Settings(app_mode="fixture", sqlite_path=Path(folder.name) / "test.sqlite",
            openai_api_key="test-secret", openai_model="test-text-model")
        self.calls = []

        def transport(request, timeout):
            self.calls.append((request, timeout))
            return io.BytesIO(json.dumps(dict(status="completed", output=[
                dict(type="reasoning"), dict(type="message", content=[
                    dict(type="output_text", text="A conditional forecast under the supplied CPI assumption.")])])).encode())

        self.provider = OpenAIDescriptionProvider(self.settings, transport=transport)
        self.client = TestClient(create_app(self.settings, description_provider=self.provider))
        self.addCleanup(self.client.close)
        run = self.client.post("/api/timelines", json=dict(target_id="SPY", request_id="create")).json()
        self.url = f"/api/timelines/{run['timeline_id']}"
        self.submit("Set June 11 CPI to 0.4%", 0)
        self.run = self.client.get(self.url).json()
        self.body = dict(prompt_id="p1", forecast_points=[p for p in self.run["series"]["points"] if p["kind"] == "simulated"])
        self.endpoint = self.url + "/revisions/1/description"

    def submit(self, text, revision):
        draft = self.client.post(self.url + "/interpret", json=dict(text=text, mode="add", expected_revision=revision)).json()
        result = self.client.post(self.url + "/commit", json=dict(draft_id=draft["draft_id"], expected_revision=revision,
            request_id=f"commit-{revision}"))
        self.assertEqual(result.status_code, 200, result.text)

    def test_raw_forecast_round_trip_is_separate_from_commit_and_reveal(self):
        self.assertEqual(self.calls, [])  # Commits never invoke narration.
        response = self.client.post(self.endpoint, json=self.body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["run_id"], self.run["run_id"])
        self.assertEqual(response.json()["prompt_id"], "p1")
        self.assertEqual(response.json()["model"], "test-text-model")
        request, timeout = self.calls[0]
        payload = json.loads(request.data)
        context = json.loads(payload["input"])
        self.assertEqual(context["forecast_points"], self.body["forecast_points"])
        self.assertEqual(context["unit"], "index")
        self.assertEqual(context["prompt"]["resolved_value"], 0.4)
        self.assertEqual(context["starting_point"]["kind"], "observed")
        self.assertNotIn("actuals", context)
        self.assertFalse(payload["store"])
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertEqual(timeout, 20)
        self.assertNotIn("test-secret", response.text)
        self.assertEqual(self.client.get(self.url).json(), self.run)

    def test_modified_or_incomplete_numbers_rejected_before_provider_call(self):
        wrong = json.loads(json.dumps(self.body))
        wrong["forecast_points"][0]["value"] += 0.00000001
        for body in [wrong, dict(self.body, forecast_points=self.body["forecast_points"][:-1]),
                     dict(self.body, forecast_points=[self.run["series"]["points"][0]])]:
            response = self.client.post(self.endpoint, json=body)
            self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(self.calls, [])

    def test_missing_revision_prompt_and_invalid_body(self):
        self.assertEqual(self.client.post(self.url + "/revisions/99/description", json=self.body).status_code, 404)
        self.assertEqual(self.client.post(self.endpoint, json=dict(self.body, prompt_id="absent")).status_code, 404)
        self.assertEqual(self.client.post(self.endpoint, json=dict(self.body, api_key="do-not-accept")).status_code, 422)
        self.assertEqual(self.calls, [])

    def test_previous_revision_is_described_as_that_revision(self):
        self.submit("July 15: add 0.1 percentage points to preceding reading", 1)
        response = self.client.post(self.endpoint, json=self.body)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["revision"], 1)
        self.assertEqual(self.client.get(self.url).json()["revision"], 2)

    def test_timeout_refusal_and_unconfigured_provider_preserve_forecast(self):
        def timeout(*args, **kwargs):
            raise TimeoutError("test-secret private provider detail")

        def refusal(*args, **kwargs):
            return io.BytesIO(json.dumps(dict(status="completed", output=[dict(type="message", content=[
                dict(type="refusal", refusal="Cannot describe")])])).encode())

        unconfigured = Settings(app_mode="fixture", sqlite_path=self.settings.sqlite_path,
            openai_api_key="", openai_model="")
        for provider in [OpenAIDescriptionProvider(self.settings, timeout),
                         OpenAIDescriptionProvider(self.settings, refusal), OpenAIDescriptionProvider(unconfigured)]:
            with TestClient(create_app(self.settings, description_provider=provider)) as client:
                response = client.post(self.endpoint, json=self.body)
                self.assertEqual(response.status_code, 503, response.text)
                self.assertNotIn("test-secret", response.text)
                self.assertNotIn("private provider detail", response.text)
                self.assertEqual(client.get(self.url).json(), self.run)


if __name__ == "__main__":
    unittest.main()
