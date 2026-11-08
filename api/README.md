# Durable backend and numerical interface

The canonical handoff is `docs/frontend-backend-contract.md`. Capabilities, drafts,
reveal, parser and forecast schemas now exist in `contracts.py`. `fixture_app.py`
provides the local synthetic HTTP server with OpenAPI. `app.py` provides SQLite
revisions, idempotency and replay. `APP_MODE=research` now connects the pinned real
June–August dataset and offline CPU Chronos adapter for three dependent prompts and replacement.
See [startup commands and verification](../docs/real-data-adapter.md#run-the-research-api).

The shared numerical boundary uses `ForecastRequest`/`ForecastResult`:
`forecast_segment(request) -> result`, where request contains target/base identifiers,
data/model versions, frozen evidence cutoff, ordered eligible history (indexed levels),
aligned historical covariates and explicit future session/covariate rows for only the
current segment. Result contains ordered median/q10/q90 levels, engine/version,
support count, assumptions and supported/unsupported status with reason. No reveal data
enters this request. Aashna and Aditya work together in the same chat and folder.
Real multi-prompt replay and HTTP reveal are implemented; the fixture app
continues to provide a synthetic frontend journey.

## Frontend-initiated descriptions

After installing a complete committed forecast with `applyRun`, the frontend forwards
one prompt's raw simulated points to
`POST /api/timelines/{id}/revisions/{revision}/description`. `descriptions.py` validates
the points against that immutable revision, calls the OpenAI Responses API using
server-side `OPENAI_API_KEY` / `OPENAI_MODEL`, and returns separate plain-text prose.
`OPENAI_DESCRIPTION_TIMEOUT_SECONDS` defaults to 20. Commits never wait for narration;
provider failures leave the saved forecast unchanged. Fixture-only HTTP exposes the
same route but never calls OpenAI. The exact browser flow is documented in
[the API contract](../docs/frontend-backend-contract.md#forecast--frontend--openai--frontend).
