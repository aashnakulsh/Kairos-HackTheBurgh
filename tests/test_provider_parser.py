"""Provider interpretation and bounded durable HTTP behavior, without network calls."""
import io
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from api.contracts import InterpretRequest
from api.provider_parser import OpenAIParser, OllamaParser, ScenarioParserRouter
from api.settings import Settings
from shared.fixture_service import PRESETS


def scenario(day, operation, value, reference):
    return dict(status="parsed", reason=None, choices=[], date_precision="day",
                requested_start=day, requested_end=None, scope="release", release_dates=[day],
                operation=operation, value=value,
                unit="percentage_points" if operation == "add_pp" else "percent", reference=reference)


def openai_response(parsed):
    return dict(status="completed", output=[dict(type="message", content=[
        dict(type="output_text", text=json.dumps(parsed))])])


class Transport:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error:
            raise self.error
        return io.BytesIO(json.dumps(self.result).encode())


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(sqlite_path=Path(self.temp.name) / "test.sqlite", parser_provider="auto",
                                 openai_api_key="test-secret", openai_model="test-model")
        self.june = scenario("2025-06-11", "set", 0.4, None)
        self.july = scenario("2025-07-15", "add_pp", 0.1, "preceding")
        self.august = scenario("2025-08-12", "carry", None, "p2")

    @staticmethod
    def request(text):
        return InterpretRequest(text=text, mode="add", expected_revision=0)

    def router(self, primary, local=None):
        return ScenarioParserRouter(self.settings, OpenAIParser(self.settings, primary),
                                    OllamaParser(self.settings, local or Transport(error=OSError("offline"))))

    def test_openai_structured_request_and_ordinary_wording(self):
        primary = Transport(openai_response(self.june))
        parsed = self.router(primary).parse(self.request("What if June 11, 2025 CPI were 0.4 percent?"))
        self.assertEqual(parsed.status, "parsed")
        self.assertEqual(parsed.value, 0.4)
        call, timeout = primary.calls[0]
        payload = json.loads(call.data)
        self.assertEqual(timeout, 5)
        self.assertEqual(payload["text"]["format"]["schema"]["required"],
                         list(payload["text"]["format"]["schema"]["properties"]))
        self.assertEqual(payload["store"], False)
        self.assertEqual(call.get_header("Authorization"), "Bearer test-secret")

    def test_local_fallback_and_presets_without_provider_calls(self):
        primary = Transport(error=OSError("test-secret unreachable"))
        local = Transport(dict(message=dict(content=json.dumps(self.july))))
        router = self.router(primary, local)
        preset = router.parse(self.request(next(iter(PRESETS))))
        self.assertEqual(preset.status, "parsed")
        self.assertEqual(primary.calls, [])
        parsed = router.parse(self.request("On July 15, 2025, add 0.1 pp to the previous simulated CPI reading"))
        self.assertEqual((parsed.operation, parsed.reference), ("add_pp", "preceding"))
        self.assertEqual(len(primary.calls), 1)
        self.assertEqual(len(local.calls), 1)
        self.assertIs(json.loads(local.calls[0][0].data)["think"], False)
        self.assertEqual(json.loads(local.calls[0][0].data)["options"], {"temperature": 0, "num_predict": 512})
        self.assertEqual(json.loads(local.calls[0][0].data)["format"]["required"],
                         list(json.loads(local.calls[0][0].data)["format"]["properties"]))

    def test_unavailable_or_refusal_never_exposes_provider_details(self):
        for result in [dict(status="incomplete", output=[]),
                       dict(status="completed", output=[dict(type="message", content=[dict(type="refusal")])])]:
            with self.subTest(result=result):
                parsed = self.router(Transport(result), Transport(error=OSError("private payload"))).parse(
                    self.request("What if June 11, 2025 CPI were 0.4%?"))
                self.assertEqual(parsed.status, "needs_clarification")
                self.assertNotIn("private", parsed.reason)

    def test_bad_schema_unsupported_tuple_and_ungrounded_guess(self):
        cases = [({"status": "parsed"}, "needs_clarification"),
                 (scenario("2025-06-11", "set", 0.8, None), "unsupported"),
                 (self.june, "needs_clarification")]
        texts = ["Set June 11, 2025 CPI to 0.4 percent", "Set June 11, 2025 CPI to 0.8%",
                 "Set June 11, 2025 CPI to 0.2%"]
        for (parsed, expected), prompt in zip(cases, texts):
            with self.subTest(expected=expected):
                result = self.router(Transport(openai_response(parsed))).parse(self.request(prompt))
                self.assertEqual(result.status, expected)

    def test_conflicting_values_and_year_require_clarification(self):
        for text in ["June 11, 2025 CPI: 0.4% or 0.2%",
                     "June 11, 2026 CPI should be 0.4%"]:
            with self.subTest(text=text):
                result = self.router(Transport(openai_response(self.june))).parse(self.request(text))
                self.assertEqual(result.status, "needs_clarification")

    def test_http_three_prompts_edit_and_replay_do_not_reparse(self):
        outputs = [self.june, self.july, self.august,
                   scenario("2025-06-11", "set", 0.2, None)]

        class Sequenced:
            def __init__(self):
                self.calls = 0

            def parse(self, request):
                result = outputs[self.calls]
                self.calls += 1
                return result

        primary = Sequenced()
        client = TestClient(create_app(self.settings, parser=ScenarioParserRouter(self.settings, primary=primary)))
        run = client.post("/api/timelines", json={"target_id": "SPY", "request_id": "create"}).json()
        url = "/api/timelines/" + run["timeline_id"]
        texts = ["On June 11, 2025 set CPI at 0.4%",
                 "On July 15, 2025 add 0.1 percentage points to the previous simulated reading",
                 "On August 12, 2025 keep July's simulated reading unchanged",
                 "On June 11, 2025 set CPI at 0.2%"]
        for revision, prompt in enumerate(texts):
            selected = "p1" if revision == 3 else None
            body = dict(text=prompt, mode="replace" if selected else "add",
                        selected_prompt_id=selected, expected_revision=revision)
            draft_response = client.post(url + "/interpret", json=body)
            self.assertEqual(draft_response.status_code, 200)
            draft = draft_response.json()
            self.assertEqual(draft["status"], "ready")
            committed = client.post(url + "/commit", json=dict(draft_id=draft["draft_id"],
                expected_revision=revision, request_id=f"commit-{revision}"))
            self.assertEqual(committed.status_code, 200)
        self.assertEqual(primary.calls, 4)
        self.assertEqual([p["resolved_value"] for p in committed.json()["prompts"]], [0.2, 0.3, 0.3])
        self.assertEqual([p["id"] for p in committed.json()["prompts"]], ["p1", "p2", "p3"])
        self.assertEqual(client.get(url + "/revisions/3").json()["revision"], 3)
        self.assertEqual(primary.calls, 4)


if __name__ == "__main__":
    unittest.main()
