from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7일
    upload_dir: str = "uploads"
    verification_dir: str = "verification_uploads"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
