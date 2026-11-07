# API handoff review

**GO WITH CONDITIONS** — frontend fixture work can begin; live backend is not ready.

Scope: architecture and pasted frontend requirements, repository instructions, README,
the full tracked/untracked file tree, schemas/types, fixture generators and handoff
notes. No proposed `docs/frontend-backend-contract.md` or Google Doc URL existed, so
the pasted copy supplied the requirements. The canonical spec now lives at that path.
The initial tree was clean on `3-foundation-contract-placeholders`; no teammate code
was overwritten. The existing PR #4 was closed unmerged at inspection, and main held
only documentation/board tooling. This review continues the same foundation branch.
Local inbox was checked at start and again before publication: notification test and
previous foundation announcement only; neither was archived.

## Findings and resolutions

The exact source conflicts and consequences are in the canonical spec's first table.
Key decisions follow architecture.md: trading-session points, backend-only prompt
parsing, stable IDs rather than indexes, one SPY target and supported impact rows rather
than promised company charts. The viewport is independent of data coverage/scenario
dates. No new product scope was inferred from the abbreviated pasted notes.

Implemented contract gaps: creation request, capabilities, revision-bound expiring
drafts, error body, historical snapshot retrieval, separate reveal, parser output and
numerical-adapter request/result. Added strict fields/date/unit/quantile checks,
source-linked hypotheses, resolved assumptions, creation ordering, timezone and run
provenance. Strengthened suffix deletion semantics and earlier-fork evidence cutoff.

New local fixture HTTP routes and typed frontend client/cache now exercise the
documented boundaries without models, credentials or a React app. The fixture service
is deterministic in-memory code with a tiny named-preset parser and clearly synthetic
arithmetic. It is not an implementation of production economics, persistence, interval
replay or providers. All fixtures are generated from that service where applicable;
standalone short/empty suffix and panel examples are explicitly UI examples.

## Verification actually run

| Check | Result |
|---|---|
| `python tools/export_contracts.py --check` | PASS: generated JSON Schema, OpenAPI and TypeScript match source |
| `python tools/build_example_fixtures.py --check` | PASS: 34 typed fixtures and journey manifest reproducible |
| `python tools/check_fixtures.py` | PASS: all 34 validated by JSON Schema plus Pydantic semantic validators |
| `python -m unittest discover -s tests -p "test_*.py" -v` | PASS: 15 Python HTTP/schema tests |
| `node --test tests/frontend-contract.test.mjs` | PASS: 4 frontend client/cache tests |
| Pinned TypeScript 5.9.3 strict no-emit check (command in canonical spec) | PASS: generated types, API client and cache update |
| Uvicorn on 127.0.0.1:8765, GET capabilities and OpenAPI | PASS: both HTTP 200, fixture label and presets present; process stopped after smoke check |
| Diff whitespace review | PASS |

Python tests verify the full empty/create/add/add/add/replace/reveal HTTP journey;
0.4/0.5/0.5 becomes 0.2/0.3/0.3; p1/p2/p3 survive; earlier points remain identical;
revision 3 remains retrievable; later synthetic numerical outcomes change. They also
verify second-prompt edits retain earlier simulated points, date moves in both
directions, tighter cutoff for an earlier fork, duplicate commit returning the original
result even after expiry, conflicting reuse, stale revision rejection, unsupported and
clarification no-ops, broken references, expiry, 404/422 and separate reveal reads.
Schema tests reject future target fields/observations, invalid dates, inverted bands,
wrong delta units and numeric qualitative impacts. Parser examples validate identically
for the two provider labels; this is not a provider conformance test.

Frontend tests verify immutable full/suffix application, complete three-prompt cache
journey, short/empty tail deletion, stale parent/request/timeline/base rejection, request
methods/paths/bodies and 409 handling. They do not test a rendered browser UI.

An initial Node test failed because TypeScript parameter properties are unsupported by
native stripping; replaced those with explicit fields and reran successfully. No final
test failures remain. The installed Starlette TestClient emits a non-failing deprecation
warning for httpx; production dependency consolidation remains Aashna's task.

## Not verified live / remaining owners

| Owner | First task / live blocker |
|---|---|
| Aashna | Review contract; build durable routes/revisions/idempotency and production replay around these schemas. Implement OpenAI primary and local Qwen adapters, validate schema transport, quota/timeout/offline fallbacks and keep event key server-side. Coordinate the one frontend scaffold |
| Aditya | Produce approved/versioned data and session calendar, implement `ForecastRequest -> ForecastResult` for Chronos and empirical baseline, validate numeric input/date alignment, as-of evidence and held-out evaluation on real host |
| Chohan | Build chart/timeline using fixtures and committed state; connect stable marker IDs, trading-session bands/gaps, suffix animation and separate reveal overlay |
| Orion | Wire composer/workspace to `createApi()` and `applyRun()`; preserve draft/committed state on failures, select/replace by ID, prevent stale responses, show synthetic/coverage/status labels |

Only paper/source review covers provider fallback budgets, real model invocation,
interval overlap/expiry/recurrence, licensed evidence/impacts, real reveal data, database
transaction concurrency/durability, historical scoring, real host latency, mobile,
keyboard and animation. No OpenAI/Ollama/Chronos request, data download or event-key
use occurred. The numerical fixture does not demonstrate forecast accuracy.

## Changed files

- Spec/review: `docs/frontend-backend-contract.md`, this report; updated
  `docs/architecture.md`, `docs/getting-started-team.md`, root `README.md`.
- Backend boundary and mock: `api/contracts.py`, `api/fixture_app.py`, `api/README.md`.
- Shared outputs/fixtures: `shared/contracts.schema.json`, `shared/openapi.json`,
  `shared/journey.json`, `shared/fixture_service.py`, `shared/README.md`, all examples
  listed individually by model in `shared/fixtures/manifest.json`.
- Frontend boundary: `web/src/generated/contracts.ts`, `web/src/api/client.ts`,
  `web/src/api/applyRun.ts`, `web/README.md`.
- Verification/config: `tools/export_contracts.py`, `tools/build_example_fixtures.py`,
  `tools/check_fixtures.py`, `tests/test_contract_journey.py`,
  `tests/frontend-contract.test.mjs`, `requirements-contracts.txt`, `.env.example`.

Use the exact install/check/start commands in the canonical spec. Review the pending
branch before merging; there is no guarantee of conflict-free integration. All team
handoff announcements belong on pinned Message Board issue #1.
