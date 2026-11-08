# Continuous CPI demo: implementation and integration handover

Updated 8 November 2026, approximately 06:00 London. Aashna's submission deadline
is noon; frontend integration and the presentation still need time.

## Read this first

The five-value/case whitelist has been removed from the real research pipeline.
The LLM is instructed to extract a user's numeric assumption rather than select
one of five cases. Shared backend policy validates the extracted measure, date,
operation, reference and continuous numeric domain. Chronos receives the numbers.
It does not receive or generate market prices from prose.

**This is implemented locally, not published.** Changes are present as uncommitted
files in `/Users/aashn/hackathon/TeamRelay-Hackathon`, on `backend` at `416b474`.
They were built and checked first in `/private/tmp/teamrelay-continuous-cpi`, branch
`continuous-cpi-demo`, also based on `416b474`. That isolated copy is retained.
Do not merge the empty branch tip expecting the uncommitted changes to follow it.
Stage/commit only after Aashna authorizes publication. No push, merge, deployment
or board post was performed.

**Verified:** 46 focused automated tests; unchanged exported contracts; real offline
Chronos inference for three continuous assumptions; real 47-session dependent replay;
identical final assumptions yielding identical paths; separate actual-history reveal.

**Not yet verified for this change:** new LLM instructions/schema against the live
OpenAI or Ollama service; the new journey in the rendered browser. The execution
approval request for the live API journey was declined, and no substitute route
was used to make those calls. Prior successful live calls in PR #6 validate the
older parser, not the newly expanded instructions. Do not describe this distinction
as a failed model response: the new live request was not executed.

Preview processes were started, but starting a server does not prove live parsing:

- UI: <http://127.0.0.1:5176/>, preserved complete React worktree.
- Backend: <http://127.0.0.1:8771/>, now running from the main project folder.
- Vite configuration: `VITE_API=server`, `BACKEND_URL=http://127.0.0.1:8771`.
- Older demo ports/worktrees were left alone.

## Root causes and the bounded repair

1. **Application rules vetoed valid model inputs.** The provider instructions,
   literal grounding logic and `ResearchBackend.instruction` treated PRESETS as
   domain eligibility. Removing only one layer would leave the symptom intact.
   The provider now extracts continuous values; both parser and backend use
   `api/cpi_domain.py`. PRESETS remain zero-cost examples, not permitted-value lists.
2. **The active backend folder lacked the previous provider implementation.**
   The earlier handover's task checkout had since moved to `main` at `11b7084`.
   We recovered the known PR #6 parser fixes from the local Git object `d90c447`
   and included the needed source/settings/tests and frontend patch in this change.
   We did not reset or switch the sibling checkout.
3. **The original live context was weak.** It supplied only 20 sessions with CPI
   fixed at .2%. The startup helper selects the existing expanded snapshot with
   114 eligible sessions, five CPI values and five release-indicator sessions.
   No new dataset was downloaded, altered or fabricated.
4. **Inference depended on construction history.** Appending an event previously
   forecast a five-session tail and then a bridge; editing June forecast longer
   groups in one call. The same assumptions could therefore produce different
   paths. Research replay now uses five-session blocks anchored to each release,
   including shorter blocks before the next release. Appending and replaying the
   same event sequence use the same boundaries. This was checked with a deliberately
   horizon-sensitive test engine and the actual pinned Chronos model.
5. **Research startup could silently retain the preset parser.** Research mode
   now defaults to `auto`; fixture mode defaults to `deterministic`. Explicit
   `PARSER_PROVIDER=deterministic` still selects the deliberately limited test parser.
   The new startup helper explicitly selects auto unless local-only is requested.

This does not create a learned model for every economic variable. Existing data
supports SPY and monthly headline CPI; it contains no rate, oil, earnings or policy
scenario features. Making the LLM invent those features or draw prices would make
an attractive but unsupported demonstration. The efficient deadline scope is a
complete continuous-CPI scenario product, then frontend integration and presentation.

## Supported behavior and remaining boundaries

- Target: SPY, fixed-base index levels, not dollars.
- Measure: headline CPI-U, monthly seasonally adjusted percent change.
- Continuous absolute levels: any finite value in **[-2, 2] percent**, including
  decimals, zero and negatives. This is an input plausibility/coverage boundary,
  not a list of examples or a claim of calibrated accuracy throughout the range.
- Operations: `set`, signed `add_pp`, `carry`. Decreases are negative `add_pp` values.
- Units: percent for a level, percentage points for a change. One basis point is
  .01 percentage points. Relative percent growth is a different operation and
  requires clarification rather than silently treating it as percentage points.
- Relative references: previous simulated reading, existing explicit prompt ID,
  or a named supported earlier release. The service resolves named dates to stable
  prompt IDs; it no longer assumes that July must always be prompt p2.
- Release dates: June 11, July 15, August 12, **2025**. The first fork remains June 11.
- Three active prompts, final tail five trading sessions, at most 65 forecast sessions.
- Adding July and August yields the existing 47-session journey ending August 18.
- Ambiguous alternatives, missing values/dates and unsupported measures need a
  clarification or explicit unsupported response. Do not silently convert annual
  inflation, core CPI or interest rates into headline monthly CPI.
- Resolved dependent readings are range-checked before any numerical inference or
  revision write. An earlier edit that pushes a later reading out of range fails
  without changing the saved chart.
- Same-date supersession remains existing behavior; named-date references must
  identify exactly one earlier existing prompt, otherwise clarification is returned.
- Written-out numbers are delegated to the LLM. Numeric literals with explicit
  units are independently cross-checked. This is not an exhaustive rule-based
  English parser, and live language coverage remains to be checked.

Examples to try (they are not the only supported numbers):

1. `What if headline CPI came in at 0.35 percent on June 11, 2025?`
2. `On July 15, 2025, lower the previous simulated CPI reading by 7.5 basis points.`
3. `On August 12, 2025, keep July's simulated reading unchanged.`
4. Select prompt 1 and replace with `Set monthly headline CPI on June 11, 2025 to 0.6%.`

Expected resolved readings: **.35 / .275 / .275**, then **.6 / .525 / .525**.
The canonical/numerical journey is verified; these exact sentences still need
live-provider verification. An ambiguous example is `June 11 CPI could be 0.4% or 0.2%`.
20% monthly CPI remains outside the numerical domain; explain the measure/range
instead of returning the old message that only .4% or .2% is allowed.

## Architecture and API integration

```text
Frontend text + expected revision
  → POST /interpret
  → OpenAI structured extraction (or local Ollama on provider failure)
  → numeric grounding + common domain policy + timeline reference validation
  → ready draft with canonical assumptions
  → POST /commit
  → dependency resolution + resolved-value checks
  → pinned historical data + explicit future CPI/release covariates
  → offline Chronos, consistently segmented
  → immutable saved run/full or suffix response
  → frontend applies run and renders chart
  → frontend forwards full selected segment to /description
  → server-side OpenAI narration → matching-revision panel
```

No external frontend wire schemas changed. Continue using the generated v1 types
and existing `applyRun` / `descriptionRequest` / `matchesDescription` helpers.

| Call | Required use |
|---|---|
| `GET /api/capabilities` | Read actual scope, limits and optional examples. `supported_event_families` now contains `headline_cpi_mom`. |
| `POST /api/timelines` | `{target_id:"SPY", request_id:"unique-id"}`. Create a new timeline for the v3 engine/dataset. |
| `POST /api/timelines/{id}/interpret` | `{text, mode:"add" or "replace", selected_prompt_id:null or ID, expected_revision}`. Render returned errors/clarifications; commit only `status:"ready"`. |
| `POST /api/timelines/{id}/commit` | `{draft_id, expected_revision, request_id}`. Install full/suffix result through the existing cache helper. |
| `GET /api/timelines/{id}` | Restore full current run. |
| `GET /api/timelines/{id}/revisions/{n}` | Read an immutable older run. |
| `POST /api/timelines/{id}/revisions/{n}/description` | `{prompt_id, forecast_points}` with complete unrounded saved segment. Prose is separate from the numbers. |
| `GET /api/timelines/{id}/revisions/{n}/reveal` | Separate actual-history overlay; never feed it to the forecast. |

`/interpret` returns `Instruction.value` .35 for an absolute example and -.075 for
the basis-point decrease. `Prompt.resolved_value` is calculated at commit. Relative
operations remain relative so editing an earlier prompt recalculates later readings.
The parser-only structured schema adds `measure`; it is validated/removed before
`ParsedScenario` reaches the HTTP contract. The browser does not send that field.

Generic interpretation problems now use code `scenario_interpretation`, rather
than `choose_preset`. Use `status`, `reason` and `choices`; do not match hardcoded
old error text. Examples still travel in the legacy field `fixture_presets` for
compatibility. Treat those buttons as suggestions, not a required selection menu.

The complete frontend integration patch has also been restored to the version
containing the earlier reveal-range fix. It is already applied in the verification
UI. Do not reapply it there or blindly overwrite the frontend team's edits.
Backend minimal `web/` still is not a complete React application.

## Model and environment

- New engine identity: `chronos-2-2.3.2-29ec3766d36d-cpu-cpi-v3`.
- Same pretrained weights: `amazon/chronos-2`, revision
  `29ec3766d36d6f73f0696f85560a422f50e8498c`; package 2.3.2; offline CPU.
- v3 records changed inference segmentation. Old v2 timelines are readable but
  are not writable under v3. Preserve old databases; create a new timeline.
- Expanded dataset: `spy-8c865e107520d2cdab66` under original `data/local/processed/`.
- Original dataset preserved: `spy-99baca8c94f5871aff6b`.
- OpenAI configured for preview: `gpt-5.6-sol`, the model Aashna previously selected.
- Provider: `auto`; 20-second OpenAI timeout from launcher unless env file overrides;
  existing Ollama fallback `qwen3.5:9b`, thinking off, 512-token cap.
- Credentials loaded only into the Python server from ignored `.env.local`.
  No key printed or copied into Vite, code, docs or patch. No secret file changed.
- No LLM is trained in this change, and no manual stock-return multiplier is added.

Restart from the original repository, reusing the existing Mac environment:

```sh
.venv/bin/python tools/serve_research.py \
  --env-file /Users/aashn/hackathon/TeamRelay-Hackathon/.env.local \
  --data-dir /Users/aashn/hackathon/TeamRelay-Hackathon/data/local \
  --model gpt-5.6-sol --port 8771
```

The helper creates a new timestamped SQLite file by default, checks the real
snapshot at startup and prints only non-secret model/data/database metadata.
To restore that specific new workspace later, pass `--database /absolute/path`.
It never downloads weights. If the snapshot/cache is missing, stop and obtain the
correct local assets; do not silently switch to synthetic mode.

Frontend startup (complete verification UI, dependencies already installed):

```sh
cd /private/tmp/teamrelay-pr6-ui-verify/web
PATH=/private/tmp/node-v24.11.0-darwin-arm64/bin:$PATH \
VITE_API=server BACKEND_URL=http://127.0.0.1:8771 \
/private/tmp/node-v24.11.0-darwin-arm64/bin/npm run dev -- \
  --host 127.0.0.1 --port 5176 --strictPort
```

Do not start another process on an occupied port. This task did not alter any
frontend source files. The earlier integration work remains uncommitted in its
own worktrees and must be reconciled deliberately with the frontend team's branch.

## Evidence from this implementation

Focused checks: `test_provider_parser.py` (8), `test_research_http.py` (18),
`test_contract_journey.py` (15), `test_descriptions.py` (5): all passed.
`tools/export_contracts.py --check` passed; no schema regeneration was needed.
After later parser/default-setting/test improvements, the affected parser and
research HTTP suites were rerun and passed. No broad repeated test campaign.

The replay regression test uses a horizon- and context-sensitive test model so
it can detect the old append-vs-replace issue; the basic constant-output test
model alone would have hidden it.

Real offline inference, with the same 114-session history and five-session horizon:

| CPI assumption | Final forecast median index |
|---|---:|
| .2% | 143.781433 |
| .35% | 143.874619 |
| .6% | 143.900391 |

The first call loaded cached weights and took about 2.24 seconds; warmed calls
took about .24 seconds. Exact timing varies. Outputs show modest input sensitivity,
not proof of an economically correct sign, predictive advantage or causal effect.
Do not amplify the changes artificially for presentation.

The real offline service journey injected canonical parsed fields (no live LLM):

- Three prompts resolved to .35/.275/.275, 47 simulated sessions.
- Replacing June by the same .35 produced exactly the same saved series.
- Replacing June by .6 resolved .6/.525/.525 and changed the path.
- Stable IDs p1/p2/p3 retained; actual reveal returned 47 points without changing run.
- Old revisions/data were preserved.

Local receipts (ignored, not publication artifacts):

- `data/local/results/continuous-cpi-offline.json`: exact controlled model inputs/outputs.
- `data/local/results/continuous-cpi-replay.json`: full before/after replay and DB path.
- `/private/tmp/teamrelay-continuous-live.py`: prepared, unexecuted live proxy journey.
  It would use the configured providers and create a new timeline; execution was declined.

Chronos remains an exploratory conditional forecaster. It is not a causal economic
model; uncertainty is uncalibrated here, and later bands condition on earlier medians.
The richer history improves supplied information, not evidence of predictive skill.
The older report's empirical evaluation still does not establish a production model.

## Files to review

- `api/cpi_domain.py`: continuous range, release calendar and canonical operation policy.
- `api/provider_parser.py`: real providers, generalized instructions, measure gate,
  numeric normalization/grounding, explicit ambiguity and provider fallback.
- `api/research_backend.py`: removes tuple whitelist; resolves named-date references;
  scope labels/capabilities. Rechecks drafts at commit.
- `api/replay.py`: resolved bounds before inference; consistent release-anchored blocks.
- `data/real_market.py`: shares range/date policy; preserves snapshot/target validation.
- `training/chronos_adapter.py`: v3 identity; model math/weights remain unchanged.
- `api/settings.py`, `api/durable_service.py`: provider routing/defaults and interpretation code.
- `tools/serve_research.py`, `.env.example`: explicit reproducible local startup.
- `tests/test_provider_parser.py`, `tests/test_research_http.py`: focused regressions.
- `integration/frontend-research.patch`: previous PR #6 integration/reveal fix, not
  new UI design. Its changes must be reviewed separately against the team's UI branch.
- `docs/pr6-live-verification.md`: historical verification report, recovered from d90c447;
  its old checkout/remote/status statements are historical, not freshly reverified.

## Next actions before noon

1. **Finish one live language/UI journey once authorized.** Use the four sentences
   above, verify exact canonical values and visible chart, then one description.
   Confirm browser network `/api` requests go to this preview and backend logs show
   `OpenAIParser` or `OllamaParser`. A preset click makes no LLM call and cannot prove
   language parsing. Test ambiguity once; preserve graph/revision on failure.
2. **Integrate with the frontend team immediately.** Keep the API contract fixed.
   Use a new v3 timeline, clear stale workspace selection only through the UI/new
   origin, label example buttons, show supported measure/dates and backend messages.
   Reuse existing narration/revision guards. No chart rewrite is needed.
3. **Freeze the demo scope.** Demonstrate non-preset input, a basis-point decrease,
   carry-forward, editing/replay and separate actual reveal. Do not add rate/oil/
   political-event model paths before the presentation without data/model support.
4. **Prepare the presentation.** Explain the actual architecture: LLM converts
   language into structured assumptions; real historical data plus Chronos produces
   conditional numeric scenarios; a separate LLM explains saved outputs. Show both
   flexibility and explicit boundaries. Do not claim causality or trading accuracy.
5. **Publish only on Aashna's instruction.** Check current remote changes before
   committing/pushing. Do not blindly merge PR #6 or the uncommitted worktree branch.

Suggested new-chat instruction:

> Read AGENTS.md and docs/continuous-cpi-demo-handover.md. Preserve all uncommitted
> work. Continuous CPI changes are in the main backend folder and an isolated copy.
> Complete only the remaining live-provider/frontend integration check, with the
> appropriate execution approval. The prior live script was not executed. Use
> gpt-5.6-sol server-side, the expanded local snapshot, and new v3 timelines. The
> numerical and focused offline checks already passed; don't restart a broad testing
> loop or add unsupported economic features. Help finish the demo/presentation.

The structured-output transport follows the [official OpenAI documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).
Schema conformity does not replace semantic validation or live language testing.
