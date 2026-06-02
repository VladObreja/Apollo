from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", frozen=True
    )

    @field_validator("imap_username", "ollama_model_digest")
    def check_not_empty(cls, v: str, info) -> str:
        if not v.strip():
            raise ValueError(f"{info.field_name} must not be empty")
        return v


settings = Settings()
