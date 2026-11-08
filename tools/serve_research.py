"""Start the real CPI scenario API with explicit local assets; never print credentials."""
import argparse
import os
from pathlib import Path
import shlex
import sys
from time import time_ns

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def load_provider_env(path):
    """Read only provider settings, without executing shell code or exporting to Vite."""
    allowed = {"OPENAI_API_KEY", "OPENAI_MODEL", "OLLAMA_MODEL", "OLLAMA_BASE_URL",
               "OPENAI_TIMEOUT_SECONDS", "OLLAMA_TIMEOUT_SECONDS", "OPENAI_DESCRIPTION_TIMEOUT_SECONDS",
               "SCENARIO_TIMEOUT_SECONDS"}
    for line in path.read_text().splitlines():
        line = line.strip().removeprefix("export ")
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() in allowed:
            parts = shlex.split(value, comments=True)
            if len(parts) > 1:
                raise ValueError("Quote environment values containing spaces")
            os.environ[name.strip()] = parts[0] if parts else ""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path("data/local"))
    parser.add_argument("--dataset-version", default="spy-8c865e107520d2cdab66")
    parser.add_argument("--database", type=Path, help="Defaults to a NEW file; old timelines are preserved")
    parser.add_argument("--model", help="Override OPENAI_MODEL for this process only")
    parser.add_argument("--parser-provider", choices=["auto", "ollama"], default="auto")
    parser.add_argument("--port", type=int, default=8771)
    args = parser.parse_args()
    if args.env_file:
        load_provider_env(args.env_file)
    if args.model:
        os.environ["OPENAI_MODEL"] = args.model
    os.environ.setdefault("OPENAI_TIMEOUT_SECONDS", "20")
    os.environ.update(APP_MODE="research", PARSER_PROVIDER=args.parser_provider,
                      DATA_DIR=str(args.data_dir.resolve()), DATASET_VERSION=args.dataset_version,
                      SQLITE_PATH=str((args.database or args.data_dir / f"continuous-cpi-{time_ns()}.sqlite").resolve()),
                      FORECAST_DEVICE="cpu", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    if args.parser_provider == "auto" and not all(os.environ.get(k) for k in ("OPENAI_API_KEY", "OPENAI_MODEL")):
        parser.error("OpenAI key/model missing; configure them server-side, or choose --parser-provider ollama")
    from api.app import create_app
    from api.settings import Settings
    import uvicorn
    settings = Settings()
    app = create_app(settings)
    print(f"Research API: http://127.0.0.1:{args.port}; provider={args.parser_provider}; model={settings.openai_model or settings.ollama_model}")
    print(f"Dataset={settings.dataset_version}; database={settings.sqlite_path}; history={len(app.state.backend_service.research.points)} sessions")
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
