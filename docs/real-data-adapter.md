# Real-data adapter and research API

Aashna and Aditya are working together in this chat, folder and `backend` branch.
The bounded June real-data path now works through the durable HTTP API as well as
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
against a prior standalone run, add:

```sh
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

Creation returns 20 eligible observed sessions (May 13–June 10), the pinned dataset,
model/corpus versions, March 7, 2022 index base, and June 11 12:29:59 UTC cutoff.
The first commit returns a full snapshot; replacement returns a five-point suffix.
The complete snapshots are stored immutably. Numerical work stays outside the SQLite
write transaction, with expiry/revision checks repeated before the atomic write.
Completed identical retries return their original response before expiry, stale
revision, changed runtime configuration or model execution checks.

Capabilities advertise one prompt, a five-session horizon and two June presets.
The v1 wire enum has only `fixture`/`live`; research uses `live` to identify real
inputs and inference, while `data_label` explicitly says **local historical research**.
This is not a streaming feed or approval for public display. Source/rights notes,
the May 13 BLS evidence available before cutoff, and numerical limitations appear
in capabilities, draft warnings and result panels. The June 11 actual CPI value is
not used as prior evidence. Additional prompts, relative instructions, July/August
dates and unsupported text are rejected before inference. Moving between runtime
modes/datasets cannot rewrite existing timelines; their saved snapshots remain
readable, and writes require the original pinned configuration.

**Not enabled in this step:** HTTP actual-history reveal, multiple real prompts,
broader date/cutoff support, automatic empirical fallback, or OpenAI/Ollama parsing.
The separate `tools/real_forecast.py --reveal` path remains available. Research mode
uses the deterministic parser and makes no paid calls.

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

There are no original releases before May 13 on disk. We do not extract revised
historical tables or treat a later page's retrospective readings as earlier vintages.
The frozen fork is **June 11, 2025 at 12:29:59 UTC**, one second before publication.
Only the May 13 reading is known then. It enters the historical series from its
publication session, never from April 1. A release after a session close enters
the next session. CPI units are percentage values: `0.2`, not `0.002` or a daily shock.

## Files and numerical interface

The current snapshot is `spy-99baca8c94f5871aff6b`. Its identity hashes raw source
hashes, package versions, cutoff and preprocessing policy. Full SHA-256 hashes,
source URLs, source citation metadata, units, coverage, missing inputs, and rights
notes are in `data/local/processed/<version>/manifest.json`. File download times
were not supplied and are explicitly unknown. Readers verify processed file hashes.

| Local output | Purpose |
|---|---|
| `processed/<version>/spy_daily.parquet` | Observed levels available by cutoff only |
| `processed/<version>/cpi_releases.parquet` | Four original vintages; loader filters by publication time |
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

The supported loader is deliberately bounded to this June fork and the four supplied
vintages. It accepts a hypothetical monthly CPI reading between -2% and 2%, held over
five sessions, with a release indicator only on the first. July/August replay chains,
simulated history and broader cutoffs need the next coordinated integration; this
adapter rejects them today. Only 20 sessions have known CPI: the threshold is an
engineering minimum for this example, **not** evidence of adequate forecasting skill.

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

At this fork there is **one** completed reference release (May 13) and **zero**
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

Verified on this Mac: 58 Python tests (32 original, 13 market/adapter and 13 research
HTTP/configuration tests),
34 schema fixtures, 4 frontend tests, strict TypeScript, dependency consistency,
the actual raw-file audit, and both actual offline CPU scenarios. The first measured
forecast took 2.84 seconds including imports/model load; a later reveal run took
4.20 seconds cold. The warmed second scenario took 0.07 seconds in both runs.
These are individual observations, not a latency guarantee.
Calendar, duplicate/gap policy, publication/DST alignment, frozen inputs, hash checks,
separate reveal, bad model outputs, baseline cutoff exclusion, and eight-release
supported behavior are tested. A dependency warning from exchange-calendars/pandas
and sandbox CPU-feature warnings from Arrow did not affect passing checks.

An actual single-worker Uvicorn server was also tested on localhost with the real
snapshot and cached Chronos weights. Both HTTP forecasts matched the standalone
quantiles. Full/suffix updates, immutable history, exact restore and identical
commit retries passed again after stopping and restarting that server. The temporary
test server was stopped. Tests use temporary SQLite files; no existing user database
was migrated or rewritten. Contract export and generated fixture checks passed.

The next shared tasks are HTTP reveal and real multi-prompt replay, then broader
coverage and evaluation. Expand the adapter to support simulated histories and
event-to-event segments before enabling three-prompt real replay. Obtain older
original CPI releases and build chronological evaluation with errors, band
coverage/width and baseline comparison. Runtime OpenAI/Ollama parsing remains
separate. No publication, commit, push, merge or deployment was performed.
