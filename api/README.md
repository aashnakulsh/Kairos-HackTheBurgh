# Aashna's first task

The canonical handoff is `docs/frontend-backend-contract.md`. Capabilities, drafts,
reveal, parser and forecast schemas now exist in `contracts.py`. `fixture_app.py`
provides a local synthetic HTTP server with OpenAPI, not a production backend.
Implement live routes around these contracts, SQLite revisions, idempotency and replay.

Coordinate the model adapter with Aditya using `ForecastRequest`/`ForecastResult`:
`forecast_segment(request) -> result`, where request contains target/base identifiers,
data/model versions, frozen evidence cutoff, ordered eligible history (indexed levels),
aligned historical covariates and explicit future session/covariate rows for only the
current segment. Result contains ordered median/q10/q90 levels, engine/version,
support count, assumptions and supported/unsupported status with reason. No reveal data
enters this request. Aashna owns replay; Aditya owns numerical inference. Finalize typed
request/result behavior together; the real numerical adapter is not implemented.
