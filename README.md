# TeamRelay-Hackathon

Human-directed coding with a shared GitHub issue and a notification-only listener.

Board: https://github.com/aashnakulsh/TeamRelay-Hackathon/issues/1

1. Read AGENTS.md. Choose your task with your human.
2. In a separate Bash terminal, run `bash tools/board listen` (60-second polling).
3. In your coding agent, ask it to read `bash tools/board inbox` and summarize requests.
4. Decide what to implement, then use an issue branch and PR.
5. After handling a message, archive its local copy with `bash tools/board ack COMMENT_ID`.

The listener never codes, invokes an LLM, posts, commits, pushes or merges. It writes only ignored local notification files. It does not inject messages into an idle Codex extension. Claude hooks can surface the local inbox when a human sends a prompt. Keep normal permission checks enabled.

Flexible roles and focus areas are in AGENTS.md. The selected React/TypeScript/Vite,
Plotly, FastAPI, SQLite and Parquet design is in [architecture.md](docs/architecture.md).

## API handoff and fixture development

Read [the canonical contract](docs/frontend-backend-contract.md) and
[review results](docs/api-handoff-review.md). The local API is a synthetic in-memory
fixture service, not the live backend. No provider keys or model downloads are needed.

```sh
python -m pip install -r requirements-contracts.txt
python tools/export_contracts.py --check
python tools/build_example_fixtures.py --check
python tools/check_fixtures.py
python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/frontend-contract.test.mjs
python -m uvicorn api.fixture_app:app --host 127.0.0.1 --port 8000
```

Use Python 3.10+ and Node 22.18+. Open http://127.0.0.1:8000/docs for the fixture API.
The React UI, durable backend and live provider adapters still need implementation.
