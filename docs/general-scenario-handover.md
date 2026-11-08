# General scenario implementation and frontend handover

Prepared for Aashna, Aditya and the frontend team, 8 November 2026, London.
This supersedes the CPI-only implementation plan in older handovers. Read this
first in a new chat, then inspect current Git/process state before changing anything.

## Goal and what changed

The approved product accepts an ordinary-language hypothetical event, researches
its economic implications, compares earlier events against our actual market and
economic observations, and supplies explicit numeric assumptions to Chronos.
Chronos supplies the chart numbers; OpenAI explains the result afterward.

There is no event/person/country whitelist in the new flow. Iran, US policy and
tariffs are verification examples, not supported-case definitions. There is no
CPI preset lookup or [-2%, 2%] validator in scenario mode. Extreme assumptions are
labelled extrapolation. Existing fixture and CPI research modes remain available
to preserve earlier work; they are not the new product entry point.

The root cause was wider than the old language parser: the parser, instruction
schema, release calendar, feature builder and forecast adapter all assumed a
narrow CPI demonstration. Rewording the parser alone could not give Chronos the
data channels needed for another event. The new path connects a general research
plan to measured covariates rather than forcing every prompt into a CPI field.

The numeric model still has real input constraints: our supplied channels are
oil, volatility, effective interest rates and, where original releases cover the
context, monthly CPI. OpenAI can reason about any event and propose effects on
these channels. It must disclose channels absent from the data. Open-ended
language does not establish that four variables fully explain every event.

## End-to-end architecture

```text
Frontend prompt + date/playhead
    POST interpret
Backend OpenAI Responses call 1: required web research + structured event/date
    source-linked candidate historical events
Local SPY/FRED data: measure prior analogue windows ending before frozen cutoff
    optional small GDELT daily archive retrieval/cache (up to two dates)
Backend OpenAI Responses call 2: structured numerical covariate assumptions
    validated available feature IDs, units, sources, provenance and durations
Ready draft (no saved forecast revision yet)
    POST commit
Real, pinned, offline CPU Chronos: baseline + conditional scenario paths
    immutable SQLite revision; frontend installs numeric chart immediately
Frontend POST complete selected forecast segment to description relay
    server-side OpenAI narration; separate response, cannot change chart numbers
```

Research and planning use OpenAI. Commit uses Chronos and makes no OpenAI call.
Narration is a third, separate OpenAI request initiated by the frontend after the
chart is installed. No API key goes into the frontend or any `VITE_*` variable.
The JetBrains-provided key is used for application scenarios/descriptions, not
for coding assistance. No per-task app spending limit was specified by Aashna.

## Code map

| File | Responsibility |
| --- | --- |
| `api/scenario_contracts.py` | Structured research, feature drivers, measured analogues, saved plan |
| `api/scenario_research.py` | Required web search, numerical planning, validation, research cache |
| `data/scenario_market.py` | Full local market/FRED/BLS context, coverage, analogue measurements |
| `data/scenario_events.py` | Bounded on-demand GDELT retrieval and event-date validation |
| `training/scenario_adapter.py` | Numeric covariate paths and actual Chronos calls |
| `api/scenario_backend.py` | Capabilities, interpretation, replay, baseline, panels, separate reveal |
| `api/durable_service.py` | Existing revision transactions, drafts, idempotency and concurrency checks |
| `api/contracts.py` | Shared HTTP contracts, extended with scenario plans and baseline |
| `api/descriptions.py` | Existing validated raw-number narration relay, now general-scenario aware |
| `tools/serve_scenarios.py` | Safe local launcher; new database by default; server-side env loading |
| `tests/test_general_scenarios.py` | Focused numeric boundary, state preservation and provenance regressions |
| `integration/frontend-scenario.patch` | Complete portable UI integration against frontend base `f272c22` |

## Local data and input policy

Data remains ignored under `data/local/`; do not publish or commit it.

- `raw/hf/SPY_raw_1min.parquet`: supplied IEX-only minute history, March 7,
  2022–November 6, 2026. Session price is the available daily close proxy, indexed
  to 100 on March 7, 2022. This is not a consolidated exchange-wide price feed.
- `raw/fred/DFF.csv`, `DCOILWTICO.csv`, `VIXCLS.csv`: supplied observation-date
  exports, March 7, 2022–November 3, 2026. The first column must be
  `observation_date`; the second must match the filename's series ID.
- `raw/bls/` and `raw/bls-expanded/`: original CPI releases when available. CPI
  is a monthly percent reading; it is not an annual rate or stock-price multiplier.
- `raw/gdelt/`: original supplied archive and small automatically cached daily
  archives. Archive date is not automatically the event date: rows must match
  the requested event date. These are dated news-event context, not causal labels.

The hashed snapshot built during this run is
`processed/scenario-969dbdff807fea8ccf36/`. Its manifest records source hashes and
alignment policy. Adding/changing source files builds another dataset identity;
start another timeline when data/model identity changes. If preprocessing policy
is changed later, version that policy/cache as well; do not silently reuse old
processed files with different semantics.

FRED CSVs are current vintages, not ALFRED historical vintages. The implementation
lags observations two calendar days and carries prior non-missing values for at
most seven days. That is an explicit conservative approximation, not verified
publication-time availability. BLS context uses original release times. Every
forecast discloses these limitations.

The context has at most 252 prior market sessions and requires at least 20
contiguous observed sessions. The missing SPY session on December 23, 2024 causes
context to restart after that gap; early dates immediately after it lack enough
context. Features missing anywhere in the selected context are excluded from the
catalog, rather than filled with invented values. Later dates can therefore lack
CPI while retaining FRED channels. A requested non-session date aligns to the
next NYSE session. The earliest raw date is not automatically forecastable.
Future forecasts need contiguous observed history up to the cutoff; selecting
a distant future start cannot bypass missing intervening market observations.

Analogue windows must be complete and end strictly before the timeline's frozen
cutoff. The backend computes market return, daily volatility, worst close return
relative to the pre-event close, and measured feature changes. It does not label
those changes as caused by the event. A cited URL is checked against URLs actually
returned by the web tool; the LLM's event interpretation/publication metadata is
not independently fact-checked. Unknown or later publication dates are disclosed
in the scenario plan; they are not inserted into the old pre-cutoff evidence panel.

## Numerical model and replay

Chronos model: `amazon/chronos-2`, package `chronos-forecasting` 2.3.2, pinned
revision `29ec3766d36d6f73f0696f85560a422f50e8498c`, CPU, offline cached weights.
New model identity: `chronos-2-2.3.2-29ec3766d36d-scenario-v1`.

Historical frame contains the SPY target and measured covariates. Future frame
contains only numeric covariates: never future SPY prices, returns or revealed
actuals. `predict_df` uses a regular session-ordinal clock and maps output back to
exchange dates. Quantiles must be finite/ordered and the median must be positive.

A driver specifies `feature`, `operation` (`set`, `add`, `multiply`), `value`,
`transition_sessions`, optional `duration_sessions` and `recovery_sessions`.
It ramps from the preceding simulated feature level to the endpoint. Duration
counts from event start; after that it returns to the preceding level over the
specified recovery period. `null` duration means persistent. Each assumption
records `basis`: `user_assumption`, `historical_analogue`, or `llm_hypothesis`,
plus a rationale and source URLs. These operations are input units, not fixed
event-to-stock-return coefficients. CPI has no arbitrary magnitude cap here.

Baseline holds the last observed feature values constant. Scenario uses the
planned paths. Both are independently inferred by Chronos in fixed five-session
blocks, rolling forward their own simulated medians and covariates. Later bands
are conditional quantiles, not a calibrated joint long-horizon confidence region.

Existing workspace limits remain three active prompts and 65 total simulated
sessions (default 20). These are timeline/compute limits, not event categories.
Events replay in chronological order, stable IDs survive replacement, and actual
history remains frozen before the earliest cutoff. Editing/appending recomputes
the full simulated run; responses use `series_mode: "full"` and `changed_from`
at the frozen cutoff. Known future covariates within a block can affect earlier
points in that block. Do not assume the pre-edit simulated prefix is immutable.

Provider/inference failures do not save revisions, substitute mock forecasts or
fall back to the CPI parser. Scenario mode currently requires OpenAI research;
the old CPI mode's Ollama fallback is not a general web-research replacement.

## API calls for the frontend team

Routes retain contract version `1`, with additive fields/enum members. Consumers
with exhaustive operation switches must update. Schema source is Python; run
`python tools/export_contracts.py` to regenerate OpenAPI/JSON Schema/TypeScript.

1. `GET /api/capabilities`: scenario mode advertises
   `supported_event_families: ["open_ended_scenario"]` and no fixture presets.
2. `POST /api/timelines` with `{"target_id":"SPY","request_id":"unique-create-id"}`.
   Revision 0 has an empty chart because no scenario date has been chosen yet.
3. `POST /api/timelines/{id}/interpret`, for example:

```json
{
  "text": "What if Iran halted oil exports for one month starting June 11, 2025? Forecast 20 trading sessions.",
  "mode": "add",
  "selected_prompt_id": null,
  "playhead": null,
  "expected_revision": 0
}
```

Ready responses contain `draft_id`, `instruction.operation: "scenario"`,
`scope: "event"`, `unit: "scenario"`, and `instruction.scenario` with the entire
auditable plan. `value` and `reference` are null, `release_dates` is empty. Do not
assume every prompt has `resolved_value` or CPI units. `needs_clarification` and
`unsupported` may be HTTP 200 `Problem` responses; inspect the body status.

4. `POST /api/timelines/{id}/commit`:
   `{"draft_id":"returned-draft-id","expected_revision":0,"request_id":"unique-commit-id"}`.
   Retry an uncertain commit with the identical request ID/body. Success returns
   `series.points`, optional `baseline` (same Series shape), `scenario_warnings`,
   saved prompts/plans and panels. Install these numbers immediately.
5. `POST /api/timelines/{id}/revisions/{revision}/description` with `prompt_id`
   and the complete, exact `forecast_points` for that prompt's simulated segment.
   The backend validates numbers against the immutable saved revision. Do not
   round, omit quantiles, or send baseline/revealed history as forecast points.
   Use `descriptionRequest` and `matchesDescription` from the patched API client.
   The server adds saved scenario/driver context and baseline comparison.
6. Editing uses `mode: "replace"`, the existing `selected_prompt_id`, and current
   `expected_revision`, followed by another commit. Clear/ignore old narration;
   match timeline, run, revision and prompt before displaying the new response.
7. Restore: `GET /api/timelines/{id}`. History:
   `GET /api/timelines/{id}/revisions/{revision}`. Actual overlay:
   `GET /api/timelines/{id}/revisions/{revision}/reveal`. Reveal never feeds inference.

The browser calls same-origin `/api`; Vite proxies to the selected backend.
Research may take minutes on an uncached prompt (two sequential provider calls,
optional archive fetches). Do not use the old short CPI-parser timeout for this
flow. `SCENARIO_TIMEOUT_SECONDS` defaults to 90 per provider request; narration
has its separate 20-second default. There is no silent research retry/fallback.
Validated plans are cached under ignored `data/local/cache/scenario-research/`,
keyed by prompt/context/model/data/policy; edits/replays preserve saved plans.

## Start or resume the local demo

From `/Users/aashn/hackathon/TeamRelay-Hackathon`:

```bash
.venv/bin/python tools/serve_scenarios.py \
  --env-file /Users/aashn/hackathon/TeamRelay-Hackathon/.env.local \
  --model gpt-5.6-sol --port 8772
```

The launcher loads approved provider variables without executing the env file,
keeps credentials server-side, and creates a NEW ignored SQLite file by default.
Use `--database <existing-file>` to intentionally resume a saved scenario database.
Do not source the credential file into a frontend terminal. The model override
does not modify the credential file. Default `api.app` without this launcher or
explicit `APP_MODE=scenario` is still fixture mode.

Complete isolated UI: `/private/tmp/teamrelay-scenario-ui/web`:

```bash
VITE_API=server BACKEND_URL=http://127.0.0.1:8772 npm run dev -- --host 127.0.0.1 --port 5177 --strictPort
```

On this Mac, Node is `/private/tmp/node-v24.11.0-darwin-arm64/bin/node`; add that
directory to PATH if `npm`/`node` are unavailable. Dependencies in this isolated
checkout are symlinked to the existing complete UI's node_modules. Elsewhere use
`npm ci` in `web/` if dependencies are missing. Keep the demo localhost-only.

The live verification backend used
`data/local/general-live-1794121139797924000.sqlite`, port 8772; UI port 5177.
Check processes before restarting; previous CPI servers on other ports were
left untouched. Do not mistake an old CPI server or browser mock for scenario mode.

## Frontend integration without overwriting teammates

Original backend folder still does not contain the complete React application.
The new complete UI is isolated at `/private/tmp/teamrelay-scenario-ui` on detached
base `f272c22`. Original frontend worktrees were inspected and preserved.

`integration/frontend-scenario.patch` is the FULL diff from that base: previous
research API/description wiring, generated types, general scenario panels, and
the dashed purple baseline. It is not merely an incremental add-on to the older
`frontend-research.patch`. Do not blindly apply both. Use `git apply --check` and
`git apply --reverse --check` in the intended checkout; reconcile overlapping
teammate edits explicitly. No one else's files should be reset or overwritten.
The frontend team may port the typed API/components into their final UI instead.

Display forecast/quantiles, baseline, date, driver assumptions with their basis,
measured analogue associations, source links and uncertainty. The patched UI
places detailed evidence behind an expandable section, retaining the short
narration and chart. Sector impacts are currently empty; do not fabricate them.

## Verification and handoff status

Source-citation repair: the numerical planner now receives only accepted research
sources and measured analogues, and its structured citation choices are restricted
to those same accepted URLs. Final backend validation remains enabled. This small
repair was not tested or live-run at Aashna's request; restart the backend before
testing it independently. The 65-session timeline limit is unchanged.

Focused unit/HTTP tests cover real covariate frame construction without future
targets, continuous driver values/duration/recovery, arbitrary dates, stable IDs,
add/edit replay, idempotency, old revisions, separate reveal, and state preservation
on provider/model failure. Additional checks cover cutoff/gap handling and GDELT
row dates. Fixtures use injected models; these tests alone do not establish live
forecast behavior. Live checks are recorded separately below.

- Real OpenAI research/planning (`gpt-5.6-sol`) plus offline Chronos: an Iran
  export halt on June 11, 2025, 20 sessions. Four measured historical windows,
  seven research sources, distinct final baseline/scenario medians:
  144.26280212402344 / 142.2519073486328. Receipt:
  `data/local/results/general-scenario-live.json` (ignored, not a canned API result).
- Rendered Chrome: remove all US import tariffs for 30 days starting April 3,
  2025, forecast 10 sessions. Three measured historical windows, distinct final
  medians 134.1996 / 135.7531. Backend HTTP logs confirmed interpret/commit requests
  on the new server. Chart and baseline were visible while UI said
  “Writing description with OpenAI…”, followed by a real description labelled
  `gpt-5.6-sol`.
- The first general live attempt exposed an unavailable/duplicated feature-name
  plan. The fix gives OpenAI a structured enum of actual available columns and
  requires one driver per feature. This limits numeric input identifiers, not
  accepted event topics. Failed interpretation saved no revision.
- Focused general tests: 7 passed. Existing provider parser: 8 passed. Description
  relay: 5 passed. Contract journey: 15 passed. Research HTTP: 18 passed during
  implementation. Contract exporter check passed. TypeScript/Vite build passed;
  existing large Plotly bundle warning remains.

No changes have been committed, pushed, merged or deployed for this task. Original
backend uncommitted work was preserved. A pre-task source-only backup exists at
`/private/tmp/teamrelay-before-general-scenarios-1794120614620428000.tar.gz`.
The branch still includes preexisting continuous-CPI work; review the combined
diff carefully before staging intended files. Never stage credentials, env files,
local data, model weights, node_modules or the Message Board inbox.

## Remaining practical work

1. Coordinate the frontend team's integration using the typed API and portable
   patch. Preserve their design and changes. Point their server to scenario mode.
2. Prepare the presentation around “researched, data-conditioned scenarios,” with
   one concise scenario and a visible assumption change, baseline and sources.
   The examples above are repeatable checks, not an allowed-input list.
3. Before publishing, review intended source changes, data display permissions
   and deployment configuration. No deployment/publication was authorized here.
4. Longer-term work: independently evaluate analogue selection, sensitivity,
   calibration and out-of-distribution behavior; improve data channels/vintages
   and source timing; add efficient research caching/streaming progress if needed.
   Do not block the current integrated demo on a broad perfection/testing loop.

Do not claim this reconstructs what would actually have happened. Real data plus
a real pretrained time-series model and a real LLM do not establish causal truth.
The implemented product is an auditable hypothetical forecast with explicit
assumptions, measured historical associations and uncertainty.
