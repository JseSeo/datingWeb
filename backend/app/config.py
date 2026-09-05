from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7일
    upload_dir: str = "uploads"
    verification_dir: str = "verification_uploads"

    # 기본 True — Railway에서 환경변수를 빠뜨렸을 때 기능이 조용히 죽는 쪽이 더 나쁘다.
    # 테스트는 conftest.py에서 False로 내린다
    scheduler_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
