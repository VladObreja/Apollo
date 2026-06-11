import logging
from typing import Any

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/apollo"

    # SMTP configuration — defaults match Proton Mail Bridge (localhost:1025)
    smtp_host: str = "127.0.0.1"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from_address: str = "apollo.admin@proton.me"
    asset_email_address: str = "apollo.asset1@proton.me"
    smtp_use_tls: bool = False

    # IMAP configuration — defaults match Proton Mail Bridge (localhost:1143)
    imap_host: str = "127.0.0.1"
    imap_port: int = 1143
    imap_username: str = ""
    imap_password: SecretStr = SecretStr("")
    imap_mailbox: str = "INBOX"
    imap_use_ssl: bool = False

    # Ollama configuration — model MUST be pinned by digest in .env
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_digest: str = ""
    ollama_timeout_seconds: int = 60

    # Asset location — used for Local Sidereal Time computation
    asset_latitude: float = 44.43  # Bucharest, Romania (degrees N)
    asset_longitude: float = 26.10  # Bucharest, Romania (degrees E)

    closure_ceremony_interval_days: int = 7

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", frozen=True
    )

    @field_validator("imap_username", "ollama_model_digest")
    def check_not_empty(cls, v: str, info: Any) -> str:
        if not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v

    def model_post_init(self, __context: Any) -> None:
        if not self.imap_use_ssl:
            logger.warning(
                "apollo.config: IMAP connection is unencrypted (imap_use_ssl=False)",
                extra={"imap_use_ssl": self.imap_use_ssl},
            )


settings = Settings()
