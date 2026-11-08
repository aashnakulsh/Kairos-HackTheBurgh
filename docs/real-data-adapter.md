# Current general-scenario entry point
For the newly approved open-ended scenario flow, start with
[general-scenario-handover.md](general-scenario-handover.md).
`APP_MODE=scenario` uses the full raw SPY history and local FRED CSVs, optional
original BLS releases, on-demand GDELT context, OpenAI research and Chronos numeric
covariate conditioning. The older CPI snapshot workflow below remains available
as `APP_MODE=research`; it does not describe the general scenario limits.

# Real-data adapter and research API

> **Current implementation update (8 November 2026):** Use
> [continuous-cpi-demo-handover.md](continuous-cpi-demo-handover.md) for startup and
> integration. The real backend now accepts continuous validated CPI values,
> defaults to provider parsing in research mode, and uses v3 consistent inference
> blocks. The new launcher selects the richer existing snapshot. Earlier sections
> describing five allowed presets, a deterministic-only parser, v2 identity or
> specific running ports are historical; the underlying data/provenance details
> remain relevant.

Aashna and Aditya are working together in this chat, folder and `backend` branch.
The bounded June–August three-prompt real-data path now works through the durable HTTP API as well as
the standalone scripts. `api/contracts.py`, shared schemas and frontend wire types
are unchanged. The fixture app remains available for frontend development.

## Do this now on the MacBook

Run from the repository root in VS Code. This Mac already has the dependencies and
pinned weights; installation is only needed after an environment change.

```sh
source .venv/bin/activate
# Optional if setting up again; needs internet:
python -m pip install -r requirements-forecast.txt
# These commands use local files and cached weights, with no network/model API calls:
python tools/prepare_market_data.py
python tools/real_forecast.py
# Optional separate actual-history reveal, after the forecasts:
python tools/real_forecast.py --reveal
```

The default runs hypothetical CPI **0.4% and 0.2%**, with one warmed CPU pipeline.
Use `--cpi 0.2` to run one scenario. `DATA_DIR` or `--data-dir` changes the local data
root; keep any custom root outside version control. Explicitly pin an existing
snapshot with `--dataset-version spy-99baca8c94f5871aff6b` rather than `latest.txt`.
Never copy raw data, processed data, result JSON, keys, databases or model weights
into tracked folders. Existing `.gitignore` already excludes `data/local/`.

Windows PowerShell uses the same scripts:

```powershell
# On a new machine only: py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-forecast.txt
# On a new machine only: downloads the public weights; no cloud account/key needed.
python tools/chronos_smoke.py download
python tools/chronos_smoke.py load --offline
python tools/prepare_market_data.py
python tools/real_forecast.py
```

On another machine obtain the source files with appropriate rights and retain the
same raw subdirectories. The existing Mac needs no transfer or Git publication.
CPU is explicit; no Apple-only dependency or acceleration is required. Windows and
Linux execution have **not** been verified. If activation is restricted, invoke
`.venv\Scripts\python.exe` directly instead of changing execution policy.

## OpenAI descriptions after the forecast

The research API still returns Chronos numeric points immediately. The frontend
then forwards the selected prompt's complete, unrounded simulated segment to the
new description relay, which calls OpenAI with a server-side key and returns prose
to the frontend. Descriptions never modify the saved chart or feed back into replay.
Export `OPENAI_API_KEY` and an available `OPENAI_MODEL` before backend startup to
enable this optional stage; `OPENAI_DESCRIPTION_TIMEOUT_SECONDS` defaults to 20.
Without configuration the relay returns a typed 503 and the basic panel/forecast
remains usable. The frontend integration patch includes the caller and display.
See [the exact API flow and request fields](frontend-backend-contract.md#forecast--frontend--openai--frontend).

## Run the research API

The inputs and weights already present on this Mac are sufficient. From the
repository root, run these commands in the server terminal:

```sh
source .venv/bin/activate
export APP_MODE=research
export DATA_DIR=./data/local
export DATASET_VERSION=spy-99baca8c94f5871aff6b
export SQLITE_PATH=./data/local/teamrelay-research.sqlite
export FORECAST_DEVICE=cpu
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
python -m uvicorn api.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

Open <http://127.0.0.1:8000/docs>. In a second activated terminal:

```sh
source .venv/bin/activate
python tools/research_backend_demo.py --receipt data/local/results/research-http-journey.json
```

This creates a timeline, commits **Set June 11 CPI to 0.4%**, replaces p1 with
**Set June 11 CPI to 0.2%**, and checks restore, the unchanged observed prefix,
the immutable previous revision and an identical commit retry. To also compare
against a standalone run made with the current model version, first regenerate that result (old v1 numerical results are not comparable), then run:

```sh
python tools/real_forecast.py --dataset-version spy-99baca8c94f5871aff6b
python tools/research_backend_demo.py --expected-forecast data/local/results/spy-99baca8c94f5871aff6b/forecast.json --receipt data/local/results/research-http-journey.json
```

Each invocation without `--restore-from` creates a new local timeline. After stopping
the server with Ctrl+C and restarting it with the same settings/database, verify
the exact saved snapshots and retry without running inference:

```sh
python tools/research_backend_demo.py --restore-from data/local/results/research-http-journey.json
```

PowerShell server setup, using the existing environment:

```powershell
.\.venv\Scripts\Activate.ps1
$env:APP_MODE = 'research'
$env:DATA_DIR = './data/local'
$env:DATASET_VERSION = 'spy-99baca8c94f5871aff6b'
$env:SQLITE_PATH = './data/local/teamrelay-research.sqlite'
$env:FORECAST_DEVICE = 'cpu'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
python -m uvicorn api.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

The client commands are identical in a second activated PowerShell terminal.
These are local startup commands, not deployment. Environment variables are read
at process start; `.env` is not loaded automatically. `APP_MODE=fixture` selects
the existing synthetic durable behavior. With no explicit `SQLITE_PATH`, research
mode defaults to `DATA_DIR/teamrelay-research.sqlite` and fixture mode to
`DATA_DIR/teamrelay.sqlite`. `api.fixture_app:app` ignores these mode settings.

Research mode requires an explicit snapshot name; it never follows `latest.txt`.
Missing files, invalid hashes or a different manifest version fail startup. Snapshot
inputs load once, and Chronos loads offline on the first commit and stays warm.
Creation and interpretation perform no inference. The server remains usable for
restore/retries without loading model weights. Use one worker initially.

With the original four-release snapshot, creation returns 20 eligible observed sessions (May 13–June 10), the pinned dataset,
model/corpus versions, March 7, 2022 index base, and June 11 12:29:59 UTC cutoff.
The first commit returns a full snapshot; replacement returns a five-point suffix.
The complete snapshots are stored immutably. Numerical work stays outside the SQLite
write transaction, with expiry/revision checks repeated before the atomic write.
Completed identical retries return their original response before expiry, stale
revision, changed runtime configuration or model execution checks.

Capabilities advertise three prompts and up to 65 simulated sessions, with five deterministic presets. The supported journey is June 11 set 0.4%, July 15 add 0.1 percentage points to the preceding reading, August 12 keep July, then replace June with 0.2%. The resulting readings are 0.2 / 0.3 / 0.3. This journey ends August 18 (47 exchange sessions after the fork). Later segments use earlier simulated medians; actual future prices never enter replay. Bands are conditional on that median trajectory, not joint propagated path uncertainty.

The first event must remain June 11. Replacing a later event uses the earlier old/new start; suffixes remove obsolete tails. New events can extend the prior five-session tail across intervening sessions, so those additions return a full response when the previously displayed prefix gains points. Prompt IDs and earlier revisions remain intact.

`GET /api/timelines/{id}/revisions/{revision}/reveal` returns matching-index actual observations for that saved revision's simulated dates, source attribution and explicit gaps. It performs no inference or writes. Missing or corrupt local actuals return an explicit failure; saved forecasts remain unchanged.

The v1 wire enum has only fixture/live; research uses live with an explicit local historical research label. This is not a streaming feed or approval for public display. The deterministic parser makes no paid calls. General free-form parsing, deletion through the real API and automatic empirical fallback remain unsupported.

The replay model identity now ends in `cpu-cpi-v2`. Existing v1 timelines remain readable, but cannot be edited using v2. Use a new timeline/database for the new behavior; do not delete old databases. Dataset changes similarly require new timelines.

## Actual input audit, 2026-11-08

`SPY_raw_1min.parquet` contains **455,875 rows** from **2022-03-07 09:30** through
**2026-11-06 15:59 America/New_York**, all `source=iex`. Columns are `datetime`
(naive nanosecond timestamp), `Open/High/Low/Close` (float64), `Volume` (int64), and
`source` (string). There are no nulls, duplicate timestamps, invalid OHLC values,
zero-volume rows, or entirely absent trading sessions in that span.

| Check | Actual finding and policy |
|---|---|
| Trading sessions in raw span | 1,174 |
| Missing minute bars | 414 across 60 sessions; no interpolation |
| Out-of-session records | 49 quarantined, timestamps retained in manifest audit |
| Missing closing minute | December 23, 2024; exclude that daily close |
| Eligible daily close proxies | 1,173 in separate actuals store; 818 at the frozen cutoff |
| June example | All 20 history sessions and five requested outcome sessions complete |
| Base | March 7, 2022 close proxy, USD 419.47 = index level 100, fixed across edits |
| 2025 calendar | 250 sessions, 11 weekday closures, 3 early closes |
| 2008 | Unsupported: source starts in March 2022 |

The [provider dictionary](https://hfdatalibrary.com/pages/dictionary) identifies
timestamps as Eastern time and prices as split-adjusted, not dividend-adjusted.
These are **IEX-only minute bars**, not consolidated US-market prices. A daily
observation is the last minute's close only if its timestamp is exactly one minute
before the exchange close. Its modeled availability is the minute's end (16:00 ET,
or 13:00 on early-close days). Interior missing minutes are recorded; a valid final
minute may still supply the close. This is a disclosed close proxy, not an official
closing-auction price or total-return index. Exact duplicate rows can be deduplicated
with a count; conflicting timestamps, nulls or invalid OHLC fail preparation.

The supplied NYSE PDF was visually checked, including January 9 and the July 3,
November 28 and December 24 early closes. The generated XNYS schedule from pinned
`exchange-calendars==4.13.2` is cross-checked against those 2025 dates. The
[NYSE closure announcement](https://ir.theice.com/press/news-details/2024/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of-Mourning/default.aspx)
also confirms January 9. Years outside 2025 use the library's rules and have not
been independently reconciled against annual official PDFs.

Original CPI narrative values are parsed from the saved BLS pages, with filename,
publication time, reference month, adjustment and units validation:

| Original release | Reference month | Headline CPI-U monthly, seasonally adjusted | Publication |
|---|---|---|---|
| [May 13](https://www.bls.gov/news.release/archives/cpi_05132025.htm) | April 2025 | 0.2% | 08:30 ET / 12:30 UTC |
| [June 11](https://www.bls.gov/news.release/archives/cpi_06112025.htm) | May 2025 | 0.1% | 08:30 ET / 12:30 UTC |
| [July 15](https://www.bls.gov/news.release/archives/cpi_07152025.htm) | June 2025 | 0.3% | 08:30 ET / 12:30 UTC |
| [August 12](https://www.bls.gov/news.release/archives/cpi_08122025.htm) | July 2025 | 0.2% | 08:30 ET / 12:30 UTC |

The original snapshot contains only these four releases. The expanded snapshot described below adds earlier original vintages. We do not extract revised
historical tables or treat a later page's retrospective readings as earlier vintages.
The frozen fork is **June 11, 2025 at 12:29:59 UTC**, one second before publication.
In the original snapshot only the May 13 reading is known then. It enters the historical series from its
publication session, never from April 1. A release after a session close enters
the next session. CPI units are percentage values: `0.2`, not `0.002` or a daily shock.

## Files and numerical interface

The original snapshot is `spy-99baca8c94f5871aff6b`. The additional snapshot is `spy-8c865e107520d2cdab66`. Its identity hashes raw source
hashes, package versions, cutoff and preprocessing policy. Full SHA-256 hashes,
source URLs, source citation metadata, units, coverage, missing inputs, and rights
notes are in `data/local/processed/<version>/manifest.json`. File download times
were not supplied and are explicitly unknown. Readers verify processed file hashes.

| Local output | Purpose |
|---|---|
| `processed/<version>/spy_daily.parquet` | Observed levels available by cutoff only |
| `processed/<version>/cpi_releases.parquet` | Original vintages; loader filters by publication time |
| `processed/<version>/sessions.parquet` | Session dates and timezone-aware UTC open/close |
| `processed/<version>/minute_gaps.parquet` | Per-session counts, missing minute timestamps, valid-close flag |
| `reveal/<version>/spy_actuals.parquet` | Actual outcomes, available only through `data/reveal.py` |
| `results/<version>/forecast.json` | Both requests/results, baselines, timings, inference versions; optional reveal |

`data/real_market.py:MarketInputs.request(cpi_percent, model_version)` constructs
the existing `ForecastRequest`. It supplies 20 contiguous known-CPI sessions,
May 13–June 10, and the five future sessions **June 11, 12, 13, 16, 17**.
`training/chronos_adapter.py:ChronosAdapter.forecast_segment` implements the existing
`NumericalAdapter` protocol; `api/synthetic_forecast.py` is unchanged.

The adapter uses `amazon/chronos-2`, `chronos-forecasting==2.3.2`, weight revision
`29ec3766d36d6f73f0696f85560a422f50e8498c`, CPU, four Torch threads, and a lock around
the warmed pipeline. Weights load from the existing Hugging Face cache, offline.
`predict_df` receives indexed historical levels and CPI/release-indicator
covariates. Future input has no target column. An artificial regular daily grid
represents **trading-session ordinal**, then maps output back to actual session dates.
`ForecastResult.value` is q50; q10/q90 are the requested model quantiles. Failed
loads, nonfinite/crossing bands, incorrect output sessions, unsupported snapshots,
instruments, horizons or modified historical inputs return explicit unsupported
results with no points. No synthetic fallback is substituted.

The live research cutoff remains June 11. Numerical requests may extend that frozen observed prefix with contiguous simulated medians and June/July/August interventions. Historical context is capped at 252 contiguous sessions and starts after the last missing close; gaps are never imputed. The original snapshot has 20 known-CPI sessions, the expanded snapshot has 114 (December 24–June 10, after the missing December 23 close). Twenty sessions is an engineering minimum, not evidence of forecasting skill.

The forecast is conditional association, not an estimated causal CPI response.
Current-vintage split-adjusted prices and bar-end availability assumptions are not
point-in-time delivery evidence. Pretrained weights may include post-cutoff training
data; this demonstration is **not a leakage-free historical backtest**. Bands are
uncalibrated on SPY, and Chronos support_count=0 makes no analogue-count claim.

## Baseline and unsupported coverage

`training/baseline.py` implements two disclosed modes over completed earlier release
windows. Each needs the preceding close plus all five outcome closes available by
cutoff. Missing closes exclude the entire window. Duplicate release vintages are
rejected, and a missing preceding reference month cannot supply an analogue delta.

- **Reference:** empirical distribution of all eligible five-session level ratios;
  ignores hypothetical CPI and is labeled accordingly.
- **Analogue:** match the hypothetical change from the previously published reading
  to prior release changes within **±0.1 percentage points**.
- Both use a fixed **eight distinct release** floor, disclose eligible release dates
  and count, and compute pointwise empirical q10/q50/q90. The architecture's eight
  analogue minimum is also conservatively applied to reference output here.

In the original four-release snapshot there is **one** completed reference release (May 13) and **zero**
analogue releases because its preceding original CPI publication is missing.
Both correctly return unsupported for both scenarios. Obtain at least eight complete
eligible earlier releases plus their predecessor vintages (more may be needed to
obtain eight tolerance matches). Do not lower the floor to make the demo pass.
No automatic fallback to an unsupported empirical output is enabled.

## Rights and publication

The manifest supports local academic/educational research only. HF's
[terms](https://hfdatalibrary.com/pages/terms) restrict intended use to research and
education, describe compilation/documentation attribution under CC BY 4.0, and
incorporate the [IEX terms](https://www.iex.io/legal/hist-data-terms). Retain the
provider citation and linked IEX attribution. The manifest does **not** approve
public demo/display or redistribution; review the intended use before enabling a feed.
BLS material is generally public domain with source credit, subject to exceptions
for third-party material ([BLS policy](https://www.bls.gov/opub/copyright-information.htm)).
NYSE PDF redistribution has not been approved; keep the source artifact local and
cite NYSE/ICE for calendar facts. No credentials or restricted datasets are committed.

## Verification and next integration

Commands (the optional real-data tests use invented tiny fixtures, not raw market files):

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
python tools/check_fixtures.py
node --test tests/frontend-contract.test.mjs
npx --yes --package typescript@5.9.3 tsc --noEmit --strict --target ES2022 --module ESNext --moduleResolution bundler --allowImportingTsExtensions --lib ES2022,DOM web/src/api/client.ts web/src/api/applyRun.ts
python -m pip check
```

Verified on this Mac in this integration pass: 65 Python tests, 34 schema fixtures, contract/fixture regeneration checks, four frontend contract tests in each checkout, and the frontend TypeScript/production build. Real offline CPU HTTP checks passed for June replacement and the complete three-prompt journey. Actual-history reveal through the Vite proxy returned all 47 exchange sessions without changing the saved revision. The real frontend client/cache also passed its HTTP journey through the Vite proxy, and real process restart preserved exact snapshots and original commit retries. Browser automation was unavailable, so rendered interactions still need the manual checklist below. Windows/Linux were not executed.

## Expanded CPI history and evaluation

The direct BLS downloader received HTTP 403 on this Mac. Instead, 28 official original archive pages were retrieved through the web reader and preserved as clearly labeled `.txt` source captures in `data/local/raw/bls-expanded/`; these are not claimed to be original HTML bytes. Combined with the original four HTML releases, they cover reference months December 2022–July 2025 without gaps. The manifest records each source file hash, official archive URL, publication timestamp, units and extraction method. Source: https://www.bls.gov/bls/news-release/cpi.htm . No revised historical tables were used.

```sh
python tools/prepare_market_data.py --cpi-directory data/local/raw/bls-expanded
python tools/real_forecast.py --dataset-version spy-8c865e107520d2cdab66
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python tools/evaluate_market.py --dataset-version spy-8c865e107520d2cdab66
```

The preparation command preserves the original snapshot and writes a new version. `latest.txt` now points to the expanded version; pin versions explicitly for reproducibility. To obtain original HTML on another network, `python tools/download_cpi_archives.py` is available; it validates each narrative before accepting it and does not bypass provider restrictions. HTML and text captures have different hashes and therefore produce different snapshot IDs.

At the June cutoff the expanded baseline has 29 complete reference windows. Analogue support is 10 for CPI 0.4% and 15 for CPI 0.2%, both above the unchanged floor of eight. These standalone baselines are not silently substituted for Chronos in the HTTP API.

`tools/evaluate_market.py` uses 18 chronological publication dates, January 2024–June 2025. Each fold freezes history one second before publication, explicitly conditions on the subsequently published CPI as a scenario, and loads actual outcome prices only after forecasting. It records mean absolute index error, q10–q90 coverage and interval width. January 2025 is unsupported because the missing December 23 close leaves fewer than 20 contiguous sessions. Some analogue folds have fewer than eight matches and remain unsupported.

Local results in `data/local/results/spy-8c865e107520d2cdab66/evaluation.json`:

| Engine | Scored / attempted folds | Mean absolute index error | Pointwise interval coverage |
|---|---:|---:|---:|
| Chronos | 17 / 18 | 1.6021 | 78.82% |
| Reference | 17 / 18 | 1.4315 | 72.94% |
| Analogue | 6 / 18 | 1.2062 | 76.67% |

The analogue row uses a different subset and is not a comparable leaderboard. These are descriptive diagnostics, not calibrated trading evidence or a leakage-free held-out evaluation: pretrained weights and current split-adjusted prices may contain later information. Non-2025 calendars are from exchange-calendars and have not been manually reconciled against annual NYSE PDFs.

## Frontend integration and manual browser check

The remote `frontend` branch was inspected at `f272c22` in a separate detached worktree, `/private/tmp/teamrelay-frontend-integration`. The backend checkout stays on `backend`. Eight frontend files are adjusted locally, including the generated description types and mock API boundary: server prompt limits/presets, separate mock/server stored timeline IDs, unsupported reveal handling, stale-reveal guards, hiding unsupported deletion, configurable development proxy, and frontend-initiated OpenAI descriptions. The description request/response types and endpoint are additive wire changes; existing run payloads are unchanged.

A portable copy of these changes is stored in `integration/frontend-research.patch`. It targets the frontend commit above and is not applied to the backend's minimal web directory. To apply in another frontend checkout after inspecting its working tree:

```sh
git apply --check /path/to/TeamRelay-Hackathon/integration/frontend-research.patch
git apply /path/to/TeamRelay-Hackathon/integration/frontend-research.patch
```

Do not apply it twice in the existing temporary worktree. Keep this patch until the frontend changes are deliberately committed on an appropriate branch; temporary directories are not permanent storage.

Start the backend above on port 8000, using a fresh `SQLITE_PATH=./data/local/teamrelay-research-v2.sqlite` for a clean preview. In a separate terminal:

```sh
cd /private/tmp/teamrelay-frontend-integration/web
# Node 22.18+; dependencies are already installed in this worktree.
VITE_API=server BACKEND_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5174
```

PowerShell, from the equivalent frontend checkout's web directory:

```powershell
$env:VITE_API = 'server'
$env:BACKEND_URL = 'http://127.0.0.1:8000'
npm ci --ignore-scripts
npm run dev -- --host 127.0.0.1 --port 5174
```

The current temporary preview is already running at http://127.0.0.1:5174, proxied to the test backend at port 8766 with `/private/tmp/teamrelay-integration.sqlite`. It uses the original snapshot, not your existing port-8000 server or database. To reproduce the nonvisual frontend integration check:

```sh
node tools/frontend_research_check.mjs /private/tmp/teamrelay-frontend-integration/web http://127.0.0.1:5174
```

Run that command from the backend repository root. It creates one local test timeline.

Open http://127.0.0.1:5174 and perform this remaining visual check:

1. Confirm the local historical research label; select the June 0.4% preset and submit.
2. Confirm the median/bands and prompt marker; add the July relative and August carry presets.
3. Select p1, choose June 0.2%, and replace. Confirm all three markers remain and the panels resolve to 0.2 / 0.3 / 0.3.
4. Reload and confirm the saved chart restores. Reveal actual history, then hide it; the forecast must stay unchanged.
5. Submit an unsupported prompt and confirm the existing chart stays visible with an explanation. Deletion should not appear in server mode.

No commits, pushes, posts, merges or deployment were performed. Runtime OpenAI/Ollama parsing and broader event families remain separate follow-up work.
