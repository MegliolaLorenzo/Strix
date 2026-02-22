from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    tavily_api_key: str = ""
    gnews_api_key: str = ""

    strix_host: str = "127.0.0.1"
    strix_port: int = 8000
    strix_db_path: str = str(Path(__file__).parent / "strix.db")

    model_config = {
        "env_file": str(Path(__file__).parent.parent / ".env"),
        "extra": "ignore",
    }


settings = Settings()
