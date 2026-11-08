# Durable backend milestone and host handoff

Current real-data/reveal/three-prompt integration: see [real-data-adapter.md](real-data-adapter.md). The synthetic milestone details below remain applicable to fixture mode.

Current update: Aashna and Aditya work together in this folder/chat. The bounded
June real-data path is now available through `APP_MODE=research`; see
[the research API startup and tests](real-data-adapter.md#run-the-research-api).
The original synthetic milestone and its verification are recorded below.

Work stays on `backend`, tracking `origin/backend`, as explicitly authorized by
Aashna. The tree was clean at task start. Board #1 and the local inbox contained
test notifications and Aditya's foundation announcement; no active conflicting
edit was found. Nothing has been posted, committed, pushed, merged or deployed.

## Implemented behavior

`api/app.py:create_app` supplies the existing HTTP commands with durable SQLite
storage. `api/fixture_app.py:app` remains the original in-memory frontend fixture
server. Both use the unchanged `api/contracts.py` wire schemas.

- SQLite stores timeline pointers, immutable full revision snapshots, bound drafts,
  creation retry records and timeline-scoped commit retry records. WAL, foreign keys,
  full synchronous writes and short `BEGIN IMMEDIATE` transactions are enabled.
- Candidates are built outside transactions. The final transaction checks the active
  revision and draft expiry again, then writes pointer, snapshot and original retry
  response together. Any failure rolls everything back. No process-local mutex is
  needed for correctness; initially run one worker to limit model memory later.
- Canonical request bodies are SHA-256 hashed. Identical completed retries return
  the stored original response before checking revision or expiry, including after
  restart. A reused ID with another body conflicts. Creation retries are also durable.
- Drafts last five minutes and bind timeline, revision, text, mode and selected ID.
  Their canonical instruction is saved; replay never reparses previous prompts.
- Three single-release prompts support set, relative percentage-point addition and
  carry. Stable IDs/display numbers survive edits and chronological reordering.
  Replacement uses the earlier old/new start. Saved prefix points are reused exactly;
  downstream inference receives the preceding simulated medians and re-resolved CPI.
- Snapshot history is the checkpoint for this bounded release-only milestone.
  Forecast calls receive only the current segment's covariates; the next prompt
  enters only at its activation. Later edits never advance the evidence cutoff.
- `SyntheticAdapter` is deliberately arithmetic, with synthetic labels on every run
  and panel. `capabilities.mode` remains `fixture` because the contract only offers
  fixture/live and there is no real feed. Durability does not imply real forecasting.
- Real reveal is unavailable and returns an explicit unsupported Problem. The fixture
  app still provides synthetic reveal. No invented actual prices are returned here.

### Full responses and bridge additions

Creation, first commit and restore return full responses. Replacements return suffixes
when the prefix before `changed_from` is unchanged, including shorter tails and date
moves. A suffix deletes the entire old tail before appending its replacement.

There is a necessary handoff detail in the existing spec: a June five-session run ends
June 17, whereas adding July 15 creates a June–July bridge **before** the new event's
`changed_from`. A July-only suffix cannot transport those new bridge points. The durable
service returns a full snapshot in that case while keeping `changed_from` at July 15.
Existing `applyRun()` already supports it; no frontend or schema change is needed.
This qualifies the prose expectation that every later commit is a suffix. The test
suite checks that applying either response form exactly reconstructs restore. Earlier
existing points retain their values. Coordinate this detail with the frontend before
publication; the old fixture generator has not been changed.

## Do this now on the MacBook

Start in a fresh VS Code terminal at the repository root. This checkout uses pip and
requirements files, not Poetry/Conda/a project uv lock. A local Python **3.11** `.venv`
was created for these checks because the terminal's system Python was 3.9.6. A temporary
uv bootstrap downloaded the interpreter; pip remains the project's dependency manager.

### 1. Activate, install, download and load separately

```sh
source .venv/bin/activate
python --version
python -m pip install -r requirements-contracts.txt
python -m pip install -r requirements-chronos-smoke.txt
python tools/chronos_smoke.py download
python tools/chronos_smoke.py load --offline
```

Expected Python on this Mac: 3.11.18. On another Mac/Linux host with Python 3.11
installed, first run `python3.11 -m venv .venv`, then the activation above. Use
`python -m pip`, so installs go to the selected environment rather than system Python.

The two pip installs and first weight download need internet. The public, ungated
`amazon/chronos-2` weights need no cloud account, AWS service or API key. The download
step caches a pinned snapshot; it does not prove that the model loads or predicts.
`load --offline` blocks Hub/network access and loads the local snapshot on **CPU**.
Expected messages are `weights cached` and then, in the separate process,
`PASS: Chronos-2 loaded on CPU`. No Apple-only runtime is required by these commands.
[Model metadata](https://huggingface.co/api/models/amazon/chronos-2).

Default weights cache: `~/.cache/huggingface/hub/models--amazon--chronos-2/`, with
snapshot `29ec3766d36d6f73f0696f85560a422f50e8498c`. The script prints its actual path.
Set `HF_HOME` or `HF_HUB_CACHE` before both download and reload to use another location.
Keep that location outside Git. [Hugging Face cache documentation](https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache).

The checkout already explicitly selects `amazon/chronos-2`, package
`chronos-forecasting`, CPU and `predict_df` in `docs/architecture.md:86` and
`.env.example:10`. `requirements-contracts.txt:1-6` originally contained **no Chronos
version constraint**. The new optional `requirements-chronos-smoke.txt:4` pins 2.3.2.
This is a host smoke-test pin, not a completed pipeline lockfile. Upstream 2.3.2 requires
Python >=3.10, torch >=2.2,<3, transformers >=4.41,<6, accelerate >=1.1.0,<2,
numpy >=1.21,<3, einops >=0.7,<1 and pandas >=2,<4. Record the resolved environment
when Aditya pins the actual adapter. [Versioned package metadata](https://raw.githubusercontent.com/amazon-science/chronos-forecasting/v2.3.2/pyproject.toml),
[PyPI release](https://pypi.org/project/chronos-forecasting/2.3.2/).

### 2. Forecast synthetic numbers before obtaining market data

```sh
python tools/chronos_smoke.py forecast --offline
```

This separately loads the cached model and predicts five artificial daily steps from
96 synthetic levels. Expected: five rows with columns `0.1`, `0.5`, `0.9`, all finite,
with q10 <= q50 <= q90, followed by a PASS line. Exact numerical values are not an
acceptance target. This checks the actual pretrained engine on CPU; it says nothing
about SPY accuracy or causal CPI effects. There are no market downloads in the script.

All Chronos steps are optional for the durable/fixture suite. If package or weight
download is unavailable, skip them and start/test the backend below. Do not replace
the synthetic backend adapter with this smoke script.

### 3. Obtain real inputs; none are bundled in this checkout

`data/` and `training/` initially contained only READMEs. There was no download script,
real source-rights manifest, Parquet file, session calendar, trained adapter or raw
market file. `shared/fixtures/manifest.json` indexes **synthetic contract examples**;
it is not a real-data rights manifest. All proposed local destinations below are
under ignored `data/local/`. They are handoff paths, not loaders implemented here.

Create destination directories on either platform:

```sh
python -c "from pathlib import Path; [Path(p).mkdir(parents=True, exist_ok=True) for p in ['data/local/raw/hf', 'data/local/raw/bls', 'data/local/processed', 'data/local/reveal']]"
```

| Input | Direct source and steps | Destination and usable range | Access / display conditions |
|---|---|---|---|
| SPY prices | [HF download](https://hfdatalibrary.com/pages/download): sign in/create a free account, search SPY, choose one-minute Raw, download Parquet and retain the original filename/hash. There is no repo downloader. Aditya must validate bars and derive daily eligible closes. | `data/local/raw/hf/`; proposed `processed/spy_daily.parquet`. Provider coverage starts **2022-03-07**, ticker-dependent through latest available bar; actual SPY endpoints/gaps are unverified until downloaded. Start with June 11 and July 15, 2025 release windows plus sufficient prior context. | Free account; programmatic access uses its personal API key. Academic/educational research terms, CC BY 4.0 compilation attribution, and IEX linked notice apply. Verify the intended public judging/display use before enabling a feed. Keep raw files local. |
| As-released headline CPI-U, seasonally adjusted monthly percent change | [BLS archive](https://www.bls.gov/bls/news-release/cpi.htm). Save original release HTML for [June 11](https://www.bls.gov/news.release/archives/cpi_06112025.htm), [July 15](https://www.bls.gov/news.release/archives/cpi_07152025.htm) and [August 12](https://www.bls.gov/news.release/archives/cpi_08122025.htm), plus preceding releases for every history date. Use browser Save Page As if automated access is blocked. No repo downloader exists. | `data/local/raw/bls/cpi_06112025.htm`, analogous filenames; proposed `processed/cpi_releases.parquet`. Initial scenario publications June–August 2025; archives also have older years, but coverage must intersect prices. | Public archived HTML; no API key/account. Credit BLS; third-party photos/illustrations are excluded from its public-domain statement. |
| Exchange sessions | [NYSE hours/calendars](https://www.nyse.com/markets/hours-calendars). Aditya must construct and verify the chosen exchange calendar, including holidays, early closes and America/New_York timestamps. | Proposed `processed/sessions.parquet`, covering context and all five-session windows (initially 2025). No real calendar is on disk. | Public reference page, no login. Record calendar source/version; do not treat weekdays alone as exchange sessions. |
| Dated explanatory evidence | Use the same original BLS release text for a first supported source; save source URL, release timestamp and paragraph/table locator. The hypothetical event's own release and later archives cannot become pre-fork evidence. | `raw/bls/` plus proposed local evidence index/manifest. Evidence must be published at or before the frozen cutoff. | Cite BLS; keep citations tied to the archived version. No separate licensed political-evidence corpus is present. |
| Reveal outcomes | Derive actual post-fork SPY closes from the licensed price file using a **separate reader**. | Proposed `reveal/spy_actuals.parquet`; for first scenario June 11, 12, 13, 16, 17, 2025. | Same price-feed rights. Never place these future target levels in `ForecastRequest.future`. |

The price provider covers one exchange, not a consolidated SPY tape, and adjusts for
splits rather than dividends. Its Clean version uses a centered outlier filter; for an
as-of experiment, Aditya must audit that look-ahead risk or use Raw with causal
validation. Do not forward-fill missing prices as if observed. The provider begins
in March 2022: **2008 and all earlier requested years are unsupported by this price
source**, regardless of available CPI archives or the 1980–2026 viewport.
[Coverage/methodology](https://hfdatalibrary.com/pages/docs),
[Raw/Clean definitions](https://hfdatalibrary.com/pages/versions).

HF terms restrict the purpose to academic/educational research and exclude trading
use. A public demo is not automatically a blanket redistribution clearance. Record
source/version/hash, coverage, terms snapshot, attribution and allowed display in
Aditya's source manifest. Include HF's citation and the notice/link required by
IEX §1 when displaying or providing its historical data.
[HF terms](https://hfdatalibrary.com/pages/terms),
[IEX terms](https://www.iex.io/legal/hist-data-terms),
[BLS reuse rules](https://www.bls.gov/opub/copyright-information.htm).

CPI alignment uses **publication**, not reference month. May 2025 CPI was released
June 11 at 08:30 Eastern (`2025-06-11T12:30:00Z`); June CPI was published July 15 and
July CPI August 12. Carry the last reading actually released at each session. Set
`release_indicator=1` at an eligible publication session and zero otherwise. Preserve
original vintages: archived figures can differ from today's revised database. At a
pre-release fork, exclude that release's realized value from history; insert the
user's explicit assumption into future covariates. [June archive](https://www.bls.gov/news.release/archives/cpi_06112025.htm),
[BLS archive revision notice](https://www.bls.gov/bls/news-release/cpi.htm).

### 4. Smallest integration for Aditya

The interface already exists at `api/contracts.py:381` (`ForecastRequest`) and
`:406` (`ForecastResult`). `api/synthetic_forecast.py:NumericalAdapter` defines
`forecast_segment(request) -> ForecastResult`, with a stable `model_version` attribute.
Inject an adapter through `create_app(adapter=...)` for tests. The current replay
data source is synthetic; adding a real adapter alone does **not** make it a real run.

First task: provide one versioned eligible June 11 request and supported/unsupported
results using a rights-reviewed price slice, CPI vintages and a verified calendar.
Proposed `processed/spy_daily.parquet`, `processed/cpi_releases.parquet`,
`processed/sessions.parquet` and the source manifest supply history, publication
availability, covariates and session mapping. They do not exist yet. The existing
`shared/fixtures/forecast-request.json` and `forecast-result.json` illustrate shape
only and must not be relabeled as real data.

For the minimal request, freeze information at `2025-06-11T12:29:59Z`; history ends
with June 10's eligible close. Index the observed SPY levels on one pinned base and
retain that base across revisions. Use all required historical context, not just one
price. Future rows are:

| date | cpi_percent, original | cpi_percent, replacement | release_indicator |
|---|---:|---:|---:|
| 2025-06-11 | 0.4 | 0.2 | 1 |
| 2025-06-12 | 0.4 | 0.2 | 0 |
| 2025-06-13 | 0.4 | 0.2 | 0 |
| 2025-06-16 | 0.4 | 0.2 | 0 |
| 2025-06-17 | 0.4 | 0.2 | 0 |

These are the next five sessions **including release day**, since the fork is before
the opening session. 0.4/0.2 are hypothetical monthly CPI percentages, not actual
releases or daily market shocks. Map session ordinals to a regular model grid and
map back to these exact dates. Request 0.1/0.5/0.9 quantiles. Return exactly five
`kind=simulated` indexed levels, finite ordered bands, correct segment ID, actual
engine/version, honest support count and explicit assumptions. Unsupported means
reason plus empty points; do not silently return a shorter horizon. Keep the actual
June 11–17 target prices solely in the reveal reader.

Additional integration inputs needed: immutable dataset/weight/config versions,
rights status, full eligible historical window, split/base policy, calendar/version,
CPI vintages with availability timestamps, context length, supported horizon, and
baseline support definition. Adapter assumptions are surfaced in panels. Downstream
segments inherit simulated medians; the backend enforces exact output sessions and
segment/engine/version correspondence. Longer bridges need explicit Chronos support;
the five-session baseline must reject unsupported lengths. Real loading, numerical
pipeline, baseline and evaluation remain Aditya's work.

## Prompt model selection (independent of Chronos)

OpenAI remains the intended primary parser with its key on the server; Ollama is the
planned fallback. Neither provider is called by the milestone. `ScenarioParser.parse`
returns `ParsedScenario`; a future provider must use the same server validation.
Environment settings are read directly; `.env.example` is a reference and `.env`
is not automatically loaded. There is no API key requirement for these tests.

```sh
ollama list
export OLLAMA_BASE_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=qwen3.5:9b
python tools/check_ollama.py
# Later, choose the other installed tag and verify without editing code:
export OLLAMA_MODEL=qwen3.6:27b
python tools/check_ollama.py
```

The Mac reports `qwen3.5:9b` (7.6 GB) and `qwen3.6:27b` (18 GB). The checker uses
`GET /api/tags` and `POST /api/show`; it checks installed metadata, not generation.
Its selected tag can feed the future Ollama parser through `Settings.ollama_model`.
The durable app intentionally continues to use `PresetParser` until provider adapters
are implemented and tested. A configuration change does not falsely enable them.

## Start and verify the durable backend

```sh
source .venv/bin/activate
export SQLITE_PATH=./data/local/teamrelay.sqlite
python -m uvicorn api.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

Open `http://127.0.0.1:8000/docs`. Stop with Ctrl+C; restart the same command and restore
the saved timeline ID. To run the original fixture server instead (on another port):

```sh
python -m uvicorn api.fixture_app:app --host 127.0.0.1 --port 8001 --workers 1
```

With the durable server running, open a second terminal at the repository root:

```sh
source .venv/bin/activate
python tools/backend_demo.py
```

It creates a synthetic timeline, adds three prompts, replaces p1, verifies restore,
and prints the timeline URL. After a server restart, use
`python tools/backend_demo.py --restore TIMELINE_ID` with the ID it printed.

Checks from the activated environment; Chronos/Ollama are not required:

```sh
python tools/export_contracts.py --check
python tools/build_example_fixtures.py --check
python tools/check_fixtures.py
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/frontend-contract.test.mjs
npx --yes --package typescript@5.9.3 tsc --noEmit --strict --target ES2022 --module ESNext --moduleResolution bundler --allowImportingTsExtensions --lib ES2022,DOM web/src/api/client.ts web/src/api/applyRun.ts
```

Node 22.18+ is required for native TypeScript stripping. No Node was initially on this
terminal's PATH. The agent used a checksum-verified official Node 24.11.0 archive under
`/private/tmp/node-v24.11.0-darwin-arm64/` for frontend checks; that is a temporary test
runtime, not a project dependency. Install Node LTS normally for continued frontend work.

### Windows PowerShell equivalents

With Python 3.11 installed, create `.venv` only if it does not exist:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -m pip install -r requirements-contracts.txt
# Optional model checks:
python -m pip install -r requirements-chronos-smoke.txt
python tools/chronos_smoke.py download
python tools/chronos_smoke.py load --offline
python tools/chronos_smoke.py forecast --offline
ollama list
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434'
$env:OLLAMA_MODEL = 'qwen3.5:9b'
python tools/check_ollama.py
$env:SQLITE_PATH = './data/local/teamrelay.sqlite'
python -m uvicorn api.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

If PowerShell activation is restricted, invoke `.\.venv\Scripts\python.exe` instead of
`python`; no execution-policy change is necessary. All test commands above otherwise
work in PowerShell. The default HF cache is under the user's `.cache\huggingface\hub`;
use `$env:HF_HOME = 'D:\teamrelay-model-cache'` to choose a writable alternative.
Windows/Linux execution has not been claimed from Mac-only tests.

## Remaining work and next integration

The next integration step is the existing browser API client and cache against the
durable app: create, add three presets, replace p1, reload the saved timeline and
inspect revision 3. Verify the full bridge-addition behavior before wiring chart
animations. Real parser providers, licensed market data, actual reveal, Chronos/baseline
adapter, evidence retrieval and general interval/recurrence semantics are unfinished.
No authentication or internet-facing deployment is included. Start on localhost.

SQLite snapshots currently retain the complete bounded history; data migration and
retention policies will be needed before growing beyond this local demo. Model version
changes across an existing scenario also need an explicit migration/replay policy.
The fixed synthetic calendar/base/history in `api/replay.py` must be replaced with
Aditya's versioned data boundary before a real feed is enabled.

## Verification on this Mac, 8 November 2026

| Check | Observed result |
|---|---|
| Python 3.11.18, repository requirements in `.venv` | Installed; `pip check` passed |
| Contract export | Passed; fixed only the exporter's Python-version-dependent HTTP 422 description; existing generated outputs remain unchanged |
| Fixture regeneration and schema/semantic checks | All 34 fixtures and journey reproducible and valid |
| Python suite | 32 tests passed: 15 existing plus 17 durable tests |
| Frontend Node tests | All 4 passed on Node 24.11.0 |
| TypeScript 5.9.3 strict no-emit | Passed with the documented command |
| Uvicorn HTTP demo | Create/add/add/add/replace and full restore passed on localhost; process stopped, restarted, revision 4 restored; server stopped afterward |
| Git whitespace check | Passed; changes remain uncommitted on `backend` |
| Ollama | Installed tags listed; selected `qwen3.5:9b` metadata verified; no generation or parser conformance check |
| Chronos download | Pinned public snapshot cached without authentication |
| Chronos CPU offline load | Passed in a separate process with offline mode enabled |
| Chronos CPU offline prediction | Five synthetic steps passed finite/ordered q10/q50/q90 checks |

The successful Chronos host environment resolved `chronos-forecasting 2.3.2`,
`torch 2.15.0`, `transformers 5.22.2`, `accelerate 1.15.0`, `numpy 2.4.6`,
`pandas 3.1.1`, `huggingface_hub 2.4.0`. The optional requirements file pins Chronos
only; this list records this run, not a cross-platform dependency lock. Torch printed
a non-failing macOS multiprocessing-redirection note; single-process CPU inference
completed. The first synthetic forecast row was approximately
`104.378952 / 104.497482 / 104.587585`; all five rows were ordered. These are artificial
series values, not SPY forecasts or forecast-accuracy evidence.

Not tested: Windows/Linux execution, rendered frontend, real market data, rights-approved
public display, real-data Chronos/baseline inference, provider fallback/conformance,
or general intervals/recurrence. No market dataset was downloaded and no paid model
call was made. The optional CPU smoke script is independent of backend runtime.
