"""Durable timeline commands. No parser or numerical work runs under the write lock."""
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4
from api.backend_errors import BackendError
from api.contracts import Instruction, ParsedScenario, ReadyDraft
from api.preset_parser import PresetParser
from api.replay import candidate
from api.sqlite_store import SQLiteStore, body_hash, encode
from api.synthetic_forecast import LABEL, SyntheticAdapter
from shared.fixture_service import SESSIONS, capabilities, empty


class DurableService:
    def __init__(self, settings, parser=None, adapter=None, now=None):
        self.settings = settings
        self.research = None
        if settings.app_mode == "research":
            from api.research_backend import ResearchBackend
            self.research = ResearchBackend(settings, adapter)
        self.store = SQLiteStore(settings.sqlite_path)
        self.parser = parser or (self.research.parser if self.research else PresetParser())
        self.adapter = self.research.adapter if self.research else (adapter or SyntheticAdapter())
        self.now = now or (lambda: datetime.now(timezone.utc))

    def capabilities(self):
        if self.research:
            return self.research.capabilities()
        # Contract has fixture/live only. Keep fixture to advertise synthetic data
        # even though state is now durable; live would imply a real data pipeline.
        return capabilities()

    def _compatible(self, run):
        if self.research:
            self.research.compatible(run)
        elif run["dataset_version"] != "synthetic-v1":
            raise BackendError(409, "conflict", "timeline_configuration_mismatch",
                "This timeline requires its original research configuration", run["revision"])

    @staticmethod
    def _get(db, timeline_id, revision=None):
        row = db.execute("SELECT active_revision FROM timelines WHERE id=?", (timeline_id,)).fetchone()
        if row is None:
            raise BackendError(404, "not_found", "timeline_not_found", "Unknown timeline")
        revision = row[0] if revision is None else revision
        row = db.execute("SELECT snapshot FROM revisions WHERE timeline_id=? AND revision=?",
            (timeline_id, revision)).fetchone()
        if row is None:
            raise BackendError(404, "not_found", "revision_not_found", "Unknown revision")
        return json.loads(row[0])

    def get(self, timeline_id, revision=None):
        with self.store.connection() as db:
            return self._get(db, timeline_id, revision)

    @staticmethod
    def _retry(db, timeline_id, request):
        row = db.execute("SELECT body_hash,response FROM commits WHERE timeline_id=? AND request_id=?",
            (timeline_id, request.request_id)).fetchone()
        if row:
            if row["body_hash"] != body_hash(request):
                raise BackendError(409, "conflict", "request_id_reused", "Request ID reused with different body")
            return json.loads(row["response"])
        return None

    def create(self, request):
        with self.store.connection(write=True) as db:
            row = db.execute("SELECT body_hash,response FROM creates WHERE request_id=?", (request.request_id,)).fetchone()
            if row:
                if row["body_hash"] != body_hash(request):
                    raise BackendError(409, "conflict", "request_id_reused", "Creation ID reused with different body")
                return json.loads(row["response"])
            timeline_id = f"timeline-{uuid4().hex}"
            run = self.research.empty(timeline_id) if self.research else empty(timeline_id)
            run["model_version"] = self.adapter.model_version
            db.execute("INSERT INTO timelines VALUES (?,0)", (run["timeline_id"],))
            db.execute("INSERT INTO revisions VALUES (?,0,?)", (run["timeline_id"], encode(run)))
            db.execute("INSERT INTO creates VALUES (?,?,?)", (request.request_id, body_hash(request), encode(run)))
            return run

    def interpret(self, timeline_id, request):
        run = self.get(timeline_id)
        self._expected(run, request.expected_revision)
        self._compatible(run)
        if request.mode == "replace" and request.selected_prompt_id not in {p["id"] for p in run["prompts"]}:
            raise BackendError(422, "invalid", "unknown_prompt", "Unknown selected prompt", run["revision"])
        parsed = ParsedScenario.model_validate(self.parser.parse(request))
        if parsed.status != "parsed":
            raise BackendError(200, parsed.status, "choose_preset", parsed.reason, run["revision"], parsed.choices)
        day = parsed.requested_start
        # The server validates provider output independently. No arbitrary calendar,
        # recurring or interval behavior is promised by this release-only milestone.
        if self.research:
            instruction = self.research.instruction(run, request, parsed)
        elif (parsed.scope != "release" or parsed.date_precision != "day" or parsed.requested_end is not None
                or day not in SESSIONS[1:] or parsed.release_dates != [day]):
            raise BackendError(200, "unsupported", "unsupported_scope", "Only single covered synthetic release sessions are supported")
        else:
            instruction = Instruction(date_precision="day", requested_start=day, requested_end=None,
                effective_start=day, effective_end=None, effective_at=f"{day}T08:30:00-04:00",
                timezone="America/New_York", scope="release", release_dates=[day],
                operation=parsed.operation, value=parsed.value, unit=parsed.unit, reference=parsed.reference)
        draft = ReadyDraft(status="ready", draft_id=f"draft-{uuid4().hex}", timeline_id=timeline_id,
            expected_revision=run["revision"], mode=request.mode, selected_prompt_id=request.selected_prompt_id,
            text=request.text, expires_at=(self.now() + timedelta(seconds=self.settings.draft_ttl_seconds)).isoformat(),
            instruction=instruction, warnings=self.research.warnings if self.research else [LABEL])
        with self.store.connection(write=True) as db:
            self._expected(self._get(db, timeline_id), request.expected_revision)
            db.execute("INSERT INTO drafts VALUES (?,?,?)", (draft.draft_id, timeline_id, draft.model_dump_json()))
        return draft.model_dump()

    @staticmethod
    def _expected(run, expected):
        if run["revision"] != expected:
            raise BackendError(409, "conflict", "stale_revision", "Restore before reapplying", run["revision"])

    def _draft(self, db, timeline_id, request, run):
        row = db.execute("SELECT body FROM drafts WHERE id=? AND timeline_id=?",
            (request.draft_id, timeline_id)).fetchone()
        if row is None:
            raise BackendError(404, "not_found", "draft_not_found", "Unknown draft", run["revision"])
        draft = ReadyDraft.model_validate_json(row[0])
        if datetime.fromisoformat(draft.expires_at) <= self.now():
            raise BackendError(410, "draft_expired", "draft_expired", "Reinterpret the preserved text", run["revision"])
        if draft.expected_revision != run["revision"]:
            raise BackendError(409, "conflict", "stale_draft", "Draft is bound to another revision", run["revision"])
        return draft

    def commit(self, timeline_id, request):
        with self.store.connection() as db:
            retry = self._retry(db, timeline_id, request)
            if retry is not None:
                return retry
            old = self._get(db, timeline_id)
            self._expected(old, request.expected_revision)
            self._compatible(old)
            draft = self._draft(db, timeline_id, request, old)
        replay = self.research.candidate if self.research else candidate
        run, response = replay(old, draft, request.request_id, self.adapter)
        with self.store.connection(write=True) as db:
            # A competing identical request may have completed during inference.
            retry = self._retry(db, timeline_id, request)
            if retry is not None:
                return retry
            current = self._get(db, timeline_id)
            self._expected(current, request.expected_revision)
            self._draft(db, timeline_id, request, current)  # expiry also applies after slow inference
            changed = db.execute("UPDATE timelines SET active_revision=? WHERE id=? AND active_revision=?",
                (run["revision"], timeline_id, request.expected_revision)).rowcount
            if changed != 1:
                raise BackendError(409, "conflict", "stale_revision", "Restore before reapplying")
            db.execute("INSERT INTO revisions VALUES (?,?,?)", (timeline_id, run["revision"], encode(run)))
            db.execute("INSERT INTO commits VALUES (?,?,?,?)",
                (timeline_id, request.request_id, body_hash(request), encode(response)))
        return response

    def reveal(self, timeline_id, revision):
        run = self.get(timeline_id, revision)
        if self.research:
            from data.reveal import reveal_run
            from data.real_market import UnsupportedInput
            try:
                return reveal_run(self.settings.data_dir, run)
            except UnsupportedInput as exc:
                raise BackendError(200, "unsupported", "reveal_unavailable", str(exc), revision) from exc
            except (OSError, ValueError, KeyError) as exc:
                raise BackendError(503, "unavailable", "reveal_unavailable",
                    "Pinned actual-history data is missing or invalid; the forecast is unchanged", revision) from exc
        raise BackendError(200, "unsupported", "reveal_unavailable",
            ("HTTP actual-history reveal is not enabled for this research milestone. Use the separate local reveal reader."
             if self.research else "The synthetic runtime has no real reveal. The separate fixture server provides synthetic examples."), revision)
