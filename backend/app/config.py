from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7일
    upload_dir: str = "uploads"
    verification_dir: str = "verification_uploads"

    # 관리자 시드 전용. 앱 구동에는 필요 없어 기본 None — 없으면 시드가 종료한다
    admin_email: str | None = None
    admin_password: str | None = None

    # 기본 True — Railway에서 환경변수를 빠뜨렸을 때 기능이 조용히 죽는 쪽이 더 나쁘다.
    # 테스트는 conftest.py에서 False로 내린다
    scheduler_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
