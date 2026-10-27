from __future__ import annotations

import os
import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_project_root() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8765
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = ""

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    MSGRAPH_CLIENT_ID: str = ""
    MSGRAPH_TENANT_ID: str = ""
    MSGRAPH_REDIRECT_URI: str = "http://localhost:8765/api/v1/auth/msgraph/callback"

    CAPTCHA_PROVIDER: str = "capsolver"
    CAPSOLVER_API_KEY: str = ""
    ANTICAPTCHA_API_KEY: str = ""
    TWOCAPTCHA_API_KEY: str = ""
    EZCAPTCHA_API_KEY: str = ""

    SMS_PROVIDER_API_KEY: str = ""
    SMS_PROVIDER_BASE_URL: str = ""
    SMS_PROVIDER_NAME: str = "generic"

    CAPTCHA_SOLVE_ENABLED: bool = False
    MOCK_MODE: bool = False

    BROWSER_HEADLESS: bool = True
    BROWSER_TIMEOUT_MS: int = 30000
    PROXY_URL: str = ""

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    MAX_WORKER_COUNT: int = 10
    MAX_QUEUE_SIZE: int = 1000
    JOB_TIMEOUT_SECONDS: int = 300
    MAX_RETRIES: int = 3
    IMPORT_MAX_ROWS: int = 10000
    IMPORT_MAX_FILE_BYTES: int = 10 * 1024 * 1024
    BACKUP_RETENTION_DAYS: int = 30

    def get_secret_key(self) -> str:
        if self.APP_SECRET_KEY:
            return self.APP_SECRET_KEY
        key_path = _project_root() / "data" / "secret.key"
        if key_path.exists():
            return key_path.read_text(encoding="utf-8").strip()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key = secrets.token_urlsafe(64)
        key_path.write_text(key, encoding="utf-8")
        os.chmod(str(key_path), 0o600)
        return key

    def get_db_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("sqlite"):
            db_path = url.split("///")[-1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return url


settings = Settings()
