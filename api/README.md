# Durable backend and numerical interface

The canonical handoff is `docs/frontend-backend-contract.md`. Capabilities, drafts,
reveal, parser and forecast schemas now exist in `contracts.py`. `fixture_app.py`
provides the local synthetic HTTP server with OpenAPI. `app.py` provides SQLite
revisions, idempotency and replay. `APP_MODE=research` now connects the pinned real
June dataset and offline CPU Chronos adapter for one prompt and replacement.
See [startup commands and verification](../docs/real-data-adapter.md#run-the-research-api).

The shared numerical boundary uses `ForecastRequest`/`ForecastResult`:
`forecast_segment(request) -> result`, where request contains target/base identifiers,
data/model versions, frozen evidence cutoff, ordered eligible history (indexed levels),
aligned historical covariates and explicit future session/covariate rows for only the
current segment. Result contains ordered median/q10/q90 levels, engine/version,
support count, assumptions and supported/unsupported status with reason. No reveal data
enters this request. Aashna and Aditya work together in the same chat and folder.
Real multi-prompt replay and HTTP reveal remain subsequent tasks; the fixture app
continues to provide the existing complete synthetic frontend journey.
