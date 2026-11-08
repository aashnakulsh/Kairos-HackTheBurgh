# Frontend/backend handoff — contract v1

**Current runtime:** `api.app:create_app` supplies the durable fixture/research API;
`api.fixture_app:app` remains a synthetic, in-memory handoff. The full React app is
in the separate frontend worktree, with its integration preserved in
`integration/frontend-research.patch`. The review history below describes earlier
milestones; the current description flow here supersedes older narration ownership.

The runtime schema source is `api/contracts.py`; generated copies are
`shared/contracts.schema.json`, `shared/openapi.json` and
`web/src/generated/contracts.ts`. Regenerate all three with
`python tools/export_contracts.py`; do not edit the generated copies manually.

## Forecast → frontend → OpenAI → frontend

The browser orchestrates a **separate description request after a successful forecast**:

1. Interpret/commit a scenario as usual. Commit returns numeric `series.points` immediately;
   it does not call OpenAI. In research mode these are the validated Chronos median (`value`),
   q10 and q90 index levels, mapped to exchange-session dates without display rounding.
2. Apply the response using `applyRun()` so the browser has the complete saved revision.
   Suffix responses alone may omit part of a prompt's segment.
3. Forward the selected prompt's complete simulated segment to the description relay.
   The relay checks the points against the immutable saved revision and adds the saved
   assumptions, scenario context, starting level, model/base identity and source metadata.
4. The relay calls the OpenAI Responses API with its **server-side** key. OpenAI returns
   prose to the relay, which returns `DescriptionResponse` to the frontend.
5. Display that prose separately from the committed forecast. Check timeline, revision,
   run and prompt IDs before displaying it. An edit invalidates older descriptions.
   OpenAI text never replaces points, changes assumptions, or creates a revision.

```text
Chronos → backend commit → frontend chart + raw forecast numbers
                                  ↓ frontend POSTs those numbers
                            backend description relay
                                  ↓ server-side API key
                                OpenAI
                                  ↓ description
                            backend relay → frontend description
```

### Description endpoint

`POST /api/timelines/{timeline_id}/revisions/{revision}/description`

Request `DescriptionRequest`:

- `prompt_id`: stable prompt ID from that saved revision.
- `forecast_points`: **all** simulated `Point` objects for that prompt, in saved order.
  Include date, kind, value, q10, q90, engine and segment_id exactly as received.
  Never send rounded chart labels, observed history, revealed actuals, or only an edit suffix.
  The current limit is 65 points.

Typed browser usage (implemented in `web/src/api/client.ts`):

```ts
import { applyRun } from "./applyRun.ts";
import { createApi, descriptionRequest, matchesDescription } from "./client.ts";

const api = createApi();
const committed = await api.commit(timelineId, commitRequest);
if ("revision" in committed) {
  const full = applyRun(previousRun, committed, commitRequest.request_id);
  // Install full in chart state now; narration must not block it.
  const description = await api.describe(full.timeline_id, full.revision,
    descriptionRequest(full, selectedPromptId));
  // Compare against the CURRENT run/selection when this asynchronous response arrives.
  if (matchesDescription(currentRun, currentPromptId, description)) {
    // Display description.description as plain text in the description panel.
  }
}
```

Response `DescriptionResponse` has `timeline_id`, `revision`, `run_id`, `prompt_id`,
`description` (plain text), `provider: "openai"` and the configured `model` ID.
No credentials are returned. The existing `panels` remain usable as basic fallback
text; generated descriptions are separate browser state, not persisted panel edits.
The integrated UI requests the focused/selected prompt after commit/restore, caches
successful descriptions for that revision during the browser session, and cancels or
ignores obsolete requests. Reload may request a new description; prose can differ.

Errors use `Problem`: 404 for missing timeline/revision/prompt; 409 `forecast_mismatch`
for altered, reordered or incomplete points; 422 for invalid bodies; 503
`description_not_configured` for missing server credentials/model or
`description_unavailable` for provider/network/timeout/refusal/incomplete-output failures.
A narration failure keeps the graph and basic description. There are no automatic
provider retries, no numerical rerun and no change to timeline state. The fixture-only
server exposes the same route but always returns 503 after validating the saved segment;
it never makes provider calls, even if credentials exist in its environment.

Enable narration on the durable app by exporting `OPENAI_API_KEY`, `OPENAI_MODEL`
(an available text model in your API project), and optionally
`OPENAI_DESCRIPTION_TIMEOUT_SECONDS=20` before server startup. `.env.example` is
reference only; it is not loaded automatically. Never put keys in `VITE_*` variables.
Each uncached description request can incur an OpenAI API call; the implementation
uses `store: false`, a bounded output and one attempt. No live paid call was required
for local verification.

OpenAI receives the forwarded forecast points plus saved context, not revealed actuals
or the full raw market dataset. Source metadata is not source passage text; the narrator
is instructed to describe supplied numbers and assumptions without inventing causal
explanations, industry impacts or citations. OpenAI's [Responses text guide](https://developers.openai.com/api/docs/guides/text)
and [API key guidance](https://developers.openai.com/api/docs/guides/api-keys) document
the provider interface and server-side credential handling.

## 1. Inventory and exact conflicts resolved

| Evidence | Gap/conflict and consequence | Resolution |
|---|---|---|
| Pasted Doc: “Every month is a datapoint”; architecture §4 and old `api/contracts.py:Series.frequency` | Monthly chart points would hide the five-session forecast and misalign CPI announcement dates | Wire series is ordered **trading-session** data. Month/year labels and viewport settings are display concerns; do not aggregate forecast inputs into monthly shocks |
| Pasted Doc: graphs “for each company”; architecture §6 | No company price producer, approved datasets or models exist | v1 supplies one SPY series and typed direct/indirect impacts. No company graphs promised; adding them is a separately scoped product extension |
| Frontend-initiated OpenAI descriptions; architecture §§1,4,8 | Parsing and narration have different inputs and responsibilities | Browser sends scenario text to `/interpret`; after commit it forwards raw forecast points to `/description`. The description relay calls OpenAI using a server key and returns prose; interpretation remains independently validated |
| Pasted Doc: prompt number may be zero-indexed; architecture §3 | Reordering dates would make array positions identify the wrong prompt | Use opaque stable `id` in commands; immutable one-based `display_number` is presentation only; `creation_order` breaks ties |
| Pasted Doc: timeframe in years | Ambiguous whether viewport or economic intervention | Year settings are local `Viewport`, default 1980–2026. Requested scenario dates come from raw text and returned instruction; a bare year needs release/rule clarification |
| Old `api/contracts.py` / `shared/README.md` | Missing create, capabilities, draft, reveal and model payloads; arbitrary strings for dates; no quantile/unit checks | Added types, validators, examples, OpenAPI and fixture routes; optional interpret fields now have defaults; null output fields remain explicit |
| Old `tools/check_fixtures.py` | Single prompt/static suffix checks could not establish three-prompt or retry behavior | Added full fixture HTTP journey, preserved revisions, duplicate/stale/unsupported tests and frontend cache tests |
| `README.md` | Claimed no stack selected despite architecture §1 | Updated to selected stack and fixture startup instructions |

Before this review there were no backend routes, frontend API calls, app components,
database, dependency files, runtime config example or test suite. Starter files were
on `3-foundation-contract-placeholders`, not main. The working tree was clean.
After review, `api/fixture_app.py` supplies **fixture routes only**; `web/src/api/client.ts`
supplies a typed caller and `applyRun.ts` supplies the pure cache update. There is still
no React/Vite application, production backend, provider adapter or real dataset.

## 2. Browser journey and endpoints

JSON over HTTP; ISO `YYYY-MM-DD` session labels; timezone-aware ISO timestamps for
effective instants, expiry and evidence. The canonical schemas define every required
field. Interpret's `selected_prompt_id` and `playhead` may be omitted or null. Other
nullable response fields are present as null. Unknown fields are rejected.

All browser callers below are methods of `createApi()` in `web/src/api/client.ts`.
All local endpoint producers are in `api/fixture_app.py`, backed by the synthetic
`shared/fixture_service.py`. Intended React components remain to be implemented.

| User action / future UI owner | Caller → endpoint | Request → response / failure |
|---|---|---|
| Empty screen, Orion | `capabilities()` → GET `/api/capabilities` | No body → `Capabilities`: coverage, frequency, units, default viewport, caps and synthetic/live label. A failed load keeps empty UI with retry |
| First submission, Orion composer | `create()` → POST `/api/timelines` | `CreateTimelineRequest` (`target_id`, client-generated `request_id`) → 201 full `RunResponse`, revision 0. Save `timeline_id`; retry same creation ID/body after uncertain transport result |
| Interpret prompt 1, Orion | `interpret()` → POST `/api/timelines/{id}/interpret` | Raw text, `mode=add`, expected revision 0 → `ReadyDraft` or HTTP 200 `Problem` with clarification/unsupported. No graph mutation |
| Commit prompt 1, Orion then Chohan chart | `commit()` → POST `/api/timelines/{id}/commit` | `draft_id`, expected revision 0, unique request ID → full `RunResponse`, revision 1, observed prefix plus simulated median/q10/q90. Only success changes chart |
| Add prompts 2 and 3 | Same interpret/commit pair | expected revision 1 then 2; successes advance to 2 then 3 and return suffixes. Complete prompt list and panels accompany every success |
| Click prompt 1, Chohan → Orion | Local `onSelectPrompt("p1")` callback | No HTTP call. Load existing text, highlight composer, label Replace prompt [1]. Escape cancels selection; no model call |
| Replace prompt 1 | `interpret()` then `commit()` | `mode=replace`, selected ID `p1`, expected revision 3. New ready draft binds those values; commit returns revision 4, parent 3, `series_mode=suffix`, `changed_from=2025-06-11` |
| Restore/reload | `restore()` → GET `/api/timelines/{id}` | Full latest `RunResponse`, including observed prefix; restart fixture server loses this in-memory state |
| Inspect previous branch | `revision()` → GET `/api/timelines/{id}/revisions/{revision}` | Full immutable earlier snapshot, displayed separately; never install it as a new active revision |
| Reveal actual history, explicit user action | `reveal()` → GET `/api/timelines/{id}/revisions/{revision}/reveal` | `RevealResponse`: same base/units, observed/gap points, sources/attribution. Store as a separate overlay; do not feed into forecasts or mutate run. Local fixture reveal is synthetic, not actual data |

`shared/journey.json` maps each request and response to a validated JSON fixture, in
execution order. It is exercised against fixture HTTP routes by the Python test suite
and against the typed client by Node tests. The full fixture journey uses these texts:

1. `Set June 11 CPI to 0.4%`
2. `July 15: add 0.1 percentage points to preceding reading`
3. `August 12: keep July simulated reading`
4. Select p1, replace with `Set June 11 CPI to 0.2%`.

The resulting assumptions are **0.2, 0.3, 0.3**, with p1/p2/p3 unchanged. `value` on
the second instruction remains the relative delta 0.1; `resolved_value` is 0.3 in
percent. `carry` has null `value`, percent unit and an explicit reference.

## 3. Dates, state, bands, panels and full/suffix updates

- `0.4` with `unit=percent` means 0.4%, not 40%. `add_pp` uses percentage_points.
  A market series is an indexed level, with fixed `base_date`, `base_value`, target
  and trading-session frequency across revisions. Preserve raw precision in transit.
- Backend retains requested dates separately from resolved sessions and effective
  instants. Execute by effective instant, then creation order. After-close/non-session
  events shift to next eligible session. Calendar membership requires the real service.
- Bare years mean inclusive requested spans but do not authorize every CPI release.
  Ask for a single release or explicit recurring rule; recurring `release_dates` lists
  the exact activations. Intervals require end bounds. The production coordinator must
  implement architecture §3 overlap, expiry and relative-reference rules.
- Initial/restore responses are full. For a suffix, require matching timeline and
  `parent_revision`, and the current pending request ID. Keep cached points strictly
  before `changed_from`; discard **all** old points from that date through the old end,
  then append the returned points. `replace_through` is max(old/new affected end).
  A shorter or empty suffix must erase the obsolete tail. Use `applyRun()`.
- Replace prompts and panels atomically with points. An obsolete response must not
  replace newer text/chart state. Abort old requests for UI convenience, but do not
  assume abort canceled a server commit; restore/retry with the original request ID.
- Replacing dates uses min(old effective start, new effective start). Keep old revision
  immutable. Later segments inherit the edited simulated median trajectory and resolve
  their relative inputs again; never silently substitute observed future prices.
- Freeze evidence before the first fork. Keep that cutoff for downstream replay and
  when moving the fork later. If moving the first fork earlier, **tighten** cutoff to
  the earlier fork as necessary; keeping a later cutoff would leak future evidence.
- `simulated` points require ordered q10 ≤ value ≤ q90 plus engine/segment ID;
  `observed` has value but null quantiles; `gap` has null value/quantiles. Never connect
  across unavailable coverage as though it were observed data. Keep reveal separate.
- `panels[prompt_id]` provides summary, labeled hypotheses, evidence, impacts, horizon,
  comparator, engine and support count. Every cited ID must exist in panel evidence;
  hypotheses require citations or `user_assumption=true`. Evidence includes title,
  URL, publication timestamp and passage locator. Real evidence must satisfy cutoff.
- Quantified impacts separate nonnegative magnitude from direction. proxy_change uses
  percent of the proxy's own starting level; index_contribution uses percentage points
  with a verified decomposition. Qualitative rows have null magnitude/unit. The
  `panel-example` fixture demonstrates formatting only, with synthetic source labels.
  Empty impacts are valid; do not invent rows to reach a target count.
- Runs include `run_id`, dataset/model/corpus versions and evidence cutoff for provenance.
  Synthetic examples advertise synthetic versions; live producers must supply actual
  pinned versions and retain the corresponding snapshots/settings server-side.

## 4. Errors, retries and drafts

Every domain/error body is `Problem {status, code, reason, choices, current_revision,
retryable}`. `choices` are suggested replacement text for a new interpretation; they
are not executable provider commands. `ReadyDraft.status=ready` distinguishes success.
Run successes have `revision`; do not install a Problem as chart state.

| HTTP | Meaning and client action |
|---|---|
| 200 with needs_clarification/unsupported | No accepted write. Keep graph and draft; show reason/choices. Ask user before reinterpreting a choice |
| 404 | Missing timeline/revision/draft. Restore available state or offer a new session |
| 409 | Stale expected revision or same request ID with a different body. Preserve unsent text, restore full snapshot, offer reapply and reinterpret |
| 410 | Draft expired. Preserve text and reinterpret against latest revision |
| 422 | Invalid shape, date, units or selected prompt. Show validation problem; leave committed state untouched |
| 503 | Service unavailable without a supported fallback. Preserve state; retry explicitly as appropriate |
| Transport failure | Commit may already have succeeded. Retry the **identical** body with the **same** request ID, or restore; never generate a new ID for a blind retry |

Interpret drafts expire after five minutes and bind timeline, revision, original text,
mode and selected ID. A fully specified ready draft may auto-commit on Enter. An
ambiguous draft never auto-commits. Interpretation alone does not create a revision.
Store successful canonical instructions; replay never calls the parser again.

Scope commit idempotency to timeline and request ID; store canonical request hash and
original response. Return a completed identical retry **before** checking stale revision
or draft expiry. Reused ID/different body is 409. Production must build candidate results
outside the write transaction then compare-and-swap revision, caches and timeline pointer
atomically. In-memory fixture tests do not prove database transactions/concurrency.

An explicitly accepted qualitative revision may have empty numeric suffix and unsupported
panel. The standalone `empty-suffix` example covers display behavior; the fixture server
does not implement a qualitative acceptance workflow. Rejected unsupported input is a
Problem and never creates that revision automatically.

## 5. Backend/model boundary

Browser initiates OpenAI narration through the description relay documented above.
Provider credentials and the actual OpenAI HTTP call stay on the server. Parsing and
numerical inference remain backend responsibilities. `.env.example` contains only
empty/example values; the fixture-only server never calls providers.

**Parser:** primary server-side OpenAI Responses API; architecture default model
`gpt-6-luna` subject to account access. Both primary and local Qwen/Ollama must produce
`ParsedScenario` and pass the same Python validation, then domain validation resolves
dates, units, references and supported numeric levers into `Instruction`. Invalid
schema, timeout, quota, transport or unavailable model triggers one local attempt.
Use 5-second primary and 12-second warm local budgets as architecture defaults. If
both fail, offer a checked preset for explicit confirmation or return clarification/
503; never treat failure as permission to fabricate a parsed scenario.

ParsedScenario contains no chart data. Strict schema transport support is documented
by [OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs) and
[local Ollama](https://docs.ollama.com/capabilities/structured-outputs). Provider adapters
must adapt the schema to the provider's supported JSON Schema subset and revalidate
with Pydantic; Pydantic semantic validators do not run inside the provider. Neither
provider was called. Model availability, schema acceptance, latency and fallback are
separate live integration checks, not established by identical parser fixtures.

**Numerical engine:** `ForecastRequest` contains indexed numeric history and aligned
historical CPI/release-indicator values, explicit assumed future covariates for this
segment only, fixed base, data/model versions and frozen evidence cutoff. No raw prompt,
political name or revealed future target enters this boundary. `FutureRow` forbids
target/level fields. Observed history must have availability <= cutoff; scenario history
uses prior simulated median levels. Production must also validate dataset provenance.

Aditya maps rows to a regular session-number model grid, calls pretrained Chronos-2
with numeric target and aligned known-future covariates, requests 0.1/0.5/0.9 quantiles,
and maps sessions back to ISO dates. This follows the
[Chronos repository](https://github.com/amazon-science/chronos-forecasting); actual
adapter execution, weights and host latency remain untested. `ForecastResult` carries
ordered simulated points, actual engine/model version, support count and assumptions,
or unsupported with reason and no points. Coordinator must verify output dates exactly
match requested future sessions and that base/target remain unchanged.

Each segment ends before the next intervention. Final segment defaults to five sessions,
total simulated horizon <=65. Later instructions enter only at activation. Downstream
bands must say conditional on preceding simulated median. On a model deadline/failure,
use the disclosed empirical fallback only within its supported five-session range;
represent unavailable tail as gaps or unsupported. Never silently extend it. A provisional
30-second forecast deadline is configurable and needs host measurement; no live behavior
is asserted. Narration is initiated by a separate frontend POST after the numeric commit. The
existing basic panel text remains the fallback. Narration cannot alter forecast/impact
values. Unsupported impacts stay qualitative.

## 6. Reproduce and acceptance evidence

From repository root, Python 3.10+ and Node 22.18+ (native TypeScript stripping):

```sh
python -m pip install -r requirements-contracts.txt
python tools/export_contracts.py --check
python tools/build_example_fixtures.py --check
python tools/check_fixtures.py
python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/frontend-contract.test.mjs
npx --yes --package typescript@5.9.3 tsc --noEmit --strict --target ES2022 --module ESNext --moduleResolution bundler --allowImportingTsExtensions --lib "ES2022,DOM" web/src/api/client.ts web/src/api/applyRun.ts
python -m uvicorn api.fixture_app:app --host 127.0.0.1 --port 8000
```

Use `http://127.0.0.1:8000/docs`; `createApi("http://127.0.0.1:8000")` targets the
fixture server. Local Vite origins localhost/127.0.0.1:5173 are allowed. Server is
in-memory, single-process and synthetic only. Do not deploy it as the live backend.
JSON fixture drafts have a fixed historical clock for reproducibility; use live fixture
`/interpret` to obtain fresh draft IDs/expiry rather than posting saved drafts blindly.
Rebuild after edits with `python tools/export_contracts.py` and
`python tools/build_example_fixtures.py`, then run the checks again.

The review report `docs/api-handoff-review.md` records actual results and remaining
owners. This contract is ready for fixture-backed work, subject to Aashna's review;
live implementation, browser rendering and database/provider integration are separate.
