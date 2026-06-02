from pydantic import SecretStr
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

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", frozen=True
    )


settings = Settings()
