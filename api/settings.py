"""Portable server settings. Environment only; no implicit .env loading."""
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    sqlite_path: Path = field(default_factory=lambda: Path(os.environ.get(
        "SQLITE_PATH", "data/local/teamrelay.sqlite")).expanduser())
    draft_ttl_seconds: int = 300
    parser_provider: str = "deterministic"
    ollama_base_url: str = field(default_factory=lambda: os.environ.get(
        "OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    ollama_model: str = field(default_factory=lambda: os.environ.get("OLLAMA_MODEL", "qwen3.5:9b"))
    forecast_device: str = field(default_factory=lambda: os.environ.get("FORECAST_DEVICE", "cpu"))

    def __post_init__(self):
        if self.draft_ttl_seconds <= 0:
            raise ValueError("Draft lifetime must be positive")
