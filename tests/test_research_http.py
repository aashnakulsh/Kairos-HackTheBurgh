"""HTTP acceptance with on-disk invented market inputs and an injected numerical engine.

No cached weights, raw downloads, API keys or network required by these tests.
The optional real weights + downloaded-data journey is tools/research_backend_demo.py.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from importlib.util import find_spec
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Barrier
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from api.app import create_app
from api.contracts import Capabilities, ForecastResult, RunResponse
from api.settings import Settings

MARKET_AVAILABLE = all(find_spec(p) for p in ("numpy", "pandas", "pyarrow", "bs4", "pypdf", "exchange_calendars"))
if MARKET_AVAILABLE:
    from data.real_market import CUTOFF, DATES, MarketInputs, digest
    from training.chronos_adapter import ChronosAdapter, MODEL_VERSION
    from test_market_adapter import fake_inputs, FakePipeline


class SettingsTests(unittest.TestCase):
    def test_research_requires_explicit_snapshot_and_cpu(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(Settings().app_mode, "fixture")
            for kwargs in [dict(app_mode="live"), dict(app_mode="research"),
                           dict(app_mode="research", dataset_version="../escape"),
                           dict(app_mode="research", dataset_version="snapshot", forecast_device="mps")]:
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    Settings(**kwargs)
        with patch.dict(os.environ, dict(APP_MODE="research", DATASET_VERSION="snapshot", DATA_DIR="custom-data"), clear=True):
            settings = Settings()
            self.assertEqual(settings.data_dir, Path("custom-data"))
            self.assertEqual(settings.sqlite_path, Path("custom-data/teamrelay-research.sqlite"))

    def test_default_durable_runtime_does_not_import_optional_market_or_model_packages(self):
        with TemporaryDirectory() as tmp:
            code = """import sys
from api.app import create_app
from api.settings import Settings
from pathlib import Path
app = create_app(Settings(app_mode='fixture', sqlite_path=Path(sys.argv[1])))
assert app.state.backend_service.capabilities()['mode'] == 'fixture'
assert not any(name in sys.modules for name in ['data.real_market', 'pandas', 'torch', 'chronos'])
"""
            subprocess.run([sys.executable, "-c", code, str(Path(tmp) / "fixture.sqlite")], check=True)


@unittest.skipUnless(MARKET_AVAILABLE, "optional: pip install -r requirements-market.txt")
class ResearchHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "research.sqlite"
        self.snapshot = self.write_snapshot("test-only")
        self.settings = Settings(app_mode="research", data_dir=self.root, dataset_version="test-only",
                                 sqlite_path=self.path, forecast_device="cpu", parser_provider="deterministic")
        self.clock = datetime(2026, 11, 8, tzinfo=timezone.utc)
        self.client, self.adapter = self.restart()
        created = self.client.post("/api/timelines", json=dict(target_id="SPY", request_id="create"))
        self.assertEqual(created.status_code, 201, created.text)
        self.initial = created.json()
        self.url = f"/api/timelines/{self.initial['timeline_id']}"

    def write_snapshot(self, name):
        inputs = fake_inputs()
        directory = self.root / "processed" / name
        directory.mkdir(parents=True)
        inputs.manifest["dataset_version"] = name
        inputs.releases["sha256"] = ["a" * 64, "b" * 64]
        inputs.releases["source_url"] = ["https://www.bls.gov/news.release/archives/cpi_05132025.htm",
                                         "https://www.bls.gov/news.release/archives/cpi_06112025.htm"]
        inputs.releases["locator"] = "Original release narrative"
        frames = {"spy_daily.parquet": inputs.prices, "cpi_releases.parquet": inputs.releases,
                  "sessions.parquet": inputs.schedule}
        for name, frame in frames.items():
            frame.to_parquet(directory / name, index=False)
        manifest = dict(inputs.manifest, files={name: digest(directory / name) for name in frames})
        import pandas as pd
        reveal = self.root / "reveal" / inputs.manifest["dataset_version"]
        reveal.mkdir(parents=True)
        actuals = pd.DataFrame(dict(date=inputs.schedule.date, level=[120.0 + i for i in range(len(inputs.schedule))],
            available_at=inputs.schedule.close.map(lambda d: d.isoformat())))
        actuals.to_parquet(reveal / "spy_actuals.parquet", index=False)
        manifest["reveal_sha256"] = digest(reveal / "spy_actuals.parquet")
        (directory / "manifest.json").write_text(json.dumps(manifest))
        return directory

    def restart(self, settings=None, adapter=None, parser=None):
        settings = settings or self.settings
        if adapter is None:
            # A test-only deterministic engine exercising the real Chronos frame boundary.
            class ScenarioPipeline(FakePipeline):
                def predict_df(inner, past, future_df, **kwargs):
                    result = super().predict_df(past, future_df, **kwargs)
                    result[["0.1", "0.5", "0.9"]] += float(future_df.cpi_percent.iloc[0])
                    return result
            inputs = MarketInputs(settings.data_dir / "processed" / settings.dataset_version)
            adapter = ChronosAdapter(inputs, pipeline=ScenarioPipeline())
        client = TestClient(create_app(settings, adapter=adapter, parser=parser, now=lambda: self.clock))
        self.addCleanup(client.close)
        return client, adapter

    def draft(self, value=.4, revision=0, mode="add", selected=None, client=None):
        result = (client or self.client).post(self.url + "/interpret", json=dict(
            text=f"Set June 11 CPI to {value}%", mode=mode, selected_prompt_id=selected, expected_revision=revision))
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["status"], "ready", result.text)
        return result.json()["draft_id"]

    def commit(self, draft_id, revision, key, client=None):
        body = dict(draft_id=draft_id, expected_revision=revision, request_id=key)
        return (client or self.client).post(self.url + "/commit", json=body), body

    def run_one(self):
        result, body = self.commit(self.draft(), 0, "first")
        self.assertEqual(result.status_code, 200, result.text)
        RunResponse.model_validate(result.json())
        return result.json(), body

    def test_capabilities_and_creation_are_frozen_real_inputs_without_inference(self):
        caps = Capabilities.model_validate(self.client.get("/api/capabilities").json())
        self.assertEqual((caps.mode, caps.max_prompts, caps.max_horizon_sessions), ("live", 3, 65))
        self.assertEqual(caps.coverage.last_session, "2025-08-18")
        self.assertEqual(len(caps.fixture_presets), 5)
        self.assertIn("unreviewed", caps.display_rights)
        run = RunResponse.model_validate(self.initial)
        expected = self.adapter.inputs.request(.2, MODEL_VERSION)
        self.assertEqual(run.dataset_version, expected.dataset_version)
        self.assertEqual(run.model_version, MODEL_VERSION)
        self.assertEqual(run.evidence_cutoff, CUTOFF)
        self.assertEqual(run.series.base_date, expected.base_date)
        self.assertEqual([(p.date, p.value) for p in run.series.points], [(r.date, r.level) for r in expected.history])
        self.assertTrue(all(p.kind == "observed" for p in run.series.points))
        self.assertFalse(self.adapter._pipeline.calls)
        self.assertEqual(self.client.post("/api/timelines", json=dict(target_id="SPY", request_id="create")).json(), self.initial)

    def test_http_commit_replace_prefix_and_immutable_revision(self):
        first, _ = self.run_one()
        self.assertEqual(first["series_mode"], "full")
        self.assertEqual(first["series"]["points"][:20], self.initial["series"]["points"])
        self.assertEqual([p["date"] for p in first["series"]["points"][20:]], DATES)
        panel = first["panels"]["p1"]
        self.assertEqual(panel["engine"], "chronos-2-cpu")
        self.assertEqual([e["publication_time"] for e in panel["evidence"]], ["2025-05-13T12:30:00Z"])
        past, future, _ = self.adapter._pipeline.calls[0]
        self.assertNotIn("target", future)
        self.assertEqual(past.cpi_percent.tolist(), [.2] * 20)
        self.assertEqual(future.cpi_percent.tolist(), [.4] * 5)
        self.assertEqual(future.release_indicator.tolist(), [1, 0, 0, 0, 0])
        second, _ = self.commit(self.draft(.2, 1, "replace", "p1"), 1, "second")
        edited = second.json(); RunResponse.model_validate(edited)
        self.assertEqual(edited["series_mode"], "suffix")
        self.assertEqual(edited["changed_from"], DATES[0])
        self.assertEqual(edited["prompts"][0]["id"], "p1")
        self.assertEqual(edited["prompts"][0]["resolved_value"], .2)
        self.assertNotEqual(first["series"]["points"][-1]["value"], edited["series"]["points"][-1]["value"])
        restored = self.client.get(self.url).json()
        self.assertEqual(restored["series"]["points"], self.initial["series"]["points"] + edited["series"]["points"])
        self.assertEqual(self.client.get(self.url + "/revisions/1").json(), first)

    def test_restart_and_retry_before_expiry_staleness_or_inference(self):
        draft_id = self.draft()
        self.client, self.adapter = self.restart()
        response, body = self.commit(draft_id, 0, "first")
        first = response.json()
        self.commit(self.draft(.2, 1, "replace", "p1"), 1, "second")
        latest = self.client.get(self.url).json()
        self.client, self.adapter = self.restart()
        self.clock += timedelta(hours=1)
        self.assertEqual(self.client.get(self.url).json(), latest)
        self.assertEqual(self.client.get(self.url + "/revisions/1").json(), first)
        self.assertEqual(self.client.post(self.url + "/commit", json=body).json(), first)
        self.assertFalse(self.adapter._pipeline.calls)
        conflict = self.client.post(self.url + "/commit", json=dict(body, draft_id="other"))
        self.assertEqual(conflict.status_code, 409)
        env = dict(os.environ, APP_MODE="research", DATA_DIR=str(self.root), DATASET_VERSION="test-only", SQLITE_PATH=str(self.path), FORECAST_DEVICE="cpu")
        code = "from api.app import create_app; import json,sys; print(json.dumps(create_app().state.backend_service.get(sys.argv[1])))"
        output = subprocess.check_output([sys.executable, "-c", code, first["timeline_id"]], env=env, text=True)
        self.assertEqual(json.loads(output), latest)

    def test_july_relative_extra_prompts_and_unknown_input_preserve_state(self):
        before, _ = self.run_one()
        for text in ["Set September CPI to 0.2%", "2008", "Change CPI"]:
            response = self.client.post(self.url + "/interpret", json=dict(text=text, mode="replace", selected_prompt_id="p1", expected_revision=1))
            self.assertIn(response.json()["status"], {"unsupported", "needs_clarification"})
            self.assertEqual(len(response.json()["choices"]), 5)
        reveal = self.client.get(self.url + "/revisions/1/reveal").json()
        self.assertEqual([p["date"] for p in reveal["series"]["points"]], DATES)
        self.assertEqual(self.client.get(self.url).json(), before)
        self.assertEqual(len(self.adapter._pipeline.calls), 1)

    def submit_text(self, text, revision, selected=None):
        draft = self.client.post(self.url + "/interpret", json=dict(text=text,
            mode="replace" if selected else "add", selected_prompt_id=selected, expected_revision=revision))
        self.assertEqual(draft.json()["status"], "ready", draft.text)
        response, _ = self.commit(draft.json()["draft_id"], revision, f"step-{revision}")
        self.assertEqual(response.status_code, 200, response.text)
        RunResponse.model_validate(response.json())
        return response.json()

    def test_three_real_prompts_inherit_medians_and_edit_preserves_ids_and_history(self):
        texts = ["Set June 11 CPI to 0.4%", "July 15: add 0.1 percentage points to preceding reading",
                 "August 12: keep July simulated reading"]
        for rev, text in enumerate(texts):
            self.submit_text(text, rev)
        original = self.client.get(self.url).json()
        self.assertEqual([p["resolved_value"] for p in original["prompts"]], [.4, .5, .5])
        self.assertEqual(original["series"]["points"][-1]["date"], "2025-08-18")
        edited = self.submit_text("Set June 11 CPI to 0.2%", 3, "p1")
        self.assertEqual([p["id"] for p in edited["prompts"]], ["p1", "p2", "p3"])
        self.assertEqual([p["resolved_value"] for p in edited["prompts"]], [.2, .3, .3])
        self.assertEqual(edited["series_mode"], "suffix")
        self.assertEqual(edited["changed_from"], "2025-06-11")
        self.assertEqual(self.client.get(self.url).json()["series"]["points"][:20], self.initial["series"]["points"])
        self.assertEqual(self.client.get(self.url + "/revisions/3").json(), original)
        last_past, last_future, _ = self.adapter._pipeline.calls[-1]
        self.assertEqual(last_past.target.iloc[-1], 100.3)
        self.assertEqual(last_future.cpi_percent.tolist(), [.3] * 5)
        self.assertNotIn("target", last_future)
        before = self.client.get(self.url).json()
        self.submit_text("Set July 15 CPI to 0.2%", 4, "p2")
        prefix = lambda run: [p for p in run["series"]["points"] if p["date"] < "2025-07-15"]
        self.assertEqual(prefix(before), prefix(self.client.get(self.url).json()))
        limit = self.client.post(self.url + "/interpret", json=dict(text=texts[0], mode="add", expected_revision=5))
        self.assertEqual(limit.json()["code"], "research_prompt_limit")

    def test_continuous_inputs_reach_forecaster_and_references_survive_edits(self):
        from api.contracts import ParsedScenario
        from test_provider_parser import scenario
        class Parser:
            output = None
            def parse(self, request):
                raw = dict(self.output)
                raw.pop("measure")
                return ParsedScenario.model_validate(raw)
        parser = Parser()
        self.client.app.state.backend_service.parser = parser
        # Unlike the basic test engine, this one is horizon/context sensitive,
        # so it detects append-vs-replace segmentation regressions.
        predict = self.adapter._pipeline.predict_df
        def horizon_sensitive(past, future_df, **kwargs):
            result = predict(past, future_df, **kwargs)
            result[["0.1", "0.5", "0.9"]] += len(future_df) / 10 + float(past.target.iloc[-1]) / 100
            return result
        self.adapter._pipeline.predict_df = horizon_sensitive
        def submit(day, op, value, ref, revision, selected=None):
            parser.output = scenario(day, op, value, ref)
            return self.submit_text("provider-extracted assumption", revision, selected)
        submit("2025-06-11", "set", .35, None, 0)
        self.assertEqual(self.adapter._pipeline.calls[0][1].cpi_percent.tolist(), [.35] * 5)
        submit("2025-07-15", "add_pp", -.075, "preceding", 1)
        result = submit("2025-08-12", "carry", None, "date:2025-07-15", 2)
        self.assertEqual([p["resolved_value"] for p in result["prompts"]], [.35, .275, .275])
        before = self.client.get(self.url).json()
        # Same event log must not depend on append vs replace inference lengths.
        submit("2025-06-11", "set", .35, None, 3, "p1")
        self.assertEqual(self.client.get(self.url).json()["series"], before["series"])
        result = submit("2025-06-11", "set", -.15, None, 4, "p1")
        self.assertEqual([p["resolved_value"] for p in result["prompts"]], [-.15, -.225, -.225])
        self.assertEqual([p["id"] for p in result["prompts"]], ["p1", "p2", "p3"])
        self.assertEqual(self.adapter._pipeline.calls[-1][1].cpi_percent.tolist(), [-.225] * 5)
        before = self.client.get(self.url).json()
        count = len(self.adapter._pipeline.calls)
        parser.output = scenario("2025-07-15", "add_pp", -3.0, "preceding")
        draft = self.client.post(self.url + "/interpret", json=dict(text="lower by 3 pp", mode="replace", selected_prompt_id="p2", expected_revision=5)).json()
        failure, _ = self.commit(draft["draft_id"], 5, "out-of-range")
        self.assertEqual(failure.json()["code"], "resolved_cpi_out_of_range")
        self.assertEqual(self.client.get(self.url).json(), before)
        self.assertEqual(len(self.adapter._pipeline.calls), count)

    def test_reveal_is_revision_scoped_and_does_not_change_inference(self):
        before, _ = self.run_one()
        count = len(self.adapter._pipeline.calls)
        actual = self.client.get(self.url + "/revisions/1/reveal").json()
        from api.contracts import RevealResponse
        RevealResponse.model_validate(actual)
        self.assertEqual(len(self.adapter._pipeline.calls), count)
        self.assertEqual(actual["series"]["base_date"], before["series"]["base_date"])
        self.assertIn("IEX", actual["attribution"])
        self.assertEqual(actual["revision"], 1)
        self.assertEqual(self.client.get(self.url).json(), before)
        self.submit_text("Set June 11 CPI to 0.2%", 1, "p1")
        past, _, _ = self.adapter._pipeline.calls[-1]
        self.assertEqual(past.target.tolist(), [p["value"] for p in self.initial["series"]["points"]])
        self.assertEqual(self.client.get(self.url + "/revisions/1/reveal").json(), actual)
        self.assertEqual(self.client.get(self.url + "/revisions/999/reveal").status_code, 404)

    def test_moving_last_prompt_earlier_replaces_from_earlier_date_and_removes_tail(self):
        for rev, text in enumerate(["Set June 11 CPI to 0.4%",
                "July 15: add 0.1 percentage points to preceding reading",
                "August 12: keep July simulated reading"]):
            self.submit_text(text, rev)
        before = self.client.get(self.url).json()
        moved = self.submit_text("Set July 15 CPI to 0.2%", 3, "p3")
        self.assertEqual(moved["changed_from"], "2025-07-15")
        self.assertEqual(moved["replace_through"], "2025-08-18")
        self.assertEqual(moved["series"]["points"][-1]["date"], "2025-07-21")
        self.assertEqual([p["id"] for p in moved["prompts"]], ["p1", "p2", "p3"])
        after = self.client.get(self.url).json()
        prefix = lambda r: [p for p in r["series"]["points"] if p["date"] < "2025-07-15"]
        self.assertEqual(prefix(before), prefix(after))
        self.assertEqual(self.client.get(self.url + "/revisions/3").json(), before)

    def test_missing_and_corrupt_reveal_preserve_forecast(self):
        before, _ = self.run_one()
        (self.root / "reveal/test-only/spy_actuals.parquet").write_bytes(b"corrupt")
        response = self.client.get(self.url + "/revisions/1/reveal")
        self.assertEqual(response.json()["status"], "unsupported")
        self.assertEqual(self.client.get(self.url).json(), before)

    def test_server_rejects_out_of_scope_provider_output(self):
        from api.preset_parser import PresetParser
        class WrongDate(PresetParser):
            def parse(inner, request):
                parsed = super().parse(request)
                parsed.requested_start = "2025-09-11"
                parsed.release_dates = ["2025-09-11"]
                return parsed
        client, _ = self.restart(parser=WrongDate())
        result = client.post(self.url + "/interpret", json=dict(text="Set June 11 CPI to 0.4%", mode="add", expected_revision=0))
        self.assertEqual(result.json()["code"], "research_scope")
        self.assertEqual(client.get(self.url).json(), self.initial)

    def test_expired_and_stale_requests_preserve_state(self):
        draft_id = self.draft()
        self.clock += timedelta(minutes=5)
        response, _ = self.commit(draft_id, 0, "expired")
        self.assertEqual(response.status_code, 410)
        self.assertEqual(self.client.get(self.url).json(), self.initial)
        self.run_one()
        response, _ = self.commit(draft_id, 0, "stale")
        self.assertEqual(response.status_code, 409)

    def test_failed_or_malformed_inference_never_commits(self):
        draft_id = self.draft()
        original = self.adapter.forecast_segment
        def fail(request):
            raise RuntimeError("private engine detail")
        def wrong_dates(request):
            result = original(request)
            return result.model_copy(update=dict(points=result.points[:-1]))
        def unsupported(request):
            return ForecastResult(status="unsupported", reason="Insufficient support", engine="chronos-2-cpu",
                                  model_version=MODEL_VERSION, support_count=0, points=[], assumptions=[])
        for method, http in [(fail, 503), (wrong_dates, 503), (unsupported, 200)]:
            self.adapter.forecast_segment = method
            response, _ = self.commit(draft_id, 0, "try")
            self.assertEqual(response.status_code, http)
            self.assertNotIn("private engine detail", response.text)
            self.assertEqual(self.client.get(self.url).json(), self.initial)
            self.assertEqual(self.client.get(self.url + "/revisions/1").status_code, 404)
        self.adapter.forecast_segment = original
        self.assertEqual(self.commit(draft_id, 0, "try")[0].json()["revision"], 1)

    def test_changed_configuration_blocks_writes_but_preserves_restore_and_completed_retries(self):
        first, body = self.run_one()
        draft_id = self.draft(.2, 1, "replace", "p1")
        self.write_snapshot("another-snapshot")
        client, adapter = self.restart(settings=replace(self.settings, dataset_version="another-snapshot"))
        self.assertEqual(client.get(self.url).json(), first)
        self.assertEqual(client.post(self.url + "/commit", json=body).json(), first)
        self.assertEqual(self.commit(draft_id, 1, "changed", client)[0].status_code, 409)
        response = client.post(self.url + "/interpret", json=dict(text="Set June 11 CPI to 0.2%", mode="replace", selected_prompt_id="p1", expected_revision=1))
        self.assertEqual(response.json()["code"], "timeline_configuration_mismatch")
        self.assertFalse(adapter._pipeline.calls)
        fixture = TestClient(create_app(replace(self.settings, app_mode="fixture")))
        self.addCleanup(fixture.close)
        self.assertEqual(fixture.get(self.url).json(), first)
        self.assertEqual(self.commit(draft_id, 1, "fixture", fixture)[0].status_code, 409)

    def test_missing_or_modified_snapshot_fails_startup_without_synthetic_fallback(self):
        with self.assertRaises(FileNotFoundError):
            create_app(replace(self.settings, dataset_version="missing"))
        (self.snapshot / "spy_daily.parquet").write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            create_app(self.settings)

    def test_competing_research_commits_cannot_both_advance_one_revision(self):
        barrier = Barrier(2)
        class Competing(ChronosAdapter):
            def forecast_segment(inner, request):
                barrier.wait(timeout=10)
                return super().forecast_segment(request)
        clients = [self.restart(adapter=Competing(MarketInputs(self.snapshot), pipeline=FakePipeline()))[0] for _ in range(2)]
        drafts = [self.draft(v) for v in (.4, .2)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(self.commit, drafts[i], 0, f"race-{i}", clients[i]) for i in range(2)]
            responses = [j.result()[0] for j in jobs]
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409])
        self.assertEqual(self.client.get(self.url).json()["revision"], 1)
        with self.client.app.state.backend_service.store.connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM commits").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM revisions").fetchone()[0], 2)

    def test_fixture_app_remains_synthetic_even_with_research_environment(self):
        with patch.dict(os.environ, dict(APP_MODE="research", DATASET_VERSION="missing")):
            from api.fixture_app import app
            with TestClient(app) as client:
                caps = client.get("/api/capabilities").json()
                self.assertEqual(caps["mode"], "fixture")
                self.assertEqual(caps["max_prompts"], 3)


if __name__ == "__main__":
    unittest.main()
