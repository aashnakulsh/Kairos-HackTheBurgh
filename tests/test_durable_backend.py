"""HTTP and SQLite acceptance tests; no model download, paid call or credentials."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Barrier
import unittest
from fastapi.testclient import TestClient
from api.app import create_app
from api.contracts import ForecastResult, RunResponse
from api.settings import Settings
from api.synthetic_forecast import SyntheticAdapter
from shared.fixture_service import PRESETS


class DurableTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "nested" / "backend.sqlite"
        self.settings = Settings(sqlite_path=self.path)
        self.clock = datetime(2026, 11, 8, tzinfo=timezone.utc)
        self.client = self.restart()
        result = self.client.post("/api/timelines", json={"target_id": "SPY", "request_id": "create"})
        self.assertEqual(result.status_code, 201)
        self.tid = result.json()["timeline_id"]
        self.url = f"/api/timelines/{self.tid}"
        self.texts = list(PRESETS)

    def restart(self, adapter=None):
        client = TestClient(create_app(self.settings, adapter=adapter, now=lambda: self.clock))
        self.addCleanup(client.close)
        return client

    def draft(self, text, revision, selected=None, client=None):
        response = (client or self.client).post(self.url + "/interpret", json=dict(text=text,
            expected_revision=revision, mode="replace" if selected else "add", selected_prompt_id=selected))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["draft_id"]

    def commit(self, draft, revision, key=None, client=None):
        body = dict(draft_id=draft, expected_revision=revision, request_id=key or f"commit-{revision}")
        return (client or self.client).post(self.url + "/commit", json=body), body

    def submit(self, text, revision, selected=None):
        response, body = self.commit(self.draft(text, revision, selected), revision)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json(), body

    def get(self):
        return self.client.get(self.url).json()

    def three(self):
        for revision, text in enumerate([self.texts[0], self.texts[2], self.texts[3]]):
            run, _ = self.submit(text, revision)
            RunResponse.model_validate(run)
        return self.get()

    def test_replay_ids_relative_assumptions_and_immutable_revision(self):
        before = self.three()
        self.assertEqual([p["resolved_value"] for p in before["prompts"]], [0.4, 0.5, 0.5])
        edited, _ = self.submit(self.texts[1], 3, "p1")
        self.assertEqual([p["resolved_value"] for p in edited["prompts"]], [0.2, 0.3, 0.3])
        self.assertEqual([p["id"] for p in edited["prompts"]], ["p1", "p2", "p3"])
        self.assertEqual(edited["prompts"][1]["value"], 0.1)
        self.assertEqual(edited["series_mode"], "suffix")
        self.assertEqual(edited["changed_from"], "2025-06-11")
        after = self.get()
        prefix = lambda run: [p for p in run["series"]["points"] if p["date"] < edited["changed_from"]]
        self.assertEqual(prefix(before), prefix(after))
        self.assertEqual(before, self.client.get(self.url + "/revisions/3").json())
        self.assertNotEqual(before["series"]["points"][-1]["value"], after["series"]["points"][-1]["value"])
        self.assertEqual(after["series_mode"], "full")

    def test_second_edit_preserves_prefix_without_reforecasting_it(self):
        before = self.three()
        calls = []
        class Recorder(SyntheticAdapter):
            def forecast_segment(inner, request):
                calls.append(request)
                return super().forecast_segment(request)
        self.client.app.state.backend_service.adapter = Recorder()
        edited, _ = self.submit(self.texts[4], 3, "p2")
        self.assertEqual(edited["series_mode"], "suffix")
        self.assertEqual(edited["changed_from"], "2025-07-15")
        earlier = lambda run: [p for p in run["series"]["points"] if p["date"] < "2025-07-15"]
        self.assertEqual(earlier(before), earlier(self.get()))
        self.assertTrue(all(row.date >= "2025-07-15" for call in calls for row in call.future))
        self.assertTrue(any(row.kind == "simulated" for row in calls[0].history))
        self.assertEqual([c.segment_id for c in calls], ["p2", "p3"])
        self.assertEqual(calls[0].future[-1].date, "2025-08-11")
        self.assertEqual(calls[1].history[-1].level, self.get()["series"]["points"][-6]["value"])

    def test_application_and_process_restart_preserve_drafts_runs_retries(self):
        draft = self.draft(self.texts[0], 0)
        self.client = self.restart()
        response, body = self.commit(draft, 0)
        before = self.get()
        self.client = self.restart()
        self.assertEqual(before, self.get())
        self.clock += timedelta(hours=1)
        self.assertEqual(response.json(), self.client.post(self.url + "/commit", json=body).json())
        code = "from api.app import create_app; from api.settings import Settings; from pathlib import Path; import sys,json; print(json.dumps(create_app(Settings(sqlite_path=Path(sys.argv[1]))).state.backend_service.get(sys.argv[2])))"
        output = subprocess.check_output([sys.executable, "-c", code, str(self.path), self.tid], text=True)
        self.assertEqual(json.loads(output), before)

    def test_duplicate_before_expiry_and_staleness_and_conflicting_body(self):
        original, body = self.submit(self.texts[0], 0)
        self.clock += timedelta(minutes=10)
        self.submit(self.texts[2], 1)
        self.assertEqual(original, self.client.post(self.url + "/commit", json=body).json())
        before = self.get()
        response = self.client.post(self.url + "/commit", json=dict(body, draft_id="other"))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "request_id_reused")
        self.assertEqual(before, self.get())

    def test_request_ids_are_scoped_to_timeline(self):
        self.submit(self.texts[0], 0)
        other = self.client.post("/api/timelines", json={"target_id": "SPY", "request_id": "other"}).json()
        old_url = self.url
        self.url = f"/api/timelines/{other['timeline_id']}"
        result, _ = self.submit(self.texts[1], 0)
        self.assertEqual(result["revision"], 1)
        self.assertNotEqual(result["timeline_id"], self.tid)
        self.url = old_url

    def test_draft_bound_to_timeline_revision_and_selection(self):
        draft = self.draft(self.texts[0], 0)
        other = self.client.post("/api/timelines", json={"target_id": "SPY", "request_id": "other"}).json()
        response = self.client.post(f"/api/timelines/{other['timeline_id']}/commit",
            json=dict(draft_id=draft, expected_revision=0, request_id="wrong"))
        self.assertEqual(response.status_code, 404)
        self.submit(self.texts[0], 0)
        response, _ = self.commit(draft, 1, "stale-draft")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "stale_draft")
        response = self.client.post(self.url + "/interpret", json=dict(text=self.texts[1], mode="replace",
            selected_prompt_id="missing", expected_revision=1))
        self.assertEqual(response.status_code, 422)

    def test_expired_and_stale_commits_preserve_state(self):
        draft = self.draft(self.texts[0], 0)
        self.clock += timedelta(minutes=5)
        before = self.get()
        response, _ = self.commit(draft, 0)
        self.assertEqual(response.status_code, 410)
        self.assertEqual(before, self.get())
        self.submit(self.texts[0], 0)
        before = self.get()
        response, _ = self.commit(draft, 0, "stale")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(before, self.get())

    def test_expiry_during_inference_prevents_commit(self):
        test = self
        class Slow(SyntheticAdapter):
            def forecast_segment(inner, request):
                test.clock += timedelta(minutes=6)
                return super().forecast_segment(request)
        self.client.app.state.backend_service.adapter = Slow()
        draft = self.draft(self.texts[0], 0)
        response, _ = self.commit(draft, 0)
        self.assertEqual(response.status_code, 410)
        self.assertEqual(self.get()["revision"], 0)

    def test_date_moves_use_earlier_start_and_keep_cutoff(self):
        first, _ = self.submit(self.texts[0], 0)
        later, _ = self.submit(self.texts[4], 1, "p1")
        self.assertEqual(later["changed_from"], "2025-06-11")
        self.assertEqual(later["evidence_cutoff"], first["evidence_cutoff"])
        self.assertEqual(later["prompts"][0]["id"], "p1")
        earlier, _ = self.submit(self.texts[1], 2, "p1")
        self.assertEqual(earlier["changed_from"], "2025-06-11")
        self.assertEqual(earlier["replace_through"], "2025-07-21")
        self.assertLess(earlier["series"]["points"][-1]["date"], earlier["replace_through"])

    def test_addition_bridge_and_suffix_both_reconstruct_restore(self):
        cached = self.get()
        for revision, text in enumerate([self.texts[0], self.texts[2], self.texts[3], self.texts[1]]):
            response, _ = self.submit(text, revision, "p1" if revision == 3 else None)
            points = response["series"]["points"]
            if response["series_mode"] == "suffix":
                points = [p for p in cached["series"]["points"] if p["date"] < response["changed_from"]] + points
            cached = dict(response, series=dict(response["series"], points=points))
            self.assertEqual(cached["series"], self.get()["series"])

    def test_unsupported_clarification_and_broken_reference_preserve_state(self):
        before = self.get()
        for text, status in [("Change CPI", "needs_clarification"), ("President in 2008", "unsupported")]:
            response = self.client.post(self.url + "/interpret", json=dict(text=text, mode="add", expected_revision=0))
            self.assertEqual(response.json()["status"], status)
        response, _ = self.commit(self.draft(self.texts[3], 0), 0)
        self.assertEqual(response.json()["code"], "broken_reference")
        self.assertEqual(before, self.get())

    def test_adapter_failure_unsupported_and_wrong_sessions_preserve_state(self):
        draft = self.draft(self.texts[0], 0)
        class Failure(SyntheticAdapter):
            def forecast_segment(inner, request):
                raise RuntimeError("private provider detail")
        class Unsupported(SyntheticAdapter):
            def forecast_segment(inner, request):
                return ForecastResult(status="unsupported", reason="No coverage", engine="synthetic",
                    model_version=inner.model_version, support_count=0, points=[], assumptions=[])
        class WrongDates(SyntheticAdapter):
            def forecast_segment(inner, request):
                result = super().forecast_segment(request)
                return result.model_copy(update={"points": result.points[:-1]})
        for adapter, status in [(Failure(), 503), (Unsupported(), 200), (WrongDates(), 503)]:
            self.client.app.state.backend_service.adapter = adapter
            response, _ = self.commit(draft, 0)
            self.assertEqual(response.status_code, status)
            self.assertNotIn("private provider detail", response.text)
            self.assertEqual(self.get()["revision"], 0)

    def test_failed_transaction_rolls_back_pointer_snapshot_and_retry_record(self):
        service = self.client.app.state.backend_service
        with service.store.connection() as db:
            db.execute("CREATE TRIGGER fail_commit BEFORE INSERT ON commits BEGIN SELECT RAISE(ABORT, 'injected disk failure'); END")
        draft = self.draft(self.texts[0], 0)
        response, body = self.commit(draft, 0)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.get()["revision"], 0)
        self.assertEqual(self.client.get(self.url + "/revisions/1").status_code, 404)
        with service.store.connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM commits").fetchone()[0], 0)
            db.execute("DROP TRIGGER fail_commit")
        self.assertEqual(self.client.post(self.url + "/commit", json=body).json()["revision"], 1)

    def test_competing_writes_only_one_commits_across_app_instances(self):
        barrier = Barrier(2)
        class Competing(SyntheticAdapter):
            def forecast_segment(inner, request):
                barrier.wait(timeout=10)
                return super().forecast_segment(request)
        clients = [self.restart(Competing()), self.restart(Competing())]
        drafts = [self.draft(self.texts[i], 0) for i in (0, 1)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(self.commit, drafts[i], 0, f"race-{i}", clients[i]) for i in range(2)]
            responses = [job.result()[0] for job in jobs]
        self.assertEqual(sorted(r.status_code for r in responses), [200, 409])
        self.assertEqual(self.get()["revision"], 1)
        with self.client.app.state.backend_service.store.connection() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM commits").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT count(*) FROM revisions").fetchone()[0], 2)

    def test_concurrent_identical_retries_return_one_original_response(self):
        barrier = Barrier(2)
        class Competing(SyntheticAdapter):
            def forecast_segment(inner, request):
                barrier.wait(timeout=10)
                return super().forecast_segment(request)
        clients = [self.restart(Competing()), self.restart(Competing())]
        draft = self.draft(self.texts[0], 0)
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(self.commit, draft, 0, "same", client) for client in clients]
            responses = [job.result()[0] for job in jobs]
        self.assertEqual([r.status_code for r in responses], [200, 200])
        self.assertEqual(responses[0].json(), responses[1].json())
        self.assertEqual(self.get()["revision"], 1)

    def test_revisions_are_immutable_at_storage_boundary(self):
        with self.client.app.state.backend_service.store.connection() as db:
            for sql in ["UPDATE revisions SET snapshot='{}'", "DELETE FROM revisions"]:
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute(sql)

    def test_create_retry_is_durable_and_reveal_is_honest(self):
        self.submit(self.texts[0], 0)
        self.client = self.restart()
        response = self.client.post("/api/timelines", json={"target_id": "SPY", "request_id": "create"})
        self.assertEqual(response.json()["timeline_id"], self.tid)
        self.assertEqual(response.json()["revision"], 0)
        before = self.get()
        reveal = self.client.get(self.url + "/revisions/1/reveal")
        self.assertEqual(reveal.json()["status"], "unsupported")
        self.assertEqual(before, self.get())


if __name__ == "__main__":
    unittest.main()
