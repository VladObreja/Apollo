from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/apollo"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", frozen=True
    )


settings = Settings()
