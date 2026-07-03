from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ACHCM_")

    database_url: str = f"sqlite:///{BASE_DIR / 'achchaosmonkey.db'}"
    ml_artifact_dir: Path = BASE_DIR / "achchaosmonkey" / "ml" / "artifacts"
    export_dir: Path = BASE_DIR / "data" / "exports"
    default_chaos_level: str = "none"


settings = Settings()
settings.ml_artifact_dir.mkdir(parents=True, exist_ok=True)
settings.export_dir.mkdir(parents=True, exist_ok=True)
