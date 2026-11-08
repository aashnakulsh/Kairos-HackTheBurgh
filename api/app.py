"""Durable FastAPI app factory. Run with uvicorn api.app:create_app --factory."""
import sqlite3
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.backend_errors import BackendError
from api.contracts import (Capabilities, CommitRequest, CreateTimelineRequest,
    InterpretRequest, Problem, ReadyDraft, RevealResponse, RunResponse)
from api.durable_service import DurableService
from api.descriptions import OpenAIDescriptionProvider, register_description_route
from api.settings import Settings


def create_app(settings=None, *, parser=None, adapter=None, now=None, description_provider=None):
    settings = settings or Settings()
    title = "local historical research" if settings.app_mode in {"research", "scenario"} else "synthetic numerical adapter"
    app = FastAPI(title=f"TeamRelay durable API — {title}", version="1")
    service = DurableService(settings, parser=parser, adapter=adapter, now=now)
    app.state.backend_service = service
    app.add_middleware(CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.exception_handler(BackendError)
    async def domain_error(_, exc):
        return JSONResponse(status_code=exc.http, content=exc.problem.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_error(_, exc):
        return JSONResponse(status_code=422, content=Problem(status="invalid", code="validation_error",
            reason="Request does not match the API schema", choices=[], current_revision=None, retryable=False).model_dump())

    @app.exception_handler(sqlite3.Error)
    async def database_error(_, exc):
        return JSONResponse(status_code=503, content=Problem(status="unavailable", code="storage_unavailable",
            reason="Storage write/read failed; retry the identical request", choices=[],
            current_revision=None, retryable=True).model_dump())

    errors = {code: {"model": Problem} for code in (404, 409, 410, 422, 503)}
    register_description_route(app, service.get, description_provider or OpenAIDescriptionProvider(settings))

    @app.get("/api/capabilities", response_model=Capabilities)
    def get_capabilities():
        return service.capabilities()

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

    @app.get("/api/timelines/{timeline_id}/revisions/{revision}/reveal", response_model=RevealResponse | Problem, responses=errors)
    def reveal(timeline_id: str, revision: int):
        return service.reveal(timeline_id, revision)

    return app
