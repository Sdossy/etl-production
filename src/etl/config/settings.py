"""
Loads config/{env}.yaml based on the ETL_ENV environment variable
(defaults to 'dev') and exposes it as a typed Settings object.

Usage:
    from etl.config.settings import get_settings
    settings = get_settings()
    settings.database.path
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class DatabaseSettings:
    path: str
    timeout_seconds: int = 30


@dataclass
class PathSettings:
    raw_data_dir: str
    sample_data_dir: str
    log_dir: str


@dataclass
class LoggingSettings:
    level: str = "INFO"
    log_to_file: bool = True
    log_file: str = "logs/etl.log"


@dataclass
class PipelineSettings:
    batch_size: int = 500
    retry_attempts: int = 3
    retry_backoff_seconds: int = 2


@dataclass
class Settings:
    environment: str
    database: DatabaseSettings
    paths: PathSettings
    logging: LoggingSettings
    pipeline: PipelineSettings


# Repo root is three levels up from this file: src/etl/config/settings.py -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_DIR = _REPO_ROOT / "config"

_settings_cache: "Settings | None" = None


def get_settings(env: str | None = None, force_reload: bool = False) -> Settings:
    """
    Load settings for the given environment. If env is not passed,
    reads the ETL_ENV environment variable, defaulting to 'dev'.
    Cached after first load unless force_reload=True.
    """
    global _settings_cache

    if _settings_cache is not None and not force_reload:
        return _settings_cache

    env = env or os.environ.get("ETL_ENV", "dev")
    config_path = _CONFIG_DIR / f"{env}.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"No config file found for environment '{env}' at {config_path}"
        )

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    _settings_cache = Settings(
        environment=raw["environment"],
        database=DatabaseSettings(**raw["database"]),
        paths=PathSettings(**raw["paths"]),
        logging=LoggingSettings(**raw["logging"]),
        pipeline=PipelineSettings(**raw["pipeline"]),
    )
    return _settings_cache
