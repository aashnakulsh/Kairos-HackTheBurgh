# PR #6: Mac live verification

Verified on 8 November 2026 on Aashna's Mac, starting from task commit
`7f335ff0ee89707da73511651f8e86386e3902f0`. PR base: `backend`.

## Result

Ready for Aashna's review with the fixes described below. This does not merge the
PR or integrate the complete frontend into the backend checkout. The complete
frontend remains a separate branch/worktree; its integration is preserved as a patch.

## State preserved

- Original backend: `/Users/aashn/hackathon/TeamRelay-Hackathon`, branch `backend`.
- Isolated task checkout: `/Users/aashn/hackathon/TeamRelay-CPI-parser-check`.
- Original complete frontend: `/private/tmp/teamrelay-frontend-integration` at
  detached `f272c22`, with its eight pre-existing edited files preserved.
- Aditya's original task patch reverse-checked successfully in that frontend;
  it was already applied and was not applied twice.
- The reveal fix was made in `/private/tmp/teamrelay-pr6-ui-verify`, reconstructed
  from `f272c22` plus the task patch. Existing installed Node dependencies were
  reused; no npm install or model download was needed.
- The updated `integration/frontend-research.patch` includes the original
  integration plus the reveal fix and its regression test. It targets `f272c22`.
  Do not apply it blindly over the already modified original frontend worktree.

## Live settings (no secrets)

| Setting | Value |
|---|---|
| Backend | Task source on `127.0.0.1:8770`, one worker |
| Frontend | Isolated complete UI on `127.0.0.1:5175`, `VITE_API=server`, proxy to 8770 |
| APP_MODE / PARSER_PROVIDER | `research` / `auto` |
| DATASET_VERSION | `spy-99baca8c94f5871aff6b`, verified against the local manifest |
| Numerical engine | Offline CPU Chronos-2, pinned cached weights, existing Mac virtual environment |
| OPENAI_MODEL | `gpt-5.6-sol`, selected by Aashna and verified by real successful parser/description calls |
| Parser / narration timeouts | 5 / 20 seconds |
| Local fallback | Existing `qwen3.5:9b`, 12-second normal budget, thinking disabled, temperature 0, max 512 predicted tokens |
| SQLite | New ignored file `data/local/pr6-openai-live-1794114164263991000.sqlite` in the original backend repository |

The server key was loaded privately from the ignored original `.env.local`.
Its original model setting `gpt-6-sol` returned HTTP 404; Aashna selected
`gpt-5.6-sol` after available model IDs were checked. Only the verification
process's environment was overridden. The credential file was not edited.
**A later restart must set the working model explicitly unless its local configuration
has since been corrected by the human.** No key was printed, stored in frontend
variables, or included in source, patches or this report.

## Concrete failures and fixes

1. **Supported questions rejected by a real provider.** The original instructions
   did not explicitly map hypothetical wording to a successful parse. A real
   OpenAI response also copied the start date into `requested_end`, which the
   research-domain validator correctly rejected. The instructions now make the
   supported paraphrase and null single-release end date explicit. The backend
   validation rules were retained.
2. **Local fallback missed its interactive budget.** Installed `qwen3.5:9b` exposed
   thinking enabled by default. The original request timed out at 12 seconds, and
   a diagnostic attempt also timed out at 60 seconds. Local extraction now sends
   `think: false`, temperature 0, and a 512-token cap. Supported wording is explicit.
   The actual router with OpenAI explicitly unavailable then parsed the June
   question successfully in about 6 seconds within the normal 12-second budget.
3. **Actual history clipped above the chart.** The chart calculated its fixed y-axis
   from forecast points only, so the revealed actual path disappeared beyond the
   forecast range. `yRange` now includes the separate reveal points while visible.
   The forecast array remains unchanged. The repaired UI showed the full actual
   path through August with y-axis ticks extending to 155; hiding it restores the
   forecast-only range. A focused regression test covers an actual observation
   beyond the forecast range and unchanged forecast data.

## Checks passed

- Six focused provider-parser Python tests, rerun after the parser fix.
- Five description-relay Python tests.
- Fifteen contract-journey Python tests.
- `tools/export_contracts.py --check`.
- Original full frontend TypeScript/production build.
- Reconstructed frontend TypeScript/production build after the reveal fix.
- Focused reveal-range regression test in the reconstructed frontend.
- Native Chrome rendered journey and browser DevTools API-network inspection.
  The browser integration host was unavailable; native Chrome control worked.
- Live local fallback through the real router with OpenAI key/model explicitly
  unavailable. No new local model was downloaded.

The frontend build retains its existing large Plotly bundle warning. It is not
an integration failure. Broad evaluation and unchanged test suites were not rerun.

## Rendered browser journey

One successful timeline was created at
`timeline-f4f6144527c84f15b8d789b39d6ead58` in the new verification database.

1. Entered `What if June 11, 2025 CPI were 0.4 percent?`.
2. Entered `On July 15, 2025, add 0.1 percentage points to the previous simulated reading.`.
3. Entered `On August 12, 2025, keep July’s simulated reading unchanged.`.
4. Selected June and replaced it with `Set June 11, 2025 CPI to 0.2%.`.

Saved revision 3 resolved to `0.4 / 0.5 / 0.5`; revision 4 resolved to
`0.2 / 0.3 / 0.3`. IDs remained `p1/p2/p3`. The observed prefix was identical,
the numerical suffix changed, and three markers remained in the rendered chart.
The new revision displayed its own basic summary while narration loaded rather
than displaying the old revision's description.

Real OpenAI descriptions appeared in the UI with the correct model credit. The
chart and reveal control were available while `Writing description with OpenAI…`
was displayed. Reload restored the committed chart and prompts.

Submitted `June 11 CPI could be 0.4% or 0.2%` as an edit. The UI asked the user to
select one value; no revision was committed. The saved database still contained
only revisions 0–4.

Reveal returned 47 actual sessions on the same index base. A saved-snapshot audit
confirmed reveal did not mutate the forecast. Reveal/hide worked as a separate
rendered overlay, and the repaired range displayed its complete path. Neither
forecasting nor description-context construction reads revealed outcomes.

To test narration failure, only the verification backend was temporarily restarted
with an unavailable OpenAI key while retaining the same database/configuration.
Reload showed a typed narration-unavailable message and the saved chart, three
markers and usable reveal control. OpenAI-enabled operation was then restored;
the reloaded UI again displayed a real description.

The local verification receipt is ignored at
`data/local/results/pr6-live-verification-receipt.json` in the original repository.
It contains database/timeline identifiers and assertions, not credentials. Local
market data, databases and provider responses are not included in the PR.

## Review/integration notes

- Review `api/provider_parser.py`, its focused test change, and the updated frontend
  patch. No run-response schema changed for these fixes.
- Integrate the complete frontend from its branch; do not scaffold a new application
  in the backend's minimal `web/`. Preserve the frontend team's client methods when
  reconciling API-client changes.
- The original frontend worktree intentionally remains on the earlier patch. The
  running verification UI uses the separate repaired worktree on port 5175.
- This verifies the bounded five-instruction CPI scope, not arbitrary CPI values,
  instruments or historical periods. Public deployment/data display rights and
  broader scenarios remain outside this task.
- No merge, deployment, Message Board post, data publication or credential change
  was performed. Push only the reviewed source/test/patch/report fix commit to the
  existing task branch after rechecking its remote head; never force-push.
