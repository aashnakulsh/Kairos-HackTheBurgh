# Aashna's first task

Implement FastAPI routes from architecture section 5 around `contracts.py`; add
capabilities, interpreted-draft and reveal schemas first. Add SQLite revision storage,
idempotency and replay separately. This directory does not contain a server yet.

Agree the model adapter with Aditya before either side calls it. Proposed boundary:
`forecast_segment(request) -> result`, where request contains target/base identifiers,
data/model versions, frozen evidence cutoff, ordered eligible history (indexed levels),
aligned historical covariates and explicit future session/covariate rows for only the
current segment. Result contains ordered median/q10/q90 levels, engine/version,
support count, assumptions and supported/unsupported status with reason. No reveal data
enters this request. Aashna owns replay; Aditya owns numerical inference. Finalize typed
request/result models together; this prose is not an implemented adapter.
