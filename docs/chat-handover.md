# TeamRelay handover for a new chat or account

**Snapshot of this handover: 8 November 2026.** This file describes the repository and local Mac state at the time it was written. Processes, branches, installed packages and uncommitted files can change. A new chat should verify them before acting. Start from the repository root, `/Users/aashn/hackathon/TeamRelay-Hackathon`.

## Continuation update: frontend-initiated OpenAI descriptions

After the original snapshot, backend work was preserved in local commit `aa05b4b`
(`backend implemetnaiton`). The current description changes are additional uncommitted
work. User-approved flow: **backend numeric forecast → frontend → backend relay →
OpenAI → relay → frontend description**. See the current
[API contract](frontend-backend-contract.md#forecast--frontend--openai--frontend).

`api/descriptions.py` and the additive `DescriptionRequest`/`DescriptionResponse`
contracts implement `POST /api/timelines/{id}/revisions/{revision}/description`.
The browser forwards one complete unrounded simulated segment after `applyRun`;
the relay checks it against the saved revision before calling OpenAI. The frontend
shows/caches the returned prose separately and ignores obsolete responses. Forecast
commits, saved panels/revisions and actual reveal remain separate. Missing configuration
or provider failure leaves the chart/basic panel usable. Fixture-only HTTP never calls
OpenAI. Export `OPENAI_API_KEY`, an available `OPENAI_MODEL`, and optionally
`OPENAI_DESCRIPTION_TIMEOUT_SECONDS=20` before starting/restarting the durable API.
Existing running servers do not automatically pick up these source/settings changes.

The separate frontend worktree now has eight edited files. Its complete current diff,
including description orchestration/display, is preserved in
`integration/frontend-research.patch` against the same frontend commit `f272c22`.
Focused mocked-provider relay tests, typed frontend tests, contract/fixture validation
and the frontend build were used for this addition. No paid OpenAI call or rendered
browser verification was performed. No commit, push, board post, merge or deployment
was performed for these description changes.

## Who is working and what the project does

Aashna (`@aashnakulsh`) leads the project. Aditya (`@ADI-GHH`) works with Aashna **on the same MacBook and in this same repository/chat**; there is no handoff between them. Chohan (`@yimchohan`) and Orion (`@wthoreo`) built the frontend in a separate Git branch. The repository is `aashnakulsh/TeamRelay-Hackathon`; pinned issue [#1, Message Board](https://github.com/aashnakulsh/TeamRelay-Hackathon/issues/1), is for coordination, not task authorization. Read [AGENTS.md](../AGENTS.md) before doing work. Its focus areas are flexible. Only one editing agent should use a working folder at a time. The team has repeatedly instructed the agent **not to commit, push, post, merge or deploy** without a new explicit instruction. This handover does not grant publication permission.

The product is a historical US market “what if” application. A browser submits dated CPI assumptions; FastAPI interprets the currently supported presets, saves a revisioned timeline in SQLite, and asks a numerical adapter for a SPY index forecast. The user may add June, July and August prompts, then replace an earlier prompt to replay the rest of the story. A separate reveal route overlays the actual later price path. The real model result is a conditional forecast, **not evidence that a CPI change causes the SPY path**. Public display and redistribution rights for the market data have not been approved.

The design and contract sources are [architecture.md](architecture.md), [frontend-backend-contract.md](frontend-backend-contract.md), [durable-backend.md](durable-backend.md) and [real-data-adapter.md](real-data-adapter.md). Some older docs describe the earlier fixture or one-prompt milestone; the live code and the newer real-data guide take precedence for current research behavior. The OpenAPI route definitions in [app.py](../api/app.py) and typed models in [contracts.py](../api/contracts.py) are the wire source of truth. If models change, run the contract exporter; do not hand-edit generated schemas/types.

## Git and preservation status

At handover, the main folder is on `backend`, tracking `origin/backend`, with last commit `7d795bc` (“Add validated local SPY/CPI data preparation…”). **The latest reveal, real replay, CPI expansion, evaluation, frontend patch and this handover are uncommitted.** They are visible only on this Mac until publication is explicitly authorized. Do not reset, clean, checkout another branch in this folder, or use `git add -A` while preserving this work.

The frontend team’s published branch was fetched as `origin/frontend` at commit `f272c22`. It was checked out in a second Git worktree at `/private/tmp/teamrelay-frontend-integration`, with detached HEAD. Six frontend files were changed there for research integration but remain uncommitted. A copy of their diff is [frontend-research.patch](../integration/frontend-research.patch), in the backend working tree. **`/private/tmp` is temporary storage.** Preserve the patch and review both worktrees before publication or removal. The `backend` branch’s tracked `web/` contains only the earlier typed client/cache and generated types, not the complete React application. The full Vite/React/Plotly application is in the separate frontend worktree/branch. Do not try to start Vite from the backend folder’s `web/`.

Commands to establish the current state:

```sh
pwd
git status --short --branch
git log -1 --oneline
git worktree list
git -C /private/tmp/teamrelay-frontend-integration status --short --branch
bash tools/board inbox
```

The inbox currently contains three old unacknowledged coordination messages: Aashna’s test mention, Aditya’s foundation announcement, and Orion’s architecture notice. They were read, not acknowledged; they do not authorize new work. Do not run `tools/board listen` or an autonomous coding loop just to resume this project.

## How the code is arranged

| Path | Current job |
|---|---|
| `api/contracts.py` | Pydantic HTTP and `ForecastRequest` / `ForecastResult` models. |
| `api/app.py`, `api/settings.py` | FastAPI routes and environment configuration. `APP_MODE=fixture` is the default; `APP_MODE=research` requires an explicit dataset version. |
| `api/durable_service.py`, `api/sqlite_store.py` | Timeline creation, immutable revisions, expiring drafts, idempotent commit receipts and SQLite transactions. Identical commit retries return the saved response before stale/expiry checks; conflicting request-ID reuse fails. |
| `api/preset_parser.py`, `api/replay.py`, `api/research_backend.py` | Deterministic supported prompt parsing; ordered replay; real data/calendar context and research capabilities. June .4, July +.1 percentage point, August carry, then replace June .2 gives .2/.3/.3 while keeping p1/p2/p3. |
| `api/synthetic_forecast.py`, `api/fixture_app.py`, `shared/` | Synthetic fixture path and contract fixtures for frontend development. Synthetic arithmetic is clearly labeled and is not market forecasting. |
| `data/real_market.py` | Audits raw SPY minutes, parses original CPI narratives, checks NYSE sessions, produces versioned Parquet snapshots, and builds frozen numerical requests. Missing closes truncate context; they are not filled. |
| `data/reveal.py` | Reads actual prices only after forecasting. The research reveal route returns actual observations for the requested saved revision and index base. |
| `training/chronos_adapter.py`, `training/baseline.py`, `training/evaluation.py` | Offline CPU Chronos-2; empirical reference/analogue baselines with an eight-window floor; chronological fold preparation and scoring. Forecasting does not import the reveal reader. |
| `tools/prepare_market_data.py`, `tools/real_forecast.py`, `tools/evaluate_market.py` | Rebuild local snapshots; run standalone June forecast/baselines; run optional historical diagnostics. |
| `tools/backend_demo.py`, `tools/research_backend_demo.py`, `tools/frontend_research_check.mjs` | Three-prompt real HTTP journey, June replace/restart check, and full frontend typed-client/cache journey against a running research API. |
| `tests/` | Contract, durability, market-adapter and research HTTP tests. |
| `/private/tmp/teamrelay-frontend-integration/web/` | Complete React/TypeScript/Vite/Plotly UI with locally changed research integration files. |

The API endpoints are `GET /api/capabilities`, `POST /api/timelines`, `GET /api/timelines/{id}`, `GET /api/timelines/{id}/revisions/{n}`, `POST /api/timelines/{id}/interpret`, `POST /api/timelines/{id}/commit`, and `GET /api/timelines/{id}/revisions/{n}/reveal`. The real API does **not** implement the frontend branch’s draft delete endpoint; the local frontend integration hides delete in server mode. Unsupported prompts return typed problems without changing the saved timeline. Forecast points, quantiles and actuals are index levels, not USD prices; CPI `0.2` means **0.2 percent monthly seasonally adjusted CPI-U**, not `0.002`.

## Local data and model state

Everything under `data/local/` is ignored by Git; it must not be staged or pushed. The raw inputs on this Mac are:

- `data/local/raw/hf/SPY_raw_1min.parquet`: 455,875 IEX minute rows, March 7, 2022 to November 6, 2026; timestamps are naive Eastern time, prices split-adjusted, with OHLC, volume and source columns. 2008 is outside its coverage. Audit found 414 missing minutes and a missing last minute on December 23, 2024. Valid closing minutes yield 1,173 daily close proxies; these are not official consolidated closes.
- `data/local/raw/bls/`: four original BLS HTML releases for May 13, June 11, July 15 and August 12, 2025. Parsing uses the first original release narrative and publication time, not later revised tables.
- `data/local/raw/bls-expanded/`: 28 earlier official BLS archive **text captures** obtained through a web reader when the direct BLS downloader received HTTP 403. They span reference months December 2022–March 2025. They are labeled as text captures rather than claimed to be original HTML bytes. Combined with the four HTML files, reference months run consecutively through July 2025. The optional downloader script is `tools/download_cpi_archives.py`; a 403 does not justify inventing missing releases.
- `data/local/raw/nyse/ICE_NYSE_2025_Yearly_Trading_Calendar.pdf`: supplied 2025 exchange calendar. The code cross-checks the XNYS software calendar against its 250 sessions, closures and early closes. Other years have not been manually reconciled to annual NYSE PDFs.

Two versioned snapshots exist. `spy-99baca8c94f5871aff6b` is the original four-release version with 20 known-CPI sessions before the June fork. `spy-8c865e107520d2cdab66` is the expanded version with 114 contiguous pre-fork sessions after the missing December 23 close. `data/local/processed/latest.txt` currently points at the expanded version; **pin a version explicitly for repeatable runs**. Each version has `processed/<version>/manifest.json`, `spy_daily.parquet`, `cpi_releases.parquet`, `sessions.parquet` and `minute_gaps.parquet`; actual prices live separately in `reveal/<version>/spy_actuals.parquet`; standalone/evaluation outputs live in `results/<version>/`. Manifests contain hashes, units, source references, package versions and rights notes. An old `forecast.json` in the original snapshot may contain results from the old `cpu-cpi-v1` model identity. Regenerate it before comparing exact numbers with current `cpu-cpi-v2`; do not overwrite it casually.

The numerical model is `amazon/chronos-2`, `chronos-forecasting==2.3.2`, pinned weight revision `29ec3766d36d6f73f0696f85560a422f50e8498c`, loaded from the existing Hugging Face cache on CPU. The cache is normally under `~/.cache/huggingface/hub/models--amazon--chronos-2/`. The pinned offline load and five-step prediction passed earlier. No cloud account, key, paid model call or Apple-only accelerator is required for current tests. The intended future prompt interpreter is server-side OpenAI, with local Ollama fallback (initially `qwen3.5:9b`); current runtime uses deterministic presets. `ollama list`, `OLLAMA_MODEL=qwen3.5:9b python tools/check_ollama.py` can verify an installed local tag without paid calls. The current adapter does not claim causal effects or calibrated uncertainty.

The four-release baseline has too few eligible windows; the expanded snapshot supports the June reference baseline with 29 windows, and analogue support counts of 10 for the .4 scenario and 15 for the .2 scenario. The optional chronological evaluation attempted 18 monthly publication folds from January 2024 through June 2025. Chronos and reference each scored 17; analogue scored six because other folds lacked eight matches. The missing December 23 close blocks the January 2025 fold’s 20-session context. The observed mean absolute index errors were about 1.60 for Chronos, 1.43 for reference and 1.21 for analogue **on different fold sets**. See `data/local/results/spy-8c865e107520d2cdab66/evaluation.json`; this is a descriptive diagnostic, not a leakage-free backtest or a comparable ranking. Current-vintage adjusted prices and pretrained weights may include later information.

## VS Code terminals: what to run, and what was running

The backend and frontend are **two long-running processes in separate VS Code terminals**. Commands go into the terminal panel (`Terminal` → `New Terminal`), not a Python file or the VS Code editor. Use a third terminal for test/demo commands while the first two stay open. Press `Ctrl+C` in the terminal running a server to stop that server. Environment exports affect only the terminal in which they were run; open terminals do not share them. Start commands from the stated directories. Use one backend worker initially.

**Terminal 1 — real backend, from the repository root:**

```sh
cd /Users/aashn/hackathon/TeamRelay-Hackathon
source .venv/bin/activate
export APP_MODE=research
export DATA_DIR=./data/local
export DATASET_VERSION=spy-99baca8c94f5871aff6b
export SQLITE_PATH=./data/local/teamrelay-research-v2.sqlite
export FORECAST_DEVICE=cpu
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
python -m uvicorn api.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

Use the expanded version in `DATASET_VERSION` when you want longer observed CPI context and supported standalone empirical baselines. Keep the database path stable across restarts for durable timelines. Changing the dataset/model identity prevents writes to old timelines, though old revisions remain readable; make a fresh timeline/database for the new configuration. To run synthetic durable mode, set `APP_MODE=fixture` and omit `DATASET_VERSION`; the independent original fixture app is `python -m uvicorn api.fixture_app:app --host 127.0.0.1 --port 8001 --workers 1`. Open `http://127.0.0.1:8000/docs` only after the backend starts. Its API docs prove route availability, not browser behavior.

**Terminal 2 — complete frontend, from the separate frontend worktree:**

```sh
cd /private/tmp/teamrelay-frontend-integration/web
# If dependencies are missing: npm ci --ignore-scripts
export VITE_API=server
export BACKEND_URL=http://127.0.0.1:8000
npm run dev -- --host 127.0.0.1 --port 5174
```

Open `http://127.0.0.1:5174/` in a normal browser. Vite proxies `/api` requests to `BACKEND_URL`, avoiding a direct cross-origin browser request. This machine previously used a verified temporary Node 24 binary at `/private/tmp/node-v24.11.0-darwin-arm64/bin`; if `node` or `npm` is missing from `PATH`, install a current Node version or prefix the command with `PATH=/private/tmp/node-v24.11.0-darwin-arm64/bin:$PATH`. The frontend’s default is a browser mock; **`VITE_API=server` is required** to exercise the real backend. The local frontend patch separates mock/server timeline storage keys, uses backend prompt limits and presets, handles unsupported/stale reveal responses and hides unsupported deletion.

**Terminal 3 — checks, from the backend repository root:**

```sh
cd /Users/aashn/hackathon/TeamRelay-Hackathon
source .venv/bin/activate
python tools/research_backend_demo.py --receipt data/local/results/research-http-journey.json
python tools/backend_demo.py
node tools/frontend_research_check.mjs /private/tmp/teamrelay-frontend-integration/web http://127.0.0.1:5174
```

The first script exercises June .4 then replacement .2 and stores a restart receipt. After stopping/restarting Terminal 1 with the same database, use `python tools/research_backend_demo.py --restore-from data/local/results/research-http-journey.json`. The second script exercises all three prompts and replacement. The third uses the real frontend API client/cache through Vite, then checks restore, revision history, reveal and unsupported preservation. Each fresh journey creates a new local timeline. If backend port 8000 is occupied, inspect the current server first; either reuse the correct research server or choose a different port and update `BACKEND_URL` plus demo `--base-url`.

At the time of this handover, local `lsof` showed listeners on **8000 (PID 89714)**, **8766 (PID 95487)** and **5174 (PID 94311)**. Port 8766 was started by the previous integration run using the original snapshot and `/private/tmp/teamrelay-integration.sqlite`; Vite at 5174 was started with `BACKEND_URL=http://127.0.0.1:8766`. Port 8000 was already occupied before that integration run; its exact environment was not verified. This tool session could not connect to loopback even though `lsof` saw listeners, so **do not assume any of these servers is reachable or still running in a new chat**. In a normal VS Code terminal, verify with:

```sh
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:8766 -sTCP:LISTEN
lsof -nP -iTCP:5174 -sTCP:LISTEN
curl -fsS http://127.0.0.1:8000/api/capabilities
curl -fsS http://127.0.0.1:8766/api/capabilities
```

Do not kill PID 89714 merely because it occupies 8000; it may be Aashna’s existing server. Stop your own process using `Ctrl+C` in its terminal. `/private/tmp/teamrelay-frontend-integration`, the temporary database, test receipts and the temporary Node binary can disappear after cleanup or reboot; rely on the tracked handover/patch plus the real branch to reconstruct them.

On Windows, replace `source .venv/bin/activate` with `.\.venv\Scripts\Activate.ps1`, use `$env:APP_MODE = 'research'` style assignments, and run the same `python -m uvicorn ...` command. The guide has the full PowerShell example. Windows/Linux execution has not been run on this Mac.

## What has been tested and what remains

The last full local backend run passed **65 Python tests**, contract export, 34 typed fixtures, four Node frontend contract tests in each checkout, and frontend TypeScript/production build. `python -m pip check` found no broken requirements. The real CPU HTTP flow passed June replacement and the complete three-prompt edit. A real process restart preserved the saved snapshots and original idempotent response. Actual reveal via the Vite proxy returned 47 June 11–August 18 exchange sessions with the same index base and did not alter the forecast. The actual frontend client/cache passed its full HTTP journey. The source diff and frontend diff passed whitespace checks; the patch was checked against the frontend worktree in reverse.

The rendered browser journey **was not verified** because the browser-control service was unavailable. Manually open the frontend, submit June .4, add July +.1 and August carry, replace p1 with June .2, then reload, reveal and hide actuals. Verify three prompt markers, .2/.3/.3 resolved values, chart bands, retained history, no delete control in server mode, and an unsupported input leaving the graph unchanged. The new chat may automate this if a browser tool is available. Windows/Linux startup and public demo rights remain unverified. OpenAI/Ollama runtime parsing, broader free-form event families and a real delete API remain unfinished. The UI’s impact/narrative details are only as rich as current research panels; do not claim causal explanations.

Useful checks after any new changes:

```sh
python tools/export_contracts.py --check
python tools/build_example_fixtures.py --check
python tools/check_fixtures.py
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/frontend-contract.test.mjs
cd /private/tmp/teamrelay-frontend-integration/web && npm run build
```

For optional expanded-data work from the backend root:

```sh
python tools/prepare_market_data.py --cpi-directory data/local/raw/bls-expanded
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python tools/real_forecast.py --dataset-version spy-8c865e107520d2cdab66
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python tools/evaluate_market.py --dataset-version spy-8c865e107520d2cdab66
```

Preparation rebuilds/version-checks local ignored outputs and may update `processed/latest.txt`; it does not publish data. These model runs are optional for the fixture suite. If using the frontend checkout’s own tests, run `node --test tests/frontend-contract.test.mjs` from that worktree root.

## Starting a new chat safely

Give the new chat this file, [AGENTS.md](../AGENTS.md), [the real-data guide](real-data-adapter.md), and the repository root path. Tell it that Aashna and Aditya share this Mac and folder; no separate handoff is needed. Ask it to inspect both Git worktrees and any current servers before making changes. The uncommitted backend files and [frontend patch](../integration/frontend-research.patch) are the most important local state to preserve, especially if the new account cannot see this chat or local ignored data. The new account may not have the same filesystem access, cached weights, downloaded datasets, GitHub login or Node/Python environment. If it is running elsewhere, this file alone does **not** transfer the ignored data, model cache, SQLite timelines or detached frontend edits.

No commit, push, issue-board post, merge or deployment was performed for the latest integration. Publication is a separate user decision. Before any authorized publication, review the exact diffs, data rights, frontend branch ownership and whether the separate worktree patch still applies cleanly; stage only intended source/docs/tests. Never upload `data/local/`, SQLite files, credentials, `.venv`, downloaded weights or the NYSE PDF.
