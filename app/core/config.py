from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    database_url: str
    secret_key: str
    default_plan_name: str = "FREE"

    model_config = SettingsConfigDict(
        env_file=".env",
    )


settings = Settings()
