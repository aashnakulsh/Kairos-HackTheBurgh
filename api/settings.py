"""Portable server settings. Environment only; no implicit .env loading."""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    sqlite_path: Path | None = field(default_factory=lambda: Path(os.environ["SQLITE_PATH"]).expanduser()
                                   if os.environ.get("SQLITE_PATH") else None)
    app_mode: str = field(default_factory=lambda: os.environ.get("APP_MODE", "fixture"))
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("DATA_DIR", "data/local")).expanduser())
    dataset_version: str | None = field(default_factory=lambda: os.environ.get("DATASET_VERSION") or None)
    draft_ttl_seconds: int = 300
    parser_provider: str = "deterministic"
    ollama_base_url: str = field(default_factory=lambda: os.environ.get(
        "OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    ollama_model: str = field(default_factory=lambda: os.environ.get("OLLAMA_MODEL", "qwen3.5:9b"))
    forecast_device: str = field(default_factory=lambda: os.environ.get("FORECAST_DEVICE", "cpu"))
    openai_api_key: str = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""), repr=False)
    openai_model: str = field(default_factory=lambda: os.environ.get("OPENAI_MODEL", ""))
    description_timeout_seconds: float = field(default_factory=lambda: float(os.environ.get(
        "OPENAI_DESCRIPTION_TIMEOUT_SECONDS", "20")))

    def __post_init__(self):
        object.__setattr__(self, "data_dir", Path(self.data_dir).expanduser())
        database = self.sqlite_path if self.sqlite_path is not None else self.data_dir / (
            "teamrelay-research.sqlite" if self.app_mode == "research" else "teamrelay.sqlite")
        object.__setattr__(self, "sqlite_path", Path(database).expanduser())
        if self.draft_ttl_seconds <= 0:
            raise ValueError("Draft lifetime must be positive")
        if not 0 < self.description_timeout_seconds <= 120:
            raise ValueError("Description timeout must be between zero and 120 seconds")
        if self.app_mode not in {"fixture", "research"}:
            raise ValueError("APP_MODE must be fixture or research")
        if self.app_mode == "research":
            if not self.dataset_version or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", self.dataset_version):
                raise ValueError("Research mode requires an explicit DATASET_VERSION snapshot name")
            if self.forecast_device != "cpu":
                raise ValueError("Research mode currently requires FORECAST_DEVICE=cpu")
