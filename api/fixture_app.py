"""Local fixture-only HTTP handoff. No provider calls, secrets, or durable state."""
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.contracts import (Capabilities, CreateTimelineRequest, InterpretRequest,
    CommitRequest, ReadyDraft, RunResponse, RevealResponse, Problem)
from shared.fixture_service import FixtureService, FixtureError, capabilities
from api.backend_errors import BackendError
from api.descriptions import register_description_route


def create_app():
    app = FastAPI(title="TeamRelay fixture API — synthetic only", version="1")
    service = FixtureService()
    app.state.fixture_service = service
    app.add_middleware(CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.exception_handler(FixtureError)
    async def fixture_error(_, exc):
        return JSONResponse(status_code=exc.http, content=Problem.model_validate(exc.body).model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_error(_, exc):
        # Never echo raw input/key values in error messages.
        return JSONResponse(status_code=422, content=Problem(status="invalid", code="validation_error",
            reason="Request does not match the API schema", choices=[], current_revision=None, retryable=False).model_dump())

    errors = {code: {"model": Problem} for code in (404, 409, 410, 422, 503)}

    class DisabledDescriptions:
        def generate(self, context):
            raise BackendError(503, "unavailable", "description_not_configured",
                "Fixture-only server never calls OpenAI; use api.app for descriptions")

    @app.exception_handler(BackendError)
    async def description_error(_, exc):
        return JSONResponse(status_code=exc.http, content=exc.problem.model_dump())

    register_description_route(app, service.get, DisabledDescriptions())

    @app.get("/api/capabilities", response_model=Capabilities)
    def get_capabilities():
        return capabilities()

    @app.post("/api/timelines", status_code=201, response_model=RunResponse, responses=errors)
    def create(request: CreateTimelineRequest):
        return service.create(request)

    @app.get("/api/timelines/{timeline_id}", response_model=RunResponse, responses=errors)
    def restore(timeline_id: str):
        return service.get(timeline_id)

    @app.get("/api/timelines/{timeline_id}/revisions/{revision}", response_model=RunResponse, responses=errors)
    def historical(timeline_id: str, revision: int):
        return service.get(timeline_id, revision)

    @app.post("/api/timelines/{timeline_id}/interpret", response_model=ReadyDraft | Problem, responses=errors)
    def interpret(timeline_id: str, request: InterpretRequest):
        return service.interpret(timeline_id, request)

    @app.post("/api/timelines/{timeline_id}/commit", response_model=RunResponse | Problem, responses=errors)
    def commit(timeline_id: str, request: CommitRequest):
        return service.commit(timeline_id, request)

    @app.get("/api/timelines/{timeline_id}/revisions/{revision}/reveal", response_model=RevealResponse, responses=errors)
    def reveal(timeline_id: str, revision: int):
        return service.reveal(timeline_id, revision)

    return app


app = create_app()
